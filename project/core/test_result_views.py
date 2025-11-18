# test_result_views.py
# 測驗結果管理相關視圖

import logging
import json
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.utils.text import slugify
from .models import (
    TestInvitation, TestProjectResult, 
    TestProject, TestInvitee
)
from utils.crawler_service import PITestResultCrawler
from utils.pdf_report_generator import generate_test_result_pdf
from utils.radar_calculations import compute_role_based_scores
from .services.test_result_listing import build_test_result_listing, ListingOptions

logger = logging.getLogger(__name__)

# ===== 權限裝飾器 =====
def enterprise_required(view_func):
    """企業用戶權限裝飾器"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.user_type not in ['enterprise', 'admin']:
            messages.error(request, '此功能僅限企業用戶或管理員使用')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    """管理員權限裝飾器"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_staff and request.user.user_type != 'admin':
            messages.error(request, '此功能僅限管理員使用')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

# ===== 測驗結果管理視圖 =====

@login_required
@enterprise_required
def test_result_list(request):
    """測驗結果管理列表頁面"""
    user = request.user
    
    # 根據用戶類型決定查詢範圍
    if user.user_type == 'admin':
        invitations = TestInvitation.objects.select_related(
            'invitee', 'test_project', 'testprojectresult'
        )
    else:
        invitations = TestInvitation.objects.filter(
            enterprise=user
        ).select_related(
            'invitee', 'test_project', 'testprojectresult'
        )
    
    listing_context = build_test_result_listing(
        request,
        invitations,
        options=ListingOptions(
            user=user,
            per_page=50,
            allow_project_filter=True,
        ),
    )
    page_obj = listing_context['page_obj']
    
    # 統計數據
    if user.user_type == 'admin':
        all_invitations = TestInvitation.objects.all()
    else:
        all_invitations = TestInvitation.objects.filter(enterprise=user)
    
    stats = {
        'total_invitations': all_invitations.count(),
        'completed_invitations': all_invitations.filter(status='completed').count(),
        'crawlable_invitations': all_invitations.filter(
            status='completed',
            testprojectresult__isnull=True
        ).count(),
        'crawled_results': TestProjectResult.objects.filter(
            test_invitation__in=all_invitations
        ).count(),
    }
    
    # 狀態選項
    status_choices = TestInvitation.STATUS_CHOICES
    
    if user.user_type == 'admin':
        project_choices = TestProject.objects.filter(
            testinvitation__test_project__isnull=False
        ).distinct().order_by('name')
        position_choices = TestInvitee.objects.exclude(
            position=''
        ).order_by('position').values_list('position', flat=True).distinct()
    else:
        project_choices = TestProject.objects.filter(
            testinvitation__enterprise=user,
            testinvitation__test_project__isnull=False
        ).distinct().order_by('name')
        position_choices = TestInvitee.objects.filter(
            enterprise=user
        ).exclude(position='').order_by('position').values_list('position', flat=True).distinct()

    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params = query_params.copy()
        query_params.pop('page')

    context = {
        **listing_context,
        'stats': stats,
        'lock_project_filter': False,
    }
    
    return render(request, 'test_management/test_result_list.html', context)

@login_required
@enterprise_required
@require_POST
def start_crawling(request, invitation_id):
    """啟動爬蟲作業"""
    user = request.user
    
    # 權限檢查
    if user.user_type == 'admin':
        invitation = get_object_or_404(TestInvitation, id=invitation_id)
    else:
        invitation = get_object_or_404(TestInvitation, id=invitation_id, enterprise=user)
    
    test_result = None  # 初始化變數
    try:
        # 檢查邀請狀態
        if invitation.status == 'pending':
            return JsonResponse({
                'success': False,
                'error': '受測者尚未開始測驗，請等待受測者點擊邀請連結開始測驗'
            })
        elif invitation.status == 'in_progress':
            return JsonResponse({
                'success': False,
                'error': '測驗正在進行中，請等待受測者完成測驗後再取得結果'
            })
        elif invitation.status == 'expired':
            return JsonResponse({
                'success': False,
                'error': '測驗邀請已過期，無法取得結果'
            })
        elif invitation.status == 'cancelled':
            return JsonResponse({
                'success': False,
                'error': '測驗邀請已取消，無法取得結果'
            })
        elif invitation.status != 'completed':
            return JsonResponse({
                'success': False,
                'error': f'測驗狀態為「{invitation.get_status_display()}」，只有已完成的測驗才能取得結果'
            })
        
        # 檢查是否已經爬取過 (暫時忽略此檢查以便測試)
        existing_result = TestProjectResult.objects.filter(
            test_invitation=invitation
        ).first()
        
        # 暫時註解掉重複檢查，允許重複爬取進行測試
        # if existing_result:
        #     return JsonResponse({
        #         'success': False,
        #         'error': '此測驗結果已經爬取過了'
        #     })
        
        # 如果已存在結果，先刪除舊的以便重新爬取
        if existing_result:
            existing_result.delete()
        
        # 更新爬蟲狀態為進行中
        test_result = TestProjectResult.objects.create(
            test_invitation=invitation,
            test_project=invitation.test_project,
            crawl_status='crawling'
        )
        
        # 啟動爬蟲（這裡是同步處理，未來可改為異步）
        try:
            crawler = PITestResultCrawler()
            result = crawler.crawl_test_result(invitation_id)
            
            return JsonResponse({
                'success': True,
                'message': '測驗結果爬取完成！',
                'result_id': result.id if result else None
            })
        except Exception as crawler_error:
            # 爬蟲失敗，更新狀態
            if test_result:
                test_result.crawl_status = 'failed'
                test_result.save()
            raise crawler_error
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"爬蟲作業失敗：{error_message}")
        
        # 如果 test_result 已創建，更新其狀態為失敗
        if test_result:
            test_result.crawl_status = 'failed'
            test_result.save()
        
        # 根據錯誤類型提供更友善的訊息
        if '應用職位篩選失敗' in error_message:
            return JsonResponse({
                'success': False,
                'error': '無法找到對應的測驗結果，可能原因：\n1. 受測者尚未完成測驗\n2. 測驗結果尚未生成\n3. 受測者信箱或職位設定有誤\n請確認受測者已完成測驗後再試'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'系統處理失敗：{error_message}\n請稍後重試，如問題持續發生請聯繫技術支援'
            })

@login_required
@require_POST
def force_recrawl_invitation(request, invitation_id):
    """管理員強制重新爬取測驗結果"""
    from core.tasks import force_recrawl_test_result
    
    try:
        # 權限檢查
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': '請先登入'
            }, status=401)
        
        if not (request.user.is_staff or request.user.user_type == 'admin'):
            logger.warning(f"非管理員用戶 {request.user.username} (類型: {request.user.user_type}) 嘗試執行強制重新爬取")
            return JsonResponse({
                'success': False,
                'error': '此功能僅限管理員使用'
            }, status=403)
        
        # 檢查邀請是否存在
        invitation = get_object_or_404(TestInvitation, id=invitation_id)
        
        logger.info(f"管理員 {request.user.username} (類型: {request.user.user_type}) 發起強制重新爬取，邀請ID: {invitation_id}")
        
        # 嘗試異步任務，如果失敗則使用同步方式
        try:
            # 啟動異步任務進行強制重新爬取
            task = force_recrawl_test_result.delay(invitation_id)
            
            return JsonResponse({
                'success': True,
                'message': '已啟動強制重新爬取任務 (異步)',
                'task_id': task.id
            })
            
        except Exception as celery_error:
            logger.warning(f"Celery 異步任務啟動失敗，轉為同步執行: {str(celery_error)}")
            
            # 如果 Celery 不可用，直接同步執行
            try:
                result = force_recrawl_test_result(invitation_id)
                
                if result.get('success'):
                    return JsonResponse({
                        'success': True,
                        'message': '強制重新爬取完成 (同步)',
                        'result_id': result.get('result_id')
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': result.get('error', '同步執行失敗')
                    })
                    
            except Exception as sync_error:
                logger.error(f"同步執行也失敗: {str(sync_error)}")
                return JsonResponse({
                    'success': False,
                    'error': f'強制重新爬取失敗: {str(sync_error)}'
                })
        
    except Exception as e:
        logger.error(f"啟動強制重新爬取失敗：{str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'啟動強制重新爬取失敗：{str(e)}'
        })

@login_required
@enterprise_required 
def test_result_detail(request, result_id):
    """測驗結果詳情"""
    user = request.user
    
    # 權限檢查
    if user.user_type == 'admin':
        result = get_object_or_404(TestProjectResult, id=result_id)
    else:
        result = get_object_or_404(
            TestProjectResult, 
            id=result_id, 
            test_invitation__enterprise=user
        )
    
    # 處理原始數據，將key名稱格式化
    formatted_raw_data = {}
    if result.raw_data:
        # 排除不需要在表格中顯示的項目
        exclude_keys = ['details', 'vehicles', 'vehicles_percentage', 'composite_index']
        for key, value in result.raw_data.items():
            if (key not in exclude_keys and 
                isinstance(value, (int, float)) and 
                0 <= value <= 100):
                formatted_key = key.replace('_', ' ').title()
                formatted_raw_data[formatted_key] = value
    
    # 計算分類分數和準備雷達圖數據
    category_scores = {}
    category_traits = {}
    category_labels = []
    category_values = []

    print(f"[DEBUG] Raw data keys: {list(result.raw_data.keys()) if result.raw_data else 'No raw data'}")
    logger.info(f"Raw data keys: {list(result.raw_data.keys()) if result.raw_data else 'No raw data'}")

    role_based_metrics = None
    mixed_roles = None

    if result.raw_data and result.test_project:
        radar_mode = getattr(result.test_project, 'radar_mode', 'role')
        use_weighted = radar_mode == 'score'
        show_mixed_role = getattr(result.test_project, 'show_mixed_role', False)

        matched_raw_keys = set()

        def resolve_trait_score(trait):
            trait_score = None
            trait_scores_data = result.raw_data.get('trait_scores') if isinstance(result.raw_data, dict) else None
            if isinstance(trait_scores_data, dict):
                for key, value in trait_scores_data.items():
                    value_dict = value if isinstance(value, dict) else None
                    candidate_score = (
                        value_dict.get('score') if value_dict and isinstance(value_dict.get('score'), (int, float))
                        else value if isinstance(value, (int, float)) else None
                    )
                    if candidate_score is None:
                        continue
                    key_normalized = key.lower().replace(' ', '_')
                    if (
                        key == trait.system_name
                        or key == trait.chinese_name
                        or key_normalized == (trait.system_name or '').lower().replace(' ', '_')
                    ):
                        trait_score = float(candidate_score)
                        matched_raw_keys.add(key)
                        break

            if trait_score is None and isinstance(result.raw_data, dict):
                direct_keys = [
                    trait.system_name,
                    trait.chinese_name,
                    (trait.system_name or '').lower().replace(' ', '_'),
                ]
                for key in direct_keys:
                    if not key:
                        continue
                    value = result.raw_data.get(key)
                    if isinstance(value, (int, float)):
                        trait_score = float(value)
                        matched_raw_keys.add(key)
                        break
                    if isinstance(value, dict) and isinstance(value.get('score'), (int, float)):
                        trait_score = float(value['score'])
                        matched_raw_keys.add(key)
                        break
            return trait_score

        categories = result.test_project.categories.prefetch_related('category_traits__trait', 'traits').all()
        category_map = {category.name: category for category in categories}
        role_inputs = {}
        debug_project_traits = {}

        for category in categories:
            category_trait_list = []
            trait_score_map = {}

            for trait in category.traits.all():
                score = resolve_trait_score(trait)
                if isinstance(score, (int, float)):
                    trait_score_map[trait.id] = score
                    category_trait_list.append({
                        'name': trait.chinese_name,
                        'score': score,
                        'system_name': trait.system_name
                    })

            if not trait_score_map:
                matched_ids = set()
            else:
                matched_ids = set(trait_score_map.keys())

            debug_traits_entries = []
            has_missing_trait = False
            for relation in category.category_traits.select_related('trait').all():
                trait = relation.trait
                if not trait:
                    continue
                trait_score = float(trait_score_map[trait.id]) if trait.id in trait_score_map else None
                matched = trait.id in matched_ids
                if not matched:
                    has_missing_trait = True
                debug_traits_entries.append({
                    'trait_id': trait.id,
                    'system_name': trait.system_name,
                    'chinese_name': trait.chinese_name,
                    'weight': float(relation.weight or 0),
                    'matched': matched,
                    'score': trait_score,
                })
            debug_project_traits[category.name] = {
                'traits': debug_traits_entries,
                'included': bool(trait_score_map),
                'has_missing': has_missing_trait or not trait_score_map,
            }

            if not trait_score_map:
                continue

            raw_score = Decimal('0')
            weight_sum = Decimal('0')
            for relation in category.category_traits.select_related('trait').all():
                trait = relation.trait
                if not trait or trait.id not in trait_score_map:
                    continue
                try:
                    weight = Decimal(str(relation.weight))
                except (InvalidOperation, TypeError, ValueError):
                    continue
                score_value = Decimal(str(trait_score_map[trait.id]))
                raw_score += score_value * weight
                weight_sum += weight

            max_score = weight_sum * Decimal('100')
            role_index = Decimal('0')
            if max_score != 0:
                role_index = (raw_score / max_score) * Decimal('100')

            role_inputs[category.name] = {
                'raw_score': float(raw_score),
                'max_score': float(max_score),
                'role_index': float(role_index),
                'weight_sum': float(weight_sum),
            }
            category_traits[category.name] = category_trait_list
        if role_inputs:
            role_based_metrics = compute_role_based_scores(
                role_inputs,
                show_mixed_role=show_mixed_role,
            )
            if use_weighted:
                category_scores = {
                    name: max(0.0, min(100.0, role_based_metrics["role_index"].get(name, 0.0)))
                    for name in role_based_metrics["role_index"]
                }
                mixed_roles = None
            else:
                category_scores = role_based_metrics["contrast_index"]
                mixed_roles = role_based_metrics["mixed_roles"]
            category_labels = list(category_scores.keys())
            category_values = [category_scores[label] for label in category_labels]

        mixed_role_categories = []
        mixed_role_sentence = None
        if mixed_roles:
            for role_name in mixed_roles:
                category_obj = category_map.get(role_name)
                if category_obj:
                    mixed_role_categories.append(category_obj)
            if mixed_role_categories:
                quoted_names = [f'”{category.name}”' for category in mixed_role_categories]
                names_text = '、'.join(quoted_names)
                mixed_role_sentence = f'兼具{names_text}的特點，具備不同角色發展適性，亦可做為跨角色溝通橋樑'
    else:
        mixed_role_categories = []
        mixed_role_sentence = None
        category_labels = []
        category_values = []

    print(f"[DEBUG] Final category_scores: {category_scores}")
    print(f"[DEBUG] category_scores bool: {bool(category_scores)}")
    if role_based_metrics:
        print(f"[DEBUG] Role-based metrics: {role_based_metrics}")
    logger.info(f"Final category_scores: {category_scores}")
    if role_based_metrics:
        logger.info(f"Role-based metrics: {role_based_metrics}")

    # 處理關鍵特質分數 - 從 trait_results 中選擇前10個高分特質
    key_traits = {}
    if result.trait_results:
        # 將特質按分數排序並取前10個
        sorted_traits = []
        for trait_name, trait_data in result.trait_results.items():
            if isinstance(trait_data, dict) and 'score' in trait_data:
                sorted_traits.append((trait_name, trait_data))
        
        # 按分數降序排序
        sorted_traits.sort(key=lambda x: x[1].get('score', 0), reverse=True)
        
        # 取前10個
        for trait_name, trait_data in sorted_traits[:10]:
            key_traits[trait_name] = trait_data

    debug_raw_traits = []
    if isinstance(result.raw_data, dict):
        trait_scores_data = result.raw_data.get('trait_scores')
        if isinstance(trait_scores_data, dict):
            for trait_key, trait_value in trait_scores_data.items():
                if isinstance(trait_value, dict):
                    debug_raw_traits.append({
                        'key': trait_key,
                        'chinese_name': trait_value.get('chinese_name', ''),
                        'score': trait_value.get('score'),
                        'matched': trait_key in matched_raw_keys or trait_value.get('chinese_name', '') in matched_raw_keys,
                    })
                else:
                    debug_raw_traits.append({
                        'key': trait_key,
                        'chinese_name': '',
                        'score': trait_value,
                        'matched': trait_key in matched_raw_keys,
                    })

    debug_summary_json = ''
    show_debug = request.GET.get('debug') == '1'
    if show_debug:
        debug_summary = {
            'categories': [],
            'raw_traits': debug_raw_traits,
        }
        for category_name, info in debug_project_traits.items():
            summary_entry = {
                'category': category_name,
                'included': info.get('included', False),
                'has_missing': info.get('has_missing', False),
                'traits': [],
            }
            for trait in info.get('traits', []):
                summary_entry['traits'].append({
                    'system_name': trait.get('system_name'),
                    'chinese_name': trait.get('chinese_name'),
                    'weight': trait.get('weight'),
                    'score': trait.get('score'),
                    'matched': trait.get('matched'),
                })
            debug_summary['categories'].append(summary_entry)

        debug_summary_json = json.dumps(debug_summary, ensure_ascii=False, indent=2)

    has_debug_data = show_debug and (
        bool(debug_project_traits) or bool(debug_raw_traits) or bool(debug_summary_json)
    )
    
    # 將數據轉換為JSON格式供前端使用
    category_labels_json = json.dumps(category_labels)
    category_values_json = json.dumps(category_values)
    
    # Debug: 輸出最終結果
    print(f"[DEBUG] Final category_scores: {category_scores}")
    print(f"[DEBUG] Final category_labels: {category_labels}")
    print(f"[DEBUG] Final category_values: {category_values}")
    print(f"[DEBUG] category_scores bool: {bool(category_scores)}")
    logger.info(f"Final category_scores: {category_scores}")
    logger.info(f"Final category_labels: {category_labels}")
    logger.info(f"Final category_values: {category_values}")
    if role_based_metrics:
        logger.info(f"Role-based metrics: {role_based_metrics}")
    
    context = {
        'result': result,
        'is_admin': user.user_type == 'admin',
        'formatted_raw_data': formatted_raw_data,
        'category_scores': category_scores,
        'category_traits': category_traits,
        'category_labels': category_labels_json,
        'category_values': category_values_json,
        'key_traits': key_traits,  # 添加關鍵特質數據
        'mixed_roles': mixed_roles,
        'role_based_metrics': role_based_metrics,
        'mixed_role_categories': mixed_role_categories,
        'mixed_role_sentence': mixed_role_sentence,
        'debug_project_traits': debug_project_traits if show_debug else {},
        'debug_raw_traits': debug_raw_traits if show_debug else [],
        'debug_summary_json': debug_summary_json,
        'show_debug': show_debug,
        'has_debug_data': has_debug_data,
    }

    return render(request, 'test_management/test_result_detail.html', context)

@login_required
@admin_required
def view_raw_data(request, result_id):
    """管理員查看爬蟲原始數據"""
    result = get_object_or_404(TestProjectResult, id=result_id)
    
    # 準備要顯示的數據
    basic_info = {
        '受測者姓名': result.test_invitation.invitee.name,
        '受測者Email': result.test_invitation.invitee.email,
        '測驗項目': result.test_project.name,
        '爬取時間': result.crawled_at.isoformat() if result.crawled_at else None,
        '爬取狀態': result.get_crawl_status_display(),
    }
    
    # 將數據轉換為JSON字符串
    import json
    basic_info_json = json.dumps(basic_info, ensure_ascii=False, indent=2)
    raw_data_json = json.dumps(result.raw_data, ensure_ascii=False, indent=2) if result.raw_data else None
    category_results_json = json.dumps(result.category_results, ensure_ascii=False, indent=2) if result.category_results else None
    trait_results_json = json.dumps(result.trait_results, ensure_ascii=False, indent=2) if result.trait_results else None
    
    context = {
        'result': result,
        'basic_info_json': basic_info_json,
        'raw_data_json': raw_data_json,
        'category_results_json': category_results_json,
        'trait_results_json': trait_results_json,
        'result_id': result_id,
    }
    
    return render(request, 'test_management/raw_data_view.html', context)
@login_required
@enterprise_required
def export_filtered_test_results(request):
    """匯出目前過濾的測驗結果為 CSV"""
    import csv
    from django.utils.encoding import smart_str
    from django.http import HttpResponse

    user = request.user

    if user.user_type == 'admin':
        invitations = TestInvitation.objects.select_related('invitee', 'test_project', 'testprojectresult')
    else:
        invitations = TestInvitation.objects.filter(enterprise=user).select_related('invitee', 'test_project', 'testprojectresult')

    search = request.GET.get('search', '').strip()
    if search:
        invitations = invitations.filter(
            Q(invitee__name__icontains=search) |
            Q(invitee__email__icontains=search)
        )

    project_id = request.GET.get('project', '')
    if project_id:
        invitations = invitations.filter(test_project__id=project_id)

    identity_filter = request.GET.get('identity', '')
    if identity_filter:
        invitations = invitations.filter(invitee__status=identity_filter)

    position_filter = request.GET.get('position', '')
    if position_filter:
        invitations = invitations.filter(invitee__position=position_filter)

    status = request.GET.get('status', '')
    if status:
        invitations = invitations.filter(status=status)

    crawl_status = request.GET.get('crawl_status', '')
    if crawl_status == 'pending':
        invitations = invitations.filter(
            Q(testprojectresult__isnull=True) |
            Q(testprojectresult__crawl_status='pending')
        )
    elif crawl_status in ['crawling', 'completed', 'failed']:
        invitations = invitations.filter(testprojectresult__crawl_status=crawl_status)

    invitations = invitations.annotate(
        effective_score=Coalesce(
            'score',
            'testprojectresult__score_value',
            Value(0.0),
            output_field=FloatField()
        )
    )

    order_option = request.GET.get('order', 'completion_desc')
    if order_option == 'completion_asc':
        invitations = invitations.order_by(
            F('completed_at').asc(nulls_last=True),
            '-invited_at'
        )
    elif order_option == 'score_desc':
        invitations = invitations.order_by(
            F('effective_score').desc(),
            F('completed_at').desc(nulls_last=True)
        )
    elif order_option == 'score_asc':
        invitations = invitations.order_by(
            F('effective_score').asc(),
            F('completed_at').asc(nulls_last=True)
        )
    else:
        invitations = invitations.order_by(
            F('completed_at').desc(nulls_last=True),
            '-invited_at'
        )

    response = HttpResponse(content_type='text/csv')
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')

    if user.user_type == 'enterprise':
        company_name = getattr(getattr(user, 'enterprise_profile', None), 'company_name', None)
    else:
        first_invitation = invitations.first()
        company_name = None
        if first_invitation and first_invitation.enterprise:
            company_profile = getattr(getattr(first_invitation.enterprise, 'enterprise_profile', None), 'company_name', None)
            company_name = company_profile or first_invitation.enterprise.username

    if not company_name:
        company_name = 'test_results'

    safe_ascii = slugify(company_name, allow_unicode=False)
    if not safe_ascii:
        safe_ascii = 'test_results'
    ascii_filename = f'{safe_ascii}_{timestamp}.csv'

    from urllib.parse import quote
    utf8_filename = f'{company_name}_{timestamp}.csv'
    quoted_utf8 = quote(utf8_filename)

    response['Content-Disposition'] = (
        f"attachment; filename={ascii_filename}; filename*=UTF-8''{quoted_utf8}"
    )

    writer = csv.writer(response)
    writer.writerow([
        smart_str('評鑑別'),
        smart_str('受試者名字'),
        smart_str('電子郵件'),
        smart_str('身份別'),
        smart_str('CI分數'),
        smart_str('預測值分數'),
    ])

    for invitation in invitations:
        project_name = invitation.test_project.name if invitation.test_project else ''
        name = invitation.invitee.name
        email = invitation.invitee.email
        identity = invitation.invitee.get_status_display()

        result = getattr(invitation, 'testprojectresult', None)
        ci_score = ''
        prediction_score = ''

        if result and result.crawl_status == 'completed':
            raw = result.raw_data or {}
            metrics = raw.get('performance_metrics', {})

            ci_score = metrics.get('CI_Raw_Value')
            if not ci_score:
                score_field = getattr(invitation.test_project, 'score_field_system', None)
                if score_field:
                    ci_score = metrics.get(score_field) or raw.get(score_field)

            prediction_field = getattr(invitation.test_project, 'prediction_field_system', None)
            if prediction_field:
                prediction_score = metrics.get(prediction_field) or raw.get(prediction_field) or ''

        writer.writerow([
            smart_str(project_name),
            smart_str(name),
            smart_str(email),
            smart_str(identity),
            smart_str(ci_score if ci_score is not None else ''),
            smart_str(prediction_score if prediction_score is not None else ''),
        ])

    return response
def export_test_result(request, result_id):
    """匯出測驗結果"""
    user = request.user
    
    # 權限檢查
    if user.user_type == 'admin':
        result = get_object_or_404(TestProjectResult, id=result_id)
    else:
        result = get_object_or_404(
            TestProjectResult, 
            id=result_id, 
            test_invitation__enterprise=user
        )
    
    # 準備匯出數據
    export_data = {
        'basic_info': {
            'invitee_name': result.test_invitation.invitee.name,
            'invitee_email': result.test_invitation.invitee.email,
            'test_project': result.test_project.name,
            'crawled_at': result.crawled_at.isoformat() if result.crawled_at else None,
        },
        'performance_metrics': {
            'score_field': result.test_project.score_field_chinese,
            'score_value': result.score_value,
            'prediction_field': result.test_project.prediction_field_chinese,
            'prediction_value': result.prediction_value,
        },
        'category_results': result.category_results,
        'trait_results': result.trait_results,
        'raw_data': result.raw_data,
    }
    
    # 生成 PDF 報告 (替代原本的 JSON 下載)
    try:
        from utils.pdf_report_generator import generate_test_result_pdf
        logger.info(f"正在為結果ID {result_id} 生成PDF報告...")
        
        # 直接生成PDF報告
        response = generate_test_result_pdf(result)
        logger.info(f"✅ PDF報告生成成功")
        
        return response
        
    except Exception as e:
        logger.error(f"PDF報告生成失敗: {str(e)}", exc_info=True)
        # 如果PDF生成失敗，回退到JSON下載
        response = JsonResponse(export_data, json_dumps_params={'ensure_ascii': False, 'indent': 2})
        response['Content-Disposition'] = f'attachment; filename="test_result_{result.id}.json"'
        return response

@login_required
@enterprise_required
def generate_test_result_pdf_report(request, result_id):
    """生成測驗結果 PDF 報告"""
    user = request.user
    
    # 權限檢查
    if user.user_type == 'admin':
        result = get_object_or_404(TestProjectResult, id=result_id)
    else:
        result = get_object_or_404(
            TestProjectResult, 
            id=result_id, 
            test_invitation__enterprise=user
        )
    
    # 詳細調試信息
    logger.info(f"開始生成PDF報告，結果ID: {result_id}")
    logger.info(f"用戶: {user.username}, 用戶類型: {user.user_type}")
    logger.info(f"測驗結果: {result}")
    logger.info(f"測驗項目: {result.test_project.name}")
    
    try:
        # 檢查是否已安裝reportlab
        try:
            import reportlab
            logger.info(f"✅ reportlab 已安裝，版本: {reportlab.Version}")
        except ImportError as e:
            logger.error(f"❌ reportlab 未安裝: {e}")
            return JsonResponse({
                'error': 'PDF 生成套件未安裝',
                'details': str(e)
            }, status=500)
        
        # 生成 PDF 報告
        logger.info("正在調用 generate_test_result_pdf...")
        response = generate_test_result_pdf(result)
        logger.info(f"✅ PDF 生成成功，響應類型: {type(response)}")
        
        if hasattr(response, 'status_code'):
            logger.info(f"響應狀態碼: {response.status_code}")
        if hasattr(response, 'content'):
            logger.info(f"響應內容長度: {len(response.content)} 字節")
            
        return response
        
    except ImportError as e:
        error_msg = f'PDF 生成套件問題: {str(e)}'
        logger.error(error_msg)
        return JsonResponse({
            'error': error_msg,
            'type': 'ImportError'
        }, status=500)
    except Exception as e:
        error_msg = f"PDF 生成失敗: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return JsonResponse({
            'error': error_msg,
            'type': type(e).__name__,
            'traceback': str(e)
        }, status=500)

@login_required
@enterprise_required
@require_POST
def bulk_crawl_results(request):
    """批量爬取測驗結果"""
    user = request.user
    
    try:
        invitation_ids = request.POST.getlist('invitation_ids')
        if not invitation_ids:
            return JsonResponse({
                'success': False,
                'error': '請選擇要爬取的測驗邀請'
            })
        
        # 權限檢查
        if user.user_type == 'admin':
            invitations = TestInvitation.objects.filter(
                id__in=invitation_ids,
                status='completed'
            )
        else:
            invitations = TestInvitation.objects.filter(
                id__in=invitation_ids,
                enterprise=user
                # status='completed'  # 暫時忽略狀態檢查以便測試
            )
        
        # 過濾掉已經爬取過的邀請 (暫時忽略此檢查以便測試)
        # crawlable_invitations = []
        # result_invitation_ids = TestProjectResult.objects.values_list('test_invitation_id', flat=True)
        # for invitation in invitations:
        #     if invitation.id not in result_invitation_ids:
        #         crawlable_invitations.append(invitation)
        
        # 暫時允許所有邀請進行爬取測試
        crawlable_invitations = list(invitations)
        
        # 清理已存在的結果以便重新爬取
        existing_results = TestProjectResult.objects.filter(
            test_invitation__in=crawlable_invitations
        )
        existing_results.delete()
        
        if not crawlable_invitations:
            return JsonResponse({
                'success': False,
                'error': '沒有可爬取的邀請'
            })
        
        # 執行批量爬取（未來可改為異步任務）
        successful_count = 0
        failed_count = 0
        
        for invitation in crawlable_invitations:
            try:
                # 創建爬蟲結果記錄
                test_result = TestProjectResult.objects.create(
                    test_invitation=invitation,
                    test_project=invitation.test_project,
                    crawl_status='crawling'
                )
                
                # 執行爬蟲
                crawler = PITestResultCrawler()
                crawler.crawl_test_result(invitation.id)
                successful_count += 1
                
            except Exception as e:
                logger.error(f"批量爬取失敗，邀請ID：{invitation.id}，錯誤：{str(e)}")
                # 更新失敗狀態
                if 'test_result' in locals():
                    test_result.crawl_status = 'failed'
                    test_result.save()
                failed_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'批量爬取完成！成功：{successful_count} 個，失敗：{failed_count} 個',
            'successful_count': successful_count,
            'failed_count': failed_count
        })
        
    except Exception as e:
        logger.error(f"批量爬取作業失敗：{str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'批量爬取作業失敗：{str(e)}'
        })

@login_required
@admin_required
def test_result_dashboard(request):
    """測驗結果管理儀表板（管理員專用）"""
    # 統計數據
    total_invitations = TestInvitation.objects.count()
    completed_invitations = TestInvitation.objects.filter(status='completed').count()
    crawled_results = TestProjectResult.objects.count()
    failed_results = TestProjectResult.objects.filter(crawl_status='failed').count()
    
    # 最近的爬蟲活動
    recent_results = TestProjectResult.objects.select_related(
        'test_invitation__invitee', 'test_project'
    ).order_by('-crawled_at')[:10]
    
    # 爬蟲狀態分佈
    crawl_status_stats = {
        'pending': TestProjectResult.objects.filter(crawl_status='pending').count(),
        'crawling': TestProjectResult.objects.filter(crawl_status='crawling').count(),
        'completed': TestProjectResult.objects.filter(crawl_status='completed').count(),
        'failed': TestProjectResult.objects.filter(crawl_status='failed').count(),
    }
    
    # 測驗項目使用統計
    from django.db.models import Count
    project_stats = TestInvitation.objects.values(
        'test_project__name'
    ).annotate(
        invitation_count=Count('id'),
        completed_count=Count('id', filter=Q(status='completed'))
    ).order_by('-invitation_count')[:10]
    
    context = {
        'stats': {
            'total_invitations': total_invitations,
            'completed_invitations': completed_invitations,
            'crawled_results': crawled_results,
            'failed_results': failed_results,
            'completion_rate': (completed_invitations / total_invitations * 100) if total_invitations > 0 else 0,
            'crawl_rate': (crawled_results / completed_invitations * 100) if completed_invitations > 0 else 0,
        },
        'recent_results': recent_results,
        'crawl_status_stats': crawl_status_stats,
        'project_stats': project_stats,
    }
    
    return render(request, 'admin/test_result_dashboard.html', context)

# 簡單的雷達圖測試頁面
def test_chart_simple(request):
    """簡單的 Chart.js 雷達圖測試頁面"""
    return render(request, 'test_chart_simple.html')

# core/individual_test_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from .models import TestProject, UserPointBalance, PointTransaction, IndividualTestRecord, IndividualTestResult
from utils.point_service import PointService
from utils.pdf_report_generator import generate_test_result_pdf
import logging

logger = logging.getLogger(__name__)

@login_required
def individual_tests(request):
    """個人測驗頁面 - 顯示所有可用的測驗項目"""
    if request.user.user_type != 'individual':
        messages.error(request, '此功能僅開放給個人用戶使用')
        return redirect('dashboard')
    
    # 檢查並更新現有測驗記錄的狀態
    _update_test_record_statuses(request.user)
    
    # 獲取可用的測驗項目
    available_projects = TestProject.get_available_projects_for_user(request.user)
    
    # 獲取用戶已購買的測驗記錄
    purchased_records = IndividualTestRecord.objects.filter(
        user=request.user
    ).select_related('test_project')
    
    # 建立已購買測驗的 ID 集合
    purchased_project_ids = set(record.test_project.id for record in purchased_records)
    
    # 為每個測驗項目添加購買狀態
    projects_with_status = []
    for project in available_projects:
        project_data = {
            'project': project,
            'is_purchased': project.id in purchased_project_ids,
            'record': None
        }
        
        # 如果已購買，獲取記錄詳情
        if project.id in purchased_project_ids:
            project_data['record'] = purchased_records.filter(test_project=project).first()
        
        projects_with_status.append(project_data)
    
    # 獲取用戶點數餘額
    try:
        point_balance = UserPointBalance.objects.get(user=request.user)
        current_points = point_balance.balance
    except UserPointBalance.DoesNotExist:
        current_points = 0
    
    context = {
        'projects_with_status': projects_with_status,
        'current_points': current_points,
        'user': request.user,
        'purchased_count': len(purchased_project_ids),
        'available_count': len(available_projects),
    }
    
    return render(request, 'individual_tests/test_list.html', context)

@login_required
def test_purchase_confirm(request, project_id):
    """測驗購買確認頁面"""
    if request.user.user_type != 'individual':
        messages.error(request, '此功能僅開放給個人用戶使用')
        return redirect('dashboard')
    
    project = get_object_or_404(TestProject, id=project_id)
    
    # 檢查測驗是否對用戶開放
    available_projects = TestProject.get_available_projects_for_user(request.user)
    if project not in available_projects:
        messages.error(request, '您沒有權限購買此測驗項目')
        return redirect('individual_tests')
    
    # 獲取用戶點數餘額
    try:
        point_balance = UserPointBalance.objects.get(user=request.user)
        current_points = point_balance.balance
    except UserPointBalance.DoesNotExist:
        current_points = 0
    
    # 測驗費用（目前設定為1點）
    test_cost = 1
    remaining_points = current_points - test_cost
    
    # 檢查點數是否足夠
    if current_points < test_cost:
        messages.error(request, f'點數不足！目前點數：{current_points}，需要：{test_cost}')
        return redirect('individual_tests')
    
    context = {
        'project': project,
        'current_points': current_points,
        'test_cost': test_cost,
        'remaining_points': remaining_points,
        'user': request.user,
    }
    
    return render(request, 'individual_tests/purchase_confirm.html', context)

@login_required
def test_purchase_process(request, project_id):
    """處理測驗購買"""
    if request.method != 'POST':
        return redirect('individual_tests')
    
    if request.user.user_type != 'individual':
        messages.error(request, '此功能僅開放給個人用戶使用')
        return redirect('dashboard')
    
    project = get_object_or_404(TestProject, id=project_id)
    
    # 檢查測驗是否對用戶開放
    available_projects = TestProject.get_available_projects_for_user(request.user)
    if project not in available_projects:
        messages.error(request, '您沒有權限購買此測驗項目')
        return redirect('individual_tests')
    
    # 測驗費用
    test_cost = 1
    
    try:
        with transaction.atomic():
            # 使用點數服務進行消費
            point_service = PointService()
            success = point_service.consume_points(
                user=request.user,
                action_type='test_execution',
                quantity=test_cost,
                description=f'購買測驗：{project.name}',
                reference_id=str(project.id)
            )
            
            if success:
                # 創建個人測驗記錄
                test_record, created = IndividualTestRecord.objects.get_or_create(
                    user=request.user,
                    test_project=project,
                    defaults={
                        'points_consumed': test_cost,
                        'status': 'purchased'
                    }
                )
                
                # 標記測驗被進入
                test_record.mark_accessed()
                
                messages.success(request, f'成功購買測驗「{project.name}」！已扣除 {test_cost} 點數')
                
                # 重定向到測驗連結 (使用 HttpResponseRedirect 處理外部 URL)
                return HttpResponseRedirect(project.test_link)
            else:
                messages.error(request, '點數不足，無法購買測驗')
                return redirect('individual_tests')
                
    except Exception as e:
        logger.error(f'測驗購買失敗: {str(e)}')
        messages.error(request, '購買失敗，請稍後再試')
        return redirect('individual_tests')

@login_required
def check_points_ajax(request):
    """Ajax 檢查用戶點數"""
    if request.user.user_type != 'individual':
        return JsonResponse({'error': '無效的用戶類型'}, status=403)
    
    try:
        point_balance = UserPointBalance.objects.get(user=request.user)
        return JsonResponse({
            'current_points': point_balance.balance,
            'has_enough': point_balance.balance >= 1  # 假設測驗費用是1點
        })
    except UserPointBalance.DoesNotExist:
        return JsonResponse({
            'current_points': 0,
            'has_enough': False
        })

@login_required
def direct_test_access(request, project_id):
    """直接進入已購買的測驗"""
    if request.user.user_type != 'individual':
        messages.error(request, '此功能僅開放給個人用戶使用')
        return redirect('dashboard')
    
    project = get_object_or_404(TestProject, id=project_id)
    
    # 檢查用戶是否已購買此測驗
    try:
        test_record = IndividualTestRecord.objects.get(
            user=request.user,
            test_project=project
        )
    except IndividualTestRecord.DoesNotExist:
        messages.error(request, '您尚未購買此測驗項目')
        return redirect('individual_tests')
    
    # 檢查測驗是否可以進入
    if not test_record.can_access_test:
        if test_record.status == 'completed':
            messages.info(request, '此測驗已完成，請前往「我的結果」查看測驗報告')
        else:
            messages.error(request, '此測驗項目已過期或無法進入')
        return redirect('individual_tests')
    
    # 標記測驗被進入
    test_record.mark_accessed()
    
    # 判斷使用哪個連結
    if test_record.status == 'purchased' and test_record.access_count <= 1:
        # 首次進入：使用測驗項目設定的連結
        target_url = project.test_link
        logger.info(f"首次進入測驗，使用項目連結: {target_url}")
    else:
        # 繼續測驗：使用繼續測驗連結，並可能包含自動登入
        target_url = _get_continue_test_url(request.user)
        logger.info(f"繼續測驗，使用繼續連結: {target_url}")
    
    # 重定向到測驗連結
    return HttpResponseRedirect(target_url)

@login_required
def individual_test_result_detail(request, result_id):
    """個人測驗結果詳細頁面"""
    if request.user.user_type != 'individual':
        messages.error(request, '此功能僅開放給個人用戶使用')
        return redirect('dashboard')
    
    # 獲取測驗結果，確保是當前用戶的
    result = get_object_or_404(IndividualTestResult, id=result_id, user=request.user)
    
    # 檢查結果是否真正完整
    if not result.is_result_complete() or not result.test_completion_date:
        # 如果結果不完整，顯示處理中頁面
        context = {
            'result': result,
            'test_record': result.individual_test_record,
            'test_project': result.test_project,
            'user': request.user,
            'result_incomplete': True,
        }
        return render(request, 'individual_tests/result_processing.html', context)
    
    # 使用個人測驗結果的真實資料
    category_analysis = result.get_category_analysis()
    trait_analysis = result.get_trait_analysis()
    strengths_weaknesses = result.get_strengths_and_weaknesses()
    
    # 如果個人測驗結果資料不完整，創建基本的預設資料
    if not category_analysis:
        # 從測驗項目的分類獲取基本結構
        from core.models import TestProjectCategory
        categories = TestProjectCategory.objects.filter(test_project=result.test_project)
        
        category_analysis = {}
        for category in categories:
            category_analysis[category.name] = {
                'score': result.score_value if result.score_value else 0,
                'percentage': int((result.score_value or 0) * 20),  # 假設5分制轉百分制
                'role_name': category.role_name or f"{category.name}專家",
                'tag_text': category.tag_text or f"{category.name},專業",
                'role_info': category.content or f"在{category.name}領域的表現。",
                'strength_advice': category.advantage_suggestions or f"建議繼續發展{category.name}能力。",
                'development_direction': category.development_direction or f"可在{category.name}領域持續成長。",
                'image': category.role_image if category.role_image else None
            }
    
    # 如果仍然沒有資料，創建一個基本的顯示
    if not category_analysis:
        category_analysis = {
            '綜合能力': {
                'score': result.score_value if result.score_value else 3.0,
                'percentage': int((result.score_value or 3.0) * 20),
                'role_name': '測驗參與者',
                'tag_text': '學習成長,自我提升',
                'role_info': '已完成測驗，正在分析結果中。',
                'strength_advice': '請等待詳細分析結果。',
                'development_direction': '持續關注個人成長與發展。',
                'image': None
            }
        }
    
    # 找出最高分分類
    highest_category = None
    if category_analysis:
        highest_cat_name = max(category_analysis.keys(), key=lambda x: category_analysis[x]['score'])
        highest_category = category_analysis[highest_cat_name].copy()
        highest_category['name'] = highest_cat_name
    
    # 準備雷達圖數據
    radar_data = {
        'labels': list(category_analysis.keys()),
        'scores': [data['score'] for data in category_analysis.values()],
        'percentages': [data['percentage'] for data in category_analysis.values()]
    }
    
    context = {
        'result': result,
        'test_record': result.individual_test_record,
        'test_project': result.test_project,
        'category_analysis': category_analysis,
        'trait_analysis': trait_analysis,
        'strengths_weaknesses': strengths_weaknesses,
        'radar_data': radar_data,
        'highest_category': highest_category,
        'user': request.user,
    }
    
    return render(request, 'individual_tests/result_detail.html', context)

@login_required
def individual_test_results_list(request):
    """個人測驗結果列表頁面"""
    if request.user.user_type != 'individual':
        messages.error(request, '此功能僅開放給個人用戶使用')
        return redirect('dashboard')
    
    # 獲取用戶的所有測驗結果
    results = IndividualTestResult.objects.filter(
        user=request.user
    ).select_related('test_project', 'individual_test_record').order_by('-created_at')
    
    # 統計資訊
    total_results = results.count()
    completed_results = results.filter(result_status='completed').count()
    average_score = None
    
    if completed_results > 0:
        scores = [r.score_value for r in results.filter(result_status='completed') if r.score_value]
        if scores:
            average_score = round(sum(scores) / len(scores), 2)
    
    context = {
        'results': results,
        'total_results': total_results,
        'completed_results': completed_results,
        'average_score': average_score,
        'user': request.user,
    }
    
    return render(request, 'individual_tests/results_list.html', context)

class IndividualTestResultAdapter:
    """適配器類，讓IndividualTestResult可以與PDF生成器兼容"""
    
    def __init__(self, individual_result):
        self.individual_result = individual_result
        self._create_mock_invitation()
    
    def _create_mock_invitation(self):
        """為個人測驗結果創建模擬的邀請對象"""
        from types import SimpleNamespace
        
        # 創建模擬的受邀者對象
        mock_invitee = SimpleNamespace()
        mock_invitee.name = self.individual_result.user.individual_profile.real_name if hasattr(self.individual_result.user, 'individual_profile') and self.individual_result.user.individual_profile else self.individual_result.user.username
        mock_invitee.email = self.individual_result.user.email
        mock_invitee.position = "個人用戶"
        mock_invitee.get_status_display = lambda: "個人用戶"
        
        # 創建模擬的邀請對象
        mock_invitation = SimpleNamespace()
        mock_invitation.invitee = mock_invitee
        mock_invitation.invited_at = self.individual_result.individual_test_record.purchase_date
        mock_invitation.started_at = self.individual_result.individual_test_record.first_access_date
        mock_invitation.completed_at = self.individual_result.created_at  # 使用測驗結果建立時間作為完成時間
        
        self.test_invitation = mock_invitation
    
    def __getattr__(self, name):
        # 如果屬性不存在於適配器中，則從原始對象獲取
        return getattr(self.individual_result, name)

@login_required
def generate_individual_test_result_pdf(request, result_id):
    """生成個人測驗結果 PDF 報告"""
    if request.user.user_type != 'individual':
        messages.error(request, '此功能僅開放給個人用戶使用')
        return redirect('dashboard')
    
    # 獲取測驗結果，確保是當前用戶的
    result = get_object_or_404(IndividualTestResult, id=result_id, user=request.user)
    
    # 使用適配器包裝結果對象
    adapted_result = IndividualTestResultAdapter(result)
    
    # 詳細調試信息
    logger.info(f"開始生成個人PDF報告，結果ID: {result_id}")
    logger.info(f"用戶: {request.user.username}, 用戶類型: {request.user.user_type}")
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
        response = generate_test_result_pdf(adapted_result)
        logger.info(f"✅ PDF 生成成功，響應類型: {type(response)}")
        
        if hasattr(response, 'status_code'):
            logger.info(f"響應狀態碼: {response.status_code}")
        if hasattr(response, 'content'):
            logger.info(f"響應內容長度: {len(response.content)} 字節")
            
        # 更新報告生成狀態
        result.report_generated = True
        result.report_generated_at = timezone.now()
        result.save()
            
        return response
        
    except ImportError as e:
        error_msg = f'PDF 生成套件問題: {str(e)}'
        logger.error(error_msg)
        return JsonResponse({
            'error': error_msg,
            'details': '請確保已安裝 reportlab 套件'
        }, status=500)
        
    except Exception as e:
        error_msg = f'PDF 生成過程中發生錯誤: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return JsonResponse({
            'error': error_msg,
            'details': '請聯繫系統管理員或稍後重試'
        }, status=500)

def _update_test_record_statuses(user):
    """檢查並更新用戶的測驗記錄狀態"""
    try:
        # 獲取用戶所有的測驗記錄
        records = IndividualTestRecord.objects.filter(user=user)
        
        for record in records:
            # 檢查是否有對應的測驗結果且有完成時間
            if hasattr(record, 'test_result'):
                result = record.test_result
                if result.test_completion_date and record.status != 'completed':
                    record.status = 'completed'
                    record.save()
                    logger.info(f"更新測驗記錄狀態：{record.id} -> completed")
                    
    except Exception as e:
        logger.error(f"更新測驗記錄狀態失敗：{str(e)}")

def _get_continue_test_url(user):
    """取得繼續測驗的URL"""
    return "https://whohire.ai"

@login_required
def auto_login_to_test_platform(request):
    """自動登入測驗平台頁面"""
    if request.user.user_type != 'individual':
        messages.error(request, '此功能僅開放給個人用戶使用')
        return redirect('dashboard')
    
    redirect_url = request.GET.get('redirect_url', 'https://whohire.ai')
    
    # 獲取用戶的測驗平台登入資訊
    try:
        profile = request.user.individual_profile
        if not profile.test_platform_username or not profile.test_platform_password:
            messages.error(request, '尚未設定測驗平台登入資訊，請先至個人資料設定')
            return redirect('individual_tests')
        
        context = {
            'username': profile.test_platform_username,
            'password': profile.test_platform_password,
            'redirect_url': redirect_url,
            'user': request.user,
        }
        
        return render(request, 'individual_tests/auto_login.html', context)
        
    except Exception as e:
        logger.error(f"自動登入頁面錯誤: {str(e)}")
        messages.error(request, '無法載入登入資訊，請直接前往測驗平台')
        return HttpResponseRedirect(redirect_url)

@login_required
def server_side_auto_login(request):
    """後端自動登入（使用爬蟲技術）"""
    if request.user.user_type != 'individual':
        messages.error(request, '此功能僅開放給個人用戶使用')
        return redirect('individual_tests')
    
    redirect_url = request.GET.get('redirect_url', 'https://whohire.ai')
    
    try:
        profile = request.user.individual_profile
        if not profile.test_platform_username or not profile.test_platform_password:
            messages.error(request, '尚未設定測驗平台登入資訊，請先至個人資料設定')
            return redirect('individual_tests')
        
        # 如果是 GET 請求，顯示實用的自動登入頁面
        if request.method == 'GET':
            return render(request, 'individual_tests/practical_auto_login.html', {
                'fallback_url': redirect_url,
                'username': profile.test_platform_username,
                'password': profile.test_platform_password
            })
        
        # 如果是 POST 請求，執行自動登入
        if request.method == 'POST':
            logger.info(f"開始為用戶 {request.user.username} 進行自動登入")
            
            # 使用爬蟲進行自動登入
            from .auto_login_service import AutoLoginService
            login_service = AutoLoginService()
            
            success, result = login_service.auto_login_whohire(
                profile.test_platform_username,
                profile.test_platform_password
            )
            
            if success:
                logger.info(f"用戶 {request.user.username} 自動登入成功")
                
                # 創建包含 cookies 的響應
                cookies = result.get('cookies', [])
                final_url = result.get('redirect_url', redirect_url)
                
                # 檢查是否成功取得重要的 cookies
                important_cookies = [c for c in cookies if c['name'] in ['ASP.NET_SessionId', '__RequestVerificationToken']]
                
                if important_cookies:
                    # 返回 cookies 資訊讓前端處理
                    return JsonResponse({
                        'success': True,
                        'redirect_url': final_url,
                        'cookies': cookies,
                        'message': '自動登入成功，正在設定認證資訊...'
                    })
                else:
                    # 沒有取得重要 cookies，回退到手動登入
                    return JsonResponse({
                        'success': False,
                        'redirect_url': redirect_url,
                        'message': '自動登入技術限制，請手動登入'
                    })
            else:
                logger.error(f"用戶 {request.user.username} 自動登入失敗: {result}")
                return JsonResponse({
                    'success': False,
                    'redirect_url': redirect_url,
                    'message': f'自動登入失敗：{result}'
                })
                
    except Exception as e:
        logger.error(f"後端自動登入失敗: {str(e)}")
        if request.method == 'POST':
            return JsonResponse({
                'success': False,
                'redirect_url': redirect_url,
                'message': '自動登入服務暫時無法使用，請手動登入'
            })
        else:
            messages.error(request, '自動登入服務暫時無法使用，請手動登入')
            return HttpResponseRedirect(redirect_url)

@login_required
def check_auto_login_status(request):
    """檢查自動登入狀態的 API 端點"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '僅支援 POST 請求'})
    
    if request.user.user_type != 'individual':
        return JsonResponse({'success': False, 'message': '此功能僅開放給個人用戶使用'})
    
    redirect_url = request.GET.get('redirect_url', 'https://whohire.ai')
    
    try:
        profile = request.user.individual_profile
        if not profile.test_platform_username or not profile.test_platform_password:
            return JsonResponse({
                'success': False,
                'redirect_url': redirect_url,
                'message': '尚未設定測驗平台登入資訊'
            })
        
        logger.info(f"開始檢查用戶 {request.user.username} 的自動登入狀態")
        
        # 使用爬蟲進行自動登入
        from .auto_login_service import AutoLoginService
        login_service = AutoLoginService()
        
        success, result = login_service.auto_login_whohire(
            profile.test_platform_username,
            profile.test_platform_password
        )
        
        if success:
            logger.info(f"用戶 {request.user.username} 自動登入成功")
            final_url = result.get('redirect_url', redirect_url)
            return JsonResponse({
                'success': True,
                'redirect_url': final_url,
                'message': '自動登入成功'
            })
        else:
            logger.error(f"用戶 {request.user.username} 自動登入失敗: {result}")
            return JsonResponse({
                'success': False,
                'redirect_url': redirect_url,
                'message': f'自動登入失敗：{result}'
            })
            
    except Exception as e:
        logger.error(f"檢查自動登入狀態失敗: {str(e)}")
        return JsonResponse({
            'success': False,
            'redirect_url': redirect_url,
            'message': '自動登入服務暫時無法使用'
        })
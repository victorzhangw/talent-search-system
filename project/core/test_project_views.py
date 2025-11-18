# core/test_project_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q, Count, Max
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import (
    TestProjectIndividualAssignment, User, TestProject, TestProjectCategory, Trait,
    TestProjectCategoryTrait, TestProjectTrait, TestProjectAssignment, EnterpriseProfile,
    Notification, TestInvitation, TestProjectResult
)
from .purchase_services import record_enterprise_purchase, generate_order_number
from decimal import Decimal, InvalidOperation
from django.urls import reverse
import json
import logging

logger = logging.getLogger(__name__)

# 權限裝飾器
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


def safe_create_notification(**kwargs):
    """
    Create notification and swallow DB errors so workflow does not break.
    """
    try:
        Notification.objects.create(**kwargs)
    except Exception:
        logger.exception("Failed to create notification", exc_info=True)


def _serialize_traits_for_form():
    return [
        {
            'id': trait.id,
            'chinese_name': trait.chinese_name,
            'system_name': trait.system_name,
            'description': trait.description,
        }
        for trait in Trait.objects.order_by('chinese_name', 'system_name')
    ]

@login_required
@admin_required
def test_project_list(request):
    """測驗項目列表"""
    projects = TestProject.objects.all().select_related('created_by').prefetch_related('categories__traits')
    
    # 搜尋功能
    search = request.GET.get('search', '')
    if search:
        projects = projects.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search)
        )
    
    # 指派類型過濾
    assignment_type = request.GET.get('assignment_type', '')
    if assignment_type:
        projects = projects.filter(assignment_type=assignment_type)
    
    projects = projects.order_by('-created_at')
    
    # 為每個項目添加統計數據
    for project in projects:
        project.total_traits_count = sum(cat.traits.count() for cat in project.categories.all())
    
    # 分頁
    paginator = Paginator(projects, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 統計數據（移除啟用/停用統計）
    stats = {
        'total': TestProject.objects.count(),
        'all_open': TestProject.objects.filter(assignment_type='all_open').count(),
        'enterprise_only': TestProject.objects.filter(assignment_type='enterprise_only').count(),
        'individual_only': TestProject.objects.filter(assignment_type='individual_only').count(),
        'specific_assignment': TestProject.objects.filter(assignment_type='specific_assignment').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'assignment_type_filter': assignment_type,
        'assignment_choices': TestProject.ASSIGNMENT_TYPE_CHOICES,
        'stats': stats,
    }
    
    return render(request, 'admin/test_project_list.html', context)

@login_required
@admin_required
def test_project_create(request):
    """新增測驗項目"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 建立測驗項目
                radar_mode = request.POST.get('radar_mode', 'role')
                show_mixed_role = request.POST.get('show_mixed_role') == 'on' if radar_mode == 'role' else False

                project = TestProject.objects.create(
                    name=request.POST.get('name'),
                    description=request.POST.get('description', ''),
                    name_abbreviation=request.POST.get('name_abbreviation', ''),
                    title_name=request.POST.get('title_name', ''),
                    title_name_english=request.POST.get('title_name_english', ''),
                    introduction=request.POST.get('introduction', ''),
                    usage_guide=request.POST.get('usage_guide', ''),
                    precautions=request.POST.get('precautions', ''),
                    test_link=request.POST.get('test_link'),
                    # 新增：頁首資訊
                    header_text_content=request.POST.get('header_text_content', ''),
                    # 新增：頁尾資訊
                    footer_text_content=request.POST.get('footer_text_content', ''),
                    # 新增：個人分享共同資訊
                    personal_share_title=request.POST.get('personal_share_title', ''),
                    personal_share_footer_content=request.POST.get('personal_share_footer_content', ''),
                    score_field_chinese=request.POST.get('score_field_chinese'),
                    score_field_system=request.POST.get('score_field_system'),
                    prediction_field_chinese=request.POST.get('prediction_field_chinese'),
                    prediction_field_system=request.POST.get('prediction_field_system'),
                    job_role_system_name=request.POST.get('job_role_system_name', ''),  # job role欄位
                    assignment_type=request.POST.get('assignment_type', 'specific_assignment'),
                    radar_mode=radar_mode,
                    show_mixed_role=show_mixed_role,
                    created_by=request.user
                )
                
                # 處理頁首Logo上傳
                if 'header_logo' in request.FILES:
                    project.header_logo = request.FILES['header_logo']
                    project.save()

                # 處理測驗特質設定
                project.project_trait_relations.all().delete()
                project_traits_data = json.loads(request.POST.get('project_traits_data', '[]'))
                selected_trait_ids = set()
                trait_object_map = {}
                for trait_index, trait_data in enumerate(project_traits_data):
                    trait_id = trait_data.get('trait_id')
                    try:
                        trait_id = int(trait_id)
                    except (TypeError, ValueError):
                        continue

                    try:
                        trait_obj = Trait.objects.get(id=trait_id)
                    except Trait.DoesNotExist:
                        continue

                    use_custom_description = bool(trait_data.get('use_custom_description'))
                    custom_description = trait_data.get('custom_description') or ''

                    TestProjectTrait.objects.create(
                        test_project=project,
                        trait=trait_obj,
                        custom_description=custom_description,
                        use_custom_description=use_custom_description,
                        sort_order=trait_index
                    )

                    selected_trait_ids.add(trait_obj.id)
                    trait_object_map[trait_obj.id] = trait_obj
                
                # 處理分類數據
                categories_data = json.loads(request.POST.get('categories_data', '[]'))
                next_category_id = (TestProjectCategory.objects.aggregate(max_id=Max('id'))['max_id'] or 0) + 1
                next_category_trait_id = (TestProjectCategoryTrait.objects.aggregate(max_id=Max('id'))['max_id'] or 0) + 1
                next_category_trait_id = (TestProjectCategoryTrait.objects.aggregate(max_id=Max('id'))['max_id'] or 0) + 1
                for cat_index, category_data in enumerate(categories_data):
                    category_id = category_data.get('id')
                    try:
                        category_id = int(category_id)
                    except (TypeError, ValueError):
                        category_id = None

                    if not category_id:
                        category_id = next_category_id
                        next_category_id += 1

                    category = TestProjectCategory.objects.create(
                        id=category_id,
                        test_project=project,
                        name=category_data.get('name', ''),
                        english_name=category_data.get('english_name', ''),
                        description=category_data.get('description', ''),
                        test_link=category_data.get('test_link', ''),
                        advantage_analysis=category_data.get('advantage_analysis', ''),
                        disadvantage_analysis=category_data.get('disadvantage_analysis', ''),
                        development_parameter_name=category_data.get('development_parameter_name', ''),
                        development_parameter_content=category_data.get('development_parameter_content', ''),
                        # 新增：角色相關欄位
                        role_name=category_data.get('role_name', ''),
                        tag_text=category_data.get('tag_text', ''),
                        content=category_data.get('content', ''),
                        advantage_suggestions=category_data.get('advantage_suggestions', ''),
                        development_direction=category_data.get('development_direction', ''),
                        score_type_name=category_data.get('score_type_name', ''),
                        sort_order=cat_index
                    )
                    
                    # 處理角色圖片上傳
                    role_image_key = f'role_image_{cat_index}'
                    if role_image_key in request.FILES:
                        category.role_image = request.FILES[role_image_key]
                        category.save()
                    
                    # 處理特質數據
                    traits_data = category_data.get('traits', [])
                    for trait_index, trait_data in enumerate(traits_data):
                        trait_id = trait_data.get('trait_id')
                        try:
                            trait_id = int(trait_id)
                        except (TypeError, ValueError):
                            continue

                        if trait_id not in selected_trait_ids:
                            continue

                        trait_obj = trait_object_map.get(trait_id)
                        if not trait_obj:
                            continue

                        weight_value = trait_data.get('weight', 1)

                        try:
                            weight_decimal = Decimal(str(weight_value))
                        except (InvalidOperation, TypeError, ValueError):
                            weight_decimal = Decimal('1')

                        relation_id = trait_data.get('relation_id')
                        try:
                            relation_id = int(relation_id)
                        except (TypeError, ValueError):
                            relation_id = None

                        if not relation_id:
                            relation_id = next_category_trait_id
                            next_category_trait_id += 1

                        TestProjectCategoryTrait.objects.create(
                            id=relation_id,
                            category=category,
                            trait=trait_obj,
                            weight=weight_decimal,
                            sort_order=trait_index
                        )
                
                # 處理用戶指派（如果是指定開放）
                if project.assignment_type == 'specific_assignment':
                    # 清除舊指派
                    project.enterprise_assignments.all().delete()
                    next_assignment_id = (TestProjectAssignment.objects.aggregate(max_id=Max('id'))['max_id'] or 0) + 1
                    next_individual_assignment_id = (TestProjectIndividualAssignment.objects.aggregate(max_id=Max('id'))['max_id'] or 0) + 1
                    
                    # 建立新指派
                    assigned_enterprises = request.POST.getlist('assigned_enterprises')
                    for enterprise_id in assigned_enterprises:
                        if enterprise_id:
                            enterprise = User.objects.get(id=enterprise_id, user_type='enterprise')
                            TestProjectAssignment.objects.create(
                                id=next_assignment_id,
                                test_project=project,
                                enterprise_user=enterprise,
                                assigned_by=request.user
                            )
                            next_assignment_id += 1
                    
                    # 處理個人用戶指派
                    assigned_individuals = request.POST.getlist('assigned_individuals')
                    for individual_id in assigned_individuals:
                        if individual_id:
                            individual = User.objects.get(id=individual_id, user_type='individual')
                            TestProjectIndividualAssignment.objects.create(
                                id=next_individual_assignment_id,
                                test_project=project,
                                individual_user=individual,
                                assigned_by=request.user
                            )
                            next_individual_assignment_id += 1
                else:
                    # 如果改為其他類型，清除特定指派
                    project.enterprise_assignments.all().delete()
                    project.individual_assignments.all().delete()

                logger.info(f"管理員 {request.user.username} 建立測驗項目：{project.name}")
                messages.success(request, f'測驗項目「{project.name}」建立成功！')
                return redirect('test_project_list')
                
        except Exception as e:
            logger.error(f"建立測驗項目失敗：{str(e)}")
            messages.error(request, f'建立失敗：{str(e)}')
    
    # 獲取企業和個人用戶列表（用於指派）
    # GET 請求的處理邏輯保持不變...
    enterprises = User.objects.filter(
        user_type='enterprise',
        enterprise_profile__verification_status='approved'
    ).select_related('enterprise_profile')
    
    individuals = User.objects.filter(
        user_type='individual',
        is_email_verified=True
    ).select_related('individual_profile')
    
    available_traits = _serialize_traits_for_form()

    context = {
        'enterprises': enterprises,
        'individuals': individuals,
        'assignment_choices': TestProject.ASSIGNMENT_TYPE_CHOICES,
        'radar_mode_choices': TestProject.RADAR_MODE_CHOICES,
        'current_radar_mode': 'role',
        'current_show_mixed_role': True,
        'available_traits_json': json.dumps(available_traits, ensure_ascii=False),
        'project_traits_json': json.dumps([], ensure_ascii=False),
    }
    
    return render(request, 'admin/test_project_form.html', context)

@login_required
@admin_required
def test_project_edit(request, project_id):
    """編輯測驗項目"""
    project = get_object_or_404(TestProject, id=project_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # 更新基本資料
                project.name = request.POST.get('name')
                project.description = request.POST.get('description', '')
                project.name_abbreviation = request.POST.get('name_abbreviation', '')
                project.title_name = request.POST.get('title_name', '')
                project.title_name_english = request.POST.get('title_name_english', '')
                project.introduction = request.POST.get('introduction', '')
                project.usage_guide = request.POST.get('usage_guide', '')
                project.precautions = request.POST.get('precautions', '')
                project.test_link = request.POST.get('test_link')
                # 新增：頁首資訊
                project.header_text_content = request.POST.get('header_text_content', '')
                # 新增：頁尾資訊
                project.footer_text_content = request.POST.get('footer_text_content', '')
                # 新增：個人分享共同資訊
                project.personal_share_title = request.POST.get('personal_share_title', '')
                project.personal_share_footer_content = request.POST.get('personal_share_footer_content', '')
                project.score_field_chinese = request.POST.get('score_field_chinese')
                project.score_field_system = request.POST.get('score_field_system')
                project.prediction_field_chinese = request.POST.get('prediction_field_chinese')
                project.prediction_field_system = request.POST.get('prediction_field_system')
                project.job_role_system_name = request.POST.get('job_role_system_name', '')  # 新增這行
                project.assignment_type = request.POST.get('assignment_type', 'specific_assignment')

                radar_mode = request.POST.get('radar_mode', project.radar_mode or 'role')
                project.radar_mode = radar_mode
                project.show_mixed_role = request.POST.get('show_mixed_role') == 'on' if radar_mode == 'role' else False
                
                # 處理頁首Logo上傳
                if 'header_logo' in request.FILES:
                    project.header_logo = request.FILES['header_logo']
                
                project.save()

                # 更新測驗特質設定
                project.project_trait_relations.all().delete()
                project_traits_data = json.loads(request.POST.get('project_traits_data', '[]'))
                selected_trait_ids = set()
                trait_object_map = {}
                for trait_index, trait_data in enumerate(project_traits_data):
                    trait_id = trait_data.get('trait_id')
                    try:
                        trait_id = int(trait_id)
                    except (TypeError, ValueError):
                        continue

                    try:
                        trait_obj = Trait.objects.get(id=trait_id)
                    except Trait.DoesNotExist:
                        continue

                    use_custom_description = bool(trait_data.get('use_custom_description'))
                    custom_description = trait_data.get('custom_description') or ''

                    TestProjectTrait.objects.create(
                        test_project=project,
                        trait=trait_obj,
                        custom_description=custom_description,
                        use_custom_description=use_custom_description,
                        sort_order=trait_index
                    )

                    selected_trait_ids.add(trait_obj.id)
                    trait_object_map[trait_obj.id] = trait_obj
                
                # 清除舊的分類和特質
                project.categories.all().delete()
                
                # 重新建立分類和特質
                categories_data = json.loads(request.POST.get('categories_data', '[]'))
                next_category_id = (TestProjectCategory.objects.aggregate(max_id=Max('id'))['max_id'] or 0) + 1
                for cat_index, category_data in enumerate(categories_data):
                    category_id = category_data.get('id')
                    try:
                        category_id = int(category_id)
                    except (TypeError, ValueError):
                        category_id = None

                    if not category_id:
                        category_id = next_category_id
                        next_category_id += 1

                    category = TestProjectCategory.objects.create(
                        id=category_id,
                        test_project=project,
                        name=category_data.get('name', ''),
                        english_name=category_data.get('english_name', ''),
                        description=category_data.get('description', ''),
                        test_link=category_data.get('test_link', ''),
                        advantage_analysis=category_data.get('advantage_analysis', ''),
                        disadvantage_analysis=category_data.get('disadvantage_analysis', ''),
                        development_parameter_name=category_data.get('development_parameter_name', ''),
                        development_parameter_content=category_data.get('development_parameter_content', ''),
                        # 新增：角色相關欄位
                        role_name=category_data.get('role_name', ''),
                        tag_text=category_data.get('tag_text', ''),
                        content=category_data.get('content', ''),
                        advantage_suggestions=category_data.get('advantage_suggestions', ''),
                        development_direction=category_data.get('development_direction', ''),
                        score_type_name=category_data.get('score_type_name', ''),
                        sort_order=cat_index
                    )
                    
                    # 處理角色圖片上傳
                    role_image_key = f'role_image_{cat_index}'
                    if role_image_key in request.FILES:
                        category.role_image = request.FILES[role_image_key]
                        category.save()
                    
                    traits_data = category_data.get('traits', [])
                    for trait_index, trait_data in enumerate(traits_data):
                        trait_id = trait_data.get('trait_id')
                        try:
                            trait_id = int(trait_id)
                        except (TypeError, ValueError):
                            continue

                        if trait_id not in selected_trait_ids:
                            continue

                        trait_obj = trait_object_map.get(trait_id)
                        if not trait_obj:
                            continue

                        weight_value = trait_data.get('weight', 1)

                        try:
                            weight_decimal = Decimal(str(weight_value))
                        except (InvalidOperation, TypeError, ValueError):
                            weight_decimal = Decimal('1')

                        relation_id = trait_data.get('relation_id')
                        try:
                            relation_id = int(relation_id)
                        except (TypeError, ValueError):
                            relation_id = None

                        if not relation_id:
                            relation_id = next_category_trait_id
                            next_category_trait_id += 1

                        TestProjectCategoryTrait.objects.create(
                            id=relation_id,
                            category=category,
                            trait=trait_obj,
                            weight=weight_decimal,
                            sort_order=trait_index
                        )
                
                # 處理用戶指派（如果是指定開放）
                if project.assignment_type == 'specific_assignment':
                    # 清除舊指派
                    project.enterprise_assignments.all().delete()
                    project.individual_assignments.all().delete()
                    next_assignment_id = (TestProjectAssignment.objects.aggregate(max_id=Max('id'))['max_id'] or 0) + 1
                    next_individual_assignment_id = (TestProjectIndividualAssignment.objects.aggregate(max_id=Max('id'))['max_id'] or 0) + 1
                    
                    # 建立新的企業指派
                    assigned_enterprises = request.POST.getlist('assigned_enterprises')
                    for enterprise_id in assigned_enterprises:
                        if enterprise_id:
                            enterprise = User.objects.get(id=enterprise_id, user_type='enterprise')
                            TestProjectAssignment.objects.create(
                                id=next_assignment_id,
                                test_project=project,
                                enterprise_user=enterprise,
                                assigned_by=request.user
                            )
                            next_assignment_id += 1
                    
                    # 建立新的個人用戶指派
                    assigned_individuals = request.POST.getlist('assigned_individuals')
                    for individual_id in assigned_individuals:
                        if individual_id:
                            individual = User.objects.get(id=individual_id, user_type='individual')
                            TestProjectIndividualAssignment.objects.create(
                                id=next_individual_assignment_id,
                                test_project=project,
                                individual_user=individual,
                                assigned_by=request.user
                            )
                            next_individual_assignment_id += 1
                else:
                    # 如果改為其他類型，清除特定指派
                    project.enterprise_assignments.all().delete()
                    project.individual_assignments.all().delete()
                
                logger.info(f"管理員 {request.user.username} 更新測驗項目：{project.name}")
                messages.success(request, f'測驗項目「{project.name}」更新成功！')
                return redirect('test_project_edit', project_id=project.id)
                
        except Exception as e:
            logger.error(f"更新測驗項目失敗：{str(e)}")
            messages.error(request, f'更新失敗：{str(e)}')
    
    # 獲取企業和個人用戶列表（用於指派）
    enterprises = User.objects.filter(
        user_type='enterprise',
        enterprise_profile__verification_status='approved'
    ).select_related('enterprise_profile')
    
    individuals = User.objects.filter(
        user_type='individual',
        is_email_verified=True
    ).select_related('individual_profile')
    
    # 獲取當前指派的企業和個人用戶
    assigned_enterprise_ids = list(project.enterprise_assignments.values_list('enterprise_user_id', flat=True))
    assigned_individual_ids = list(project.individual_assignments.values_list('individual_user_id', flat=True))
    
    # 測驗特質設定
    project_traits_data = []
    trait_description_map = {}
    for relation in project.project_trait_relations.select_related('trait').order_by('sort_order', 'id'):
        trait = relation.trait
        effective_description = relation.custom_description if relation.use_custom_description and relation.custom_description else trait.description
        project_traits_data.append({
            'trait_id': trait.id,
            'chinese_name': trait.chinese_name,
            'system_name': trait.system_name,
            'default_description': trait.description,
            'custom_description': relation.custom_description,
            'use_custom_description': relation.use_custom_description,
            'description': effective_description,
            'sort_order': relation.sort_order,
        })
        trait_description_map[trait.id] = effective_description
    
    # 準備分類和特質數據給前端
    categories_data = []
    for category in project.categories.prefetch_related('category_traits__trait'):
        traits_data = []
        for category_trait in category.category_traits.select_related('trait').order_by('sort_order', 'id'):
            trait = category_trait.trait
            effective_description = trait_description_map.get(trait.id, trait.description)
            traits_data.append({
                'relation_id': category_trait.id,
                'trait_id': trait.id,
                'chinese_name': trait.chinese_name,
                'system_name': trait.system_name,
                'description': effective_description,
                'weight': float(category_trait.weight),
                'sort_order': category_trait.sort_order,
            })
        
        categories_data.append({
            'id': category.id,
            'name': category.name,
            'english_name': category.english_name,
            'description': category.description,
            'test_link': category.test_link,
            'advantage_analysis': category.advantage_analysis,
            'disadvantage_analysis': category.disadvantage_analysis,
            'development_parameter_name': category.development_parameter_name,
            'development_parameter_content': category.development_parameter_content,
            # 新增：角色相關欄位
            'role_name': category.role_name,
            'tag_text': category.tag_text,
            'content': category.content,
            'advantage_suggestions': category.advantage_suggestions,
            'development_direction': category.development_direction,
            'score_type_name': category.score_type_name,
            'traits': traits_data,
        })
    
    context = {
        'project': project,
        'enterprises': enterprises,
        'individuals': individuals,
        'assigned_enterprise_ids': assigned_enterprise_ids,
        'assigned_individual_ids': assigned_individual_ids,
        'assignment_choices': TestProject.ASSIGNMENT_TYPE_CHOICES,
        'radar_mode_choices': TestProject.RADAR_MODE_CHOICES,
        'current_radar_mode': project.radar_mode or 'role',
        'current_show_mixed_role': project.show_mixed_role,
        'categories_json': json.dumps(categories_data, ensure_ascii=False),
        'available_traits_json': json.dumps(_serialize_traits_for_form(), ensure_ascii=False),
        'project_traits_json': json.dumps(project_traits_data, ensure_ascii=False),
        'is_edit': True,
    }
    
    return render(request, 'admin/test_project_form.html', context)

@login_required
@admin_required
def test_project_detail(request, project_id):
    """測驗項目詳細資訊"""
    project = get_object_or_404(TestProject, id=project_id)
    
    # 獲取指派的企業
    assigned_enterprises = project.enterprise_assignments.select_related('enterprise_user__enterprise_profile').all()
    
    # 獲取分類和特質
    categories = project.categories.prefetch_related('traits').all()
    
    # 統計數據
    stats = {
        'categories_count': categories.count(),
        'traits_count': sum(cat.traits.count() for cat in categories),
        'assigned_enterprises_count': assigned_enterprises.count(),
    }
    
    context = {
        'project': project,
        'assigned_enterprises': assigned_enterprises,
        'categories': categories,
        'stats': stats,
    }
    
    return render(request, 'admin/test_project_detail.html', context)

@login_required
@admin_required
@require_POST
def test_project_delete(request, project_id):
    """刪除測驗項目"""
    project = get_object_or_404(TestProject, id=project_id)
    
    try:
        project_name = project.name
        project.delete()
        
        logger.info(f"管理員 {request.user.username} 刪除測驗項目：{project_name}")
        messages.success(request, f'測驗項目「{project_name}」已刪除')
    except Exception as e:
        logger.error(f"刪除測驗項目失敗：{str(e)}")
        messages.error(request, f'刪除失敗：{str(e)}')
    
    return redirect('test_project_list')

@login_required
@admin_required
@require_POST
def test_project_toggle_status(request, project_id):
    """切換測驗項目狀態"""
    project = get_object_or_404(TestProject, id=project_id)
    
    try:
        project.is_active = not project.is_active
        project.save()
        
        status_text = '啟用' if project.is_active else '停用'
        logger.info(f"管理員 {request.user.username} {status_text}測驗項目：{project.name}")
        messages.success(request, f'測驗項目「{project.name}」已{status_text}')
    except Exception as e:
        logger.error(f"切換狀態失敗：{str(e)}")
        messages.error(request, f'操作失敗：{str(e)}')
    
    return redirect('test_project_list')

# AJAX API 相關
@login_required
@admin_required
def api_test_project_assignments(request):
    """獲取測驗項目指派API"""
    if request.method == 'GET':
        project_id = request.GET.get('project_id')
        if project_id:
            try:
                project = TestProject.objects.get(id=project_id)
                assignments = project.enterprise_assignments.select_related('enterprise_user__enterprise_profile').all()
                
                data = []
                for assignment in assignments:
                    data.append({
                        'id': assignment.id,
                        'enterprise_id': assignment.enterprise_user.id,
                        'enterprise_name': assignment.enterprise_user.enterprise_profile.company_name,
                        'contact_person': assignment.enterprise_user.enterprise_profile.contact_person,
                        'assigned_at': assignment.assigned_at.strftime('%Y-%m-%d %H:%M'),
                        'is_active': assignment.is_active,
                        'assigned_quota': assignment.assigned_quota,
                        'used_quota': assignment.used_quota,
                        'remaining_quota': assignment.remaining_quota,
                        'is_unlimited': assignment.is_unlimited,
                    })
                
                return JsonResponse({'status': 'success', 'data': data})
            except TestProject.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': '測驗項目不存在'})
        else:
            return JsonResponse({'status': 'error', 'message': '缺少參數'})
    
    return JsonResponse({'status': 'error', 'message': '不支援的請求方法'})

@login_required
@admin_required
def test_project_assignments(request, project_id):
    """測驗項目指派管理"""
    project = get_object_or_404(TestProject, id=project_id)
    
    if request.method == 'POST':
        try:
            action = request.POST.get('action')
            
            if action == 'add_assignment':
                enterprise_ids = request.POST.getlist('enterprise_ids')
                raw_quota = request.POST.get('assigned_quota', '').strip()
                assigned_quota = 0
                if raw_quota:
                    try:
                        assigned_quota = int(raw_quota)
                        if assigned_quota < 0:
                            messages.warning(request, '可用份數不能為負數，已設為 0 (不限)。')
                            assigned_quota = 0
                    except ValueError:
                        messages.warning(request, '可用份數格式不正確，已設為 0 (不限)。')
                        assigned_quota = 0
                
                if enterprise_ids:
                    enterprises = User.objects.filter(id__in=enterprise_ids, user_type='enterprise').select_related('enterprise_profile')
                    created_names = []
                    skipped_names = []

                    for enterprise in enterprises:
                        if project.enterprise_assignments.filter(enterprise_user=enterprise).exists():
                            skipped_names.append(enterprise.enterprise_profile.company_name)
                            continue

                        assignment = TestProjectAssignment.objects.create(
                            test_project=project,
                            enterprise_user=enterprise,
                            assigned_by=request.user,
                            assigned_quota=assigned_quota
                        )
                        if assigned_quota > 0:
                            try:
                                record_enterprise_purchase(
                                    enterprise_user=enterprise,
                                    test_project=project,
                                    quantity=assigned_quota,
                                    created_by=request.user,
                                    assignment=assignment,
                                    order_number=generate_order_number('ASSIGN'),
                                    payment_date=timezone.now(),
                                    notes='指派頁面新增指派',
                                    adjust_assignment=False,
                                )
                            except Exception as exc:
                                logger.warning(f"建立指派時紀錄購買資訊失敗：{exc}")
                        safe_create_notification(
                            recipient=enterprise,
                            title=f"新增測驗指派：{project.name}",
                            message=(
                                f"管理員已將「{project.name}」指派給您的企業，"
                                f"目前可用份數為 {'不限' if assigned_quota == 0 else f'{assigned_quota} 份'}，"
                                "請前往快速邀請頁面安排受測人員。"
                            ),
                            notification_type='test_invitation',
                            metadata={'link': reverse('quick_invitation', args=[project.id])}
                        )
                        created_names.append(enterprise.enterprise_profile.company_name)

                    if created_names:
                        messages.success(
                            request,
                            '已指派給企業：' + '、'.join(created_names)
                        )
                    if skipped_names:
                        messages.warning(
                            request,
                            '以下企業已存在指派，略過：' + '、'.join(skipped_names)
                        )
                else:
                    messages.warning(request, '請至少選擇一間企業進行指派')

            elif action == 'toggle_assignment':
                assignment_id = request.POST.get('assignment_id')
                if assignment_id:
                    try:
                        assignment = project.enterprise_assignments.get(id=assignment_id)
                        assignment.is_active = not assignment.is_active
                        assignment.save(update_fields=['is_active'])

                        company_name = assignment.enterprise_user.enterprise_profile.company_name
                        logger.info(
                            "管理員 %s 切換企業指派狀態：project=%s enterprise=%s active=%s",
                            request.user.username,
                            project.name,
                            company_name,
                            assignment.is_active,
                        )
                        if assignment.is_active:
                            messages.success(
                                request,
                                f'已恢復企業「{company_name}」對「{project.name}」的測驗使用權。'
                            )
                            safe_create_notification(
                                recipient=assignment.enterprise_user,
                                title=f"測驗指派已恢復：{project.name}",
                                message=(
                                    f"管理員已恢復「{project.name}」的使用權，"
                                    "您可以繼續邀請受測者參加此測驗。"
                                ),
                                notification_type='test_invitation',
                                metadata={'link': reverse('quick_invitation', args=[project.id])}
                            )
                        else:
                            messages.success(
                                request,
                                f'已暫停企業「{company_name}」對「{project.name}」的測驗使用權。'
                            )
                            safe_create_notification(
                                recipient=assignment.enterprise_user,
                                title=f"測驗指派已暫停：{project.name}",
                                message=(
                                    f"管理員已暫停「{project.name}」的使用權。"
                                    "暫停期間既有資料仍可查閱，但請勿再建立新的測驗邀請。"
                                ),
                                notification_type='test_invitation',
                                metadata={'link': reverse('quick_invitation', args=[project.id])}
                            )
                    except TestProjectAssignment.DoesNotExist:
                        messages.error(request, '找不到指定的企業指派。')

            elif action == 'remove_assignment':
                assignment_id = request.POST.get('assignment_id')
                if assignment_id:
                    try:
                        with transaction.atomic():
                            assignment = project.enterprise_assignments.select_for_update().get(id=assignment_id)
                            enterprise_user = assignment.enterprise_user
                            company_name = enterprise_user.enterprise_profile.company_name

                            invitations = TestInvitation.objects.filter(
                                enterprise=enterprise_user,
                                test_project=project
                            )
                            invitation_ids = list(invitations.values_list('id', flat=True))
                            invitation_count = len(invitation_ids)
                            result_count = (
                                TestProjectResult.objects.filter(test_invitation_id__in=invitation_ids).count()
                                if invitation_ids else 0
                            )

                            if invitation_ids:
                                TestProjectResult.objects.filter(test_invitation_id__in=invitation_ids).delete()
                                TestInvitation.objects.filter(id__in=invitation_ids).delete()

                            assignment.delete()

                        detail_msg = (
                            f'刪除邀請 {invitation_count} 筆、測驗結果 {result_count} 筆。'
                            if invitation_count or result_count else '此企業尚未建立相關測驗資料。'
                        )
                        logger.info(
                            "管理員 %s 移除企業指派：project=%s enterprise=%s invitations=%s results=%s",
                            request.user.username,
                            project.name,
                            company_name,
                            invitation_count,
                            result_count,
                        )
                        messages.success(
                            request,
                            f'已移除企業「{company_name}」的指派。{detail_msg}'
                        )
                        safe_create_notification(
                            recipient=enterprise_user,
                            title=f"測驗指派已刪除：{project.name}",
                            message=(
                                f"管理員已移除「{project.name}」的測驗指派，"
                                "相關測驗邀請與結果皆已刪除。如需重新使用，請洽平台管理員。"
                            ),
                            notification_type='test_invitation'
                        )
                    except TestProjectAssignment.DoesNotExist:
                        messages.error(request, '找不到指定的企業指派。')

            elif action == 'batch_operation':
                batch_action = request.POST.get('batch_action')
                valid_actions = {'activate_all', 'deactivate_all', 'remove_all'}

                if batch_action not in valid_actions:
                    messages.warning(request, '請選擇要執行的批量操作。')
                else:
                    assignments_qs = project.enterprise_assignments.select_related(
                        'enterprise_user__enterprise_profile'
                    )

                    if not assignments_qs.exists():
                        messages.info(request, '目前沒有企業指派可供批次操作。')
                    elif batch_action == 'activate_all':
                        to_activate = [a for a in assignments_qs if not a.is_active]
                        if not to_activate:
                            messages.info(request, '所有企業指派已經是啟用狀態。')
                        else:
                            project.enterprise_assignments.filter(
                                id__in=[a.id for a in to_activate]
                            ).update(is_active=True)
                            for assignment in to_activate:
                                safe_create_notification(
                                    recipient=assignment.enterprise_user,
                                    title=f"測驗指派已恢復：{project.name}",
                                    message=(
                                        f"管理員已恢復「{project.name}」的使用權，"
                                        "您可以繼續邀請受測者參加此測驗。"
                                    ),
                                    notification_type='test_invitation',
                                    metadata={'link': reverse('quick_invitation', args=[project.id])}
                                )
                            messages.success(request, f'已啟用 {len(to_activate)} 間企業的測驗指派。')

                    elif batch_action == 'deactivate_all':
                        to_deactivate = [a for a in assignments_qs if a.is_active]
                        if not to_deactivate:
                            messages.info(request, '所有企業指派已經是停用狀態。')
                        else:
                            project.enterprise_assignments.filter(
                                id__in=[a.id for a in to_deactivate]
                            ).update(is_active=False)
                            for assignment in to_deactivate:
                                safe_create_notification(
                                    recipient=assignment.enterprise_user,
                                    title=f"測驗指派已暫停：{project.name}",
                                    message=(
                                        f"管理員已暫停「{project.name}」的使用權。"
                                        "暫停期間既有資料仍可查閱，但請勿再建立新的測驗邀請。"
                                    ),
                                    notification_type='test_invitation',
                                    metadata={'link': reverse('quick_invitation', args=[project.id])}
                                )
                            messages.success(request, f'已停用 {len(to_deactivate)} 間企業的測驗指派。')

                    elif batch_action == 'remove_all':
                        assignments_list = list(assignments_qs)
                        total_invitations_deleted = 0
                        total_results_deleted = 0
                        removed_companies = []

                        with transaction.atomic():
                            for assignment in assignments_list:
                                enterprise_user = assignment.enterprise_user
                                company_name = enterprise_user.enterprise_profile.company_name

                                invitation_ids = list(
                                    TestInvitation.objects.filter(
                                        enterprise=enterprise_user,
                                        test_project=project
                                    ).values_list('id', flat=True)
                                )
                                invitation_count = len(invitation_ids)

                                if invitation_ids:
                                    result_qs = TestProjectResult.objects.filter(
                                        test_invitation_id__in=invitation_ids
                                    )
                                    result_count = result_qs.count()
                                    result_qs.delete()
                                    TestInvitation.objects.filter(id__in=invitation_ids).delete()
                                else:
                                    result_count = 0

                                total_invitations_deleted += invitation_count
                                total_results_deleted += result_count
                                removed_companies.append(company_name)
                                assignment.delete()

                                safe_create_notification(
                                    recipient=enterprise_user,
                                    title=f"測驗指派已刪除：{project.name}",
                                    message=(
                                        f"管理員已移除「{project.name}」的測驗指派，"
                                        "相關測驗邀請與結果皆已刪除。如需重新使用，請洽平台管理員。"
                                    ),
                                    notification_type='test_invitation'
                                )

                        logger.info(
                            "管理員 %s 批次移除企業指派：project=%s enterprises=%s invitations=%s results=%s",
                            request.user.username,
                            project.name,
                            ', '.join(removed_companies),
                            total_invitations_deleted,
                            total_results_deleted,
                        )
                        messages.success(
                            request,
                            (
                                f"已移除 {len(removed_companies)} 間企業的指派，"
                                f"刪除邀請 {total_invitations_deleted} 筆、測驗結果 {total_results_deleted} 筆。"
                            )
                        )

            elif action == 'update_quota':
                assignment_id = request.POST.get('assignment_id')
                new_quota_raw = request.POST.get('assigned_quota', '').strip()
                if assignment_id:
                    try:
                            assignment = project.enterprise_assignments.get(id=assignment_id)
                            new_quota = int(new_quota_raw) if new_quota_raw != '' else 0
                            if new_quota < 0:
                                messages.warning(request, '可用份數不能為負數，已取消更新。')
                            elif new_quota != 0 and new_quota < assignment.used_quota:
                                messages.error(request, f'無法將可用份數設為 {new_quota}，已使用份數為 {assignment.used_quota}。')
                            else:
                                old_quota = assignment.assigned_quota
                                assignment.assigned_quota = new_quota
                                assignment.save(update_fields=['assigned_quota'])
                                if new_quota > 0 and (old_quota == 0 or new_quota > old_quota):
                                    delta = new_quota if old_quota == 0 else new_quota - old_quota
                                    try:
                                        record_enterprise_purchase(
                                            enterprise_user=assignment.enterprise_user,
                                            test_project=assignment.test_project,
                                            quantity=delta,
                                            created_by=request.user,
                                            assignment=assignment,
                                            order_number=generate_order_number('ADJ'),
                                            payment_date=timezone.now(),
                                            notes='指派頁面調整份數',
                                            adjust_assignment=False,
                                        )
                                    except Exception as exc:
                                        logger.warning(f"更新份數時記錄購買資訊失敗：{exc}")
                                messages.success(request, f'已更新企業 {assignment.enterprise_user.enterprise_profile.company_name} 的可用份數。')
                                safe_create_notification(
                                    recipient=assignment.enterprise_user,
                                    title=f"測驗份數更新：{project.name}",
                                    message=(
                                        f"「{project.name}」的可用份數已調整為 "
                                        f"{'不限' if new_quota == 0 else f'{new_quota} 份'}。"
                                    ),
                                    notification_type='test_invitation',
                                    metadata={'link': reverse('quick_invitation', args=[project.id])}
                                )
                    except TestProjectAssignment.DoesNotExist:
                        messages.error(request, '找不到指定的企業指派。')
                    except ValueError:
                        messages.error(request, '可用份數必須為整數。')

            return redirect('test_project_assignments', project_id=project.id)
            
        except Exception as e:
            logger.error(f"指派操作失敗：{str(e)}")
            messages.error(request, f'操作失敗：{str(e)}')
    
    # 獲取已指派的企業
    assigned_enterprises = project.enterprise_assignments.select_related('enterprise_user__enterprise_profile').all()
    
    # 獲取可指派的企業（排除已指派的）
    assigned_ids = [a.enterprise_user.id for a in assigned_enterprises]
    available_enterprises = User.objects.filter(
        user_type='enterprise',
        enterprise_profile__verification_status='approved'
    ).exclude(id__in=assigned_ids).select_related('enterprise_profile')
    
    context = {
        'project': project,
        'assigned_enterprises': assigned_enterprises,
        'available_enterprises': available_enterprises,
    }
    
    return render(request, 'admin/test_project_assignments.html', context)

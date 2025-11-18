from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from .models import User, TestInvitee, TestInvitation, TestTemplate, TestCategory, Notification, TestProject, TestProjectAssignment
from .purchase_services import log_quota_usage
from .services.test_result_listing import build_test_result_listing, ListingOptions
import logging

logger = logging.getLogger(__name__)

def enterprise_required(view_func):
    """企業用戶權限裝飾器"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.user_type != 'enterprise':
            messages.error(request, '此功能僅限企業用戶使用')
            return redirect('dashboard')
        if not hasattr(request.user, 'enterprise_profile') or request.user.enterprise_profile.verification_status != 'approved':
            messages.error(request, '企業尚未通過審核，無法使用此功能')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@enterprise_required
def enterprise_test_dashboard(request):
    """企業測驗管理儀表板"""
    user = request.user
    
    # 統計數據 - 修改這部分，加入所有狀態的統計
    stats = {
        'total_invitees': TestInvitee.objects.filter(enterprise=user).count(),
        'total_invitations': TestInvitation.objects.filter(enterprise=user).count(),
        'pending_invitations': TestInvitation.objects.filter(enterprise=user, status='pending').count(),
        'in_progress_invitations': TestInvitation.objects.filter(enterprise=user, status='in_progress').count(),
        'completed_invitations': TestInvitation.objects.filter(enterprise=user, status='completed').count(),
        'expired_invitations': TestInvitation.objects.filter(enterprise=user, status='expired').count(),
        'cancelled_invitations': TestInvitation.objects.filter(enterprise=user, status='cancelled').count(),
    }
    
    # 最近的受測人員
    recent_invitees = TestInvitee.objects.filter(enterprise=user).order_by('-created_at')[:5]
    
    # 最近的測驗邀請
    recent_invitations = TestInvitation.objects.filter(enterprise=user).select_related('invitee', 'test_template', 'test_project').order_by('-invited_at')[:5]
    
    # 可用的測驗範本（如果還在使用舊系統）
    available_templates = TestTemplate.objects.filter(is_active=True)[:10]
    
    context = {
        'stats': stats,
        'recent_invitees': recent_invitees,
        'recent_invitations': recent_invitations,
        'available_templates': available_templates,
    }
    
    return render(request, 'test_management/dashboard.html', context)

@login_required
@enterprise_required
def invitee_list(request):
    """受測人員列表"""
    user = request.user
    invitees = TestInvitee.objects.filter(enterprise=user)
    
    # 搜尋功能
    search = request.GET.get('search', '')
    if search:
        invitees = invitees.filter(
            Q(name__icontains=search) | 
            Q(email__icontains=search) |
            Q(position__icontains=search)  # 改為搜尋職位
        )
    
    invitees = invitees.order_by('-created_at')
    
    # 分頁
    paginator = Paginator(invitees, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
    }
    
    return render(request, 'test_management/invitee_list.html', context)


@login_required
@enterprise_required
@require_POST
def create_invitee(request):
    """新增受測人員 AJAX API"""
    from .invitee_forms import TestInviteeForm
    
    try:
        form = TestInviteeForm(enterprise_user=request.user, data=request.POST)
        
        if form.is_valid():
            invitee = form.save()
            
            # 回傳成功資料
            return JsonResponse({
                'success': True,
                'message': f'受測人員「{invitee.name}」新增成功！',
                'invitee': {
                    'id': invitee.id,
                    'name': invitee.name,
                    'email': invitee.email,
                    'phone': invitee.phone or '-',
                    'position': invitee.position or '-',
                    'created_at': invitee.created_at.strftime('%Y-%m-%d'),
                }
            })
        else:
            # 回傳表單錯誤
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
            
    except Exception as e:
        logger.error(f"新增受測人員失敗：{str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'新增失敗：{str(e)}'
        })

@login_required
@enterprise_required
def edit_invitee(request, invitee_id):
    """編輯受測人員"""
    from .invitee_forms import TestInviteeForm
    
    invitee = get_object_or_404(TestInvitee, id=invitee_id, enterprise=request.user)
    
    if request.method == 'POST':
        form = TestInviteeForm(enterprise_user=request.user, data=request.POST, instance=invitee)
        
        if form.is_valid():
            invitee = form.save()
            messages.success(request, f'受測人員「{invitee.name}」資料更新成功！')
            return redirect('invitee_list')
    else:
        form = TestInviteeForm(enterprise_user=request.user, instance=invitee)
    
    context = {
        'form': form,
        'invitee': invitee,
        'is_edit': True,
    }
    
    return render(request, 'test_management/invitee_form.html', context)

@login_required
@enterprise_required
@require_POST
def delete_invitee(request, invitee_id):
    """刪除受測人員"""
    invitee = get_object_or_404(TestInvitee, id=invitee_id, enterprise=request.user)
    
    # 檢查是否有關聯的測驗邀請
    invitation_count = TestInvitation.objects.filter(invitee=invitee).count()
    
    if invitation_count > 0:
        return JsonResponse({
            'success': False,
            'message': f'無法刪除「{invitee.name}」，因為已有 {invitation_count} 筆測驗邀請記錄'
        })
    
    try:
        invitee_name = invitee.name
        invitee.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'受測人員「{invitee_name}」刪除成功！'
        })
        
    except Exception as e:
        logger.error(f"刪除受測人員失敗：{str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'刪除失敗：{str(e)}'
        })
    
@login_required
@enterprise_required
def invitation_list(request):
    """測驗邀請列表"""
    user = request.user
    invitations = TestInvitation.objects.filter(enterprise=user).select_related('invitee', 'test_template')

    # 過濾功能
    status = request.GET.get('status', '')
    if status:
        invitations = invitations.filter(status=status)

    search = request.GET.get('search', '').strip()
    if search:
        invitations = invitations.filter(
            Q(invitee__name__icontains=search) |
            Q(invitee__email__icontains=search)
        )

    invitations = invitations.order_by('-invited_at')

    # 分頁
    paginator = Paginator(invitations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status,
        'status_choices': TestInvitation.STATUS_CHOICES,
        'search': search,
    }
    
    return render(request, 'test_management/invitation_list.html', context)

@login_required
@enterprise_required
def test_templates(request):
    """企業可用測驗項目列表"""
    user = request.user
    
    # 使用新的 TestProject 模型，獲取企業可用的測驗項目
    projects = TestProject.get_available_projects_for_user(user)
    
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

    # 為每個項目計算邀請統計 - 修改這部分
    projects_with_stats = []
    for project in projects:
        invitations = TestInvitation.objects.filter(
            enterprise=user,
            test_project=project
        )
        
        project.invitation_stats = {
            'total': invitations.count(),
            'pending': invitations.filter(status='pending').count(),
            'in_progress': invitations.filter(status='in_progress').count(),
            'completed': invitations.filter(status='completed').count(),
            'expired': invitations.filter(status='expired').count(),
            'cancelled': invitations.filter(status='cancelled').count(),
        }
        projects_with_stats.append(project)

    # 分頁
    paginator = Paginator(projects_with_stats, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 統計數據
    stats = {
        'total': projects.count(),
        'all_open': projects.filter(assignment_type='all_open').count(),
        'enterprise_only': projects.filter(assignment_type='enterprise_only').count(),
        'specific_assignment': projects.filter(assignment_type='specific_assignment').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'assignment_type_filter': assignment_type,
        'stats': stats,
        'assignment_type_choices': TestProject.ASSIGNMENT_TYPE_CHOICES,
    }
    
    return render(request, 'test_management/test_templates.html', context)

@login_required
@enterprise_required
def enterprise_test_project_detail(request, project_id):
    """企業端測驗項目詳情"""
    
    # 獲取測驗項目，並檢查權限
    project = get_object_or_404(TestProject, id=project_id)
    
    # 權限檢查：確保企業用戶有權限查看此測驗項目
    if not project.get_available_for_user(request.user):
        messages.error(request, '您沒有權限查看此測驗項目')
        return redirect('test_templates')
    
    # 獲取分類和特質
    categories = project.categories.prefetch_related('traits').all()
    
    # 獲取此企業對該測驗項目的邀請統計 - 修改這部分
    invitations = TestInvitation.objects.filter(
        enterprise=request.user,
        test_project=project
    )
    
    invitation_stats = {
        'total': invitations.count(),
        'pending': invitations.filter(status='pending').count(),
        'in_progress': invitations.filter(status='in_progress').count(),
        'completed': invitations.filter(status='completed').count(),
        'expired': invitations.filter(status='expired').count(),
        'cancelled': invitations.filter(status='cancelled').count(),
    }
    
    context = {
        'project': project,
        'categories': categories,
        'invitation_stats': invitation_stats,
    }
    
    return render(request, 'test_management/enterprise_test_project_detail.html', context)

@login_required
@enterprise_required
def enterprise_test_project_stats(request, project_id):
    """企業端測驗項目統計"""
    # 獲取測驗項目，並檢查權限
    project = get_object_or_404(TestProject, id=project_id)
    
    # 權限檢查：確保企業用戶有權限查看此測驗項目
    if not project.get_available_for_user(request.user):
        messages.error(request, '您沒有權限查看此測驗項目')
        return redirect('test_templates')
    
    invitations = TestInvitation.objects.filter(
        enterprise=request.user,
        test_project=project
    ).select_related('invitee', 'test_project', 'testprojectresult')

    listing_context = build_test_result_listing(
        request,
        invitations,
        options=ListingOptions(
            user=request.user,
            per_page=50,
            allow_project_filter=False,
            locked_project_id=project.id,
        ),
    )
    
    # 統計數據 - 修改這部分
    all_invitations = TestInvitation.objects.filter(
        enterprise=request.user,
        test_project=project
    )
    
    invitation_stats = {
        'total': all_invitations.count(),
        'pending': all_invitations.filter(status='pending').count(),
        'in_progress': all_invitations.filter(status='in_progress').count(),
        'completed': all_invitations.filter(status='completed').count(),
        'expired': all_invitations.filter(status='expired').count(),
        'cancelled': all_invitations.filter(status='cancelled').count(),
    }
    
    context = {
        **listing_context,
        'project_overview': {
            'project': project,
            'invitation_stats': invitation_stats,
        },
        'lock_project_filter': True,
    }
    
    return render(request, 'test_management/test_result_list.html', context)

@login_required
@enterprise_required
def create_invitation(request, project_id):
    """建立測驗邀請"""
    # 🔧 調試日誌
    logger.info(f"=== 建立測驗邀請請求 ===")
    logger.info(f"請求方法: {request.method}")
    logger.info(f"用戶: {request.user}")
    logger.info(f"項目ID: {project_id}")
    logger.info(f"POST 數據: {request.POST}")
    
    from .invitation_forms import TestInvitationForm
    from utils.url_shortener import URLShortenerService
    from datetime import timedelta
    import uuid
    
    project = get_object_or_404(TestProject, id=project_id)
    
    # 權限檢查
    if not project.get_available_for_user(request.user):
        messages.error(request, '您沒有權限使用此測驗項目')
        return redirect('test_templates')
    
    if request.method == 'POST':
        form = TestInvitationForm(
            enterprise_user=request.user,
            test_project=project,
            data=request.POST
        )
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    invitees = form.cleaned_data['invitees']
                    expires_at = form.cleaned_data['expires_at']
                    custom_message = form.cleaned_data['custom_message']
                    send_immediately = form.cleaned_data['send_immediately']
                    
                    assignment = TestProjectAssignment.objects.select_for_update().filter(
                        test_project=project,
                        enterprise_user=request.user
                    ).first()

                    required_slots = len(invitees)
                    if assignment and not assignment.has_available_quota(required_slots):
                        remaining = assignment.remaining_quota if assignment.remaining_quota is not None else 0
                        messages.error(request, f'剩餘可用份數不足（剩餘 {remaining} 份），無法邀請 {required_slots} 人。')
                        return redirect('create_invitation', project_id=project_id)

                    created_invitations = []
                    
                    for invitee in invitees:
                        # 生成邀請碼
                        invitation_code = uuid.uuid4()
                        
                        # 建立邀請記錄
                        invitation = TestInvitation.objects.create(
                            enterprise=request.user,
                            invitee=invitee,
                            test_project=project,
                            invitation_code=invitation_code,
                            custom_message=custom_message,
                            expires_at=expires_at,
                            points_consumed=1,
                            status='pending'
                        )
                        
                        # 生成短網址
                        short_url_data = URLShortenerService.generate_short_url(
                            original_url=project.test_link,
                            invitation_id=invitation.id
                        )
                        
                        # 儲存短網址資訊到邀請記錄
                        invitation.result_data = {
                            'short_url': short_url_data['short_url'],
                            'short_code': short_url_data['short_code'],
                            'original_url': short_url_data['original_url']
                        }
                        invitation.save()
                        
                        # 更新受測人員統計
                        invitee.invited_count += 1
                        invitee.save()

                        created_invitations.append(invitation)

                        if assignment:
                            assignment.consume_quota()
                            log_quota_usage(
                                assignment=assignment,
                                invitation=invitation,
                                action='consume',
                                created_by=request.user,
                            )
                    
                    # 發送邀請郵件
                    logger.info(f"準備發送邀請郵件，send_immediately: {send_immediately}, 邀請數量: {len(created_invitations)}")
                    if send_immediately:
                        from utils.email_service import EmailService
                        success_count = 0
                        failed_emails = []
                        
                        for invitation in created_invitations:
                            logger.info(f"正在發送邀請給: {invitation.invitee.email}")
                            if EmailService.send_test_invitation_email(invitation):
                                success_count += 1
                                logger.info(f"邀請郵件發送成功: {invitation.invitee.email}")
                            else:
                                failed_emails.append(invitation.invitee.email)
                                logger.error(f"邀請郵件發送失敗: {invitation.invitee.email}")
                        
                        if success_count == len(created_invitations):
                            messages.success(request, f'成功發送 {success_count} 份測驗邀請！')
                        else:
                            messages.warning(request, f'發送了 {success_count}/{len(created_invitations)} 份邀請，部分郵件發送失敗。失敗的郵件地址: {", ".join(failed_emails)}')
                    else:
                        messages.success(request, f'成功建立 {len(created_invitations)} 份測驗邀請！')
                    
                    return redirect('enterprise_test_project_stats', project_id=project.id)
                
                # 檢查是否為 AJAX 請求
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'成功發送 {len(created_invitations)} 份測驗邀請！',
                        'redirect_url': reverse('enterprise_test_project_stats', args=[project.id])
                    })
                else:
                    # 一般表單提交，重導向
                    return redirect('enterprise_test_project_stats', project_id=project.id)
                    
                    
            except Exception as e:
                logger.error(f"建立測驗邀請失敗：{str(e)}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'建立邀請失敗：{str(e)}'
                    })
                else:
                    messages.error(request, f'建立邀請失敗：{str(e)}')
        else:
            # 表單驗證失敗
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': '表單驗證失敗，請檢查輸入資料',
                    'errors': form.errors
                })
            else:
                # 非AJAX請求的表單驗證失敗，顯示錯誤訊息
                messages.error(request, '表單驗證失敗，請檢查輸入資料')
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{form.fields[field].label}: {error}')
    else:
        # GET請求，初始化空表單
        form = TestInvitationForm(
            enterprise_user=request.user,
            test_project=project
        )
    
    # 獲取受測人員統計
    invitees = TestInvitee.objects.filter(enterprise=request.user)
    invitee_stats = {
        'total': invitees.count(),
        'no_invitations': invitees.filter(invited_count=0).count(),
    }
    
    context = {
        'form': form,
        'project': project,
        'invitee_stats': invitee_stats,
    }
    
    return render(request, 'test_management/create_invitation.html', context)

@login_required
@enterprise_required
def quick_invitation(request, project_id):
    """快速邀請（新增受測人員並立即邀請）"""
    
    # 🔧 調試日誌 - 加在這裡
    logger.info(f"=== 快速邀請請求 ===")
    logger.info(f"請求方法: {request.method}")
    logger.info(f"用戶: {request.user}")
    logger.info(f"項目ID: {project_id}")
    logger.info(f"POST 數據: {request.POST}")
    
    from .invitation_forms import QuickInvitationForm
    from .invitee_forms import TestInviteeForm
    from utils.url_shortener import URLShortenerService
    from datetime import timedelta
    import uuid
    
    project = get_object_or_404(TestProject, id=project_id)
    
    # 權限檢查
    if not project.get_available_for_user(request.user):
        messages.error(request, '您沒有權限使用此測驗項目')
        return redirect('test_templates')
    
    if request.method == 'POST':
        logger.info("🔧 接收到 POST 請求，開始處理表單")
        
        form = QuickInvitationForm(
            enterprise_user=request.user,
            test_project=project,
            data=request.POST
        )
        
        logger.info(f"🔧 表單驗證結果: {form.is_valid()}")
        if not form.is_valid():
            logger.error(f"🔧 表單驗證失敗: {form.errors}")
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    assignment = TestProjectAssignment.objects.select_for_update().filter(
                        test_project=project,
                        enterprise_user=request.user
                    ).first()

                    if assignment and not assignment.has_available_quota():
                        remaining = assignment.remaining_quota if assignment.remaining_quota is not None else 0
                        messages.error(request, f'剩餘可用份數不足（剩餘 {remaining} 份），無法建立新的邀請。')
                        return redirect('quick_invitation', project_id=project_id)

                    # 建立或獲取受測人員
                    if hasattr(form, 'existing_invitee'):
                        invitee = form.existing_invitee
                    else:
                        invitee = TestInvitee.objects.create(
                            enterprise=request.user,
                            name=form.cleaned_data['name'],
                            email=form.cleaned_data['email'],
                            phone=form.cleaned_data['phone'],
                            position=form.cleaned_data['position']
                        )
                    
                    # 計算過期時間（支援自訂時間）
                    expires_at = form.cleaned_data.get('expires_at')
                    if not expires_at:
                        # 如果表單沒有 expires_at（舊邏輯備用）
                        days = int(form.cleaned_data['expires_in_days'])
                        expires_at = timezone.now() + timedelta(days=days)
                    
                    invitation_code = uuid.uuid4()
                    
                    # 建立邀請
                    invitation = TestInvitation.objects.create(
                        enterprise=request.user,
                        invitee=invitee,
                        test_project=project,
                        invitation_code=invitation_code,
                        custom_message=form.cleaned_data['custom_message'],
                        expires_at=expires_at,
                        points_consumed=1,
                        status='pending'
                    )
                    
                    # 生成短網址
                    short_url_data = URLShortenerService.generate_short_url(
                        original_url=project.test_link,
                        invitation_id=invitation.id
                    )
                    
                    invitation.result_data = {
                        'short_url': short_url_data['short_url'],
                        'short_code': short_url_data['short_code'],
                        'original_url': short_url_data['original_url']
                    }
                    invitation.save()
                    
                    # 更新統計
                    invitee.invited_count += 1
                    invitee.save()
                    
                    if assignment:
                        assignment.consume_quota()
                        log_quota_usage(
                            assignment=assignment,
                            invitation=invitation,
                            action='consume',
                            created_by=request.user,
                        )
                    
                    # 發送邀請郵件
                    from utils.email_service import EmailService
                    if EmailService.send_test_invitation_email(invitation):
                        messages.success(request, f'成功邀請「{invitee.name}」參加測驗！')
                    else:
                        messages.warning(request, f'邀請建立成功，但郵件發送失敗，請稍後重新發送')
                    
                    return redirect('enterprise_test_project_stats', project_id=project.id)
                    
            except Exception as e:
                logger.error(f"快速邀請失敗：{str(e)}")
                messages.error(request, f'邀請失敗：{str(e)}')
    else:
        form = QuickInvitationForm(
            enterprise_user=request.user,
            test_project=project
        )
    
    context = {
        'form': form,
        'project': project,
        'is_quick_mode': True,
    }
    
    return render(request, 'test_management/create_invitation.html', context)


@login_required
@enterprise_required
def invitation_detail(request, invitation_id):
    """邀請詳情"""
    invitation = get_object_or_404(
        TestInvitation, 
        id=invitation_id, 
        enterprise=request.user
    )
    
    # 獲取此受測人員的其他邀請（用於側邊欄顯示）
    other_invitations = TestInvitation.objects.filter(
        enterprise=request.user,
        invitee=invitation.invitee
    ).exclude(id=invitation.id).order_by('-invited_at')[:5]
    
    context = {
        'invitation': invitation,
        'other_invitations': other_invitations,
    }
    
    return render(request, 'test_management/invitation_detail.html', context)

@login_required
@enterprise_required
@require_POST
def resend_invitation(request, invitation_id):
    """重新發送邀請"""
    invitation = get_object_or_404(
        TestInvitation, 
        id=invitation_id, 
        enterprise=request.user
    )
    
    try:
        # 檢查邀請狀態
        if invitation.status == 'completed':
            return JsonResponse({
                'success': False,
                'message': '已完成的測驗無法重新發送邀請'
            })
        
        if invitation.status == 'cancelled':
            return JsonResponse({
                'success': False,
                'message': '已取消的邀請無法重新發送'
            })
        
        # 重新生成短網址
        from utils.url_shortener import URLShortenerService
        project = invitation.test_project
        short_url_data = URLShortenerService.generate_short_url(
            original_url=project.test_link,
            invitation_id=invitation.id
        )
        
        # 更新邀請資料
        invitation.result_data = {
            'short_url': short_url_data['short_url'],
            'short_code': short_url_data['short_code'],
            'original_url': short_url_data['original_url']
        }
        invitation.status = 'pending'
        invitation.save()
        
        # 重新發送郵件
        from utils.email_service import EmailService
        if EmailService.send_test_invitation_email(invitation):
            logger.info(f"重新發送邀請成功：{invitation.id}")
            return JsonResponse({
                'success': True,
                'message': f'已重新發送邀請給「{invitation.invitee.name}」'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '郵件發送失敗，請稍後再試'
            })
            
    except Exception as e:
        logger.error(f"重新發送邀請失敗：{str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'重新發送失敗：{str(e)}'
        })

@login_required
@enterprise_required
@require_POST
def cancel_invitation(request, invitation_id):
    """取消邀請"""
    invitation = get_object_or_404(
        TestInvitation, 
        id=invitation_id, 
        enterprise=request.user
    )
    
    try:
        # 檢查邀請狀態
        if invitation.status == 'completed':
            return JsonResponse({
                'success': False,
                'message': '已完成的測驗無法取消'
            })
        
        if invitation.status == 'cancelled':
            return JsonResponse({
                'success': False,
                'message': '邀請已經被取消了'
            })
            
        # 檢查是否已經開始測驗（如果有started_at時間，表示已開始）
        if invitation.started_at:
            return JsonResponse({
                'success': False,
                'message': '受測者已開始測驗，無法取消邀請'
            })
        
        with transaction.atomic():
            assignment = TestProjectAssignment.objects.select_for_update().filter(
                test_project=invitation.test_project,
                enterprise_user=request.user
            ).first()

            # 更新邀請狀態
            invitation.status = 'cancelled'
            invitation.save()

            if assignment:
                assignment.release_quota()
                log_quota_usage(
                    assignment=assignment,
                    invitation=invitation,
                    action='release',
                    created_by=request.user,
                )
        
        logger.info(f"取消邀請成功：{invitation.id}")
        return JsonResponse({
            'success': True,
            'message': f'已取消對「{invitation.invitee.name}」的邀請'
        })
            
    except Exception as e:
        logger.error(f"取消邀請失敗：{str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'取消失敗：{str(e)}'
        })

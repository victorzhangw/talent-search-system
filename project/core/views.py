from django.http import HttpResponse, JsonResponse
from django.views.generic import TemplateView
import time
import re
import requests
import json
# ===== 登入=====
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.views import LogoutView as AuthLogoutView
from django.urls import reverse, reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
# ===== 權限 =====
from django.views.generic import TemplateView

# ===== 權限測試 ======
from .decorators import check_permission
from django.shortcuts import render,redirect

# ===== 匯出的通用裝飾器
from django.utils.decorators import method_decorator
from utils.view_decorators import exportable
from .export_views import generate_sample_quotes
from django.core.paginator import Paginator

from django.contrib.auth import login
from django.contrib import messages
from django.shortcuts import get_object_or_404
from .forms import IndividualRegistrationForm, EnterpriseRegistrationForm, EmailAuthenticationForm
from .models import User
from utils.email_service import EmailService
from .notification_service import NotificationService

# ====== 忘記密碼
from django.contrib.auth.hashers import make_password
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
import uuid

# ====== 建立帳號管理者審核
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator

# ====== 點數
from utils.point_service import PointService, require_points

# 爬蟲
import logging
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import (
    CrawlerConfig, TestInvitation, TestProjectResult, 
    TestProject, TestInvitee
)

from utils.crawler_service import PITestResultCrawler

logger = logging.getLogger(__name__)

# ===== 權限裝飾器定義 =====

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

def enterprise_required(view_func):
    """企業用戶權限裝飾器"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.user_type != 'enterprise':
            messages.error(request, '此功能僅限企業用戶使用')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

class IndexView(TemplateView):
    """智能首頁 - 根據登入狀態跳轉"""
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # 已登入用戶根據類型跳轉到對應儀表板
            return redirect('dashboard')
        else:
            # 未登入用戶跳轉到登入頁面
            return redirect('login')
        
@check_permission('order_manage')
def order_view(request):
    return render(request, 'order.html')

@check_permission('shipment_manage')
def shipment_view(request):
    return render(request, 'shipment.html')

def test_login(request, user_type):
    # 模擬不同權限的用戶登入
    if user_type == 'business':
        # 業務人員權限
        request.session['user_permissions'] = ['quote_manage', 'order_manage']
    elif user_type == 'admin':
        # 管理員權限
        request.session['user_permissions'] = ['quote_manage', 'order_manage', 'shipment_manage']
    return redirect('home')

from utils.permission_handler import PermissionHandler

def test_login(request, user_type):
    # 將用戶類型存儲在 cookie 中
    response = redirect('home')
    response.set_cookie('user_type', user_type)
    return response

# 添加一個上下文處理器，使權限在所有模板中可用
def permission_context_processor(request):
    user_type = request.COOKIES.get('user_type', '')
    permissions = PermissionHandler.get_permissions(user_type)
    print(f"Current user type: {user_type}, Permissions: {permissions}")  # 添加調試輸出
    return {
        'user_permissions': permissions
    }


# =========================== 註冊功能 ===========================
class LoginView(AuthLoginView):
    template_name = 'auth/login.html'
    redirect_authenticated_user = True  # 已登入用戶自動跳轉
    authentication_form = EmailAuthenticationForm
    
    def get(self, request, *args, **kwargs):
        """GET請求時清除可能殘留的訊息"""
        # 清除任何可能從登出頁面殘留的訊息
        if not request.user.is_authenticated:
            # 只有在用戶未登入時才清除訊息，避免清除有用的訊息
            if hasattr(request, '_messages'):
                from django.contrib.messages.api import get_messages
                storage = get_messages(request)
                # 遍歷並清空所有訊息
                list(storage)
        
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        """驗證成功前檢查企業用戶審核狀態"""
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')

        # 先檢查用戶是否存在，不論is_active狀態
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(username=username)
            # 檢查密碼是否正確
            if user.check_password(password):
                # 如果是企業用戶，檢查審核狀態
                if user.user_type == 'enterprise' and hasattr(user, 'enterprise_profile'):
                    if user.enterprise_profile.verification_status == 'pending':
                        messages.warning(self.request, '目前註冊需求審核中，審核通過後才能登入')
                        return self.form_invalid(form)
                    elif user.enterprise_profile.verification_status == 'rejected':
                        messages.error(self.request, '註冊申請已被拒絕，如有疑問請聯繫客服')
                        return self.form_invalid(form)
                
                # 檢查帳號是否已啟用（Email驗證）
                if not user.is_active:
                    if user.user_type == 'enterprise':
                        messages.warning(self.request, '請先完成信箱驗證，檢查您的郵件並點擊驗證連結')
                    else:
                        messages.warning(self.request, '請先完成信箱驗證，檢查您的郵件並點擊驗證連結')
                    return self.form_invalid(form)
            else:
                # 密碼錯誤，讓Django處理
                pass
        except User.DoesNotExist:
            # 用戶不存在，讓Django處理
            pass
        
        # 正常登入流程
        return super().form_valid(form)
    
    def get_success_url(self):
        # 根據用戶類型跳轉到不同頁面
        user = self.request.user
        next_url = self.request.GET.get('next')
        
        if next_url:
            return next_url
        
        if user.user_type == 'admin':
            return reverse_lazy('dashboard')
        elif user.user_type == 'enterprise':
            return reverse_lazy('dashboard')  # 之後改為企業儀表板
        elif user.user_type == 'individual':
            return reverse_lazy('dashboard')  # 之後改為個人儀表板
        
        return reverse_lazy('dashboard')
    
    def form_invalid(self, form):
        """表單驗證失敗時的處理，包括檢查企業用戶狀態"""
        # 檢查是否已有自訂錯誤訊息
        existing_messages = list(messages.get_messages(self.request))
        if existing_messages:
            # 只重新添加與當前登入失敗相關的訊息，避免殘留的成功訊息
            for msg in existing_messages:
                # 過濾掉非錯誤類型的訊息（例如成功邀請的訊息）
                if msg.level in [messages.ERROR, messages.WARNING]:
                    messages.add_message(self.request, msg.level, msg.message)
            return super().form_invalid(form)
        
        # 沒有自訂訊息，檢查用戶名是否對應企業用戶
        username = form.cleaned_data.get('username') if form.cleaned_data else self.request.POST.get('username')
        
        if username:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                user = User.objects.get(username=username)
                
                # 如果是企業用戶，優先顯示審核狀態訊息
                if user.user_type == 'enterprise' and hasattr(user, 'enterprise_profile'):
                    if user.enterprise_profile.verification_status == 'pending':
                        if user.is_active:
                            messages.warning(self.request, '目前註冊需求審核中，審核通過後才能登入')
                        else:
                            messages.warning(self.request, '請先完成信箱驗證，並等待企業審核通過')
                        return super().form_invalid(form)
                    elif user.enterprise_profile.verification_status == 'rejected':
                        messages.error(self.request, '註冊申請已被拒絕，如有疑問請聯繫客服')
                        return super().form_invalid(form)
                
                # 檢查Email驗證狀態
                if not user.is_active:
                    messages.warning(self.request, '請先完成信箱驗證，檢查您的郵件並點擊驗證連結')
                    return super().form_invalid(form)
                    
            except User.DoesNotExist:
                pass
        
        # 預設錯誤訊息
        messages.error(self.request, '帳號或密碼錯誤，請重新輸入。')
        return super().form_invalid(form)

class LogoutView(AuthLogoutView):
    next_page = reverse_lazy('login')  # 登出後跳轉到登入頁面
    
    def dispatch(self, request, *args, **kwargs):
        # 在執行登出前清除所有訊息
        if hasattr(request, '_messages'):
            # 清除當前請求中的所有訊息
            from django.contrib.messages.api import get_messages
            storage = get_messages(request)
            # 遍歷並清空所有訊息
            list(storage)
        
        response = super().dispatch(request, *args, **kwargs)
        
        # 登出後再次確保清除session中的訊息
        if hasattr(request, 'session'):
            # 清除session中可能殘留的訊息
            if '_messages' in request.session:
                del request.session['_messages']
        
        return response

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'
    login_url = 'login'  # 未登入時跳轉的頁面

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 添加儀表板需要的數據
        return context
    
class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "core/index.html"
    login_url = 'login'
    
    def dispatch(self, request, *args, **kwargs):
        # 如果用戶未登入，重定向到登入頁面
        if not request.user.is_authenticated:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

class FAQView(LoginRequiredMixin, TemplateView):
    template_name = "core/faq.html"
    login_url = 'login'


class UserListView(TemplateView):
    template_name = 'user/user_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 這裡之後會加入真實的用戶數據
        context['users'] = [
            {
                'username': 'admin',
                'name': '系統管理員',
                'department': '資訊部',
                'role': '管理員',
                'email': 'admin@example.com',
                'status': '啟用',
                'last_login': '2024-02-24 10:30'
            },
            # 可以添加更多測試數據
        ]
        return context

class RoleListView(TemplateView):
    template_name = 'user/role_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 這裡之後會加入真實的角色數據
        context['roles'] = [
            {
                'name': '系統管理員',
                'description': '擁有所有系統權限',
                'user_count': 1,
                'created_at': '2024-02-24'
            },
            {
                'name': '一般用戶',
                'description': '基本操作權限',
                'user_count': 5,
                'created_at': '2024-02-24'
            },
        ]
        return context
        

class IndividualRegisterView(TemplateView):
    """個人用戶註冊"""
    template_name = 'auth/individual_register.html'
    
    def get(self, request, *args, **kwargs):
        # 清除之前的訊息
        storage = messages.get_messages(request)
        for message in storage:
            pass  # 迭代會清除訊息
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = IndividualRegistrationForm()
        return context
    
    def post(self, request, *args, **kwargs):
        form = IndividualRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # 發送驗證郵件
            if EmailService.send_verification_email(user):
                messages.success(request, f'註冊成功！我們已發送驗證郵件至 {user.email}，請檢查您的信箱並點擊驗證連結。')
            else:
                messages.warning(request, '註冊成功，但驗證郵件發送失敗，請聯繫客服。')
            
            return redirect('register_success')
        
        return render(request, self.template_name, {'form': form})

class EnterpriseRegisterView(TemplateView):
    """企業用戶註冊"""
    template_name = 'auth/enterprise_register.html'
    
    def get(self, request, *args, **kwargs):
        # 清除之前的訊息
        storage = messages.get_messages(request)
        for message in storage:
            pass  # 迭代會清除訊息
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = EnterpriseRegistrationForm()
        return context
    
    def post(self, request, *args, **kwargs):
        form = EnterpriseRegistrationForm(request.POST)
        
        # 添加日誌來跟蹤表單驗證狀態
        logger.info(f"企業註冊表單提交 - 表單有效性: {form.is_valid()}")
        
        if form.is_valid():
            try:
                user = form.save()
                logger.info(f"企業用戶創建成功: {user.username}")
                
                # 發送驗證郵件
                if EmailService.send_verification_email(user):
                    messages.success(request, f'企業註冊申請已提交！我們已發送驗證郵件至 {user.email}，請先完成信箱驗證。')
                else:
                    messages.warning(request, '註冊成功，但驗證郵件發送失敗，請聯繫客服。')
                
                return redirect('register_success')
            
            except Exception as e:
                logger.error(f"企業用戶創建失敗: {str(e)}")
                messages.error(request, '註冊過程中發生錯誤，請稍後再試。')
                return render(request, self.template_name, {'form': form})
        
        # 表單無效時，記錄錯誤並重新顯示表單
        logger.warning(f"企業註冊表單驗證失敗: {form.errors}")
        return render(request, self.template_name, {'form': form})

class RegisterSuccessView(TemplateView):
    """註冊成功頁面"""
    template_name = 'auth/register_success.html'

def email_verify(request, token):
    """Email驗證"""
    try:
        user = get_object_or_404(User, email_verification_token=token)
        storage = messages.get_messages(request)
        list(storage)
        
        if user.is_email_verified:
            messages.info(request, '您的信箱已經驗證過了。')
        else:
            user.is_email_verified = True
            user_saved = False
            
            # 如果是個人用戶，直接啟用帳號
            if user.user_type == 'individual':
                user.is_active = True
                messages.success(request, '信箱驗證成功！您現在可以登入系統。')
            elif user.user_type == 'enterprise':
                enterprise_profile = getattr(user, 'enterprise_profile', None)
                
                with transaction.atomic():
                    user.is_active = True
                    user.save()
                    user_saved = True
                    
                    if enterprise_profile:
                        enterprise_profile.verification_status = 'approved'
                        enterprise_profile.verified_at = timezone.now()
                        enterprise_profile.save(update_fields=['verification_status', 'verified_at'])
                
                messages.success(request, '信箱驗證成功！您的企業資料已核准，現在可以登入系統。')
                
                try:
                    EmailService.send_enterprise_approval_email(user, approved=True)
                except Exception as exc:
                    logger.warning(f"自動核准企業郵件發送失敗：{exc}")
                
                detail_link = reverse('enterprise_detail', args=[user.id])
                company_name = enterprise_profile.company_name if enterprise_profile else user.username
                
                admin_users = User.objects.filter(
                    (Q(is_staff=True) | Q(user_type='admin')),
                    is_active=True
                ).distinct()
                
                for admin in admin_users:
                    NotificationService.create_notification(
                        recipient=admin,
                        title='新的企業已完成註冊',
                        message=f'{company_name} 已完成信箱驗證並自動核准，點此查看詳細資料。',
                        notification_type='enterprise_approval',
                        priority='high',
                        metadata={'link': detail_link}
                    )
            else:
                user.is_active = True
                messages.success(request, '信箱驗證成功！您現在可以登入系統。')
            
            if not user_saved:
                user.save()
            
        return redirect('login')
        
    except User.DoesNotExist:
        messages.error(request, '無效的驗證連結。')
        return redirect('login')

class RegisterChoiceView(TemplateView):
    """註冊選擇頁面"""
    template_name = 'auth/register_choice.html'
    
    def get(self, request, *args, **kwargs):
        # 清除之前的訊息
        storage = messages.get_messages(request)
        for message in storage:
            pass  # 迭代會清除訊息
        return super().get(request, *args, **kwargs)

class ResendVerificationView(TemplateView):
    """重新發送驗證郵件"""
    template_name = 'auth/resend_verification.html'
    
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        
        try:
            # 查找用戶
            user = User.objects.get(email=email, is_email_verified=False)
            
            # 檢查是否在合理時間內重複發送（避免濫用）
            from django.utils import timezone
            from datetime import timedelta
            
            # 如果用戶在5分鐘內已經要求過重新發送，則提示等待
            if hasattr(user, '_last_verification_sent'):
                time_diff = timezone.now() - user._last_verification_sent
                if time_diff < timedelta(minutes=5):
                    remaining_time = 5 - int(time_diff.total_seconds() / 60)
                    messages.warning(request, f'請等待 {remaining_time} 分鐘後再重新發送驗證郵件。')
                    return render(request, self.template_name)
            
            # 發送驗證郵件
            if EmailService.send_verification_email(user):
                # 記錄發送時間
                user._last_verification_sent = timezone.now()
                
                messages.success(request, f'驗證郵件已重新發送至 {email}，請檢查您的信箱（包括垃圾郵件資料夾）。')
                
                # 提供額外資訊
                if user.user_type == 'enterprise':
                    messages.info(request, '企業用戶完成信箱驗證後，還需等待管理員審核才能使用系統。')
                    
            else:
                messages.error(request, '郵件發送失敗，請稍後再試或聯繫客服。')
                
        except User.DoesNotExist:
            # 不要透露用戶是否存在，統一回應
            messages.info(request, '如果該電子郵件已註冊且未驗證，驗證郵件將會發送至該信箱。')
        
        except Exception as e:
            messages.error(request, '系統錯誤，請稍後再試。')
            print(f"重新發送驗證郵件錯誤: {e}")
        
        return render(request, self.template_name)

def check_verification_status(request):
    """檢查驗證狀態的 AJAX API"""
    email = request.GET.get('email')
    
    try:
        user = User.objects.get(email=email)
        return JsonResponse({
            'exists': True,
            'is_verified': user.is_email_verified,
            'user_type': user.user_type,
            'is_active': user.is_active
        })
    except User.DoesNotExist:
        return JsonResponse({'exists': False})
    

# 忘記密碼
class ForgotPasswordView(TemplateView):
    """忘記密碼"""
    template_name = 'auth/forgot_password.html'
    
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        
        try:
            # 查找用戶（只能重設已驗證Email的用戶）
            user = User.objects.get(email=email, is_email_verified=True, is_active=True)
            
            # 檢查是否在合理時間內重複發送（避免濫用）
            if user.password_reset_token_created:
                time_diff = timezone.now() - user.password_reset_token_created
                if time_diff < timedelta(minutes=5):
                    remaining_time = 5 - int(time_diff.total_seconds() / 60)
                    messages.warning(request, f'請等待 {remaining_time} 分鐘後再重新申請密碼重設。')
                    return render(request, self.template_name)
            
            # 發送密碼重設郵件
            if EmailService.send_password_reset_email(user):
                messages.success(request, f'密碼重設連結已發送至 {email}，請檢查您的信箱（包括垃圾郵件資料夾）。')
            else:
                messages.error(request, '郵件發送失敗，請稍後再試或聯繫客服。')
                
        except User.DoesNotExist:
            # 不要透露用戶是否存在，統一回應
            messages.info(request, '如果該電子郵件已註冊且已驗證，密碼重設連結將會發送至該信箱。')
        
        except Exception as e:
            messages.error(request, '系統錯誤，請稍後再試。')
            print(f"忘記密碼錯誤: {e}")
        
        return render(request, self.template_name)

def password_reset_confirm(request, token):
    """密碼重設確認"""
    valid_token = False
    
    try:
        # 查找用戶並檢查令牌有效性
        user = User.objects.get(password_reset_token=token)
        
        # 檢查令牌是否在24小時內
        if user.password_reset_token_created:
            time_diff = timezone.now() - user.password_reset_token_created
            if time_diff < timedelta(hours=24):
                valid_token = True
            else:
                messages.error(request, '密碼重設連結已過期，請重新申請。')
        else:
            messages.error(request, '無效的密碼重設連結。')
            
    except User.DoesNotExist:
        messages.error(request, '無效的密碼重設連結。')
        user = None
    
    if request.method == 'POST' and valid_token and user:
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # 密碼驗證
        if not new_password1 or not new_password2:
            messages.error(request, '請填寫所有密碼欄位。')
        elif new_password1 != new_password2:
            messages.error(request, '兩次輸入的密碼不一致。')
        elif len(new_password1) < 8:
            messages.error(request, '密碼長度至少8個字符。')
        else:
            # 更新密碼
            user.password = make_password(new_password1)
            # 清除重設令牌
            user.password_reset_token = uuid.uuid4()  # 使令牌失效
            user.password_reset_token_created = None
            user.save()
            
            messages.success(request, '密碼重設成功！請使用新密碼登入。')
            return redirect('login')
    
    return render(request, 'auth/password_reset_confirm.html', {
        'valid_token': valid_token
    })

@method_decorator(staff_member_required, name='dispatch')
class EnterpriseApprovalListView(TemplateView):
    """企業審核列表"""
    template_name = 'admin/enterprise_approval_list.html'  # 改回正確的模板
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 獲取待審核的企業
        pending_enterprises = User.objects.filter(
            user_type='enterprise',
            enterprise_profile__verification_status='pending'
        ).select_related('enterprise_profile')
        
        # 獲取已審核的企業
        reviewed_enterprises = User.objects.filter(
            user_type='enterprise',
            enterprise_profile__verification_status__in=['approved', 'rejected']
        ).select_related('enterprise_profile').order_by('-enterprise_profile__verified_at')
        
        context.update({
            'pending_enterprises': pending_enterprises,
            'reviewed_enterprises': reviewed_enterprises,
            'pending_count': pending_enterprises.count(),
        })
        
        return context

@staff_member_required
def approve_enterprise(request, user_id):
    """核准企業"""
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id, user_type='enterprise')
            enterprise_profile = user.enterprise_profile
            
            # 核准企業
            enterprise_profile.verification_status = 'approved'
            enterprise_profile.verified_at = timezone.now()
            enterprise_profile.save()
            
            # 啟用用戶帳號
            user.is_active = True
            user.save()
            
            # 發送核准通知郵件
            EmailService.send_enterprise_approval_email(user, approved=True)
            
            messages.success(request, f'企業 {enterprise_profile.company_name} 已核准！')
            
        except Exception as e:
            messages.error(request, f'核准失敗：{str(e)}')
    
    return redirect('enterprise_approval_list')

@staff_member_required
def reject_enterprise(request, user_id):
    """拒絕企業"""
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id, user_type='enterprise')
            enterprise_profile = user.enterprise_profile
            rejection_reason = request.POST.get('rejection_reason', '')
            
            # 拒絕企業
            enterprise_profile.verification_status = 'rejected'
            enterprise_profile.verified_at = timezone.now()
            enterprise_profile.save()
            
            # 發送拒絕通知郵件
            EmailService.send_enterprise_approval_email(user, approved=False, reason=rejection_reason)
            
            messages.success(request, f'企業 {enterprise_profile.company_name} 已拒絕！')
            
        except Exception as e:
            messages.error(request, f'拒絕失敗：{str(e)}')
    
    return redirect('enterprise_approval_list')

@staff_member_required
def enterprise_detail(request, user_id):
    """企業詳細資訊"""
    user = get_object_or_404(User, id=user_id, user_type='enterprise')
    enterprise_profile = user.enterprise_profile
    
    return render(request, 'admin/enterprise_detail.html', {
        'user': user,
        'enterprise_profile': enterprise_profile
    })


# ===== 爬蟲管理視圖 =====
@login_required
@admin_required
def crawler_config_list(request):
    """爬蟲配置列表"""
    configs = CrawlerConfig.objects.all().order_by('-created_at')
    
    context = {
        'configs': configs,
    }
    
    return render(request, 'admin/crawler_config_list.html', context)

@login_required
@admin_required
def crawler_config_edit(request, config_id=None):
    """編輯爬蟲配置"""
    if config_id:
        config = get_object_or_404(CrawlerConfig, id=config_id)
    else:
        config = None
    
    if request.method == 'POST':
        try:
            data = {
                'name': request.POST.get('name'),
                'base_url': request.POST.get('base_url'),
                'username': request.POST.get('username'),
                'password': request.POST.get('password'),
                'is_active': request.POST.get('is_active') == 'on',
            }
            
            if config:
                for key, value in data.items():
                    setattr(config, key, value)
                config.save()
                messages.success(request, '爬蟲配置更新成功！')
            else:
                config = CrawlerConfig.objects.create(**data)
                messages.success(request, '爬蟲配置建立成功！')
            
            return redirect('crawler_config_list')
            
        except Exception as e:
            logger.error(f"保存爬蟲配置失敗：{str(e)}")
            messages.error(request, f'操作失敗：{str(e)}')
    
    context = {
        'config': config,
        'is_edit': config is not None,
    }
    
    return render(request, 'admin/crawler_config_form.html', context)

@login_required
@admin_required
@require_POST
def crawler_config_delete(request, config_id):
    """刪除爬蟲配置"""
    config = get_object_or_404(CrawlerConfig, id=config_id)
    
    try:
        config_name = config.name
        config.delete()
        messages.success(request, f'爬蟲配置「{config_name}」已刪除')
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"刪除爬蟲配置失敗：{str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})
    
@login_required
@enterprise_required
@require_POST
def start_crawling(request, invitation_id):
    """啟動爬蟲作業"""
    invitation = get_object_or_404(TestInvitation, id=invitation_id, enterprise=request.user)
    
    try:
        # 檢查邀請狀態
        if invitation.status != 'completed':
            return JsonResponse({
                'success': False,
                'error': '只有已完成的測驗邀請才能爬取結果'
            })
        
        # 啟動爬蟲
        crawler = PITestResultCrawler()
        result = crawler.crawl_test_result(invitation_id)
        
        return JsonResponse({
            'success': True,
            'message': '測驗結果爬取完成！',
            'result_id': result.id if result else None
        })
        
    except Exception as e:
        logger.error(f"爬蟲作業失敗：{str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
    
@login_required
@enterprise_required 
def test_result_detail(request, result_id):
    """測驗結果詳情"""
    result = get_object_or_404(
        TestProjectResult, 
        id=result_id, 
        test_invitation__enterprise=request.user
    )
    
    context = {
        'result': result,
    }
    
    return render(request, 'test_management/test_result_detail.html', context)

@login_required
@enterprise_required
def export_test_result(request, result_id):
    """匯出測驗結果"""
    result = get_object_or_404(
        TestProjectResult, 
        id=result_id, 
        test_invitation__enterprise=request.user
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
        'raw_data': result.raw_data,
    }
    
    # 生成 JSON 響應
    response = JsonResponse(export_data, json_dumps_params={'ensure_ascii': False, 'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="test_result_{result.id}.json"'
    
    return response

def api_errors(request):
    """API 錯誤處理端點"""
    return JsonResponse({'status': 'ok', 'message': 'API 運作正常'})

def favicon(request):
    """favicon 處理"""
    return HttpResponse(status=204)

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def verify_tax_id(request):
    """驗證統一編號並取得公司名稱"""
    if request.method != 'POST':
        return JsonResponse({'error': '只接受POST請求'}, status=405)
    
    try:
        data = json.loads(request.body)
        tax_id = data.get('tax_id', '').strip()
        
        if not tax_id:
            return JsonResponse({'error': '請提供統一編號'}, status=400)
            
        if not re.match(r'^\d{8}$', tax_id):
            return JsonResponse({'error': '請輸入正確統一編號，若已被註冊，請聯繫服務信箱 service@traitty.com'}, status=400)
        
        # 檢查統一編號是否已被註冊（排除被拒絕的申請）
        from .models import EnterpriseProfile
        existing_profile = EnterpriseProfile.objects.filter(tax_id=tax_id).first()
        if existing_profile and existing_profile.verification_status == 'rejected':
            # if existing_profile.verification_status in ['pending', 'approved']:
            #     # 待審核或已核准的統一編號不能重複註冊
            #     return JsonResponse({'error': '請輸入正確統一編號，若已被註冊，請聯繫服務信箱 service@traitty.com'}, status=400)
            # elif existing_profile.verification_status == 'rejected':
                # 被拒絕的申請可以重新註冊，先刪除舊記錄
            logger.info(f"刪除被拒絕的企業申請記錄: {tax_id}")
            existing_profile.user.delete()  # 這會級聯刪除EnterpriseProfile
        
        # 調用經濟部API
        api_url = f"https://data.gcis.nat.gov.tw/od/data/api/5F64D864-61CB-4D0D-8AD9-492047CC1EA6?$format=json&$filter=Business_Accounting_NO eq {tax_id}"
        
        try:
            logger.info(f"正在查詢統一編號: {tax_id}")
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            # 檢查回應內容是否為空或非JSON格式
            response_text = response.text.strip()
            logger.info(f"API回應狀態碼: {response.status_code}, 內容長度: {len(response_text)}")
            
            if not response_text:
                logger.info(f"API回應為空，統編: {tax_id}")
                return JsonResponse({'error': '查無此統一編號，請確認號碼是否正確'}, status=404)
            
            # 檢查是否回應空陣列或空物件
            if response_text.strip() in ['[]', '{}', 'null']:
                logger.info(f"API回應空資料，統編: {tax_id}")
                return JsonResponse({'error': '查無此統一編號，請確認號碼是否正確'}, status=404)
            
            try:
                api_data = response.json()
                logger.info(f"API回應解析成功，資料筆數: {len(api_data) if isinstance(api_data, list) else 'not a list'}")
            except json.JSONDecodeError as e:
                logger.error(f"經濟部API回應格式錯誤: {e}, 回應內容前200字元: {response_text[:200]}")
                return JsonResponse({'error': '查無此統一編號，請確認號碼是否正確'}, status=404)
            
            if not api_data or len(api_data) == 0:
                return JsonResponse({'error': '查無此統一編號，請確認號碼是否正確'}, status=404)
            
            # 取得第一筆資料的公司名稱
            company_data = api_data[0]
            company_name = company_data.get('Company_Name', '').strip()
            
            if not company_name:
                return JsonResponse({'error': '查無此統一編號，請確認號碼是否正確'}, status=404)
            
            return JsonResponse({
                'success': True,
                'company_name': company_name,
                'tax_id': tax_id
            })
            
        except requests.exceptions.Timeout:
            logger.error(f"調用經濟部API超時: {api_url}")
            return JsonResponse({'error': '查詢服務回應超時，請稍後再試'}, status=503)
        except requests.exceptions.ConnectionError:
            logger.error(f"無法連接經濟部API: {api_url}")
            return JsonResponse({'error': '無法連接至查詢服務，請檢查網路連線'}, status=503)
        except requests.exceptions.HTTPError as e:
            logger.error(f"經濟部API HTTP錯誤: {e}")
            if response.status_code == 404:
                return JsonResponse({'error': '查無此統一編號，請確認號碼是否正確'}, status=404)
            else:
                return JsonResponse({'error': '查詢服務暫時無法使用，請稍後再試'}, status=503)
        except requests.exceptions.RequestException as e:
            logger.error(f"調用經濟部API失敗: {e}")
            return JsonResponse({'error': '查詢服務發生錯誤，請稍後再試'}, status=503)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': '請求格式錯誤'}, status=400)
    except Exception as e:
        logger.error(f"驗證統一編號時發生錯誤: {e}")
        return JsonResponse({'error': '系統錯誤，請稍後再試'}, status=500)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction
from .models import User, IndividualProfile, EnterpriseProfile, Notification  
from .user_forms import (
    IndividualProfileForm, EnterpriseProfileForm, 
    UserBasicInfoForm, CustomPasswordChangeForm
)
import logging

logger = logging.getLogger(__name__)

@login_required
def profile_view(request):
    """用戶資料檢視頁面"""
    user = request.user
    context = {'user': user}
    
    if user.user_type == 'individual':
        try:
            profile = user.individual_profile
        except IndividualProfile.DoesNotExist:
            profile = IndividualProfile.objects.create(user=user, real_name='')
        context['profile'] = profile
        
    elif user.user_type == 'enterprise':
        try:
            profile = user.enterprise_profile
        except EnterpriseProfile.DoesNotExist:
            # 這不應該發生，但防禦性編程
            messages.error(request, '企業資料異常，請聯繫客服')
            return redirect('dashboard')
        context['profile'] = profile
    
    return render(request, 'user/profile.html', context)

@login_required
def edit_profile(request):
    """編輯用戶資料"""
    user = request.user
    
    if request.method == 'POST':
        basic_form = UserBasicInfoForm(request.POST, instance=user)
        
        if user.user_type == 'individual':
            try:
                profile = user.individual_profile
            except IndividualProfile.DoesNotExist:
                profile = IndividualProfile.objects.create(user=user, real_name='')
            profile_form = IndividualProfileForm(request.POST, instance=profile)
            
        elif user.user_type == 'enterprise':
            profile = user.enterprise_profile
            profile_form = EnterpriseProfileForm(request.POST, instance=profile)
        else:
            profile_form = None
        
        if basic_form.is_valid() and (profile_form is None or profile_form.is_valid()):
            try:
                with transaction.atomic():
                    basic_form.save()
                    if profile_form:
                        profile_form.save()
                    
                    # 建立通知
                    Notification.objects.create(
                        recipient=user,
                        title="個人資料已更新",
                        message="您的個人資料已成功更新",
                        notification_type='account'
                    )
                    
                    messages.success(request, '個人資料更新成功！')
                    return redirect('profile_view')
            except Exception as e:
                logger.error(f"更新用戶資料失敗：{str(e)}")
                messages.error(request, '更新失敗，請稍後再試')
    else:
        basic_form = UserBasicInfoForm(instance=user)
        
        if user.user_type == 'individual':
            try:
                profile = user.individual_profile
            except IndividualProfile.DoesNotExist:
                profile = IndividualProfile.objects.create(user=user, real_name='')
            profile_form = IndividualProfileForm(instance=profile)
            
        elif user.user_type == 'enterprise':
            profile = user.enterprise_profile
            profile_form = EnterpriseProfileForm(instance=profile)
        else:
            profile_form = None
    
    context = {
        'basic_form': basic_form,
        'profile_form': profile_form,
        'user': user
    }
    
    return render(request, 'user/edit_profile.html', context)

@login_required
def change_password(request):
    """修改密碼"""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # 保持登入狀態
            
            # 建立通知
            Notification.objects.create(
                recipient=user,
                title="密碼已更新",
                message="您的帳號密碼已成功更新，如非本人操作請立即聯繫客服",
                notification_type='account',
                priority='high'
            )
            
            messages.success(request, '密碼修改成功！')
            return redirect('profile_view')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'user/change_password.html', {'form': form})

@login_required
def account_settings(request):
    """帳號設定頁面"""
    return render(request, 'user/account_settings.html', {'user': request.user})

@login_required
@require_POST
def delete_account(request):
    """刪除帳號（軟刪除）"""
    user = request.user
    
    # 企業用戶不允許自行刪除帳號
    if user.user_type == 'enterprise':
        return JsonResponse({
            'status': 'error',
            'message': '企業帳號需要聯繫客服進行停用'
        })
    
    try:
        # 軟刪除：設為不活躍而不是真正刪除
        user.is_active = False
        user.save()
        
        messages.info(request, '帳號已停用，如需重新啟用請聯繫客服')
        
        # 登出用戶
        from django.contrib.auth import logout
        logout(request)
        
        return JsonResponse({'status': 'success', 'redirect': '/login/'})
        
    except Exception as e:
        logger.error(f"停用帳號失敗：{str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': '操作失敗，請稍後再試'
        })
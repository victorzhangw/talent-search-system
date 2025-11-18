from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from utils.permission_handler import PermissionHandler

def check_permission(permission_code):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            user_type = request.COOKIES.get('user_type', '')
            if PermissionHandler.has_permission(user_type, permission_code):
                return view_func(request, *args, **kwargs)
            else:
                raise PermissionDenied
        return wrapped_view
    return decorator

def enterprise_required(view_func):
    """企業用戶權限裝飾器（也允許管理員訪問）"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.user_type not in ['enterprise', 'admin']:
            messages.error(request, '此功能僅限企業用戶或管理員使用')
            return redirect('dashboard')
        # 如果是企業用戶，檢查審核狀態
        if request.user.user_type == 'enterprise':
            if not hasattr(request.user, 'enterprise_profile') or request.user.enterprise_profile.verification_status != 'approved':
                messages.error(request, '企業尚未通過審核，無法使用此功能')
                return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
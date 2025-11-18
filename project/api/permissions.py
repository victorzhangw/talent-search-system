# api/permissions.py
from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    自定義權限：只有擁有者才能編輯
    """
    def has_object_permission(self, request, view, obj):
        # 讀取權限允許任何請求
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 寫入權限只給擁有者
        return obj.enterprise == request.user

class IsEnterpriseUser(permissions.BasePermission):
    """
    只允許企業用戶訪問
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'enterprise'

class IsIndividualUser(permissions.BasePermission):
    """
    只允許個人用戶訪問
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'individual'

class IsAdminUser(permissions.BasePermission):
    """
    只允許管理員訪問
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.user_type == 'admin' or request.user.is_staff
        )

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    只允許擁有者或管理員訪問
    """
    def has_object_permission(self, request, view, obj):
        if request.user.user_type == 'admin' or request.user.is_staff:
            return True
        return obj.enterprise == request.user

class IsTestInvitee(permissions.BasePermission):
    """
    只允許受測者訪問自己的測驗
    """
    def has_object_permission(self, request, view, obj):
        # 這裡需要根據邀請碼驗證
        return hasattr(obj, 'invitation_code') and obj.invitation_code == request.GET.get('code')

class ReadOnlyPermission(permissions.BasePermission):
    """
    只讀權限
    """
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS
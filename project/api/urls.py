# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

# 建立 API 路由
urlpatterns = [
    # 認證相關
    path('auth/register/', views.UserRegistrationView.as_view(), name='api_register'),
    path('auth/login/', views.LoginView.as_view(), name='api_login'),
    path('auth/logout/', views.LogoutView.as_view(), name='api_logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    
    # 用戶相關
    path('user/profile/', views.UserProfileView.as_view(), name='api_user_profile'),
    path('user/change-password/', views.PasswordChangeView.as_view(), name='api_change_password'),
    path('user/points/', views.UserPointBalanceView.as_view(), name='api_user_points'),
    
    # 測驗項目
    path('test-projects/', views.TestProjectListView.as_view(), name='api_test_projects'),
    path('test-projects/<int:pk>/', views.TestProjectDetailView.as_view(), name='api_test_project_detail'),
    
    # 受測者管理
    path('invitees/', views.TestInviteeListCreateView.as_view(), name='api_invitees'),
    path('invitees/<int:pk>/', views.TestInviteeDetailView.as_view(), name='api_invitee_detail'),
    
    # 測驗邀請
    path('invitations/', views.TestInvitationListCreateView.as_view(), name='api_invitations'),
    path('invitations/<int:pk>/', views.TestInvitationDetailView.as_view(), name='api_invitation_detail'),
    
    # 測驗結果
    path('test-results/', views.TestResultListView.as_view(), name='api_test_results'),
    path('test-results/<int:pk>/', views.TestResultDetailView.as_view(), name='api_test_result_detail'),
    
    # 邀請模板
    path('invitation-templates/', views.InvitationTemplateListCreateView.as_view(), name='api_invitation_templates'),
    path('invitation-templates/<int:pk>/', views.InvitationTemplateDetailView.as_view(), name='api_invitation_template_detail'),
    
    # 統計數據
    path('statistics/', views.StatisticsView.as_view(), name='api_statistics'),
    
    # 管理員功能
    path('admin/statistics/', views.admin_statistics, name='api_admin_statistics'),
    
    # 系統功能
    path('health/', views.api_health_check, name='api_health_check'),
]
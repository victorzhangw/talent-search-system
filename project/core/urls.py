from django.urls import path
from django.views.generic import RedirectView
from core.views import (
    HomeView, LoginView, LogoutView, 
    UserListView, RoleListView, DashboardView, IndexView,
    IndividualRegisterView, EnterpriseRegisterView, RegisterSuccessView, 
    RegisterChoiceView, ResendVerificationView, ForgotPasswordView,
    EnterpriseApprovalListView, FAQView  # 確保有這個 import
)
from core.custom_dashboard_views import CustomDashboardView
from core import views
from core.activity_log_views import activity_log_list, activity_log_detail, export_activity_logs, dashboard_recent_activities, generate_test_logs
from core.file_manager_views import file_list, file_detail, update_file, download_file, upload_file, delete_file, generate_test_files, dashboard_recent_files, batch_delete_files
from core.export_views import export_data, export_custom_data, export_table_data, export_demo
from core.dashboard_views import get_chart_data
from core.notification_views import delete_notification, get_notification_count, get_notification_dropdown, mark_all_read, mark_notification_read, notification_list
from core.point_views import (
    point_dashboard, point_history, point_purchase, create_point_order,
    point_payment, point_orders, cancel_point_order,
    api_point_balance, api_point_costs, api_check_points, api_consume_points,
    admin_point_management, admin_point_overview, admin_adjust_points, test_point_functions
)
from core.purchase_views import purchase_record_create
from core.user_views import profile_view, edit_profile, change_password, account_settings, delete_account
from core.individual_test_views import (
    individual_tests, test_purchase_confirm, test_purchase_process, check_points_ajax, 
    direct_test_access, individual_test_result_detail, individual_test_results_list,
    generate_individual_test_result_pdf, auto_login_to_test_platform, server_side_auto_login,
    check_auto_login_status
)
# 企業管理
from core.test_invitation_views import (
    enterprise_test_dashboard, invitee_list, invitation_list, test_templates, 
    enterprise_test_project_stats, create_invitee, edit_invitee, delete_invitee,
    create_invitation, quick_invitation, invitation_detail, resend_invitation, cancel_invitation
)
from core.bulk_invitation_views import bulk_invitation, download_csv_template
from core.invitation_template_views import (
    invitation_template_list, invitation_template_create, invitation_template_edit,
    invitation_template_detail, invitation_template_delete, invitation_template_set_default,
    invitation_template_preview, create_default_templates, invitation_template_copy
)
from core.statistics_views import statistics_dashboard, statistics_api
from core.crawler_views import (
    crawler_dashboard, crawler_logs, crawler_log_details, trigger_crawler, 
    crawler_settings, crawler_status_api, crawler_schedule
)
from core.trait_views import trait_list, trait_create, trait_edit, trait_delete
# 測驗項目
from core.test_project_views import (
    test_project_list, test_project_create, test_project_edit, 
    test_project_detail, test_project_delete, test_project_toggle_status,
    test_project_assignments, api_test_project_assignments
)
# 短網址
from utils.url_shortener import short_url_redirect
# 爬蟲
from core.views import (
    # ... 現有的 imports
    crawler_config_list, crawler_config_edit, start_crawling,
    test_result_detail, export_test_result, crawler_config_delete
)
from .test_result_views import (
    test_result_list, test_result_detail, export_test_result,
    start_crawling, bulk_crawl_results, test_result_dashboard,
    test_chart_simple, generate_test_result_pdf_report, force_recrawl_invitation,
    view_raw_data, export_filtered_test_results
)
from .test_pdf_views import test_pdf_generation_view


urlpatterns = [
    # 根路徑
    path('', IndexView.as_view(), name='home'),
    path('dashboard/', CustomDashboardView.as_view(), name='dashboard'),
    
    # FAQ 常見問題
    path('faq/', FAQView.as_view(), name='faq'),
    
    # 登入相關
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # 註冊相關
    path('register/', RegisterChoiceView.as_view(), name='register_choice'),
    path('register/individual/', IndividualRegisterView.as_view(), name='individual_register'),
    path('register/enterprise/', EnterpriseRegisterView.as_view(), name='enterprise_register'),
    path('register/success/', RegisterSuccessView.as_view(), name='register_success'),
    path('email-verify/<uuid:token>/', views.email_verify, name='email_verify'),
    path('resend-verification/', ResendVerificationView.as_view(), name='resend_verification'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('password-reset/<uuid:token>/', views.password_reset_confirm, name='password_reset_confirm'),
    
    # 企業審核相關（重要：確保這些路由存在）
    path('management/enterprise-approval/', EnterpriseApprovalListView.as_view(), name='enterprise_approval_list'),
    path('management/enterprise/<int:user_id>/approve/', views.approve_enterprise, name='approve_enterprise'),
    path('management/enterprise/<int:user_id>/reject/', views.reject_enterprise, name='reject_enterprise'),
    path('management/enterprise/<int:user_id>/detail/', views.enterprise_detail, name='enterprise_detail'),
    
    # 用戶管理
    path('users/', UserListView.as_view(), name='user_list'),
    path('roles/', RoleListView.as_view(), name='role_list'),
    # NEW
    path('profile/', profile_view, name='profile_view'),
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('profile/change-password/', change_password, name='change_password'),
    path('profile/settings/', account_settings, name='account_settings'),
    path('profile/delete/', delete_account, name='delete_account'),
    
    # 個人測驗功能
    path('individual-tests/', individual_tests, name='individual_tests'),
    path('individual-tests/<int:project_id>/confirm/', test_purchase_confirm, name='test_purchase_confirm'),
    path('individual-tests/<int:project_id>/purchase/', test_purchase_process, name='test_purchase_process'),
    path('individual-tests/<int:project_id>/access/', direct_test_access, name='direct_test_access'),
    path('individual-tests/auto-login/', auto_login_to_test_platform, name='auto_login_to_test_platform'),
    path('individual-tests/server-side-auto-login/', server_side_auto_login, name='server_side_auto_login'),
    path('api/check-auto-login-status/', check_auto_login_status, name='check_auto_login_status'),
    path('api/check-points/', check_points_ajax, name='check_points_ajax'),
    
    # 個人測驗結果
    path('my-test-results/', individual_test_results_list, name='individual_test_results_list'),
    path('my-test-results/<int:result_id>/', individual_test_result_detail, name='individual_test_result_detail'),
    path('my-test-results/<int:result_id>/pdf/', generate_individual_test_result_pdf, name='generate_individual_test_result_pdf'),
    
    # 其他現有路由...
    
    # 權限測試
    path('test-login/<str:user_type>/', views.test_login, name='test_login'),

    # 操作日誌
    path('logs/', activity_log_list, name='activity_log_list'),
    path('logs/<int:log_id>/', activity_log_detail, name='activity_log_detail'),
    path('logs/export/', export_activity_logs, name='export_activity_logs'),
    path('dashboard/recent-activities/', dashboard_recent_activities, name='dashboard_recent_activities'),
    path('logs/generate-test-logs/', generate_test_logs, name='generate_test_logs'),

    # 檔案管理
    path('files/', file_list, name='file_list'),
    path('files/<int:file_id>/', file_detail, name='file_detail'),
    path('files/upload/', upload_file, name='upload_file'),
    path('files/<int:file_id>/download/', download_file, name='download_file'),
    path('files/<int:file_id>/update/', update_file, name='update_file'),
    path('files/<int:file_id>/delete/', delete_file, name='delete_file'),
    path('files/batch-delete/', batch_delete_files, name='batch_delete_files'),
    path('files/generate-test-files/', generate_test_files, name='generate_test_files'),
    path('dashboard/recent-files/', dashboard_recent_files, name='dashboard_recent_files'),

    # 匯出功能
    path('export/', export_data, name='export_data'),
    path('export/custom/', export_custom_data, name='export_custom_data'),
    path('export/table/', export_table_data, name='export_table_data'),
    path('export/demo/', export_demo, name='export_demo'),

    # 儀錶板統計
    path('api/chart-data/', get_chart_data, name='chart_data'),

    # 通知
    path('notifications/dropdown/', get_notification_dropdown, name='get_notification_dropdown'),
    path('notifications/count/', get_notification_count, name='get_notification_count'),
    path('api/check-verification/', views.check_verification_status, name='check_verification_status'),
    # 通知相關
    path('notifications/', notification_list, name='notification_list'),
    path('notifications/mark-read/<int:notification_id>/', mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', mark_all_read, name='mark_all_notifications_read'),
    path('notifications/delete/<int:notification_id>/', delete_notification, name='delete_notification'),

    # 點數系統
    path('points/', point_dashboard, name='point_dashboard'),
    path('points/history/', point_history, name='point_history'),
    path('points/purchase/', point_purchase, name='point_purchase'),
    path('points/orders/', point_orders, name='point_orders'),
    path('points/order/create/', create_point_order, name='create_point_order'),
    path('points/payment/<str:order_number>/', point_payment, name='point_payment'),
    path('points/order/<str:order_number>/cancel/', cancel_point_order, name='cancel_point_order'),

    # 點數API
    path('api/points/balance/', api_point_balance, name='api_point_balance'),
    path('api/points/costs/', api_point_costs, name='api_point_costs'),
    path('api/points/check/', api_check_points, name='api_check_points'),
    path('api/points/consume/', api_consume_points, name='api_consume_points'),

    # 管理員功能
    path('management/points/', admin_point_management, name='admin_point_management'),
    path('management/points/overview/', admin_point_overview, name='admin_point_overview'),
    path('management/points/adjust/', admin_adjust_points, name='admin_adjust_points'),

    # 測試功能（開發環境）
    path('points/test/', test_point_functions, name='test_point_functions'),
    
    # 企業管理
    path('enterprise/', enterprise_test_dashboard, name='enterprise_dashboard'),
    path('enterprise/invitees/', invitee_list, name='invitee_list'),
    path('enterprise/invitees/create/', create_invitee, name='create_invitee'),
    path('enterprise/invitees/<int:invitee_id>/edit/', edit_invitee, name='edit_invitee'),
    path('enterprise/invitees/<int:invitee_id>/delete/', delete_invitee, name='delete_invitee'),
    path('enterprise/invitations/', invitation_list, name='invitation_list'),
    path('enterprise/invitations/<int:invitation_id>/', invitation_detail, name='invitation_detail'),  # 新增
    path('enterprise/invitations/<int:invitation_id>/resend/', resend_invitation, name='resend_invitation'),  # 新增
    path('enterprise/invitations/<int:invitation_id>/cancel/', cancel_invitation, name='cancel_invitation'),  # 新增
    path('enterprise/templates/', test_templates, name='test_templates'),
    path('enterprise/test-projects/<int:project_id>/stats/', enterprise_test_project_stats, name='enterprise_test_project_stats'),
    path('enterprise/test-projects/<int:project_id>/invite/', create_invitation, name='create_invitation'),
    path('enterprise/test-projects/<int:project_id>/quick-invite/', quick_invitation, name='quick_invitation'),
    
    # 批量邀請功能
    path('enterprise/bulk-invitation/', bulk_invitation, name='bulk_invitation'),
    path('enterprise/csv-template/', download_csv_template, name='download_csv_template'),
    
    # 邀請模板管理
    path('enterprise/templates/', invitation_template_list, name='invitation_template_list'),
    path('enterprise/templates/create/', invitation_template_create, name='invitation_template_create'),
    path('enterprise/templates/<int:template_id>/', invitation_template_detail, name='invitation_template_detail'),
    path('enterprise/templates/<int:template_id>/edit/', invitation_template_edit, name='invitation_template_edit'),
    path('enterprise/templates/<int:template_id>/delete/', invitation_template_delete, name='invitation_template_delete'),
    path('enterprise/templates/<int:template_id>/set-default/', invitation_template_set_default, name='invitation_template_set_default'),
    path('enterprise/templates/<int:template_id>/preview/', invitation_template_preview, name='invitation_template_preview'),
    path('enterprise/templates/<int:template_id>/copy/', invitation_template_copy, name='invitation_template_copy'),
    path('enterprise/templates/create-defaults/', create_default_templates, name='create_default_templates'),
    
    # 統計dashboard
    path('enterprise/statistics/', statistics_dashboard, name='statistics_dashboard'),
    path('enterprise/statistics/api/', statistics_api, name='statistics_api'),

    # 短網址重定向
    path('s/<str:short_code>/', short_url_redirect, name='short_url_redirect'),

    # 測驗項目管理（管理員功能）
    path('management/test-projects/', test_project_list, name='test_project_list'),
    path('management/test-projects/create/', test_project_create, name='test_project_create'),
    path('management/test-projects/<int:project_id>/', test_project_detail, name='test_project_detail'),
    path('management/test-projects/<int:project_id>/edit/', test_project_edit, name='test_project_edit'),
    path('management/test-projects/<int:project_id>/delete/', test_project_delete, name='test_project_delete'),
    # path('management/test-projects/<int:project_id>/toggle-status/', test_project_toggle_status, name='test_project_toggle_status'),
    path('management/test-projects/<int:project_id>/assignments/', test_project_assignments, name='test_project_assignments'),

    # 測驗項目 API
    path('api/test-projects/assignments/', api_test_project_assignments, name='api_test_project_assignments'),

    # 企業購買紀錄
    path('management/purchase-records/create/', purchase_record_create, name='purchase_record_create'),

    # 測驗特質管理
    path('management/traits/', trait_list, name='trait_list'),
    path('management/traits/create/', trait_create, name='trait_create'),
    path('management/traits/<int:trait_id>/edit/', trait_edit, name='trait_edit'),
    path('management/traits/<int:trait_id>/delete/', trait_delete, name='trait_delete'),

    # 爬蟲配置管理
    path('management/crawler-config/', crawler_config_list, name='crawler_config_list'),
    path('management/crawler-config/create/', crawler_config_edit, name='crawler_config_create'),
    path('management/crawler-config/<int:config_id>/edit/', crawler_config_edit, name='crawler_config_edit'),
    path('management/crawler-config/<int:config_id>/delete/', crawler_config_delete, name='crawler_config_delete'),
    
    # 企業功能 - 測驗結果管理
    path('enterprise/test-results/', test_result_list, name='test_result_list'),
    path('enterprise/test-results/export/', export_filtered_test_results, name='export_filtered_test_results'),

    path('enterprise/test-results/<int:result_id>/', test_result_detail, name='test_result_detail'),
    path('enterprise/test-results/<int:result_id>/export/', export_test_result, name='export_test_result'),
    path('enterprise/test-results/<int:result_id>/pdf/', generate_test_result_pdf_report, name='generate_test_result_pdf'),
    path('enterprise/test-results/<int:result_id>/raw-data/', view_raw_data, name='view_raw_data'),
    path('enterprise/test-results/bulk-crawl/', bulk_crawl_results, name='bulk_crawl_results'),

    # 爬蟲操作
    path('enterprise/invitations/<int:invitation_id>/crawl/', start_crawling, name='start_crawling'),
    path('management/invitations/<int:invitation_id>/force-recrawl/', force_recrawl_invitation, name='force_recrawl_invitation'),

    # 管理員功能 - 測驗結果儀表板
    path('management/test-results/', test_result_list, name='admin_test_result_list'),
    path('management/test-results/dashboard/', test_result_dashboard, name='test_result_dashboard'),
    path('management/test-results/<int:result_id>/', test_result_detail, name='admin_test_result_detail'),
    path('management/test-results/<int:result_id>/export/', export_test_result, name='admin_export_test_result'),
    path('management/test-results/<int:result_id>/pdf/', generate_test_result_pdf_report, name='admin_generate_test_result_pdf'),
    path('management/test-results/<int:result_id>/raw-data/', view_raw_data, name='admin_view_raw_data'),
    
    # 爬蟲管理
    path('management/crawler/', crawler_dashboard, name='crawler_dashboard'),
    path('management/crawler/logs/', crawler_logs, name='crawler_logs'),
    path('management/crawler/logs/<int:log_id>/', crawler_log_details, name='crawler_log_details'),
    path('management/crawler/trigger/', trigger_crawler, name='trigger_crawler'),
    path('management/crawler/settings/', crawler_settings, name='crawler_settings'),
    path('management/crawler/schedule/', crawler_schedule, name='crawler_schedule'),
    path('api/crawler/status/', crawler_status_api, name='crawler_status_api'),
    
    # 測試頁面
    path('test/chart/', test_chart_simple, name='test_chart_simple'),
    path('test/pdf/<int:result_id>/', test_pdf_generation_view, name='test_pdf_generation'),
    
    # API 錯誤處理
    path('api/errors/', views.api_errors, name='api_errors'),
    
    # 統一編號驗證API
    path('api/verify-tax-id/', views.verify_tax_id, name='verify_tax_id'),
    
    # favicon 處理
    path('favicon.ico', views.favicon, name='favicon'),
]

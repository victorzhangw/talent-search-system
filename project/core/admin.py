from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    User, IndividualProfile, EnterpriseProfile, TestProject, 
    IndividualTestRecord, IndividualTestResult, TestInvitation, 
    TestInvitee, PointTransaction, UserPointBalance, CrawlerLog, CrawlerDetailLog
)

@admin.register(IndividualTestRecord)
class IndividualTestRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'test_project', 'status', 'purchase_date', 'access_count', 'has_result']
    list_filter = ['status', 'purchase_date', 'test_project']
    search_fields = ['user__username', 'user__email', 'test_project__name']
    readonly_fields = ['purchase_date', 'first_access_date', 'last_access_date', 'access_count']
    
    def has_result(self, obj):
        return obj.has_result()
    has_result.boolean = True
    has_result.short_description = '有測驗結果'

@admin.register(IndividualTestResult)
class IndividualTestResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'test_project', 'result_status', 'overall_score', 'test_completion_date', 'report_generated']
    list_filter = ['result_status', 'test_completion_date', 'report_generated', 'test_project']
    search_fields = ['user__username', 'user__email', 'test_project__name']
    readonly_fields = ['created_at', 'updated_at', 'crawled_at']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('individual_test_record', 'test_project', 'user')
        }),
        ('測驗結果', {
            'fields': ('score_value', 'prediction_value', 'test_completion_date', 'external_test_id', 'test_url')
        }),
        ('結果數據', {
            'fields': ('raw_data', 'processed_data', 'category_results', 'trait_results'),
            'classes': ('collapse',)
        }),
        ('處理狀態', {
            'fields': ('result_status', 'crawled_at', 'crawl_attempts', 'crawl_error_message')
        }),
        ('報告生成', {
            'fields': ('report_generated', 'report_path', 'report_generated_at')
        }),
        ('個人化設定', {
            'fields': ('allow_sharing', 'notes')
        }),
        ('系統欄位', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def overall_score(self, obj):
        return obj.overall_score
    overall_score.short_description = '整體評分'

# 爬蟲管理
@admin.register(CrawlerLog)
class CrawlerLogAdmin(admin.ModelAdmin):
    list_display = ['task_name', 'status', 'success_count', 'fail_count', 'total_count', 'executed_at']
    list_filter = ['task_name', 'status', 'executed_at']
    search_fields = ['task_name', 'message']
    readonly_fields = ['executed_at', 'duration', 'success_rate']
    ordering = ['-executed_at']
    
    fieldsets = (
        ('任務資訊', {
            'fields': ('task_name', 'status', 'executed_at', 'duration')
        }),
        ('執行結果', {
            'fields': ('success_count', 'fail_count', 'total_count', 'success_rate')
        }),
        ('詳細資訊', {
            'fields': ('message', 'error_details'),
            'classes': ('collapse',)
        }),
    )
    
    def success_rate_display(self, obj):
        rate = obj.success_rate
        if rate >= 90:
            color = 'green'
        elif rate >= 70:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, float(rate)
        )
    success_rate_display.short_description = '成功率'
    success_rate_display.admin_order_field = 'success_count'
    
    actions = ['trigger_manual_crawl']
    
    def trigger_manual_crawl(self, request, queryset):
        """手動觸發爬蟲任務"""
        from core.tasks import crawl_all_pending_results
        
        # 異步執行爬蟲任務
        result = crawl_all_pending_results.delay()
        
        self.message_user(
            request,
            f"已觸發手動爬蟲任務，任務ID: {result.id}"
        )
    trigger_manual_crawl.short_description = "觸發手動爬蟲"


@admin.register(CrawlerDetailLog)
class CrawlerDetailLogAdmin(admin.ModelAdmin):
    list_display = ['invitee_name', 'invitee_email', 'test_project_name', 'status', 'execution_time', 'executed_at']
    list_filter = ['status', 'executed_at', 'data_found']
    search_fields = ['invitee_name', 'invitee_email', 'test_project_name', 'error_message']
    readonly_fields = ['executed_at', 'execution_time', 'crawled_data_size']
    ordering = ['-executed_at']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('crawler_log', 'test_invitation')
        }),
        ('受測人員資訊', {
            'fields': ('invitee_name', 'invitee_email', 'test_project_name')
        }),
        ('執行結果', {
            'fields': ('status', 'data_found', 'execution_time', 'crawled_data_size')
        }),
        ('錯誤資訊', {
            'fields': ('error_message', 'error_details'),
            'classes': ('collapse',)
        }),
        ('其他資訊', {
            'fields': ('attempt_count', 'executed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'crawler_log', 'test_invitation', 'test_invitation__invitee'
        )
    
    def status_display(self, obj):
        colors = {
            'success': 'green',
            'failed': 'red', 
            'skipped': 'orange'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = '狀態'
    status_display.admin_order_field = 'status'

# 註冊其他模型（如果還沒註冊）
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'user_type', 'is_active', 'is_email_verified']
    list_filter = ['user_type', 'is_active', 'is_email_verified']
    search_fields = ['username', 'email', 'first_name', 'last_name']

# 修復 Celery Beat Crontab 空欄位問題
from django_celery_beat.models import CrontabSchedule
from django_celery_beat.admin import CrontabScheduleAdmin

# 取消註冊原有的 CrontabScheduleAdmin
admin.site.unregister(CrontabSchedule)

@admin.register(CrontabSchedule)
class FixedCrontabScheduleAdmin(CrontabScheduleAdmin):
    """修復空欄位問題的 Crontab Admin"""
    
    def save_model(self, request, obj, form, change):
        # 自動填入空欄位，避免 ParseException
        if not obj.hour:
            obj.hour = '*'
        if not obj.day_of_week:
            obj.day_of_week = '*'
        if not obj.day_of_month:
            obj.day_of_month = '*'
        if not obj.month_of_year:
            obj.month_of_year = '*'
        
        super().save_model(request, obj, form, change)

# core/crawler_views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q
from .models import CrawlerLog, CrawlerDetailLog, TestInvitation
from .tasks import crawl_all_pending_results, crawl_test_result_async
import json

@login_required
@staff_member_required
def crawler_dashboard(request):
    """爬蟲管理儀表板"""
    
    # 最近30天的爬蟲日誌統計
    from datetime import timedelta
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    recent_logs = CrawlerLog.objects.filter(executed_at__gte=thirty_days_ago)
    
    stats = {
        'total_executions': recent_logs.count(),
        'successful_executions': recent_logs.filter(status='completed').count(),
        'failed_executions': recent_logs.filter(status='failed').count(),
        'total_crawled': sum(log.success_count for log in recent_logs),
        'total_failed': sum(log.fail_count for log in recent_logs),
    }
    
    # 待爬取的邀請數量（包含已完成和進行中的測驗）
    pending_invitations = TestInvitation.objects.filter(
        status__in=['completed', 'in_progress'],
        test_project__isnull=False
    ).exclude(
        testprojectresult__crawl_status='completed'
    ).count()
    
    # 最近的執行日誌
    recent_executions = CrawlerLog.objects.all()[:10]
    
    context = {
        'stats': stats,
        'pending_invitations': pending_invitations,
        'recent_executions': recent_executions,
    }
    
    return render(request, 'admin/crawler_dashboard.html', context)

@login_required
@staff_member_required
def crawler_logs(request):
    """爬蟲日誌列表"""
    
    # 搜尋和過濾
    search_query = request.GET.get('search', '')
    task_filter = request.GET.get('task', '')
    status_filter = request.GET.get('status', '')
    
    logs = CrawlerLog.objects.all()
    
    if search_query:
        logs = logs.filter(
            Q(message__icontains=search_query) |
            Q(error_details__icontains=search_query)
        )
    
    if task_filter:
        logs = logs.filter(task_name=task_filter)
    
    if status_filter:
        logs = logs.filter(status=status_filter)
    
    # 分頁
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 任務和狀態選項
    task_choices = CrawlerLog.TASK_CHOICES
    status_choices = CrawlerLog.STATUS_CHOICES
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'task_filter': task_filter,
        'status_filter': status_filter,
        'task_choices': task_choices,
        'status_choices': status_choices,
    }
    
    return render(request, 'admin/crawler_logs.html', context)

@login_required
@staff_member_required
def crawler_log_details(request, log_id):
    """爬蟲日誌詳細資訊"""
    from django.shortcuts import get_object_or_404
    
    log = get_object_or_404(CrawlerLog, id=log_id)
    detail_logs = CrawlerDetailLog.objects.filter(crawler_log=log).order_by('-executed_at')
    
    # 分頁
    paginator = Paginator(detail_logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 統計資訊
    stats = {
        'total_attempts': detail_logs.count(),
        'success_count': detail_logs.filter(status='success').count(),
        'failed_count': detail_logs.filter(status='failed').count(),
        'skipped_count': detail_logs.filter(status='skipped').count(),
    }
    
    context = {
        'log': log,
        'page_obj': page_obj,
        'stats': stats,
    }
    
    return render(request, 'admin/crawler_log_details.html', context)

@login_required
@staff_member_required
def trigger_crawler(request):
    """手動觸發爬蟲"""
    
    if request.method == 'POST':
        try:
            # 觸發異步爬蟲任務
            result = crawl_all_pending_results.delay()
            
            messages.success(
                request, 
                f'已成功觸發爬蟲任務！任務ID: {result.id}'
            )
            
            return JsonResponse({
                'success': True,
                'task_id': result.id,
                'message': '爬蟲任務已啟動'
            })
            
        except Exception as e:
            messages.error(request, f'觸發爬蟲失敗：{str(e)}')
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return redirect('crawler_dashboard')

@login_required
@staff_member_required
def crawler_settings(request):
    """爬蟲設定"""
    from django.conf import settings
    
    if request.method == 'POST':
        try:
            # 動態調整爬蟲設定
            timeout = int(request.POST.get('timeout', 30))
            retry_times = int(request.POST.get('retry_times', 3))
            delay = float(request.POST.get('delay', 2))
            headless = request.POST.get('headless', 'true') == 'true'
            
            # 更新設定 (這裡可以存到資料庫或快取)
            # 暫時返回成功訊息
            return JsonResponse({
                'success': True,
                'message': '設定已儲存'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    # 取得當前設定
    crawler_settings = getattr(settings, 'CRAWLER_SETTINGS', {})
    
    # 取得當前的Celery Beat排程
    try:
        from django_celery_beat.models import PeriodicTask
        total_tasks = PeriodicTask.objects.count()
        active_tasks = PeriodicTask.objects.filter(enabled=True).count()
        
        # 今日執行次數
        from datetime import timedelta
        today = timezone.now().date()
        today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
        recent_executions_count = CrawlerLog.objects.filter(
            executed_at__gte=today_start
        ).count()
        
    except Exception:
        total_tasks = 0
        active_tasks = 0
        recent_executions_count = 0
    
    context = {
        'settings': crawler_settings,
        'total_tasks': total_tasks,
        'active_tasks': active_tasks,
        'recent_executions_count': recent_executions_count,
        'next_crawl_time': '每2小時',  # 可以計算實際的下次執行時間
    }
    
    return render(request, 'admin/crawler_settings.html', context)

@login_required
@staff_member_required
def crawler_status_api(request):
    """爬蟲狀態API（用於AJAX更新）"""
    
    # 待爬取數量（包含已完成和進行中的測驗）
    pending_count = TestInvitation.objects.filter(
        status__in=['completed', 'in_progress'],
        test_project__isnull=False
    ).exclude(
        testprojectresult__crawl_status='completed'
    ).count()
    
    # 最近一次執行狀態
    latest_log = CrawlerLog.objects.first()
    
    data = {
        'pending_count': pending_count,
        'latest_execution': {
            'time': latest_log.executed_at.isoformat() if latest_log else None,
            'status': latest_log.status if latest_log else None,
            'success_count': latest_log.success_count if latest_log else 0,
            'fail_count': latest_log.fail_count if latest_log else 0,
        } if latest_log else None
    }
    
    return JsonResponse(data)

@login_required
@staff_member_required
def crawler_schedule(request):
    """排程管理"""
    
    if request.method == 'POST':
        try:
            from django_celery_beat.models import PeriodicTask, CrontabSchedule
            from celery.schedules import crontab
            
            action = request.POST.get('action')
            task_id = request.POST.get('task_id')
            
            if action == 'toggle':
                # 切換任務啟用狀態
                task = PeriodicTask.objects.get(id=task_id)
                task.enabled = not task.enabled
                task.save()
                
                return JsonResponse({
                    'success': True,
                    'enabled': task.enabled,
                    'message': f"任務已{'啟用' if task.enabled else '停用'}"
                })
                
            elif action == 'create_schedule':
                # 新增排程任務
                task_name = request.POST.get('task_name')
                task_type = request.POST.get('task_type')
                description = request.POST.get('description', '')
                
                minute = request.POST.get('minute', '*')
                hour = request.POST.get('hour', '*')
                day_of_week = request.POST.get('day_of_week', '*')
                day_of_month = request.POST.get('day_of_month', '*')
                month_of_year = request.POST.get('month_of_year', '*')
                
                # 驗證必填欄位
                if not all([task_name, task_type, minute, hour, day_of_week, day_of_month, month_of_year]):
                    return JsonResponse({
                        'success': False,
                        'error': '請填寫所有必填欄位'
                    }, status=400)
                
                # 檢查任務名稱是否已存在
                if PeriodicTask.objects.filter(name=task_name).exists():
                    return JsonResponse({
                        'success': False,
                        'error': '任務名稱已存在，請使用不同的名稱'
                    }, status=400)
                
                # 創建或取得crontab排程
                crontab_schedule, created = CrontabSchedule.objects.get_or_create(
                    minute=minute,
                    hour=hour,
                    day_of_week=day_of_week,
                    day_of_month=day_of_month,
                    month_of_year=month_of_year,
                )
                
                # 創建新的排程任務
                new_task = PeriodicTask.objects.create(
                    name=task_name,
                    task=task_type,
                    crontab=crontab_schedule,
                    enabled=True,
                    description=description
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'排程任務「{task_name}」已成功建立',
                    'task_id': new_task.id
                })
                
            elif action == 'update_schedule':
                # 更新排程
                task = PeriodicTask.objects.get(id=task_id)
                
                minute = request.POST.get('minute', '*')
                hour = request.POST.get('hour', '*')
                day_of_week = request.POST.get('day_of_week', '*')
                day_of_month = request.POST.get('day_of_month', '*')
                month_of_year = request.POST.get('month_of_year', '*')
                
                # 創建或取得crontab排程
                crontab_schedule, created = CrontabSchedule.objects.get_or_create(
                    minute=minute,
                    hour=hour,
                    day_of_week=day_of_week,
                    day_of_month=day_of_month,
                    month_of_year=month_of_year,
                )
                
                task.crontab = crontab_schedule
                task.save()
                
                return JsonResponse({
                    'success': True,
                    'message': '排程已更新'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    # 取得所有排程任務
    try:
        from django_celery_beat.models import PeriodicTask
        
        # 只顯示爬蟲相關的任務
        crawler_tasks = PeriodicTask.objects.filter(
            task__icontains='crawl'
        ).order_by('name')
        
        # 統計資訊
        total_tasks = crawler_tasks.count()
        enabled_tasks = crawler_tasks.filter(enabled=True).count()
        disabled_tasks = total_tasks - enabled_tasks
        
    except Exception:
        crawler_tasks = []
        total_tasks = 0
        enabled_tasks = 0
        disabled_tasks = 0
    
    context = {
        'crawler_tasks': crawler_tasks,
        'total_tasks': total_tasks,
        'enabled_tasks': enabled_tasks,
        'disabled_tasks': disabled_tasks,
    }
    
    return render(request, 'admin/crawler_schedule.html', context)
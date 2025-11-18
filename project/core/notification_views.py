#通知功能Views
# views/notification_views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from utils.notification import NotificationService
import logging
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

@login_required
def notification_list(request):
    """顯示所有通知"""
    from .models import Notification

    notifications = Notification.objects.filter(
        recipient=request.user
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    ).order_by('-created_at')

    # 分頁功能
    paginator = Paginator(notifications, 10)  # 每頁顯示10個通知
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    unread_count = notifications.filter(is_read=False).count()

    return render(request, 'notification/notification_list.html', {
        'page_obj': page_obj,
        'unread_count': unread_count,
    })

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """將通知標記為已讀"""
    from .models import Notification

    try:
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
    except Notification.DoesNotExist:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': '通知不存在'}, status=404)
        raise Http404

    notification.mark_as_read()
    success = True

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success' if success else 'error'})

    next_url = request.GET.get('next', 'notification_list')
    return redirect(next_url)

@login_required
@require_POST
def mark_all_read(request):
    """將所有通知標記為已讀"""
    from .models import Notification

    qs = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    )

    updated = qs.update(is_read=True, read_at=timezone.now())
    success = updated >= 0

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success' if success else 'error', 'updated': updated})

    return redirect('notification_list')

@login_required
@require_POST
def delete_notification(request, notification_id):
    """刪除通知"""
    from .models import Notification

    try:
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
    except Notification.DoesNotExist:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': '通知不存在'}, status=404)
        raise Http404

    notification.delete()
    success = True

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success' if success else 'error'})

    return redirect('notification_list')

from django.template.loader import render_to_string
def get_notification_dropdown(request):
    """獲取通知下拉內容"""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': '未登入'})
    
    try:
        # 直接使用模型，不用外部服務
        from .models import Notification
        
        # 獲取最新的通知
        notifications = Notification.objects.filter(
            recipient=request.user
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )[:10]
        
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).count()
        
        # 渲染模板
        from django.template.loader import render_to_string
        html = render_to_string('notification/notification_dropdown.html', {
            'notifications': notifications,
            'unread_count': unread_count,
        })
        
        return JsonResponse({
            'status': 'success',
            'html': html,
            'unread_count': unread_count
        })
        
    except Exception as e:
        logger.error(f"載入通知下拉失敗：{str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': '載入通知失敗'
        })

def get_notification_count(request):
    """獲取未讀通知數量"""
    if not request.user.is_authenticated:
        return JsonResponse({'unread_count': 0})
    
    try:
        from .models import Notification  # 修改這行
        from django.db.models import Q  # 加入這行
        
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).count()
        
        return JsonResponse({'unread_count': unread_count})
    except Exception as e:
        logger.error(f"獲取通知數量失敗：{str(e)}")
        return JsonResponse({'unread_count': 0})

# ===== 待辦事項視圖 =====

def todo_list(request):
    """顯示所有待辦事項"""
    todos = NotificationService.get_todos()
    
    pending = [todo for todo in todos if todo.status == 'pending']
    in_progress = [todo for todo in todos if todo.status == 'in_progress']
    completed = [todo for todo in todos if todo.status == 'completed']
    
    return render(request, 'notification/todo_list.html', {
        'pending': pending,
        'in_progress': in_progress,
        'completed': completed,
    })

def create_todo(request):
    """建立待辦事項"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        priority = int(request.POST.get('priority', 0))
        due_date_str = request.POST.get('due_date')
        
        due_date = None
        if due_date_str:
            try:
                due_date = timezone.datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                return redirect('todo_list')
        
        NotificationService.add_todo(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date
        )
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        
        return redirect('todo_list')
    
    return render(request, 'notification/todo_form.html')

def update_todo_status(request, todo_id):
    """更新待辦事項狀態"""
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ["pending", "in_progress", "completed"]:
            success = NotificationService.update_todo_status(todo_id, status)
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success' if success else 'error'})
        
        return redirect('todo_list')
    
    return redirect('todo_list')

def delete_todo(request, todo_id):
    """刪除待辦事項"""
    success = NotificationService.delete_todo(todo_id)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success' if success else 'error'})
    
    return redirect('todo_list')

# 操作日誌Views
# views/activity_log_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from utils.activity_log import ActivityLogService
import json

def activity_log_list(request):
    """顯示操作日誌列表"""
    # 獲取過濾參數
    filters = {}
    
    if request.method == 'GET':
        filters['user'] = request.GET.get('user', '')
        filters['action'] = request.GET.get('action', '')
        filters['target'] = request.GET.get('target', '')
        filters['date_from'] = request.GET.get('date_from', '')
        filters['date_to'] = request.GET.get('date_to', '')
        filters['search'] = request.GET.get('search', '')
    
    # 獲取分頁參數
    page = request.GET.get('page', 1)
    per_page = int(request.GET.get('per_page', 20))
    
    # 排序參數
    sort_by = request.GET.get('sort_by', 'created_at')
    sort_order = request.GET.get('sort_order', 'desc')
    
    # 計算起始位置
    start = (int(page) - 1) * per_page
    
    # 獲取日誌數據
    logs, total = ActivityLogService.get_logs(start=start, limit=per_page, filters=filters)
    
    # 創建分頁對象
    paginator = Paginator(range(total), per_page)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # 添加動作和目標類型選項
    actions = [{'key': key, 'label': label} for key, label in ActivityLogService.ACTIONS.items()]
    targets = [{'key': key, 'label': label} for key, label in ActivityLogService.TARGETS.items()]
    
    # 獲取用戶列表
    users = sorted(set(log.user for log in ActivityLogService.get_logs()[0]))
    
    # 處理AJAX請求
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # 如果是AJAX請求，返回JSON數據
        log_data = []
        for log in logs:
            log_dict = log.to_dict()
            log_dict['action_label'] = ActivityLogService.get_action_label(log.action)
            log_dict['target_label'] = ActivityLogService.get_target_label(log.target)
            log_data.append(log_dict)
            
        return JsonResponse({
            'logs': log_data,
            'total': total,
            'page': int(page),
            'per_page': per_page,
            'total_pages': paginator.num_pages
        })
    
    # 渲染模板
    return render(request, 'activity_log/log_list.html', {
        'logs': logs,
        'page_obj': page_obj,
        'per_page': per_page,
        'total': total,
        'filters': filters,
        'actions': actions,
        'targets': targets,
        'users': users,
        'sort_by': sort_by,
        'sort_order': sort_order
    })

def activity_log_detail(request, log_id):
    """顯示操作日誌詳情"""
    log = ActivityLogService.get_log_by_id(int(log_id))
    
    if not log:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': '找不到指定的日誌記錄'}, status=404)
        return redirect('activity_log_list')
    
    # 如果是JSON格式的內容，嘗試解析
    content_data = None
    if log.content and log.content.startswith('{'):
        try:
            content_data = json.loads(log.content)
        except json.JSONDecodeError:
            content_data = None
    
    # 處理AJAX請求
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        log_dict = log.to_dict()
        log_dict['action_label'] = ActivityLogService.get_action_label(log.action)
        log_dict['target_label'] = ActivityLogService.get_target_label(log.target)
        log_dict['content_data'] = content_data
        return JsonResponse(log_dict)
    
    # 渲染模板
    return render(request, 'activity_log/log_detail.html', {
        'log': log,
        'content_data': content_data,
        'action_label': ActivityLogService.get_action_label(log.action),
        'target_label': ActivityLogService.get_target_label(log.target)
    })

def export_activity_logs(request):
    """匯出操作日誌"""
    # 獲取過濾參數
    filters = {}
    
    if request.method == 'GET':
        filters['user'] = request.GET.get('user', '')
        filters['action'] = request.GET.get('action', '')
        filters['target'] = request.GET.get('target', '')
        filters['date_from'] = request.GET.get('date_from', '')
        filters['date_to'] = request.GET.get('date_to', '')
        filters['search'] = request.GET.get('search', '')
    
    # 獲取匯出格式
    export_format = request.GET.get('format', 'csv')
    
    # 匯出日誌
    content = ActivityLogService.export_logs(filters=filters, format=export_format)
    
    if not content:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': '匯出失敗'}, status=400)
        return redirect('activity_log_list')
    
    # 設置文件名
    filename = f"activity_logs_{timezone.now().strftime('%Y%m%d%H%M%S')}"
    
    # 設置響應頭
    content_types = {
        'csv': 'text/csv',
        'excel': 'application/vnd.ms-excel',
        'pdf': 'application/pdf'
    }
    
    content_type = content_types.get(export_format, 'text/plain')
    
    response = HttpResponse(content, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}.{export_format}"'
    
    return response

def dashboard_recent_activities(request):
    """獲取最近的活動記錄（用於儀表板）"""
    limit = int(request.GET.get('limit', 5))
    activities = ActivityLogService.get_recent_activities(limit=limit)
    
    activity_data = []
    for activity in activities:
        activity_dict = activity.to_dict()
        activity_dict['action_label'] = ActivityLogService.get_action_label(activity.action)
        activity_dict['target_label'] = ActivityLogService.get_target_label(activity.target)
        activity_data.append(activity_dict)
    
    return JsonResponse({'activities': activity_data})

def generate_test_logs(request):
    """生成測試日誌數據"""
    # 清空現有數據並重新初始化
    from utils.activity_log import ActivityLogService
    ActivityLogService.initialize_mock_data()
    
    # 返回成功訊息
    from django.contrib import messages
    messages.success(request, '已成功生成測試日誌數據')
    from django.shortcuts import redirect
    return redirect('activity_log_list')
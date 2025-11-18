# dashboard_views.py
from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from utils.dashboard_utils import (
    generate_dashboard_stats, 
    generate_recent_activities,
    generate_sales_chart_data,
    generate_product_pie_chart,
    generate_order_status_chart,
    get_year_month_day
)
from utils.activity_log import ActivityLogService
from utils.file_manager import FileManagerService
from utils.dashboard_utils import generate_dashboard_stats

class DashboardView(TemplateView):
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 确保只生成一次 stats
        stats = generate_dashboard_stats()
        
        # 预处理进度条百分比
        def calculate_progress(value, base=100, max_percentage=20):
            return min((value / base) * max_percentage, 100)
        
        # 添加进度条相关信息
        stats['today']['orders_progress'] = calculate_progress(stats['today']['orders'])
        stats['today']['revenue_progress'] = calculate_progress(stats['today']['revenue'], base=100000)
        stats['pending']['total_progress'] = calculate_progress(stats['pending']['total'], base=10, max_percentage=30)
        
        # 获取其他数据
        activities = generate_recent_activities(10)
        logs = ActivityLogService.get_recent_activities(5)
        files = FileManagerService.get_recent_files(5)
        date_info = get_year_month_day()
        
        context.update({
            'stats': stats,
            'activities': activities,
            'logs': logs,
            'files': files,
            'date_info': date_info
        })
        
        return context

def get_chart_data(request):
    """獲取圖表數據API"""
    chart_type = request.GET.get('type', 'sales')
    
    if chart_type == 'sales':
        data = generate_sales_chart_data()
    elif chart_type == 'product':
        data = generate_product_pie_chart()
    elif chart_type == 'order_status':
        data = generate_order_status_chart()
    else:
        data = {'error': '不支持的圖表類型'}
    
    return JsonResponse(data)
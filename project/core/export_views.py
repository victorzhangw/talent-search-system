# export_views.py
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from django.contrib import messages
from utils.export_utils import ExportService
import json

@require_GET
def export_data(request):
    """通用數據匯出視圖函數"""
    # 獲取參數
    export_format = request.GET.get('format', 'csv')
    data_type = request.GET.get('data_type', '')
    filename = request.GET.get('filename', None)
    
    # 根據數據類型獲取數據
    if data_type == 'user':
        data = ExportService.generate_sample_data(count=20, data_type='user')
        headers = {
            'id': '用戶ID',
            'username': '用戶名',
            'name': '姓名',
            'email': '電子郵件',
            'department': '部門',
            'role': '角色',
            'status': '狀態',
            'last_login': '最後登入時間'
        }
    elif data_type == 'order':
        data = ExportService.generate_sample_data(count=15, data_type='order')
        headers = {
            'id': '訂單編號',
            'customer': '客戶',
            'order_date': '訂單日期',
            'delivery_date': '交貨日期',
            'status': '狀態',
            'subtotal': '小計',
            'tax': '稅金',
            'total': '總計',
            'payment_method': '付款方式',
            'sales_person': '業務'
        }
    else:
        # 如果是AJAX請求，返回錯誤訊息
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': '未指定有效的數據類型'}, status=400)
        
        # 否則重定向到首頁
        messages.error(request, '未指定有效的數據類型')
        return redirect('home')
    
    # 根據格式匯出數據
    try:
        if export_format == 'csv':
            response = ExportService.export_csv(data, headers, filename)
        elif export_format == 'excel':
            response = ExportService.export_excel(data, headers, filename)
        elif export_format == 'pdf':
            response = ExportService.export_pdf(data, headers, filename)
        else:
            # 如果格式不支持，默認使用CSV
            response = ExportService.export_csv(data, headers, filename)
        
        return response
    except Exception as e:
        # 如果是AJAX請求，返回錯誤訊息
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': f'匯出失敗: {str(e)}'}, status=500)
        
        # 否則重定向到首頁
        messages.error(request, f'匯出失敗: {str(e)}')
        return redirect('home')

@require_GET
def export_custom_data(request):
    """自定義數據匯出視圖函數"""
    # 獲取參數
    export_format = request.GET.get('format', 'csv')
    
    # 獲取自定義數據
    # 這裡可以是前端傳來的JSON數據或者查詢參數
    data_json = request.GET.get('data', '[]')
    headers_json = request.GET.get('headers', '{}')
    
    try:
        # 解析JSON數據
        data = json.loads(data_json)
        headers = json.loads(headers_json)
        
        # 獲取檔名
        filename = request.GET.get('filename', None)
        
        # 根據格式匯出數據
        if export_format == 'csv':
            response = ExportService.export_csv(data, headers, filename)
        elif export_format == 'excel':
            response = ExportService.export_excel(data, headers, filename)
        elif export_format == 'pdf':
            response = ExportService.export_pdf(data, headers, filename)
        else:
            # 如果格式不支持，默認使用CSV
            response = ExportService.export_csv(data, headers, filename)
        
        return response
    except Exception as e:
        # 如果是AJAX請求，返回錯誤訊息
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': f'匯出失敗: {str(e)}'}, status=500)
        
        # 否則重定向到首頁
        messages.error(request, f'匯出失敗: {str(e)}')
        return redirect('home')

@require_GET
def export_table_data(request):
    """表格數據匯出視圖函數"""
    # 獲取參數
    export_format = request.GET.get('format', 'csv')
    table_id = request.GET.get('table_id', '')
    
    # 這裡應該根據table_id獲取數據，現在只是示例
    # 在實際應用中，應該從數據庫或緩存中獲取表格數據
    
    # 示例數據
    data = ExportService.generate_sample_data(count=10, data_type='user')
    headers = {
        'id': '用戶ID',
        'username': '用戶名',
        'name': '姓名',
        'email': '電子郵件',
        'department': '部門',
        'role': '角色',
        'status': '狀態',
        'last_login': '最後登入時間'
    }
    
    # 獲取檔名
    filename = request.GET.get('filename', f"table_{table_id}_{export_format}")
    
    # 根據格式匯出數據
    try:
        if export_format == 'csv':
            response = ExportService.export_csv(data, headers, filename)
        elif export_format == 'excel':
            response = ExportService.export_excel(data, headers, filename)
        elif export_format == 'pdf':
            response = ExportService.export_pdf(data, headers, filename)
        else:
            # 如果格式不支持，默認使用CSV
            response = ExportService.export_csv(data, headers, filename)
        
        return response
    except Exception as e:
        # 如果是AJAX請求，返回錯誤訊息
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': f'匯出失敗: {str(e)}'}, status=500)
        
        # 否則重定向到首頁
        messages.error(request, f'匯出失敗: {str(e)}')
        return redirect('home')

# 演示頁面視圖函數
def export_demo(request):
    """匯出功能演示頁面"""
    return render(request, 'export/export_demo.html')

from django.utils import timezone
@require_GET
    
def generate_sample_quotes(count=50):
    """生成示例報價單數據"""
    import random
    from datetime import datetime, timedelta
    
    customers = ['台灣電子股份有限公司', '台北貿易有限公司', '高雄機械工業', '台中資訊科技', '新北精密工業']
    statuses = ['draft', 'submitted', 'approved', 'rejected']
    status_labels = {'draft': '草稿', 'submitted': '已提交', 'approved': '已核准', 'rejected': '已拒絕'}
    creators = ['王經理', '李業務', '張主任', '陳專員', '林協理']
    
    quotes = []
    
    now = datetime.now()
    
    for i in range(1, count + 1):
        # 生成隨機日期 (過去90天內)
        random_days = random.randint(0, 90)
        quote_date = now - timedelta(days=random_days)
        quote_date_str = quote_date.strftime('%Y-%m-%d')
        
        # 生成隨機金額
        amount = random.randint(10000, 1000000)
        
        # 生成隨機狀態
        status = random.choice(statuses)
        
        # quotes.append({
        #     'id': f'QUO-{quote_date.year}{quote_date.month:02d}-{i:04d}',
        #     'customer': random.choice(customers),
        #     'date': quote_date_str,
        #     'amount': amount,
        #     'status': status_labels[status],
        #     'status_code': status,
        #     'created_by': random.choice(creators),
        #     'created_at': (quote_date - timedelta(days=random.randint(0, 3))).strftime('%Y-%m-%d %H:%M:%S'),
        #     'updated_at': (quote_date + timedelta(days=random.randint(0, 5))).strftime('%Y-%m-%d %H:%M:%S'),
        # })
        quotes = [
            {
                'id': f'QUO-{i}',
                'customer': f'客戶 {i}',
                'date': '2024-02-24',
                'amount': 15000 * i,
                'status': '已確認'
            } for i in range(1, count + 1)
        ]
    
    # 依照日期排序 (最新的在前)
    quotes.sort(key=lambda x: x['date'], reverse=True)
    
    return quotes
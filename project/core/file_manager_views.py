# 檔案管理views
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, FileResponse
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from utils.file_manager import FileManagerService
import mimetypes
import json
import os

def file_list(request):
    """顯示檔案列表"""
    # 獲取過濾參數
    filters = {}
    
    if request.method == 'GET':
        filters['filename'] = request.GET.get('filename', '')
        filters['uploaded_by'] = request.GET.get('uploaded_by', '')
        filters['file_type'] = request.GET.get('file_type', '')
        filters['date_from'] = request.GET.get('date_from', '')
        filters['date_to'] = request.GET.get('date_to', '')
    
    # 獲取分頁參數
    page = request.GET.get('page', 1)
    per_page = int(request.GET.get('per_page', 20))
    
    # 排序參數
    sort_by = request.GET.get('sort_by', 'created_at')
    sort_order = request.GET.get('sort_order', 'desc')
    
    # 計算起始位置
    start = (int(page) - 1) * per_page
    
    # 獲取檔案數據
    files, total = FileManagerService.get_files(start=start, limit=per_page, filters=filters)
    
    # 創建分頁對象
    paginator = Paginator(range(total), per_page)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # 獲取上傳者列表
    all_files, _ = FileManagerService.get_files()
    uploaders = sorted(set(file.uploaded_by for file in all_files))
    
    # 檔案類型選項
    file_types = [
        {'key': 'image', 'label': '圖片'},
        {'key': 'document', 'label': '文件'},
        {'key': 'spreadsheet', 'label': '試算表'},
        {'key': 'presentation', 'label': '簡報'},
        {'key': 'other', 'label': '其他'}
    ]
    
    # 處理AJAX請求
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # 如果是AJAX請求，返回JSON數據
        file_data = []
        for file in files:
            file_data.append(file.to_dict())
            
        return JsonResponse({
            'files': file_data,
            'total': total,
            'page': int(page),
            'per_page': per_page,
            'total_pages': paginator.num_pages
        })
    
    # 渲染模板
    return render(request, 'file_manager/file_list.html', {
        'files': files,
        'page_obj': page_obj,
        'per_page': per_page,
        'total': total,
        'filters': filters,
        'uploaders': uploaders,
        'file_types': file_types,
        'sort_by': sort_by,
        'sort_order': sort_order
    })

def file_detail(request, file_id):
    """顯示檔案詳情"""
    file = FileManagerService.get_file_by_id(int(file_id))
    
    if not file:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': '找不到指定的檔案'}, status=404)
        return redirect('file_list')
    
    # 處理AJAX請求
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse(file.to_dict())
    
    # 渲染模板
    return render(request, 'file_manager/file_detail.html', {
        'file': file
    })

def generate_test_files(request):
    """生成測試檔案數據"""
    # 清空現有數據並重新初始化
    FileManagerService.initialize_mock_data()
    
    # 返回成功訊息
    from django.contrib import messages
    messages.success(request, '已成功生成測試檔案數據')
    return redirect('file_list')

def upload_file(request):
    """上傳檔案"""
    if request.method == 'POST':
        # 獲取上傳的檔案資訊
        uploaded_file = request.FILES.get('file')
        description = request.POST.get('description', '')
        
        if uploaded_file:
            # 在實際應用中，這裡會保存文件到磁盤或雲存儲
            # 這裡我們只是模擬保存過程
            
            # 獲取檔案類型
            file_type = uploaded_file.content_type or mimetypes.guess_type(uploaded_file.name)[0] or 'application/octet-stream'
            
            # 獲取檔案大小
            file_size = uploaded_file.size
            
            # 獲取上傳者
            uploaded_by = request.POST.get('uploaded_by', 'admin')  # 在實際應用中，從用戶會話獲取
            
            # 添加檔案
            new_file = FileManagerService.add_file(
                filename=uploaded_file.name,
                file_size=file_size,
                file_type=file_type,
                uploaded_by=uploaded_by,
                description=description
            )
            
            # 處理AJAX請求
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'file': new_file.to_dict()
                })
            
            # 顯示成功訊息
            from django.contrib import messages
            messages.success(request, f'檔案 {uploaded_file.name} 上傳成功')
            return redirect('file_list')
        else:
            # 處理AJAX請求
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': '請選擇要上傳的檔案'
                }, status=400)
            
            # 顯示錯誤訊息
            from django.contrib import messages
            messages.error(request, '請選擇要上傳的檔案')
    
    # GET請求，顯示上傳表單
    return render(request, 'file_manager/file_upload.html')

def download_file(request, file_id):
    """下載檔案"""
    file = FileManagerService.get_file_by_id(int(file_id))
    
    if not file:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': '找不到指定的檔案'}, status=404)
        
        from django.contrib import messages
        messages.error(request, '找不到指定的檔案')
        return redirect('file_list')
    
    # 在實際應用中，這裡會從磁盤或雲存儲讀取文件
    # 這裡我們只是返回一個示例響應
    
    # 創建假的檔案內容
    content = f"This is a mock file content for {file.filename}. In a real application, this would be the actual file content."
    
    response = HttpResponse(content, content_type=file.file_type)
    response['Content-Disposition'] = f'attachment; filename="{file.filename}"'
    
    return response

def update_file(request, file_id):
    """更新檔案資訊"""
    file = FileManagerService.get_file_by_id(int(file_id))
    
    if not file:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': '找不到指定的檔案'}, status=404)
        
        from django.contrib import messages
        messages.error(request, '找不到指定的檔案')
        return redirect('file_list')
    
    if request.method == 'POST':
        # 獲取更新的資訊
        filename = request.POST.get('filename')
        description = request.POST.get('description')
        
        # 更新檔案
        result = FileManagerService.update_file(
            file_id=int(file_id),
            filename=filename,
            description=description
        )
        
        if result:
            # 獲取更新後的檔案
            updated_file = FileManagerService.get_file_by_id(int(file_id))
            
            # 處理AJAX請求
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'file': updated_file.to_dict() if updated_file else None
                })
            
            # 顯示成功訊息
            from django.contrib import messages
            messages.success(request, '檔案資訊更新成功')
            return redirect('file_detail', file_id=file_id)
        else:
            # 處理AJAX請求
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': '更新檔案資訊失敗'
                }, status=400)
            
            # 顯示錯誤訊息
            from django.contrib import messages
            messages.error(request, '更新檔案資訊失敗')
    
    # GET請求，顯示更新表單
    return render(request, 'file_manager/file_update.html', {
        'file': file
    })

def delete_file(request, file_id):
    """刪除檔案"""
    if request.method == 'POST':
        result = FileManagerService.delete_file(int(file_id))
        
        if result:
            # 處理AJAX請求
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success'})
            
            # 顯示成功訊息
            from django.contrib import messages
            messages.success(request, '檔案已成功刪除')
            return redirect('file_list')
        else:
            # 處理AJAX請求
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': '刪除檔案失敗'
                }, status=400)
            
            # 顯示錯誤訊息
            from django.contrib import messages
            messages.error(request, '刪除檔案失敗')
            return redirect('file_list')
    
    # 非POST請求，重定向到檔案列表
    return redirect('file_list')

def batch_delete_files(request):
    """批量刪除檔案"""
    if request.method == 'POST':
        # 從請求體獲取要刪除的檔案ID列表
        file_ids = request.POST.getlist('file_ids')
        
        if not file_ids:
            # 處理AJAX請求
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': '請選擇要刪除的檔案'
                }, status=400)
            
            # 顯示錯誤訊息
            from django.contrib import messages
            messages.error(request, '請選擇要刪除的檔案')
            return redirect('file_list')
        
        # 批量刪除
        successful_deletes = 0
        for file_id in file_ids:
            if FileManagerService.delete_file(int(file_id)):
                successful_deletes += 1
        
        # 處理AJAX請求
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'deleted_count': successful_deletes,
                'total_count': len(file_ids)
            })
        
        # 顯示成功訊息
        from django.contrib import messages
        if successful_deletes == len(file_ids):
            messages.success(request, f'已成功刪除 {successful_deletes} 個檔案')
        else:
            messages.warning(request, f'已刪除 {successful_deletes}/{len(file_ids)} 個檔案，部分檔案刪除失敗')
        
        return redirect('file_list')
    
    # 非POST請求，重定向到檔案列表
    return redirect('file_list')

def dashboard_recent_files(request):
    """獲取最近上傳的檔案（用於儀表板）"""
    limit = int(request.GET.get('limit', 5))
    recent_files = FileManagerService.get_recent_files(limit=limit)
    
    file_data = []
    for file in recent_files:
        file_data.append(file.to_dict())
    
    return JsonResponse({'files': file_data})
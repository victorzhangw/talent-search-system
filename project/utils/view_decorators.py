from functools import wraps
from django.utils import timezone
from .export_utils import ExportService

def exportable(data_func=None, filename_prefix='export'):
    """
    裝飾器：讓視圖函數支持通用匯出功能
    
    參數:
        data_func: 獲取匯出數據的函數，如果為None則使用視圖函數獲取數據
        filename_prefix: 匯出檔案名稱前綴
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            # 檢查是否為匯出請求
            if 'export' in request.GET and request.GET.get('format'):
                export_format = request.GET.get('format')
                
                # 獲取數據
                if data_func:
                    data = data_func(request, *args, **kwargs)
                else:
                    # 從視圖函數的context獲取數據
                    response = view_func(request, *args, **kwargs)
                    if hasattr(response, 'context_data'):
                        data = response.context_data.get('items', [])
                    else:
                        data = []
                
                # 取得欄位定義
                columns = request.GET.get('columns', '').split(',')
                
                # 構建headers
                headers = {}
                for col in columns:
                    headers[col] = col.capitalize()
                
                # 匯出
                filename = f"{filename_prefix}_{timezone.now().strftime('%Y%m%d')}"
                if export_format == 'csv':
                    return ExportService.export_csv(data, headers, filename + '.csv')
                elif export_format == 'excel':
                    return ExportService.export_excel(data, headers, filename + '.xlsx')
                elif export_format == 'pdf':
                    return ExportService.export_pdf(data, headers, filename + '.pdf')
                
            # 非匯出請求，正常處理
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
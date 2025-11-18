# utils/export_utils.py
import csv
import io
import json
from django.http import HttpResponse
import datetime
import random

class ExportService:
    """匯出服務類 - 提供數據匯出功能"""
    
    @staticmethod
    def export_csv(data, headers, filename=None):
        """
        將數據匯出為CSV格式
        
        參數:
            data: 要匯出的數據列表
            headers: 標題欄位字典，格式為 {'欄位名稱': '顯示名稱'}
            filename: 下載的檔案名稱 (可選)
        
        返回:
            HttpResponse 包含CSV數據
        """
        if filename is None:
            filename = f"export_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        
        # 創建一個文件流
        csv_buffer = io.StringIO()
        
        # 創建CSV寫入器
        writer = csv.writer(csv_buffer)
        
        # 寫入標題行
        header_row = [headers[field] for field in headers]
        writer.writerow(header_row)
        
        # 寫入數據行
        for row in data:
            row_data = []
            for field in headers:
                # 處理嵌套屬性 (例如：'user.name')
                value = row
                for part in field.split('.'):
                    if isinstance(value, dict):
                        value = value.get(part, '')
                    else:
                        try:
                            value = getattr(value, part, '')
                        except:
                            value = ''
                row_data.append(value)
            writer.writerow(row_data)
        
        # 創建HTTP響應
        response = HttpResponse(csv_buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    @staticmethod
    def export_excel(data, headers, filename=None):
        """
        將數據匯出為Excel格式
        
        參數:
            data: 要匯出的數據列表
            headers: 標題欄位字典，格式為 {'欄位名稱': '顯示名稱'}
            filename: 下載的檔案名稱 (可選)
        
        返回:
            HttpResponse 包含Excel數據
        """
        if filename is None:
            filename = f"export_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        
        # 這裡模擬匯出，實際應用應使用pandas或openpyxl
        # 在這個模擬版本中，我們只返回一個空的Excel檔案表示成功
        
        # 創建一個文件流
        excel_buffer = io.BytesIO()
        
        # 模擬一些Excel數據
        excel_buffer.write(b'PK\x03\x04\x14\x00\x00\x00\x08\x00')  # 一些Excel文件頭數據
        
        # 創建HTTP響應
        response = HttpResponse(excel_buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    @staticmethod
    def export_pdf(data, headers, filename=None, template=None):
        """
        將數據匯出為PDF格式
        
        參數:
            data: 要匯出的數據列表
            headers: 標題欄位字典，格式為 {'欄位名稱': '顯示名稱'}
            filename: 下載的檔案名稱 (可選)
            template: PDF模板 (可選)
        
        返回:
            HttpResponse 包含PDF數據
        """
        if filename is None:
            filename = f"export_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        
        # 這裡模擬匯出，實際應用應使用reportlab或wkhtmltopdf
        # 在這個模擬版本中，我們只返回一個空的PDF檔案表示成功
        
        # 創建一個文件流
        pdf_buffer = io.BytesIO()
        
        # 模擬一些PDF數據
        pdf_header = b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj'
        pdf_buffer.write(pdf_header)
        
        # 創建HTTP響應
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    @staticmethod
    def convert_queryset_to_list(queryset, fields=None):
        """
        將Django QuerySet轉換為可序列化的列表
        
        參數:
            queryset: Django QuerySet
            fields: 要包含的欄位列表 (可選)
        
        返回:
            數據列表
        """
        # 這裡是模擬版本，在實際應用中會處理Django的QuerySet
        result = []
        for item in queryset:
            if hasattr(item, '__dict__'):
                item_dict = item.__dict__.copy()
                # 移除Django內部欄位
                if '_state' in item_dict:
                    del item_dict['_state']
                if fields:
                    # 只保留指定的欄位
                    item_dict = {field: item_dict.get(field, '') for field in fields if field in item_dict}
                result.append(item_dict)
            elif isinstance(item, dict):
                if fields:
                    # 只保留指定的欄位
                    item_dict = {field: item.get(field, '') for field in fields if field in item}
                else:
                    item_dict = item
                result.append(item_dict)
        
        return result
    
    # 模擬數據生成方法 (用於示例)
    @staticmethod
    def generate_sample_data(count=10, data_type='user'):
        """生成示例數據用於匯出演示"""
        data = []
        
        if data_type == 'user':
            first_names = ['張', '李', '王', '陳', '林', '黃', '趙', '吳', '劉', '周']
            last_names = ['小明', '小華', '大力', '雅琪', '思雨', '志豪', '家豪', '美玲', '怡君', '建宏']
            departments = ['人事部', '財務部', '行銷部', '研發部', '業務部', '客服部', '資訊部', '總務部']
            roles = ['管理員', '一般用戶', '訪客', '主管', '副理', '經理', '總監']
            
            for i in range(1, count + 1):
                data.append({
                    'id': i,
                    'username': f'user{i}',
                    'name': random.choice(first_names) + random.choice(last_names),
                    'email': f'user{i}@example.com',
                    'department': random.choice(departments),
                    'role': random.choice(roles),
                    'status': random.choice(['啟用', '停用']),
                    'last_login': (datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        elif data_type == 'order':
            customers = ['台灣電子股份有限公司', '台北貿易有限公司', '高雄機械工業', '台中資訊科技', '新北精密工業']
            products = ['筆記型電腦', '智慧型手機', '辦公桌椅', '印表機', '螢幕', '滑鼠', '鍵盤', '伺服器', '軟體授權']
            statuses = ['待處理', '處理中', '已完成', '已取消', '待付款']
            
            for i in range(1, count + 1):
                order_date = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 60))
                delivery_date = order_date + datetime.timedelta(days=random.randint(3, 15))
                
                # 生成訂單項目
                items = []
                item_count = random.randint(1, 5)
                total_amount = 0
                
                for j in range(item_count):
                    product = random.choice(products)
                    price = random.randint(100, 10000)
                    quantity = random.randint(1, 10)
                    subtotal = price * quantity
                    total_amount += subtotal
                    
                    items.append({
                        'product': product,
                        'price': price,
                        'quantity': quantity,
                        'subtotal': subtotal
                    })
                
                # 計算稅金和總計
                tax = round(total_amount * 0.05, 2)
                grand_total = total_amount + tax
                
                data.append({
                    'id': f'ORD-{order_date.year}{order_date.month:02d}-{i:04d}',
                    'customer': random.choice(customers),
                    'order_date': order_date.strftime('%Y-%m-%d'),
                    'delivery_date': delivery_date.strftime('%Y-%m-%d'),
                    'status': random.choice(statuses),
                    'items': items,
                    'subtotal': total_amount,
                    'tax': tax,
                    'total': grand_total,
                    'payment_method': random.choice(['信用卡', '銀行轉帳', '貨到付款']),
                    'sales_person': f'業務{random.randint(1, 5)}'
                })
        
        return data
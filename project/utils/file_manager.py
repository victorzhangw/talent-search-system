# 檔案管理工具
from django.utils import timezone
from datetime import timedelta
import random
import os
import uuid
import mimetypes

class MockFile:
    """模擬檔案類"""
    def __init__(self, id, filename, file_type, file_size, uploaded_by, description=None, created_at=None, updated_at=None):
        self.id = id
        self.filename = filename
        self.file_type = file_type
        self.file_size = file_size  # 以位元組為單位
        self.uploaded_by = uploaded_by
        self.description = description
        self.created_at = created_at or timezone.now()
        self.updated_at = updated_at or self.created_at
        
        # 設置檔案路徑和URL (模擬)
        self.file_path = f"uploads/{self.created_at.strftime('%Y/%m/%d')}/{filename}"
        self.file_url = f"/media/{self.file_path}"
    
    @property
    def time_since(self):
        """返回檔案上傳後經過的時間"""
        delta = timezone.now() - self.created_at
        
        if delta.days > 7:
            return self.created_at.strftime('%Y-%m-%d')
        elif delta.days > 0:
            return f"{delta.days} 天前"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600} 小時前"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60} 分鐘前"
        else:
            return "剛剛"
    
    @property
    def formatted_size(self):
        """返回格式化的檔案大小"""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size/1024:.1f} KB"
        elif self.file_size < 1024 * 1024 * 1024:
            return f"{self.file_size/(1024*1024):.1f} MB"
        else:
            return f"{self.file_size/(1024*1024*1024):.1f} GB"
    
    @property
    def icon_class(self):
        """返回檔案類型對應的圖標類名"""
        file_ext = os.path.splitext(self.filename)[1].lower()
        
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg']:
            return "bi-file-image"
        elif file_ext in ['.doc', '.docx']:
            return "bi-file-word"
        elif file_ext in ['.xls', '.xlsx']:
            return "bi-file-excel"
        elif file_ext in ['.ppt', '.pptx']:
            return "bi-file-ppt"
        elif file_ext in ['.pdf']:
            return "bi-file-pdf"
        elif file_ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
            return "bi-file-zip"
        elif file_ext in ['.txt', '.md', '.log']:
            return "bi-file-text"
        elif file_ext in ['.html', '.htm', '.css', '.js']:
            return "bi-file-code"
        elif file_ext in ['.mp3', '.wav', '.ogg', '.flac']:
            return "bi-file-music"
        elif file_ext in ['.mp4', '.avi', '.mov', '.wmv', '.mkv']:
            return "bi-file-play"
        else:
            return "bi-file-earmark"
    
    def to_dict(self):
        """將檔案轉換為字典"""
        return {
            'id': self.id,
            'filename': self.filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'formatted_size': self.formatted_size,
            'uploaded_by': self.uploaded_by,
            'description': self.description,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            'time_since': self.time_since,
            'file_path': self.file_path,
            'file_url': self.file_url,
            'icon_class': self.icon_class
        }


class FileManagerService:
    """檔案管理服務類 - 使用假資料"""
    _files = []
    
    @classmethod
    def initialize_mock_data(cls):
        """初始化模擬數據"""
        # 清空現有數據
        cls._files = []
        
        # 模擬用戶
        users = ['admin', '王小明', '李小華', '張經理', '陳主管']
        
        # 模擬檔案
        file_names = [
            'quarterly_report_2024Q1.pdf',
            'product_catalog_2024.xlsx',
            'customer_feedback.docx',
            'employee_handbook.pdf',
            'company_logo.png',
            'marketing_plan.pptx',
            'sales_data_2024.xlsx',
            'meeting_minutes.txt',
            'project_timeline.xlsx',
            'system_requirements.docx',
            'corporate_presentation.pptx',
            'invoice_template.docx',
            'user_manual.pdf',
            'contract_draft.pdf',
            'product_image.jpg'
        ]
        
        # 創建模擬檔案
        now = timezone.now()
        
        for i in range(1, len(file_names) + 1):
            filename = file_names[i-1]
            file_ext = os.path.splitext(filename)[1].lower()
            
            # 獲取檔案類型
            file_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            
            # 模擬檔案大小
            if file_ext in ['.pdf', '.docx', '.doc', '.pptx', '.ppt']:
                file_size = random.randint(500, 5000) * 1024  # 500KB-5MB
            elif file_ext in ['.xlsx', '.xls']:
                file_size = random.randint(100, 2000) * 1024  # 100KB-2MB
            elif file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                file_size = random.randint(50, 1000) * 1024  # 50KB-1MB
            else:
                file_size = random.randint(10, 500) * 1024  # 10KB-500KB
            
            # 模擬上傳時間
            days_ago = random.randint(0, 60)
            hours_ago = random.randint(0, 23)
            created_at = now - timedelta(days=days_ago, hours=hours_ago)
            
            # 模擬更新時間
            update_days_ago = random.randint(0, days_ago)
            update_hours_ago = random.randint(0, 23)
            updated_at = now - timedelta(days=update_days_ago, hours=update_hours_ago)
            
            # 模擬描述
            descriptions = [
                f"{os.path.splitext(filename)[0]} 文件",
                f"關於{os.path.splitext(filename)[0]}的資料",
                f"{os.path.splitext(filename)[0]} 相關文件",
                None  # 有些檔案沒有描述
            ]
            
            cls._files.append(MockFile(
                id=i,
                filename=filename,
                file_type=file_type,
                file_size=file_size,
                uploaded_by=random.choice(users),
                description=random.choice(descriptions),
                created_at=created_at,
                updated_at=updated_at
            ))
        
        # 按上傳時間降序排序
        cls._files.sort(key=lambda x: x.created_at, reverse=True)
    
    @classmethod
    def get_files(cls, start=0, limit=None, filters=None):
        """獲取檔案列表，支持分頁和過濾"""
        if not cls._files:
            cls.initialize_mock_data()
        
        # 應用過濾條件
        filtered_files = cls._files
        if filters:
            if 'filename' in filters and filters['filename']:
                search_term = filters['filename'].lower()
                filtered_files = [f for f in filtered_files if search_term in f.filename.lower()]
            
            if 'uploaded_by' in filters and filters['uploaded_by']:
                filtered_files = [f for f in filtered_files if f.uploaded_by == filters['uploaded_by']]
            
            if 'file_type' in filters and filters['file_type']:
                file_type = filters['file_type']
                if file_type == 'image':
                    filtered_files = [f for f in filtered_files if f.file_type.startswith('image/')]
                elif file_type == 'document':
                    filtered_files = [f for f in filtered_files if f.file_type in 
                                    ['application/pdf', 'application/msword', 
                                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document']]
                elif file_type == 'spreadsheet':
                    filtered_files = [f for f in filtered_files if f.file_type in 
                                    ['application/vnd.ms-excel',
                                     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']]
                elif file_type == 'presentation':
                    filtered_files = [f for f in filtered_files if f.file_type in 
                                    ['application/vnd.ms-powerpoint',
                                     'application/vnd.openxmlformats-officedocument.presentationml.presentation']]
                elif file_type == 'other':
                    exclude_types = ['image/', 'application/pdf', 'application/msword', 
                                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                    'application/vnd.ms-excel',
                                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                    'application/vnd.ms-powerpoint',
                                    'application/vnd.openxmlformats-officedocument.presentationml.presentation']
                    filtered_files = [f for f in filtered_files if not any(f.file_type.startswith(t) for t in exclude_types)]
            
            if 'date_from' in filters and filters['date_from']:
                date_from = timezone.datetime.strptime(filters['date_from'], '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
                filtered_files = [f for f in filtered_files if f.created_at >= date_from]
            
            if 'date_to' in filters and filters['date_to']:
                date_to = timezone.datetime.strptime(filters['date_to'], '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.get_current_timezone())
                filtered_files = [f for f in filtered_files if f.created_at <= date_to]
        
        # 計算總數
        total = len(filtered_files)
        
        # 分頁
        if limit:
            filtered_files = filtered_files[start:start+limit]
        
        return filtered_files, total
    
    @classmethod
    def get_file_by_id(cls, file_id):
        """根據ID獲取檔案"""
        if not cls._files:
            cls.initialize_mock_data()
            
        for file in cls._files:
            if file.id == file_id:
                return file
        return None
    
    @classmethod
    def add_file(cls, filename, file_size, file_type, uploaded_by, description=None):
        """添加一個檔案"""
        if not cls._files:
            cls.initialize_mock_data()
        
        new_id = max([file.id for file in cls._files], default=0) + 1
        
        new_file = MockFile(
            id=new_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            uploaded_by=uploaded_by,
            description=description
        )
        
        cls._files.insert(0, new_file)  # 插入到列表前面
        return new_file
    
    @classmethod
    def update_file(cls, file_id, filename=None, description=None):
        """更新檔案資訊"""
        file = cls.get_file_by_id(file_id)
        if not file:
            return False
        
        if filename:
            file.filename = filename
            # 如果檔名變了，更新檔案類型
            file.file_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            file.file_path = f"uploads/{file.created_at.strftime('%Y/%m/%d')}/{filename}"
            file.file_url = f"/media/{file.file_path}"
        
        if description is not None:  # 允許將描述設為空字符串
            file.description = description
        
        file.updated_at = timezone.now()
        
        return True
    
    @classmethod
    def delete_file(cls, file_id):
        """刪除檔案"""
        file = cls.get_file_by_id(file_id)
        if not file:
            return False
        
        cls._files.remove(file)
        return True
    
    @classmethod
    def get_recent_files(cls, limit=5):
        """獲取最近上傳的檔案"""
        if not cls._files:
            cls.initialize_mock_data()
        
        return cls._files[:limit]
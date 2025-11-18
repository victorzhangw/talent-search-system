#操作日誌
# utils/activity_log.py
from django.utils import timezone
from datetime import timedelta
import random
import uuid
import json

class MockActivityLog:
    """模擬操作日誌類"""
    def __init__(self, id, user, action, target, target_id, content=None, ip_address=None, created_at=None):
        self.id = id
        self.user = user
        self.action = action
        self.target = target
        self.target_id = target_id
        self.content = content
        self.ip_address = ip_address or f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
        self.created_at = created_at or timezone.now()
    
    @property
    def time_since(self):
        """返回日誌創建後經過的時間"""
        delta = timezone.now() - self.created_at
        
        if delta.days > 7:
            return self.created_at.strftime('%Y-%m-%d %H:%M')
        elif delta.days > 0:
            return f"{delta.days} 天前"
        elif delta.seconds > 3600:
            return f"{delta.seconds // 3600} 小時前"
        elif delta.seconds > 60:
            return f"{delta.seconds // 60} 分鐘前"
        else:
            return "剛剛"
    
    def to_dict(self):
        """將日誌轉換為字典"""
        return {
            'id': self.id,
            'user': self.user,
            'action': self.action,
            'target': self.target,
            'target_id': self.target_id,
            'content': self.content,
            'ip_address': self.ip_address,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'time_since': self.time_since
        }


class ActivityLogService:
    """操作日誌服務類 - 使用假資料"""
    _logs = []
    
    # 定義可能的操作類型
    ACTIONS = {
        'create': '創建',
        'update': '更新',
        'delete': '刪除',
        'view': '查看',
        'export': '匯出',
        'import': '匯入',
        'login': '登入',
        'logout': '登出',
        'approve': '核准',
        'reject': '拒絕'
    }
    
    # 定義可能的目標對象
    TARGETS = {
        'user': '用戶',
        'role': '角色',
        'quote': '報價單',
        'order': '訂單',
        'shipment': '出貨單',
        'product': '產品',
        'customer': '客戶',
        'supplier': '供應商',
        'system': '系統'
    }
    
    @classmethod
    def initialize_mock_data(cls):
        """初始化模擬數據"""
        # 清空現有數據
        cls._logs = []
        
        # 模擬用戶
        users = ['admin', '王小明', '李小華', '張經理', '陳主管']
        
        # 創建模擬日誌
        now = timezone.now()
        action_keys = list(cls.ACTIONS.keys())
        target_keys = list(cls.TARGETS.keys())
        
        for i in range(1, 51):  # 創建50條日誌記錄
            user = random.choice(users)
            action = random.choice(action_keys)
            target = random.choice(target_keys)
            target_id = str(uuid.uuid4())[:8]  # 隨機ID
            
            # 創建日期，最近30天內的隨機時間
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            created_at = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
            
            # 根據操作類型生成適當的內容
            content = None
            if action == 'create':
                content = f"創建了一個新的{cls.TARGETS[target]}"
            elif action == 'update':
                content = f"更新了{cls.TARGETS[target]}的信息"
                
                # 添加一些修改內容的細節
                if target == 'user':
                    changes = random.choice([
                        '{"name": ["舊值", "新值"]}',
                        '{"email": ["old@example.com", "new@example.com"]}',
                        '{"role": ["普通用戶", "管理員"]}'
                    ])
                elif target in ['quote', 'order', 'shipment']:
                    changes = random.choice([
                        '{"status": ["草稿", "已提交"]}',
                        '{"total": ["1000", "1200"]}',
                        '{"customer": ["客戶A", "客戶B"]}'
                    ])
                else:
                    changes = '{"field": ["舊值", "新值"]}'
                    
                content = json.dumps({
                    'message': content,
                    'changes': json.loads(changes)
                })
                
            elif action == 'delete':
                content = f"刪除了{cls.TARGETS[target]} (ID: {target_id})"
            elif action == 'login':
                content = "登入系統"
            elif action == 'logout':
                content = "登出系統"
            elif action == 'approve' or action == 'reject':
                content = f"{cls.ACTIONS[action]}了{cls.TARGETS[target]} (ID: {target_id})"
            
            cls._logs.append(MockActivityLog(
                id=i,
                user=user,
                action=action,
                target=target,
                target_id=target_id,
                content=content,
                created_at=created_at
            ))
        
        # 按創建時間降序排序
        cls._logs.sort(key=lambda x: x.created_at, reverse=True)
    
    @classmethod
    def get_logs(cls, start=0, limit=None, filters=None):
        """獲取日誌列表，支持分頁和過濾"""
        if not cls._logs:
            cls.initialize_mock_data()
        
        # 應用過濾條件
        filtered_logs = cls._logs
        if filters:
            if 'user' in filters and filters['user']:
                filtered_logs = [log for log in filtered_logs if log.user == filters['user']]
            
            if 'action' in filters and filters['action']:
                filtered_logs = [log for log in filtered_logs if log.action == filters['action']]
            
            if 'target' in filters and filters['target']:
                filtered_logs = [log for log in filtered_logs if log.target == filters['target']]
            
            if 'date_from' in filters and filters['date_from']:
                date_from = timezone.datetime.strptime(filters['date_from'], '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
                filtered_logs = [log for log in filtered_logs if log.created_at >= date_from]
            
            if 'date_to' in filters and filters['date_to']:
                date_to = timezone.datetime.strptime(filters['date_to'], '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.get_current_timezone())
                filtered_logs = [log for log in filtered_logs if log.created_at <= date_to]
            
            if 'search' in filters and filters['search']:
                search_term = filters['search'].lower()
                filtered_logs = [log for log in filtered_logs if 
                                search_term in log.user.lower() or 
                                (log.content and search_term in log.content.lower()) or
                                (log.target_id and search_term in log.target_id.lower())]
        
        # 計算總數
        total = len(filtered_logs)
        
        # 分頁
        if limit:
            filtered_logs = filtered_logs[start:start+limit]
        
        return filtered_logs, total
    
    @classmethod
    def add_log(cls, user, action, target, target_id, content=None, ip_address=None):
        """添加一條操作日誌"""
        if not cls._logs:
            cls.initialize_mock_data()
        
        new_id = max([log.id for log in cls._logs], default=0) + 1
        
        new_log = MockActivityLog(
            id=new_id,
            user=user,
            action=action,
            target=target,
            target_id=target_id,
            content=content,
            ip_address=ip_address
        )
        
        cls._logs.insert(0, new_log)  # 插入到列表前面
        return new_log
    
    @classmethod
    def get_log_by_id(cls, log_id):
        """根據ID獲取日誌"""
        if not cls._logs:
            cls.initialize_mock_data()
            
        for log in cls._logs:
            if log.id == log_id:
                return log
        return None
    
    @classmethod
    def get_action_label(cls, action_key):
        """獲取操作類型的顯示名稱"""
        return cls.ACTIONS.get(action_key, action_key)
    
    @classmethod
    def get_target_label(cls, target_key):
        """獲取目標對象的顯示名稱"""
        return cls.TARGETS.get(target_key, target_key)
    
    @classmethod
    def get_recent_activities(cls, limit=5):
        """獲取最近的活動記錄"""
        if not cls._logs:
            cls.initialize_mock_data()
        
        return cls._logs[:limit]
    
    @classmethod
    def export_logs(cls, filters=None, format='csv'):
        """匯出日誌"""
        logs, _ = cls.get_logs(filters=filters)
        
        if format == 'csv':
            # 假裝生成CSV
            return "csv_content"
        elif format == 'excel':
            # 假裝生成Excel
            return "excel_content"
        elif format == 'pdf':
            # 假裝生成PDF
            return "pdf_content"
        else:
            return None
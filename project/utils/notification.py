# 通知功能
# utils/notification.py
from django.utils import timezone
from datetime import timedelta
import random

class MockNotification:
    """模擬通知類"""
    def __init__(self, id, title, message, type="info", created_at=None, is_read=False, icon=None, link=None):
        self.id = id
        self.title = title
        self.message = message
        self.type = type
        self.created_at = created_at or timezone.now()
        self.is_read = is_read
        self.link = link
        
        # 根據類型設置圖標
        if icon:
            self.icon = icon
        else:
            icons = {
                'info': 'bi-info-circle',
                'warning': 'bi-exclamation-triangle',
                'success': 'bi-check-circle',
                'danger': 'bi-x-circle',
                'task': 'bi-list-check'
            }
            self.icon = icons.get(type, 'bi-bell')
    
    @property
    def time_since(self):
        """返回通知發送後經過的時間"""
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


class MockTodoItem:
    """模擬待辦事項類"""
    def __init__(self, id, title, description=None, status="pending", priority=0, due_date=None, created_at=None, completed_at=None):
        self.id = id
        self.title = title
        self.description = description
        self.status = status
        self.priority = priority
        self.due_date = due_date
        self.created_at = created_at or timezone.now()
        self.completed_at = completed_at


class NotificationService:
    """通知服務類 - 使用假資料"""
    _notifications = []
    _todos = []
    
    @classmethod
    def initialize_mock_data(cls):
        """初始化模擬數據"""
        # 清空現有數據
        cls._notifications = []
        cls._todos = []
        
        # 創建模擬通知
        notification_types = ['info', 'warning', 'success', 'danger', 'task']
        now = timezone.now()
        
        for i in range(1, 11):
            notification_type = random.choice(notification_types)
            created_time = now - timedelta(days=random.randint(0, 10), 
                                           hours=random.randint(0, 23), 
                                           minutes=random.randint(0, 59))
            
            if notification_type == 'info':
                title = "系統更新通知"
                message = "系統將於今晚進行例行維護，請提前保存您的工作。"
            elif notification_type == 'warning':
                title = "庫存警告"
                message = f"產品 SKU-{random.randint(1000, 9999)} 庫存低於警戒值"
            elif notification_type == 'success':
                title = "訂單已完成"
                message = f"訂單 #{random.randint(10000, 99999)} 已成功處理完成"
            elif notification_type == 'danger':
                title = "付款失敗"
                message = f"客戶 {random.choice(['王小明', '李小華', '張大力', '陳小芳'])} 的付款處理失敗"
            else:  # task
                title = "待處理任務"
                message = f"您有一項新的任務需要處理：{random.choice(['聯繫客戶', '審核訂單', '處理退貨申請', '更新產品資訊'])}"
                
            is_read = random.choice([True, False, False])  # 增加未讀概率
                
            cls._notifications.append(MockNotification(
                id=i,
                title=title,
                message=message,
                type=notification_type,
                created_at=created_time,
                is_read=is_read
            ))
            
        # 創建模擬待辦事項
        todo_titles = [
            "審核供應商報價單", "撰寫月度銷售報告", "準備產品發布會簡報",
            "聯繫物流公司確認配送時間", "更新產品庫存", "回覆客戶郵件",
            "處理退貨申請", "更新網站產品資訊", "與設計團隊開會討論新品包裝",
            "整理客戶反饋意見"
        ]
        
        for i in range(1, len(todo_titles) + 1):
            status = random.choice(["pending", "in_progress", "completed"])
            due_date = None
            completed_at = None
            
            if random.choice([True, False]):
                days_ahead = random.randint(-5, 14)  # 允許部分已過期
                due_date = now + timedelta(days=days_ahead)
                
            if status == "completed":
                completed_at = now - timedelta(days=random.randint(0, 5))
                
            cls._todos.append(MockTodoItem(
                id=i,
                title=todo_titles[i - 1],
                description=f"這是一個關於'{todo_titles[i - 1]}'的待辦事項詳細說明。" if random.choice([True, False]) else None,
                status=status,
                priority=random.randint(0, 3),
                due_date=due_date,
                created_at=now - timedelta(days=random.randint(0, 30)),
                completed_at=completed_at
            ))
    
    @classmethod
    def get_notifications(cls, limit=None):
        """取得通知清單"""
        if not cls._notifications:
            cls.initialize_mock_data()
        
        # 按時間排序，未讀通知優先
        sorted_notifications = sorted(
            cls._notifications, 
            key=lambda x: (not x.is_read, x.created_at), 
            reverse=True
        )
        
        return sorted_notifications[:limit] if limit else sorted_notifications
    
    @classmethod
    def get_todos(cls, status=None):
        """獲取待辦事項列表"""
        if not cls._todos:
            cls.initialize_mock_data()
            
        if status:
            return [todo for todo in cls._todos if todo.status == status]
        return cls._todos
    
    @classmethod
    def get_notification_by_id(cls, notification_id):
        """根據ID獲取通知"""
        for notification in cls._notifications:
            if notification.id == notification_id:
                return notification
        return None
    
    @classmethod
    def get_todo_by_id(cls, todo_id):
        """根據ID獲取待辦事項"""
        for todo in cls._todos:
            if todo.id == todo_id:
                return todo
        return None
    
    @classmethod
    def mark_notification_read(cls, notification_id):
        """將特定通知標記為已讀"""
        notification = cls.get_notification_by_id(notification_id)
        if notification:
            notification.is_read = True
            return True
        return False
    
    @classmethod
    def mark_all_notifications_read(cls):
        """將所有通知標記為已讀"""
        for notification in cls._notifications:
            notification.is_read = True
        return True
    
    @classmethod
    def delete_notification(cls, notification_id):
        """刪除通知"""
        notification = cls.get_notification_by_id(notification_id)
        if notification:
            cls._notifications.remove(notification)
            return True
        return False
    
    @classmethod
    def update_todo_status(cls, todo_id, status):
        """更新待辦事項狀態"""
        todo = cls.get_todo_by_id(todo_id)
        if todo:
            todo.status = status
            if status == "completed":
                todo.completed_at = timezone.now()
            return True
        return False
    
    @classmethod
    def delete_todo(cls, todo_id):
        """刪除待辦事項"""
        todo = cls.get_todo_by_id(todo_id)
        if todo:
            cls._todos.remove(todo)
            return True
        return False
    
    @classmethod
    def add_todo(cls, title, description=None, priority=0, due_date=None):
        """添加待辦事項"""
        new_id = max([todo.id for todo in cls._todos], default=0) + 1
        new_todo = MockTodoItem(
            id=new_id,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date
        )
        cls._todos.append(new_todo)
        return new_todo
    
    @classmethod
    def get_unread_count(cls):
        """取得未讀通知數量"""
        if not cls._notifications:
            cls.initialize_mock_data()
        
        return len([n for n in cls._notifications if not n.is_read])
from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from core.models import User
import logging
from django.db import models

logger = logging.getLogger(__name__)

class NotificationService:
    """通知服務類"""
    
    @classmethod
    def create_notification(cls, recipient, title, message, notification_type='system', 
                        priority='normal', related_object=None, metadata=None, expires_at=None):
        """建立通知"""
        try:
            from core.models import Notification  # 加入這行
            
            with transaction.atomic():
                notification_data = {
                    'recipient': recipient,
                    'title': title,
                    'message': message,
                    'notification_type': notification_type,
                    'priority': priority,
                    'metadata': metadata or {},
                }
                
                if expires_at:
                    notification_data['expires_at'] = expires_at
                
                if related_object:
                    notification_data['content_object'] = related_object
                
                notification = Notification.objects.create(**notification_data)
                logger.info(f"建立通知成功：{notification.id}")
                return notification
                
        except Exception as e:
            logger.error(f"建立通知失敗：{str(e)}")
            return None
    
    @classmethod
    def get_user_notifications(cls, user, limit=20, unread_only=False):
        """獲取用戶通知"""
        from core.models import Notification  # 加入導入
        
        queryset = Notification.objects.filter(recipient=user)
        
        if unread_only:
            queryset = queryset.filter(is_read=False)
        
        # 排除過期通知
        queryset = queryset.filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
        )
        
        return queryset[:limit]
    
    @classmethod
    def get_unread_count(cls, user):
        """獲取未讀通知數量"""
        from core.models import Notification  # 加入這行
        
        return Notification.objects.filter(
            recipient=user,
            is_read=False
        ).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
        ).count()
    
    @classmethod
    def mark_as_read(cls, notification_id, user=None):
        """標記通知為已讀"""
        try:
            from core.models import Notification  # 加入這行
            
            filters = {'id': notification_id}
            if user:
                filters['recipient'] = user
            
            notification = Notification.objects.get(**filters)
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
    
    @classmethod
    def mark_all_as_read(cls, user):
        """標記所有通知為已讀"""
        try:
            from core.models import Notification  # 加入這行
            
            Notification.objects.filter(
                recipient=user,
                is_read=False
            ).update(
                is_read=True,
                read_at=timezone.now()
            )
            return True
        except Exception as e:
            logger.error(f"標記所有通知已讀失敗：{str(e)}")
            return False
    
    @classmethod
    def delete_notification(cls, notification_id, user=None):
        """刪除通知"""
        try:
            from core.models import Notification  # 加入這行
            
            filters = {'id': notification_id}
            if user:
                filters['recipient'] = user
            
            notification = Notification.objects.get(**filters)
            notification.delete()
            return True
        except Notification.DoesNotExist:
            return False
    
    # 便捷方法
    @classmethod
    def notify_enterprise_approval(cls, user, approved=True):
        """企業審核通知"""
        from core.models import Notification
        if approved:
            title = "企業審核通過"
            message = f"恭喜！您的企業註冊申請已通過審核，現在可以開始使用系統功能。"
        else:
            title = "企業審核未通過"
            message = f"很抱歉，您的企業註冊申請未通過審核，請聯繫客服了解詳情。"
        
        return cls.create_notification(
            recipient=user,
            title=title,
            message=message,
            notification_type='enterprise_approval',
            priority='high'
        )
    
    @classmethod
    def notify_point_transaction(cls, user, transaction_type, amount, balance):
        """點數交易通知"""
        from core.models import Notification
        if transaction_type == 'purchase':
            title = "點數購買成功"
            message = f"您已成功購買 {amount} 點數，目前餘額：{balance} 點"
        elif transaction_type == 'consumption':
            title = "點數消費"
            message = f"消費 {abs(amount)} 點數，目前餘額：{balance} 點"
        else:
            title = "點數變動"
            message = f"點數變動 {amount:+d} 點，目前餘額：{balance} 點"
        
        return cls.create_notification(
            recipient=user,
            title=title,
            message=message,
            notification_type='point_transaction',
            priority='normal'
        )
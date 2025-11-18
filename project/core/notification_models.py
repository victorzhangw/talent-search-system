from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from .models import User

class Notification(models.Model):
    """系統通知模型"""
    NOTIFICATION_TYPES = [
        ('system', '系統通知'),
        ('enterprise_approval', '企業審核'),
        ('point_transaction', '點數交易'),
        ('test_invitation', '測驗邀請'),
        ('test_result', '測驗結果'),
        ('account', '帳號相關'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', '低'),
        ('normal', '普通'),
        ('high', '高'),
        ('urgent', '緊急'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name='接收者')
    title = models.CharField(max_length=200, verbose_name='標題')
    message = models.TextField(verbose_name='訊息內容')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='system', verbose_name='通知類型')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal', verbose_name='優先級')
    
    # 關聯對象（可選）
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # 狀態
    is_read = models.BooleanField(default=False, verbose_name='已讀')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='閱讀時間')
    
    # 時間
    created_at = models.DateTimeField(default=timezone.now, verbose_name='建立時間')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='過期時間')
    
    # 額外數據
    metadata = models.JSONField(default=dict, blank=True, verbose_name='額外資料')
    
    class Meta:
        verbose_name = '通知'
        verbose_name_plural = '通知'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.recipient.username} - {self.title}"
    
    def mark_as_read(self):
        """標記為已讀"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    @property
    def time_since(self):
        """距離現在的時間"""
        from django.utils.timesince import timesince
        return timesince(self.created_at)
    
    @property
    def icon(self):
        """根據類型返回圖標"""
        icon_map = {
            'system': 'bi-gear',
            'enterprise_approval': 'bi-building-check',
            'point_transaction': 'bi-coin',
            'test_invitation': 'bi-envelope',
            'test_result': 'bi-clipboard-data',
            'account': 'bi-person',
        }
        return icon_map.get(self.notification_type, 'bi-bell')
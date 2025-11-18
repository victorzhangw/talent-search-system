# core/invitation_template_models.py

from django.db import models
from django.utils import timezone
from .models import User

class InvitationTemplate(models.Model):
    """邀請訊息模板"""
    TEMPLATE_TYPE_CHOICES = [
        ('default', '預設模板'),
        ('formal', '正式模板'),
        ('casual', '輕鬆模板'),
        ('urgent', '緊急模板'),
        ('custom', '自定義模板'),
    ]
    
    enterprise = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='invitation_templates',
        limit_choices_to={'user_type': 'enterprise'},
        verbose_name='企業用戶'
    )
    
    name = models.CharField(max_length=100, verbose_name='模板名稱')
    template_type = models.CharField(
        max_length=20, 
        choices=TEMPLATE_TYPE_CHOICES, 
        default='custom',
        verbose_name='模板類型'
    )
    
    # 郵件內容
    subject_template = models.CharField(
        max_length=200, 
        verbose_name='郵件主旨模板',
        help_text='可使用變數：{invitee_name}, {company_name}, {test_name}, {enterprise_name}'
    )
    
    message_template = models.TextField(
        verbose_name='郵件內容模板',
        help_text='可使用變數：{invitee_name}, {company_name}, {test_name}, {enterprise_name}, {test_url}, {expires_date}'
    )
    
    # 狀態
    is_default = models.BooleanField(default=False, verbose_name='是否為預設模板')
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    
    # 使用統計
    usage_count = models.IntegerField(default=0, verbose_name='使用次數')
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name='最後使用時間')
    
    # 系統欄位
    created_at = models.DateTimeField(default=timezone.now, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = '邀請訊息模板'
        verbose_name_plural = '邀請訊息模板'
        db_table = 'invitation_template'
        unique_together = ['enterprise', 'name']
        ordering = ['-is_default', '-last_used_at', '-created_at']
    
    def __str__(self):
        return f"{self.enterprise.username} - {self.name}"
    
    def render_subject(self, context):
        """渲染郵件主旨"""
        return self.subject_template.format(**context)
    
    def render_message(self, context):
        """渲染郵件內容"""
        return self.message_template.format(**context)
    
    def mark_as_used(self):
        """標記為已使用"""
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])
    
    def set_as_default(self):
        """設為預設模板"""
        # 先取消其他預設模板
        InvitationTemplate.objects.filter(
            enterprise=self.enterprise,
            is_default=True
        ).update(is_default=False)
        
        # 設置當前模板為預設
        self.is_default = True
        self.save(update_fields=['is_default'])
    
    @classmethod
    def get_default_template(cls, enterprise):
        """取得企業的預設模板"""
        return cls.objects.filter(
            enterprise=enterprise,
            is_default=True,
            is_active=True
        ).first()
    
    @classmethod
    def create_default_templates(cls, enterprise):
        """為企業建立預設模板"""
        templates = [
            {
                'name': '標準邀請模板',
                'template_type': 'default',
                'subject_template': '【{enterprise_name}】測驗邀請 - {test_name}',
                'message_template': '''親愛的 {invitee_name} 您好：

{enterprise_name} 邀請您參與 {test_name} 測驗。

此測驗將協助我們更了解您的特質與能力，請於 {expires_date} 前完成測驗。

測驗連結：{test_url}

如有任何問題，請隨時與我們聯絡。

祝您順心
{enterprise_name} 敬上''',
                'is_default': True,
            },
            {
                'name': '正式商業模板',
                'template_type': 'formal',
                'subject_template': '{enterprise_name} - {test_name} 人才評估邀請',
                'message_template': '''尊敬的 {invitee_name}：

感謝您對 {enterprise_name} 的關注。

為了更好地了解您的專業能力與個人特質，我們誠摯邀請您參與 {test_name} 評估。

評估資訊：
• 測驗名稱：{test_name}
• 截止時間：{expires_date}
• 評估連結：{test_url}

此評估結果將作為我們人才選拔的重要參考依據，請您務必在截止時間前完成。

如有疑問，歡迎隨時聯繫我們。

此致
敬禮

{enterprise_name}
人力資源部''',
                'is_default': False,
            },
            {
                'name': '友善輕鬆模板',
                'template_type': 'casual',
                'subject_template': '來完成一個有趣的測驗吧！- {test_name}',
                'message_template': '''Hi {invitee_name}！

{enterprise_name} 這邊有個有趣的測驗想邀請你參與 😊

測驗名稱：{test_name}
花費時間：大約10-15分鐘
完成期限：{expires_date}

點這裡開始：{test_url}

這個測驗會幫助我們更了解你的特質和優勢，別擔心，沒有標準答案，誠實回答就好！

有任何問題都可以聯絡我們哦～

{enterprise_name} 團隊''',
                'is_default': False,
            }
        ]
        
        created_templates = []
        for template_data in templates:
            template, created = cls.objects.get_or_create(
                enterprise=enterprise,
                name=template_data['name'],
                defaults=template_data
            )
            if created:
                created_templates.append(template)
        
        return created_templates
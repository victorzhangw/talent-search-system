from django.contrib.auth.models import AbstractUser, UserManager as BaseUserManager
from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import uuid

# ==================== 用戶系統 ====================

class UserManager(BaseUserManager):
    """自定義用戶管理器"""
    
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """建立超級用戶時自動設定為 admin 類型"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'admin')
        extra_fields.setdefault('is_email_verified', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    """擴展用戶模型"""
    USER_TYPE_CHOICES = [
        ('individual', '個人用戶'),
        ('enterprise', '企業用戶'),
        ('admin', '管理員'),
    ]

    email = models.EmailField('電子郵件', unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='individual')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='電話')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='頭像')
    is_email_verified = models.BooleanField(default=False, verbose_name='Email已驗證')
    email_verification_token = models.UUIDField(
        default=uuid.uuid4, 
        verbose_name='Email驗證令牌',
        db_index=True
    )
    password_reset_token = models.UUIDField(
        default=uuid.uuid4, 
        verbose_name='密碼重設令牌',
        db_index=True
    )
    password_reset_token_created = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name='密碼重設令牌建立時間'
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    # 使用自定義的 UserManager
    objects = UserManager()
    
    # 解決 related_name 衝突
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )

class IndividualProfile(models.Model):
    """個人用戶資料"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='individual_profile')
    real_name = models.CharField(max_length=50, verbose_name='真實姓名')
    id_number = models.CharField(max_length=20, blank=True, null=True, verbose_name='身分證字號')
    birth_date = models.DateField(blank=True, null=True, verbose_name='生日')
    
    # 測驗平台登入資訊
    test_platform_username = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name='測驗平台帳號',
        help_text='用於自動登入測驗平台的帳號'
    )
    test_platform_password = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name='測驗平台密碼',
        help_text='用於自動登入測驗平台的密碼'
    )
    
    class Meta:
        verbose_name = '個人資料'
        verbose_name_plural = '個人資料'
        db_table = 'individual_profile'

class EnterpriseProfile(models.Model):
    """企業用戶資料"""
    VERIFICATION_STATUS_CHOICES = [
        ('pending', '待審核'),
        ('approved', '已核准'),
        ('rejected', '已拒絕'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='enterprise_profile')
    company_name = models.CharField(max_length=100, verbose_name='公司名稱')
    tax_id = models.CharField(
        max_length=8, 
        verbose_name='統一編號',
        db_index=True
    )
    contact_person = models.CharField(max_length=50, verbose_name='聯絡人姓名')
    contact_phone = models.CharField(max_length=20, verbose_name='聯絡電話')
    address = models.TextField(blank=True, null=True, verbose_name='公司地址')
    verification_status = models.CharField(
        max_length=20, 
        choices=VERIFICATION_STATUS_CHOICES, 
        default='pending',
        verbose_name='驗證狀態'
    )
    verified_at = models.DateTimeField(blank=True, null=True, verbose_name='驗證時間')
    
    class Meta:
        verbose_name = '企業資料'
        verbose_name_plural = '企業資料'
        db_table = 'enterprise_profile'
        constraints = [
            models.UniqueConstraint(fields=['user', 'tax_id'], name='unique_enterprise_user_tax_id')
        ]

# ==================== 點數系統 ====================

class UserPointBalance(models.Model):
    """用戶點數餘額"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='point_balance')
    balance = models.IntegerField(default=0, verbose_name='點數餘額')
    total_earned = models.IntegerField(default=0, verbose_name='累計獲得點數')
    total_consumed = models.IntegerField(default=0, verbose_name='累計消費點數')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = '用戶點數餘額'
        verbose_name_plural = '用戶點數餘額'
        db_table = 'user_point_balance'
    
    def __str__(self):
        return f"{self.user.username} - {self.balance} 點"

class PointTransaction(models.Model):
    """點數交易記錄"""
    TRANSACTION_TYPES = [
        ('purchase', '購買'),
        ('consumption', '消費'),
        ('refund', '退款'),
        ('admin_adjust', '管理員調整'),
        ('gift', '贈送'),
        ('registration_bonus', '註冊獎勵'),
        ('enterprise_bonus', '企業獎勵'),
    ]
    
    TRANSACTION_STATUS = [
        ('pending', '處理中'),
        ('completed', '已完成'),
        ('failed', '失敗'),
        ('cancelled', '已取消'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_transactions', verbose_name='用戶')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, verbose_name='交易類型')
    amount = models.IntegerField(verbose_name='點數數量')
    balance_before = models.IntegerField(verbose_name='交易前餘額')
    balance_after = models.IntegerField(verbose_name='交易後餘額')
    description = models.TextField(verbose_name='交易描述')
    reference_id = models.CharField(max_length=100, blank=True, verbose_name='關聯ID')
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='completed', verbose_name='狀態')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='額外資訊')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='交易時間')
    
    class Meta:
        verbose_name = '點數交易記錄'
        verbose_name_plural = '點數交易記錄'
        db_table = 'point_transaction'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'transaction_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['reference_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_transaction_type_display()} - {self.amount}"

class PointPackage(models.Model):
    """點數套餐"""
    name = models.CharField(max_length=100, verbose_name='套餐名稱')
    description = models.TextField(blank=True, verbose_name='套餐描述')
    points = models.IntegerField(verbose_name='點數數量')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='價格')
    bonus_points = models.IntegerField(default=0, verbose_name='贈送點數')
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = '點數套餐'
        verbose_name_plural = '點數套餐'
        db_table = 'point_package'
        ordering = ['sort_order', 'price']
    
    def __str__(self):
        return f"{self.name} - {self.points} 點 (${self.price})"
    
    @property
    def total_points(self):
        """總點數（包含贈送）"""
        return self.points + self.bonus_points

class PointOrder(models.Model):
    """點數購買訂單"""
    ORDER_STATUS = [
        ('pending', '待付款'),
        ('paid', '已付款'),
        ('completed', '已完成'),
        ('failed', '失敗'),
        ('cancelled', '已取消'),
        ('refunded', '已退款'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True, verbose_name='訂單號')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_orders', verbose_name='用戶')
    package = models.ForeignKey(PointPackage, on_delete=models.PROTECT, verbose_name='點數套餐')
    points = models.IntegerField(verbose_name='購買點數')
    bonus_points = models.IntegerField(default=0, verbose_name='贈送點數')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='訂單金額')
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending', verbose_name='訂單狀態')
    payment_method = models.CharField(max_length=50, blank=True, verbose_name='付款方式')
    payment_reference = models.CharField(max_length=100, blank=True, verbose_name='付款參考號')
    notes = models.TextField(blank=True, verbose_name='備註')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='付款時間')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成時間')
    
    class Meta:
        verbose_name = '點數購買訂單'
        verbose_name_plural = '點數購買訂單'
        db_table = 'point_order'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"訂單 {self.order_number} - {self.user.username}"
    
    @property
    def total_points(self):
        """總點數（包含贈送）"""
        return self.points + self.bonus_points
    
    def generate_order_number(self):
        """生成訂單號"""
        from django.utils import timezone
        import random
        import string
        
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"PO{date_str}{random_str}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

# ==================== 通知系統 ====================

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
        db_table = 'notification'
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

    @property
    def link(self):
        """通知導向連結"""
        return self.metadata.get('link') if isinstance(self.metadata, dict) else None

# ==================== 測驗項目管理系統（新版） ====================

class TestProject(models.Model):
    """測驗項目主表"""
    name = models.CharField(max_length=200, verbose_name='測驗名稱')
    description = models.TextField(blank=True, verbose_name='測驗描述')
    name_abbreviation = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='測驗名稱縮寫',
        help_text='僅供下載檔名使用'
    )
    
    # 新增標題欄位
    title_name = models.CharField(max_length=200, blank=True, verbose_name='標題名稱')
    title_name_english = models.CharField(max_length=200, blank=True, verbose_name='標題名稱英文')
    
    # 新增詳細資訊欄位
    introduction = models.TextField(blank=True, verbose_name='簡介')
    usage_guide = models.TextField(blank=True, verbose_name='使用方式')
    precautions = models.TextField(blank=True, verbose_name='注意事項')
    
    # 測驗連結
    test_link = models.URLField(verbose_name='測驗連結', help_text='外部測驗網站的連結')
    
    # 新增：頁首資訊
    header_logo = models.ImageField(upload_to='test_project_logos/', blank=True, null=True, verbose_name='頁首Logo')
    header_text_content = models.TextField(blank=True, verbose_name='頁首文字內容')
    
    # 新增：頁尾資訊
    footer_text_content = models.TextField(blank=True, verbose_name='頁尾文字內容')
    
    # 新增：個人分享共同資訊
    personal_share_title = models.CharField(max_length=200, blank=True, verbose_name='個人分享標題名稱')
    personal_share_footer_content = models.TextField(blank=True, verbose_name='個人分享頁尾內容')
    
    # 評分對應欄位
    score_field_chinese = models.CharField(max_length=100, verbose_name='評分欄位中文名稱')
    score_field_system = models.CharField(max_length=100, verbose_name='評分欄位系統名稱')
    
    # 預測對應欄位
    prediction_field_chinese = models.CharField(max_length=100, verbose_name='預測欄位中文名稱')
    prediction_field_system = models.CharField(max_length=100, verbose_name='預測欄位系統名稱')
    
    # 測驗名稱對應的job role欄位
    job_role_system_name = models.CharField(
        max_length=100, 
        verbose_name='Job Role系統對應名稱',
        help_text='爬蟲時用於篩選Job Role相關資訊的欄位名稱',
        blank=False,  # 允許為空，以免影響現有數據
        default=''
    )
    # 指派規則（修改為四種選項）
    ASSIGNMENT_TYPE_CHOICES = [
        ('all_open', '全部開放'),
        ('enterprise_only', '僅開放給企業'),
        ('individual_only', '僅開放給個人'),
        ('specific_assignment', '指定開放'),
    ]
    assignment_type = models.CharField(
        max_length=20, 
        choices=ASSIGNMENT_TYPE_CHOICES, 
        default='specific_assignment',
        verbose_name='指派類型'
    )

    RADAR_MODE_CHOICES = [
        ('role', 'Role-based'),
        ('score', 'Score-based'),
    ]
    radar_mode = models.CharField(
        max_length=10,
        choices=RADAR_MODE_CHOICES,
        default='role',
        verbose_name='雷達圖模式'
    )
    show_mixed_role = models.BooleanField(
        default=True,
        verbose_name='顯示混合型角色'
    )
    traits = models.ManyToManyField(
        'Trait',
        through='TestProjectTrait',
        related_name='test_projects',
        blank=True,
        verbose_name='測驗特質'
    )
    
    # 系統欄位
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='建立者')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = '測驗項目'
        verbose_name_plural = '測驗項目'
        ordering = ['-created_at']  # 按建立時間倒序排列
        db_table = 'test_project'
    
    def __str__(self):
        return self.name
    
    def get_available_for_user(self, user):
        """檢查此測驗項目是否對指定用戶開放"""
        if self.assignment_type == 'all_open':
            return True
        elif self.assignment_type == 'enterprise_only' and user.user_type == 'enterprise':
            return True
        elif self.assignment_type == 'individual_only' and user.user_type == 'individual':
            return True
        elif self.assignment_type == 'specific_assignment':
            # 檢查是否有具體指派
            if user.user_type == 'enterprise':
                return self.enterprise_assignments.filter(
                    enterprise_user=user, 
                    is_active=True
                ).exists()
            elif user.user_type == 'individual':
                return self.individual_assignments.filter(
                    individual_user=user, 
                    is_active=True
                ).exists()
        return False
    
    @classmethod
    def get_available_projects_for_user(cls, user):
        """獲取用戶可用的測驗項目"""
        from django.db.models import Q
        
        # 構建查詢條件
        conditions = Q(assignment_type='all_open')
        
        # 按用戶類型開放的項目
        if user.user_type == 'enterprise':
            conditions |= Q(assignment_type='enterprise_only')
        elif user.user_type == 'individual':
            conditions |= Q(assignment_type='individual_only')
        
        # 特定指派的項目
        if user.user_type == 'enterprise':
            conditions |= Q(
                assignment_type='specific_assignment',
                enterprise_assignments__enterprise_user=user,
                enterprise_assignments__is_active=True
            )
        elif user.user_type == 'individual':
            conditions |= Q(
                assignment_type='specific_assignment',
                individual_assignments__individual_user=user,
                individual_assignments__is_active=True
            )
        
        return cls.objects.filter(conditions).distinct().order_by('-created_at')

class TestProjectCategory(models.Model):
    """測驗項目分類表"""
    test_project = models.ForeignKey(TestProject, on_delete=models.CASCADE, 
                                   related_name='categories', verbose_name='測驗項目')
    name = models.CharField(max_length=200, verbose_name='分類完整名稱')
    english_name = models.CharField(max_length=200, blank=True, verbose_name='英文名稱')
    description = models.TextField(blank=True, verbose_name='說明')
    test_link = models.URLField(verbose_name='測驗連結')
    advantage_analysis = models.TextField(verbose_name='優勢分析說明')
    disadvantage_analysis = models.TextField(verbose_name='劣勢分析說明')
    
    # 發展建議參數設定
    development_parameter_name = models.CharField(max_length=200, blank=True, verbose_name='發展建議參數名稱')
    development_parameter_content = models.TextField(blank=True, verbose_name='發展建議參數內容')
    
    # 新增：角色相關欄位
    role_name = models.CharField(max_length=200, blank=True, verbose_name='角色名稱')
    tag_text = models.CharField(max_length=500, blank=True, verbose_name='Tag文字')
    role_image = models.ImageField(upload_to='role_images/', blank=True, null=True, verbose_name='角色圖')
    content = models.TextField(blank=True, verbose_name='內容')
    advantage_suggestions = models.TextField(blank=True, verbose_name='優勢建議')
    development_direction = models.TextField(blank=True, verbose_name='發展方向')
    score_type_name = models.CharField(max_length=100, blank=True, verbose_name='分數類型名稱')
    traits = models.ManyToManyField(
        'Trait',
        through='TestProjectCategoryTrait',
        related_name='categories',
        blank=True,
        verbose_name='特質'
    )
    
    # 排序
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    
    # 系統欄位
    created_at = models.DateTimeField(default=timezone.now, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = '測驗項目分類'
        verbose_name_plural = '測驗項目分類'
        db_table = 'test_project_category'
        ordering = ['sort_order', 'id']
    
    def __str__(self):
        return f"{self.test_project.name} - {self.name}"

class Trait(models.Model):
    """全域特質定義"""
    chinese_name = models.CharField(max_length=100, verbose_name='中文特質名稱')
    system_name = models.CharField(max_length=100, unique=True, verbose_name='系統對應名稱')
    description = models.TextField(blank=True, verbose_name='特質描述')

    created_at = models.DateTimeField(default=timezone.now, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        verbose_name = '特質'
        verbose_name_plural = '特質'
        db_table = 'trait'
        ordering = ['system_name']

    def __str__(self):
        return f"{self.chinese_name} ({self.system_name})"


class TestProjectTrait(models.Model):
    """測驗項目對應特質設定"""
    test_project = models.ForeignKey(
        TestProject,
        on_delete=models.CASCADE,
        related_name='project_trait_relations',
        verbose_name='測驗項目'
    )
    trait = models.ForeignKey(
        Trait,
        on_delete=models.PROTECT,
        related_name='test_project_trait_relations',
        verbose_name='特質'
    )
    custom_description = models.TextField(blank=True, verbose_name='特質自訂描述')
    use_custom_description = models.BooleanField(default=False, verbose_name='是否使用自訂描述')
    sort_order = models.IntegerField(default=0, verbose_name='排序')

    created_at = models.DateTimeField(default=timezone.now, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        verbose_name = '測驗項目特質'
        verbose_name_plural = '測驗項目特質'
        db_table = 'test_project_trait'
        unique_together = ['test_project', 'trait']
        ordering = ['test_project', 'sort_order', 'id']

    def __str__(self):
        return f"{self.test_project.name} - {self.trait.chinese_name}"


class TestProjectCategoryTrait(models.Model):
    """分類與特質對應"""
    category = models.ForeignKey(
        TestProjectCategory,
        on_delete=models.CASCADE,
        related_name='category_traits',
        verbose_name='測驗分類'
    )
    trait = models.ForeignKey(
        Trait,
        on_delete=models.PROTECT,
        related_name='category_traits',
        verbose_name='特質'
    )
    weight = models.DecimalField(max_digits=6, decimal_places=2, default=1.00, verbose_name='權重')
    sort_order = models.IntegerField(default=0, verbose_name='排序')

    created_at = models.DateTimeField(default=timezone.now, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        verbose_name = '分類特質'
        verbose_name_plural = '分類特質'
        db_table = 'test_project_category_trait'
        unique_together = ['category', 'trait']
        ordering = ['category', 'sort_order', 'id']

    def __str__(self):
        return f"{self.category.name} - {self.trait.chinese_name}"

class TestProjectAssignment(models.Model):
    """測驗項目指派表（指派給企業）"""
    test_project = models.ForeignKey(TestProject, on_delete=models.CASCADE, 
                                   related_name='enterprise_assignments', verbose_name='測驗項目')
    enterprise_user = models.ForeignKey(User, on_delete=models.CASCADE, 
                                      limit_choices_to={'user_type': 'enterprise'},
                                      verbose_name='企業用戶')
    
    assigned_quota = models.PositiveIntegerField(default=0, verbose_name='可用份數', help_text='0 表示不限')
    used_quota = models.PositiveIntegerField(default=0, verbose_name='已使用份數')

    # 指派狀態
    is_active = models.BooleanField(default=True, verbose_name='是否有效')
    
    # 系統欄位
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, 
                                  related_name='assigned_test_projects', verbose_name='指派者')
    assigned_at = models.DateTimeField(default=timezone.now, verbose_name='指派時間')
    
    class Meta:
        verbose_name = '測驗項目企業指派'
        verbose_name_plural = '測驗項目企業指派'
        unique_together = ['test_project', 'enterprise_user']
        db_table = 'test_project_assignment'
    
    def __str__(self):
        return f"{self.test_project.name} -> {self.enterprise_user.username}"

    @property
    def is_unlimited(self):
        return self.assigned_quota == 0

    @property
    def remaining_quota(self):
        if self.is_unlimited:
            return None
        return max(self.assigned_quota - self.used_quota, 0)

    def has_available_quota(self, required=1):
        if self.is_unlimited:
            return True
        return self.used_quota + required <= self.assigned_quota

    def consume_quota(self, amount=1, save=True):
        if amount <= 0:
            return
        if self.is_unlimited:
            self.used_quota += amount
        else:
            self.used_quota = min(self.assigned_quota, self.used_quota + amount)
        if save:
            self.save(update_fields=['used_quota'])

    def release_quota(self, amount=1, save=True):
        if amount <= 0:
            return
        if self.used_quota == 0:
            return
        if self.is_unlimited:
            self.used_quota = max(0, self.used_quota - amount)
        else:
            self.used_quota = max(0, self.used_quota - amount)
        if save:
            self.save(update_fields=['used_quota'])

class EnterprisePurchaseRecord(models.Model):
    """企業測驗購買紀錄"""
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', '信用卡'),
        ('atm', 'ATM'),
    ]

    enterprise_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='purchase_records',
        limit_choices_to={'user_type': 'enterprise'},
        verbose_name='企業用戶'
    )
    test_project = models.ForeignKey(
        TestProject,
        on_delete=models.CASCADE,
        related_name='purchase_records',
        verbose_name='測驗項目'
    )
    assignment = models.ForeignKey(
        'TestProjectAssignment',
        on_delete=models.CASCADE,
        related_name='purchase_records',
        verbose_name='企業指派',
        null=True,
        blank=True
    )
    order_number = models.CharField(max_length=50, unique=True, verbose_name='訂單編號')
    quantity = models.PositiveIntegerField(verbose_name='購買份數')
    payment_date = models.DateTimeField(verbose_name='付款日期')
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        verbose_name='付款方式'
    )
    payment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='付款金額'
    )
    invoice_number = models.CharField(max_length=50, blank=True, verbose_name='發票號碼')
    invoice_random_code = models.CharField(max_length=10, blank=True, verbose_name='發票隨機碼')
    invoice_info = models.TextField(blank=True, verbose_name='發票資訊')
    coupon_code = models.CharField(max_length=50, blank=True, verbose_name='優惠券')
    notes = models.TextField(blank=True, verbose_name='備註')

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='created_purchase_records',
        null=True,
        verbose_name='建立者'
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        verbose_name = '企業購買紀錄'
        verbose_name_plural = '企業購買紀錄'
        db_table = 'enterprise_purchase_record'
        ordering = ['-payment_date', '-id']

    def __str__(self):
        company = getattr(self.enterprise_user.enterprise_profile, 'company_name', self.enterprise_user.username)
        return f"{company} - {self.test_project.name} - {self.order_number}"


class EnterpriseQuotaUsageLog(models.Model):
    """企業測驗份數使用紀錄"""
    ACTION_CHOICES = [
        ('consume', '測驗'),
        ('release', '取消'),
    ]

    assignment = models.ForeignKey(
        TestProjectAssignment,
        on_delete=models.CASCADE,
        related_name='quota_logs',
        verbose_name='企業指派'
    )
    enterprise_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='quota_usage_logs',
        limit_choices_to={'user_type': 'enterprise'},
        verbose_name='企業用戶'
    )
    test_project = models.ForeignKey(
        TestProject,
        on_delete=models.CASCADE,
        related_name='quota_usage_logs',
        verbose_name='測驗項目'
    )
    invitation = models.ForeignKey(
        'TestInvitation',
        on_delete=models.SET_NULL,
        related_name='quota_logs',
        null=True,
        blank=True,
        verbose_name='邀請紀錄'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='操作')
    quantity = models.PositiveIntegerField(default=1, verbose_name='異動份數')
    invitee_name = models.CharField(max_length=100, blank=True, verbose_name='受測者姓名')
    invitee_email = models.CharField(max_length=255, blank=True, verbose_name='受測者 Email')
    action_time = models.DateTimeField(default=timezone.now, verbose_name='操作時間')
    remaining_quota = models.IntegerField(blank=True, null=True, verbose_name='剩餘份數')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='recorded_quota_logs',
        null=True,
        blank=True,
        verbose_name='紀錄建立者'
    )

    class Meta:
        verbose_name = '企業份數使用紀錄'
        verbose_name_plural = '企業份數使用紀錄'
        db_table = 'enterprise_quota_usage_log'
        ordering = ['-action_time', '-id']

    def __str__(self):
        return f"{self.get_action_display()} - {self.invitee_name or '未知受測者'}"


class TestProjectIndividualAssignment(models.Model):
    """測驗項目指派表（指派給個人用戶）"""
    test_project = models.ForeignKey(TestProject, on_delete=models.CASCADE, 
                                   related_name='individual_assignments', verbose_name='測驗項目')  # 修改這行
    individual_user = models.ForeignKey(User, on_delete=models.CASCADE, 
                                      limit_choices_to={'user_type': 'individual'},
                                      verbose_name='個人用戶')
    
    # 指派狀態
    is_active = models.BooleanField(default=True, verbose_name='是否有效')
    
    # 系統欄位
    assigned_by = models.ForeignKey(User, on_delete=models.CASCADE, 
                                  related_name='assigned_individual_projects', verbose_name='指派者')
    assigned_at = models.DateTimeField(default=timezone.now, verbose_name='指派時間')
    
    class Meta:
        verbose_name = '測驗項目個人指派'
        verbose_name_plural = '測驗項目個人指派'
        unique_together = ['test_project', 'individual_user']
        db_table = 'test_project_individual_assignment'
    
    def __str__(self):
        return f"{self.test_project.name} -> {self.individual_user.username}"

# ==================== 舊版測驗系統（保留兼容） ====================

class TestCategory(models.Model):
    """測驗類別（舊版）"""
    name = models.CharField(max_length=100, verbose_name='類別名稱')
    description = models.TextField(blank=True, verbose_name='類別描述')
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    
    class Meta:
        verbose_name = '測驗類別'
        verbose_name_plural = '測驗類別'
        db_table = 'test_category_old'
    
    def __str__(self):
        return self.name

class TestTemplate(models.Model):
    """測驗範本（舊版系統）"""
    name = models.CharField(max_length=200, verbose_name='測驗名稱')
    category = models.ForeignKey(TestCategory, on_delete=models.CASCADE, verbose_name='測驗類別')
    description = models.TextField(verbose_name='測驗描述')
    duration_minutes = models.IntegerField(verbose_name='測驗時間（分鐘）')
    question_count = models.IntegerField(verbose_name='題目數量')
    point_cost = models.IntegerField(default=1, verbose_name='邀請費用（點數）')
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    
    class Meta:
        verbose_name = '測驗範本'
        verbose_name_plural = '測驗範本'
        db_table = 'test_template'
    
    def __str__(self):
        return self.name

class TestInvitee(models.Model):
    """受測人員"""
    STATUS_CHOICES = [
        ('employed', '在職'),
        ('job_seeker', '求職者'),
    ]
    
    enterprise = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='test_invitees',
        limit_choices_to={'user_type': 'enterprise'},
        verbose_name='邀請企業'
    )
    name = models.CharField(max_length=50, verbose_name='姓名')
    email = models.EmailField(verbose_name='電子郵件')
    phone = models.CharField(max_length=20, blank=True, verbose_name='聯絡電話')
    company = models.CharField(max_length=100, blank=True, verbose_name='所屬公司')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='employed', verbose_name='狀態')
    position = models.CharField(max_length=50, blank=True, verbose_name='職位')
    notes = models.TextField(blank=True, verbose_name='備註')
    
    # 統計資料
    invited_count = models.IntegerField(default=0, verbose_name='受邀次數')
    completed_count = models.IntegerField(default=0, verbose_name='完成次數')
    last_test_date = models.DateTimeField(null=True, blank=True, verbose_name='最後測驗時間')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = '受測人員'
        verbose_name_plural = '受測人員'
        db_table = 'test_invitee'
        unique_together = ['enterprise', 'email']
    
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    @property
    def completion_rate(self):
        """完成率 - 動態計算"""
        if self.invited_count == 0:
            return 0
        
        # 動態計算完成的邀請數量
        completed_invitations = TestInvitation.objects.filter(
            invitee=self,
            status='completed'
        ).count()
        
        return round((completed_invitations / self.invited_count) * 100, 1)
    
    @property
    def latest_test_status(self):
        """最新測驗進度狀態"""
        if self.invited_count == 0:
            return "未受邀"
        
        # 獲取最新的邀請記錄
        latest_invitation = TestInvitation.objects.filter(
            invitee=self
        ).order_by('-invited_at').first()
        
        if not latest_invitation:
            return "未受邀"
        
        status_map = {
            'pending': '待開始',
            'in_progress': '進行中', 
            'completed': '已完成',
            'failed': '失敗'
        }
        
        return status_map.get(latest_invitation.status, '未知狀態')

class TestInvitation(models.Model):
    """測驗邀請"""
    STATUS_CHOICES = [
        ('pending', '待執行'),
        ('in_progress', '進行中'),
        ('completed', '已完成'),
        ('expired', '已過期'),
        ('cancelled', '已取消'),
    ]
    
    enterprise = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_invitations',
        limit_choices_to={'user_type': 'enterprise'},
        verbose_name='邀請企業'
    )
    invitee = models.ForeignKey(TestInvitee, on_delete=models.CASCADE, verbose_name='受測人員')
    test_template = models.ForeignKey(TestTemplate, on_delete=models.CASCADE, 
                                    null=True, blank=True, verbose_name='測驗範本')
    
    # 新增：關聯到測驗項目（新版系統）
    test_project = models.ForeignKey(TestProject, on_delete=models.CASCADE, 
                               null=True, blank=True, verbose_name='測驗項目')
    
    invitation_code = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name='邀請碼')
    custom_message = models.TextField(blank=True, verbose_name='自訂邀請訊息')
    
    # 時間管理
    invited_at = models.DateTimeField(auto_now_add=True, verbose_name='邀請時間')
    expires_at = models.DateTimeField(verbose_name='過期時間')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='開始時間')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成時間')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='狀態')
    
    # 點數相關
    points_consumed = models.IntegerField(verbose_name='消費點數')
    
    # 測驗結果（簡化版）
    score = models.FloatField(null=True, blank=True, verbose_name='測驗分數')
    result_data = models.JSONField(default=dict, blank=True, verbose_name='測驗結果資料')
    
    class Meta:
        verbose_name = '測驗邀請'
        verbose_name_plural = '測驗邀請'
        db_table = 'test_invitation'
        ordering = ['-invited_at']
        indexes = [
            models.Index(fields=['enterprise', 'status']),
            models.Index(fields=['invitee']),
            models.Index(fields=['invitation_code']),
            models.Index(fields=['test_project']),
        ]
    
    def __str__(self):
        if self.test_project:
            return f"{self.test_project.name} - {self.invitee.name}"
        elif self.test_template:
            return f"{self.test_template.name} - {self.invitee.name}"
        else:
            return f"測驗邀請 - {self.invitee.name}"
    
    @property
    def is_completed(self):
        """是否已完成測驗"""
        return self.status == 'completed'
        # and self.completed_at is not None
    
    def is_expired(self):
        """是否已過期"""
        return timezone.now() > self.expires_at and self.status == 'pending'
    
    @property
    def invitation_url(self):
        """邀請連結"""
        from django.urls import reverse
        return reverse('take_test', kwargs={'invitation_code': self.invitation_code})

# ==================== 測驗結果系統 ====================

class TestProjectResult(models.Model):
    """測驗項目結果表（爬蟲後儲存）"""
    test_invitation = models.OneToOneField(
        TestInvitation, 
        on_delete=models.CASCADE,
        related_name='testprojectresult',  # 明確設定 related_name
        verbose_name='測驗邀請'
    )
    test_project = models.ForeignKey(TestProject, on_delete=models.CASCADE, 
                                   verbose_name='測驗項目')
    
    # 測驗結果數據（JSON格式儲存原始數據）
    raw_data = models.JSONField(default=dict, verbose_name='原始測驗數據')
    processed_data = models.JSONField(default=dict, verbose_name='處理後數據')
    
    # 根據測驗項目配置解析的結果
    score_value = models.FloatField(null=True, blank=True, verbose_name='評分值')
    prediction_value = models.TextField(blank=True, verbose_name='預測值')
    category_results = models.JSONField(default=dict, verbose_name='分類結果')
    trait_results = models.JSONField(default=dict, verbose_name='特質結果')
    
    # 爬蟲相關
    crawled_at = models.DateTimeField(null=True, blank=True, verbose_name='爬蟲時間')
    crawl_status = models.CharField(max_length=20, choices=[
        ('pending', '待取得'),
        ('crawling', '取得中'),
        ('completed', '測驗完成'),
        ('failed', '取得失敗'),
    ], default='pending', verbose_name='受測狀態')
    
    # 報告生成
    report_generated = models.BooleanField(default=False, verbose_name='報告已生成')
    report_path = models.CharField(max_length=500, blank=True, verbose_name='報告路徑')
    
    # 系統欄位
    created_at = models.DateTimeField(default=timezone.now, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = '測驗項目結果'
        verbose_name_plural = '測驗項目結果'
        db_table = 'test_project_result'
    
    def __str__(self):
        return f"{self.test_project.name} - {self.test_invitation.invitee.email}"
    

# ==================== 邀請模板系統 ====================

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
        try:
            return self.subject_template.format(**context)
        except KeyError:
            return self.subject_template
    
    def render_message(self, context):
        """渲染郵件內容"""
        try:
            return self.message_template.format(**context)
        except KeyError:
            return self.message_template
    
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

# 爬爬蟲配置模型 
class CrawlerConfig(models.Model):
    """爬蟲配置表（簡化版）"""
    name = models.CharField(max_length=100, verbose_name='配置名稱', default='PI 爬蟲配置')
    base_url = models.URLField(verbose_name='爬蟲基礎網址', default='https://pi.perception-group.com/')
    username = models.CharField(max_length=100, verbose_name='登入帳號', blank=True)
    password = models.CharField(max_length=100, verbose_name='登入密碼', blank=True)
    
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = '爬蟲配置'
        verbose_name_plural = '爬蟲配置'
        db_table = 'crawler_config'
    
    def __str__(self):
        return self.name

# ==================== 個人測驗記錄系統 ====================

class IndividualTestRecord(models.Model):
    """個人測驗記錄 - 追蹤個人用戶購買和參與的測驗"""
    
    STATUS_CHOICES = [
        ('purchased', '已購買'),
        ('in_progress', '進行中'),
        ('completed', '已完成'),
        ('expired', '已過期'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        verbose_name='用戶',
        related_name='individual_test_records'
    )
    test_project = models.ForeignKey(
        TestProject, 
        on_delete=models.CASCADE, 
        verbose_name='測驗項目',
        related_name='individual_records'
    )
    
    # 購買和使用記錄
    purchase_date = models.DateTimeField(auto_now_add=True, verbose_name='購買時間')
    first_access_date = models.DateTimeField(null=True, blank=True, verbose_name='首次進入時間')
    last_access_date = models.DateTimeField(null=True, blank=True, verbose_name='最後進入時間')
    access_count = models.IntegerField(default=0, verbose_name='進入次數')
    
    # 狀態和結果
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='purchased',
        verbose_name='狀態'
    )
    
    # 點數記錄
    points_consumed = models.IntegerField(default=1, verbose_name='消費點數')
    point_transaction = models.ForeignKey(
        PointTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='點數交易記錄'
    )
    
    # 備註和說明
    notes = models.TextField(blank=True, verbose_name='備註')
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = '個人測驗記錄'
        verbose_name_plural = '個人測驗記錄'
        db_table = 'individual_test_record'
        unique_together = ['user', 'test_project']  # 確保每個用戶對每個測驗項目只有一筆記錄
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.test_project.name}'
    
    def mark_accessed(self):
        """標記測驗被進入"""
        from django.utils import timezone
        now = timezone.now()
        
        if not self.first_access_date:
            self.first_access_date = now
            
        self.last_access_date = now
        self.access_count += 1
        
        if self.status == 'purchased':
            self.status = 'in_progress'
            
        self.save()
    
    def is_accessible(self):
        """檢查測驗是否可以進入"""
        # 只有已購買和進行中的測驗可以進入，已完成的不能重新進入
        return self.status in ['purchased', 'in_progress']
    
    @property
    def can_access_test(self):
        """是否可以進入測驗"""
        return self.is_accessible()
    
    @property
    def purchase_days_ago(self):
        """購買後經過的天數"""
        from django.utils import timezone
        return (timezone.now() - self.purchase_date).days
    
    def has_result(self):
        """檢查是否有測驗結果"""
        return hasattr(self, 'test_result')
    
    def get_result_status(self):
        """獲取結果狀態"""
        if not self.has_result():
            return 'no_result'
        return self.test_result.result_status
    
    def create_result_placeholder(self):
        """創建結果佔位符"""
        if not self.has_result():
            from .models import IndividualTestResult  # 避免循環導入
            IndividualTestResult.objects.create(
                individual_test_record=self,
                test_project=self.test_project,
                user=self.user
            )
            return True
        return False

class IndividualTestResult(models.Model):
    """個人測驗結果表 - 儲存個人用戶的測驗結果"""
    
    # 關聯到個人測驗記錄
    individual_test_record = models.OneToOneField(
        IndividualTestRecord,
        on_delete=models.CASCADE,
        related_name='test_result',
        verbose_name='個人測驗記錄'
    )
    
    # 基本資訊
    test_project = models.ForeignKey(
        TestProject, 
        on_delete=models.CASCADE, 
        verbose_name='測驗項目'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='用戶',
        related_name='individual_test_results'
    )
    
    # 測驗結果數據（JSON格式儲存原始數據）
    raw_data = models.JSONField(default=dict, verbose_name='原始測驗數據')
    processed_data = models.JSONField(default=dict, verbose_name='處理後數據')
    
    # 根據測驗項目配置解析的結果
    score_value = models.FloatField(null=True, blank=True, verbose_name='評分值')
    prediction_value = models.TextField(blank=True, verbose_name='預測值')
    category_results = models.JSONField(default=dict, verbose_name='分類結果')
    trait_results = models.JSONField(default=dict, verbose_name='特質結果')
    
    # 個人用戶特有欄位
    test_completion_date = models.DateTimeField(null=True, blank=True, verbose_name='測驗完成時間')
    external_test_id = models.CharField(max_length=100, blank=True, verbose_name='外部測驗ID')
    test_url = models.URLField(blank=True, verbose_name='測驗結果原始連結')
    
    # 結果處理狀態
    RESULT_STATUS_CHOICES = [
        ('pending', '等待結果'),
        ('manual_input', '手動輸入'),
        ('auto_crawled', '自動爬取'),
        ('completed', '結果完整'),
        ('failed', '獲取失敗'),
    ]
    result_status = models.CharField(
        max_length=20, 
        choices=RESULT_STATUS_CHOICES, 
        default='pending',
        verbose_name='結果狀態'
    )
    
    # 爬蟲相關 (如果支援自動爬取)
    crawled_at = models.DateTimeField(null=True, blank=True, verbose_name='結果爬取時間')
    crawl_attempts = models.IntegerField(default=0, verbose_name='爬取嘗試次數')
    crawl_error_message = models.TextField(blank=True, verbose_name='爬取錯誤訊息')
    
    # 報告生成
    report_generated = models.BooleanField(default=False, verbose_name='報告已生成')
    report_path = models.CharField(max_length=500, blank=True, verbose_name='報告路徑')
    report_generated_at = models.DateTimeField(null=True, blank=True, verbose_name='報告生成時間')
    
    # 個人化設定
    allow_sharing = models.BooleanField(default=False, verbose_name='允許分享結果')
    notes = models.TextField(blank=True, verbose_name='個人備註')
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = '個人測驗結果'
        verbose_name_plural = '個人測驗結果'
        db_table = 'individual_test_result'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'test_project']),
            models.Index(fields=['result_status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f'{self.user.username} - {self.test_project.name}'
    
    def get_category_analysis(self):
        """獲取分類分析結果"""
        if not self.category_results:
            return {}
        
        analysis = {}
        for category, data in self.category_results.items():
            if isinstance(data, dict) and 'score' in data:
                analysis[category] = {
                    'score': data['score'],
                    'percentage': min(100, max(0, (data['score'] / 5.0) * 100)),
                    'level': self._get_score_level(data['score']),
                    'description': data.get('description', '')
                }
        return analysis
    
    def get_trait_analysis(self):
        """獲取特質分析結果"""
        if not self.trait_results:
            return {}
        
        traits = {}
        for trait, score in self.trait_results.items():
            if isinstance(score, (int, float)):
                traits[trait] = {
                    'score': score,
                    'percentage': min(100, max(0, (score / 5.0) * 100)),
                    'level': self._get_score_level(score)
                }
        return traits
    
    def _get_score_level(self, score):
        """根據分數獲取等級描述"""
        if score >= 4.5:
            return '非常高'
        elif score >= 3.5:
            return '高'
        elif score >= 2.5:
            return '中等'
        elif score >= 1.5:
            return '低'
        else:
            return '非常低'
    
    def get_strengths_and_weaknesses(self):
        """獲取優勢和劣勢分析"""
        analysis = self.get_category_analysis()
        if not analysis:
            return {'strengths': [], 'weaknesses': []}
        
        sorted_categories = sorted(
            analysis.items(), 
            key=lambda x: x[1]['score'], 
            reverse=True
        )
        
        # 取前2名作為優勢，後2名作為劣勢
        strengths = sorted_categories[:2]
        weaknesses = sorted_categories[-2:]
        
        return {
            'strengths': [{'name': name, **data} for name, data in strengths],
            'weaknesses': [{'name': name, **data} for name, data in weaknesses]
        }
    
    def is_result_complete(self):
        """檢查結果是否完整"""
        return (
            self.result_status == 'completed' and
            (self.category_results or self.trait_results or self.score_value is not None)
        )
    
    def can_generate_report(self):
        """檢查是否可以生成報告"""
        return self.is_result_complete()
    
    @property
    def completion_days_ago(self):
        """測驗完成後經過的天數"""
        if not self.test_completion_date:
            return None
        from django.utils import timezone
        return (timezone.now() - self.test_completion_date).days
    
    def save(self, *args, **kwargs):
        """重寫 save 方法，在結果完成時自動更新測驗記錄狀態"""
        # 檢查是否是新建立的結果或結果狀態變為 completed
        is_new = self.pk is None
        old_status = None
        
        if not is_new:
            # 獲取舊的狀態
            try:
                old_instance = IndividualTestResult.objects.get(pk=self.pk)
                old_status = old_instance.result_status
            except IndividualTestResult.DoesNotExist:
                pass
        
        # 先保存結果
        super().save(*args, **kwargs)
        
        # 如果結果狀態變為 completed 或有測驗完成時間，更新對應的測驗記錄狀態
        should_complete = (
            (is_new and self.result_status == 'completed') or
            (old_status and old_status != 'completed' and self.result_status == 'completed') or
            (self.test_completion_date is not None)  # 有完成時間就算完成
        )
        
        if should_complete:
            try:
                test_record = self.individual_test_record
                if test_record.status != 'completed':
                    test_record.status = 'completed'
                    test_record.save()
            except IndividualTestRecord.DoesNotExist:
                pass
    
    @property
    def overall_score(self):
        """整體評分"""
        if self.score_value is not None:
            return self.score_value
        
        # 如果沒有整體評分，計算分類平均
        analysis = self.get_category_analysis()
        if analysis:
            scores = [data['score'] for data in analysis.values() if 'score' in data]
            return round(sum(scores) / len(scores), 2) if scores else None
        
        return None

# ==================== 爬蟲管理 ====================

class CrawlerLog(models.Model):
    """爬蟲執行日誌"""
    TASK_CHOICES = [
        ('crawl_all_pending_results', '批量爬取測驗結果'),
        ('cleanup_old_crawl_logs', '清理舊日誌'),
        ('manual_crawl', '手動爬取'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待執行'),
        ('running', '執行中'),
        ('completed', '已完成'),
        ('failed', '失敗'),
    ]
    
    task_name = models.CharField(max_length=100, choices=TASK_CHOICES, verbose_name='任務名稱')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed', verbose_name='執行狀態')
    success_count = models.IntegerField(default=0, verbose_name='成功數量')
    fail_count = models.IntegerField(default=0, verbose_name='失敗數量')
    total_count = models.IntegerField(default=0, verbose_name='總數量')
    executed_at = models.DateTimeField(default=timezone.now, verbose_name='執行時間')
    duration = models.DurationField(null=True, blank=True, verbose_name='執行時長')
    message = models.TextField(blank=True, verbose_name='執行訊息')
    error_details = models.TextField(blank=True, verbose_name='錯誤詳情')
    
    class Meta:
        db_table = 'crawler_logs'
        verbose_name = '爬蟲執行日誌'
        verbose_name_plural = '爬蟲執行日誌'
        ordering = ['-executed_at']
    
    def __str__(self):
        return "{} - {}".format(
            self.get_task_name_display(), 
            self.executed_at.strftime('%Y-%m-%d %H:%M')
        )
    
    @property
    def success_rate(self):
        """成功率"""
        if self.total_count > 0:
            return round((self.success_count / self.total_count) * 100, 1)
        return 0


class CrawlerDetailLog(models.Model):
    """爬蟲詳細執行日誌 - 記錄每個邀請的爬取詳情"""
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失敗'),
        ('skipped', '跳過'),
    ]
    
    # 關聯到主要日誌
    crawler_log = models.ForeignKey(
        CrawlerLog, 
        on_delete=models.CASCADE, 
        related_name='detail_logs',
        verbose_name='爬蟲日誌'
    )
    
    # 邀請資訊
    test_invitation = models.ForeignKey(
        'TestInvitation',
        on_delete=models.CASCADE,
        verbose_name='測驗邀請'
    )
    
    # 受測人資訊（冗余存儲，方便查詢）
    invitee_name = models.CharField(max_length=100, verbose_name='受測人姓名')
    invitee_email = models.EmailField(verbose_name='受測人信箱')
    test_project_name = models.CharField(max_length=200, verbose_name='測驗項目')
    
    # 爬取結果
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='爬取狀態')
    error_message = models.TextField(blank=True, verbose_name='錯誤訊息')
    error_details = models.JSONField(default=dict, blank=True, verbose_name='詳細錯誤資訊')
    
    # 爬取嘗試資訊
    attempt_count = models.IntegerField(default=1, verbose_name='嘗試次數')
    execution_time = models.FloatField(null=True, blank=True, verbose_name='執行時間(秒)')
    
    # 爬取到的資料資訊
    data_found = models.BooleanField(default=False, verbose_name='是否找到資料')
    crawled_data_size = models.IntegerField(default=0, verbose_name='爬取資料大小')
    
    # 時間戳
    executed_at = models.DateTimeField(default=timezone.now, verbose_name='執行時間')
    
    class Meta:
        db_table = 'crawler_detail_logs'
        verbose_name = '爬蟲詳細日誌'
        verbose_name_plural = '爬蟲詳細日誌'
        ordering = ['-executed_at']
        
    def __str__(self):
        return f"{self.invitee_name} - {self.test_project_name} - {self.get_status_display()}"
    
    @property
    def formatted_error(self):
        """格式化錯誤訊息"""
        if self.error_message:
            return self.error_message
        return "無錯誤訊息"

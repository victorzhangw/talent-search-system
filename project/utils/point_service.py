# utils/point_service.py
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from core.models import User, PointTransaction, UserPointBalance, PointPackage, PointOrder
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class PointService:
    """點數管理服務"""
    
    # 點數消費項目定義（根據實際業務需求）
    POINT_COSTS = {
        'test_invite': 1,             # 企業邀請用戶執行測驗
        'test_execution': 1,          # 個人用戶執行測驗
        'admin_adjust': 1,            # 管理員調整點數（用於扣除）
        # 以下功能暫時不扣點，保留備用
        'test_creation': 0,           # 建立測驗（不扣點）
        'report_generation': 0,       # 生成報告（不扣點）
        'data_export': 0,             # 資料匯出（不扣點）
        'advanced_analysis': 0,       # 進階分析（不扣點）
        'bulk_invite': 0,             # 批量邀請（不扣點）
        'custom_template': 0,         # 自定義模板（不扣點）
    }
    
    # 各種獎勵點數
    BONUS_POINTS = {
        'registration': 50,           # 註冊獎勵
        'enterprise_approved': 200,   # 企業審核通過
        'first_test': 20,            # 首次測驗
        'referral': 30,              # 推薦獎勵
    }
    
    @classmethod
    def get_user_balance(cls, user):
        """獲取用戶點數餘額"""
        try:
            balance_obj = UserPointBalance.objects.get(user=user)
            return balance_obj.balance
        except UserPointBalance.DoesNotExist:
            # 如果不存在，創建新的餘額記錄
            return cls._create_user_balance(user).balance
    
    @classmethod
    def _create_user_balance(cls, user):
        """創建用戶點數餘額記錄"""
        initial_points = 0

        balance_obj = UserPointBalance.objects.create(
            user=user,
            balance=initial_points,
            total_earned=initial_points
        )
        
        # 如果有初始點數，記錄交易
        if initial_points > 0:
            PointTransaction.objects.create(
                user=user,
                transaction_type='registration_bonus',
                amount=initial_points,
                balance_before=0,
                balance_after=initial_points,
                description=f"新用戶註冊獎勵 ({user.get_user_type_display()})",
                status='completed'
            )
        
        logger.info(f"為用戶 {user.username} 創建點數帳戶，初始點數: {initial_points}")
        return balance_obj
    
    @classmethod
    def can_consume(cls, user, action_type, quantity=1):
        """檢查是否可以消費點數"""
        # 如果系統設置為無限制模式，直接返回True
        if getattr(settings, 'UNLIMITED_POINTS_MODE', True):
            logger.info(f"無限制模式：用戶 {user.username} 執行 {action_type}")
            return True
        
        # 檢查點數系統是否啟用
        if not getattr(settings, 'POINT_SYSTEM_ENABLED', True):
            return True
            
        required_points = cls.POINT_COSTS.get(action_type, 0) * quantity
        current_balance = cls.get_user_balance(user)
        
        return current_balance >= required_points
    
    @classmethod
    @transaction.atomic
    def consume_points(cls, user, action_type, quantity=1, description="", reference_id=""):
        """消費點數"""
        required_points = cls.POINT_COSTS.get(action_type, 0) * quantity
        
        if required_points <= 0:
            logger.warning(f"無效的點數消費：{action_type}")
            return True
        
        # 無限制模式下仍然記錄交易，但不實際扣點
        if getattr(settings, 'UNLIMITED_POINTS_MODE', True):
            return cls._record_virtual_transaction(
                user, action_type, required_points, description, reference_id
            )
        
        # 正式模式：檢查餘額並扣點
        balance_obj = UserPointBalance.objects.select_for_update().get(user=user)
        
        if balance_obj.balance < required_points:
            logger.warning(f"點數不足：用戶 {user.username}，需要 {required_points}，餘額 {balance_obj.balance}")
            return False
        
        # 扣除點數
        old_balance = balance_obj.balance
        balance_obj.balance -= required_points
        balance_obj.total_consumed += required_points
        balance_obj.save()
        
        # 記錄交易
        PointTransaction.objects.create(
            user=user,
            transaction_type='consumption',
            amount=-required_points,
            balance_before=old_balance,
            balance_after=balance_obj.balance,
            description=description or f"{action_type} 消費",
            reference_id=reference_id,
            status='completed',
            metadata={'action_type': action_type, 'quantity': quantity}
        )
        
        logger.info(f"點數消費成功：用戶 {user.username}，消費 {required_points}，餘額 {balance_obj.balance}")
        return True
    
    @classmethod
    def _record_virtual_transaction(cls, user, action_type, amount, description, reference_id):
        """記錄虛擬交易（無限制模式下的記錄）"""
        current_balance = cls.get_user_balance(user)
        
        PointTransaction.objects.create(
            user=user,
            transaction_type='consumption',
            amount=-amount,
            balance_before=current_balance,
            balance_after=current_balance,  # 餘額不變
            description=f"[虛擬] {description or action_type}",
            reference_id=reference_id,
            status='completed',
            metadata={'virtual': True, 'action_type': action_type}
        )
        
        logger.info(f"虛擬點數消費記錄：用戶 {user.username}，動作 {action_type}，虛擬消費 {amount}")
        return True
    
    @classmethod
    @transaction.atomic
    def add_points(cls, user, amount, description="", reference_id="", transaction_type="purchase"):
        """增加點數"""
        if amount <= 0:
            raise ValidationError("點數數量必須大於0")
        
        balance_obj, created = UserPointBalance.objects.get_or_create(
            user=user,
            defaults={'balance': 0, 'total_earned': 0, 'total_consumed': 0}
        )
        
        old_balance = balance_obj.balance
        balance_obj.balance += amount
        balance_obj.total_earned += amount
        balance_obj.save()
        
        # 記錄交易
        PointTransaction.objects.create(
            user=user,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=old_balance,
            balance_after=balance_obj.balance,
            description=description,
            reference_id=reference_id,
            status='completed'
        )
        
        logger.info(f"點數增加：用戶 {user.username}，增加 {amount}，餘額 {balance_obj.balance}")
        return True
    
    @classmethod
    @transaction.atomic
    def refund_points(cls, user, amount, description="", reference_id=""):
        """退還點數（用於取消邀請等場景）"""
        if amount <= 0:
            raise ValidationError("退還點數數量必須大於0")
        
        # 無限制模式下仍然記錄退款交易
        if getattr(settings, 'UNLIMITED_POINTS_MODE', True):
            return cls._record_virtual_refund(user, amount, description, reference_id)
        
        balance_obj, created = UserPointBalance.objects.get_or_create(
            user=user,
            defaults={'balance': 0, 'total_earned': 0, 'total_consumed': 0}
        )
        
        old_balance = balance_obj.balance
        balance_obj.balance += amount
        # 退款應該減少 total_consumed 而不是增加 total_earned
        balance_obj.total_consumed = max(0, balance_obj.total_consumed - amount)
        balance_obj.save()
        
        # 記錄退款交易
        PointTransaction.objects.create(
            user=user,
            transaction_type='refund',
            amount=amount,
            balance_before=old_balance,
            balance_after=balance_obj.balance,
            description=description or "點數退還",
            reference_id=reference_id,
            status='completed'
        )
        
        logger.info(f"點數退還：用戶 {user.username}，退還 {amount}，餘額 {balance_obj.balance}")
        return True
    
    @classmethod
    def _record_virtual_refund(cls, user, amount, description, reference_id):
        """記錄虛擬退款交易"""
        current_balance = cls.get_user_balance(user)
        
        PointTransaction.objects.create(
            user=user,
            transaction_type='refund',
            amount=amount,
            balance_before=current_balance,
            balance_after=current_balance,  # 餘額不變
            description=f"[虛擬] {description}",
            reference_id=reference_id,
            status='completed',
            metadata={'virtual': True, 'refund': True}
        )
        
        logger.info(f"虛擬點數退還記錄：用戶 {user.username}，虛擬退還 {amount}")
        return True
    
    @classmethod
    def give_bonus_points(cls, user, bonus_type, description=""):
        """給予獎勵點數"""
        bonus_amount = cls.BONUS_POINTS.get(bonus_type, 0)
        
        if bonus_amount > 0:
            return cls.add_points(
                user=user,
                amount=bonus_amount,
                description=description or f"{bonus_type} 獎勵",
                transaction_type='gift'
            )
        return False
    
    @classmethod
    def get_transaction_history(cls, user, limit=50, transaction_type=None):
        """獲取交易歷史"""
        queryset = PointTransaction.objects.filter(user=user)
        
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
            
        return queryset.order_by('-created_at')[:limit]
    
    @classmethod
    def get_consumption_stats(cls, user, days=30):
        """獲取消費統計"""
        from datetime import timedelta
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        transactions = PointTransaction.objects.filter(
            user=user,
            transaction_type='consumption',
            created_at__range=[start_date, end_date]
        )
        
        total_consumed = sum(abs(t.amount) for t in transactions)
        transaction_count = transactions.count()
        
        # 按動作類型分組統計
        action_stats = {}
        for transaction in transactions:
            action_type = transaction.metadata.get('action_type', 'unknown')
            if action_type not in action_stats:
                action_stats[action_type] = {'count': 0, 'total': 0}
            action_stats[action_type]['count'] += 1
            action_stats[action_type]['total'] += abs(transaction.amount)
        
        return {
            'total_consumed': total_consumed,
            'transaction_count': transaction_count,
            'period_days': days,
            'action_stats': action_stats,
            'start_date': start_date,
            'end_date': end_date
        }
    
    @classmethod
    def get_balance_summary(cls, user):
        """獲取餘額摘要"""
        try:
            balance_obj = UserPointBalance.objects.get(user=user)
        except UserPointBalance.DoesNotExist:
            balance_obj = cls._create_user_balance(user)
        
        # 獲取最近30天的統計
        stats = cls.get_consumption_stats(user, 30)
        
        return {
            'current_balance': balance_obj.balance,
            'total_earned': balance_obj.total_earned,
            'total_consumed': balance_obj.total_consumed,
            'recent_consumed': stats['total_consumed'],
            'recent_transactions': stats['transaction_count'],
            'last_updated': balance_obj.updated_at
        }

# 裝飾器：檢查點數權限
def require_points(action_type, quantity=1, redirect_url='point_purchase'):
    """檢查點數的裝飾器"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from django.shortcuts import redirect
            from django.contrib import messages
            
            if not request.user.is_authenticated:
                return redirect('login')
            
            if not PointService.can_consume(request.user, action_type, quantity):
                required_points = PointService.POINT_COSTS.get(action_type, 0) * quantity
                current_balance = PointService.get_user_balance(request.user)
                
                messages.error(
                    request, 
                    f'點數不足！需要 {required_points} 點，目前餘額 {current_balance} 點。請購買點數後再試。'
                )
                return redirect(redirect_url)
            
            # 執行功能前先消費點數
            success = PointService.consume_points(
                request.user, 
                action_type, 
                quantity,
                f"執行 {view_func.__name__}",
                f"view_{view_func.__name__}"
            )
            
            if not success:
                messages.error(request, '點數扣除失敗，請稍後再試')
                return redirect(redirect_url)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

# 手動檢查點數的函數
def check_and_consume_points(user, action_type, quantity=1, description=""):
    """手動檢查並消費點數"""
    if not PointService.can_consume(user, action_type, quantity):
        return False, f"點數不足，需要 {PointService.POINT_COSTS.get(action_type, 0) * quantity} 點"
    
    success = PointService.consume_points(user, action_type, quantity, description)
    if success:
        return True, "點數扣除成功"
    else:
        return False, "點數扣除失敗"

# core/point_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from utils.point_service import PointService, require_points
from core.models import (
    PointTransaction,
    User,
    UserPointBalance,
    PointPackage,
    PointOrder,
    EnterprisePurchaseRecord,
    EnterpriseQuotaUsageLog,
    TestProject,
)
from django.db.models import Q
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

@login_required
def point_dashboard(request):
    """點數儀表板"""
    user = request.user
    
    # 獲取餘額摘要
    balance_summary = PointService.get_balance_summary(user)
    
    # 獲取最近交易記錄
    recent_transactions = PointService.get_transaction_history(user, limit=10)
    
    # 獲取消費統計
    consumption_stats = PointService.get_consumption_stats(user, days=30)
    
    # 獲取可用的點數套餐
    packages = PointPackage.objects.filter(is_active=True).order_by('sort_order', 'price')
    
    context = {
        'balance_summary': balance_summary,
        'recent_transactions': recent_transactions,
        'consumption_stats': consumption_stats,
        'packages': packages,
        'point_costs': PointService.POINT_COSTS,
        'unlimited_mode': getattr(settings, 'UNLIMITED_POINTS_MODE', True),
    }
    
    return render(request, 'points/dashboard.html', context)

@login_required
@require_POST
def cancel_point_order(request, order_number):
    """取消點數訂單"""
    order = get_object_or_404(PointOrder, order_number=order_number, user=request.user)
    
    if order.status not in ['pending']:
        messages.error(request, '此訂單無法取消')
        return redirect('point_orders')
    
    order.status = 'cancelled'
    order.save()
    
    logger.info(f"用戶 {request.user.username} 取消訂單：{order_number}")
    messages.success(request, f'訂單 {order_number} 已取消')
    
    return redirect('point_orders')

# ==================== API接口 ====================

@login_required
@require_GET
def api_point_balance(request):
    """獲取用戶點數餘額API"""
    balance_summary = PointService.get_balance_summary(request.user)
    return JsonResponse({
        'status': 'success',
        'data': balance_summary
    })

@login_required
@require_GET
def api_point_costs(request):
    """獲取點數消費標準API"""
    return JsonResponse({
        'status': 'success',
        'data': {
            'costs': PointService.POINT_COSTS,
            'bonuses': PointService.BONUS_POINTS,
            'unlimited_mode': getattr(settings, 'UNLIMITED_POINTS_MODE', True)
        }
    })

@login_required
@require_POST
def api_check_points(request):
    """檢查點數是否足夠API"""
    try:
        data = json.loads(request.body)
        action_type = data.get('action_type')
        quantity = data.get('quantity', 1)
        
        if not action_type:
            return JsonResponse({'status': 'error', 'message': '缺少action_type參數'})
        
        can_consume = PointService.can_consume(request.user, action_type, quantity)
        required_points = PointService.POINT_COSTS.get(action_type, 0) * quantity
        current_balance = PointService.get_user_balance(request.user)
        
        return JsonResponse({
            'status': 'success',
            'data': {
                'can_consume': can_consume,
                'required_points': required_points,
                'current_balance': current_balance,
                'unlimited_mode': getattr(settings, 'UNLIMITED_POINTS_MODE', True)
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': '無效的JSON格式'})
    except Exception as e:
        logger.error(f"檢查點數失敗：{str(e)}")
        return JsonResponse({'status': 'error', 'message': '檢查失敗'})

@login_required
@require_POST
def api_consume_points(request):
    """消費點數API"""
    try:
        data = json.loads(request.body)
        action_type = data.get('action_type')
        quantity = data.get('quantity', 1)
        description = data.get('description', '')
        reference_id = data.get('reference_id', '')
        
        if not action_type:
            return JsonResponse({'status': 'error', 'message': '缺少action_type參數'})
        
        # 檢查是否可以消費
        if not PointService.can_consume(request.user, action_type, quantity):
            required_points = PointService.POINT_COSTS.get(action_type, 0) * quantity
            current_balance = PointService.get_user_balance(request.user)
            return JsonResponse({
                'status': 'error', 
                'message': f'點數不足，需要 {required_points} 點，目前餘額 {current_balance} 點'
            })
        
        # 消費點數
        success = PointService.consume_points(
            request.user, action_type, quantity, description, reference_id
        )
        
        if success:
            new_balance = PointService.get_user_balance(request.user)
            return JsonResponse({
                'status': 'success',
                'data': {
                    'new_balance': new_balance,
                    'consumed_points': PointService.POINT_COSTS.get(action_type, 0) * quantity
                }
            })
        else:
            return JsonResponse({'status': 'error', 'message': '點數扣除失敗'})
            
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': '無效的JSON格式'})
    except Exception as e:
        logger.error(f"消費點數失敗：{str(e)}")
        return JsonResponse({'status': 'error', 'message': '操作失敗'})

# ==================== 管理員功能 ====================

@login_required
def admin_point_overview(request):
    """管理員點數總覽頁面"""
    if not (request.user.is_staff or request.user.user_type == 'admin'):
        messages.error(request, '權限不足')
        return redirect('point_dashboard')
    
    from django.db.models import Sum, Count, Q
    
    # 獲取所有用戶點數餘額
    individual_users = UserPointBalance.objects.filter(
        user__user_type='individual'
    ).select_related('user', 'user__individual_profile').order_by('-total_earned')
    
    enterprise_users = UserPointBalance.objects.filter(
        user__user_type='enterprise'
    ).select_related('user', 'user__enterprise_profile').order_by('-total_earned')
    
    # 統計數據
    stats = {
        'total_users': UserPointBalance.objects.count(),
        'individual_count': individual_users.count(),
        'enterprise_count': enterprise_users.count(),
        'total_points_issued': UserPointBalance.objects.aggregate(
            total=Sum('total_earned')
        )['total'] or 0,
        'total_points_consumed': UserPointBalance.objects.aggregate(
            total=Sum('total_consumed')
        )['total'] or 0,
        'total_points_balance': UserPointBalance.objects.aggregate(
            total=Sum('balance')
        )['total'] or 0,
        'individual_total_points': individual_users.aggregate(
            total=Sum('total_earned')
        )['total'] or 0,
        'enterprise_total_points': enterprise_users.aggregate(
            total=Sum('total_earned')
        )['total'] or 0,
        'individual_balance_points': individual_users.aggregate(
            total=Sum('balance')
        )['total'] or 0,
        'enterprise_balance_points': enterprise_users.aggregate(
            total=Sum('balance')
        )['total'] or 0,
    }
    
    # 搜尋功能
    search_query = request.GET.get('search', '')
    user_type_filter = request.GET.get('user_type', '')
    
    # 用戶類型篩選
    if user_type_filter == 'individual':
        enterprise_users = enterprise_users.none()  # 隱藏企業用戶
    elif user_type_filter == 'enterprise':
        individual_users = individual_users.none()  # 隱藏個人用戶
    
    # 搜尋篩選
    if search_query:
        individual_users = individual_users.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__individual_profile__real_name__icontains=search_query)
        )
        enterprise_users = enterprise_users.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__enterprise_profile__company_name__icontains=search_query)
        )
    
    # 獲取最近交易
    recent_transactions = PointTransaction.objects.select_related('user').order_by('-created_at')[:10]
    
    context = {
        'stats': stats,
        'individual_users': individual_users[:20],  # 限制顯示數量
        'enterprise_users': enterprise_users[:20],   # 限制顯示數量
        'recent_transactions': recent_transactions,
        'search_query': search_query,
        'user_type_filter': user_type_filter,
    }
    
    return render(request, 'admin/point_overview.html', context)

@login_required
def admin_point_management(request):
    """管理員點數交易紀錄頁面"""
    if not (request.user.is_staff or request.user.user_type == 'admin'):
        messages.error(request, '權限不足')
        return redirect('point_dashboard')
    
    from django.db.models import Sum, Count, Q
    from django.core.paginator import Paginator
    from datetime import datetime, timedelta
    
    # 獲取篩選參數
    search_query = request.GET.get('search', '')
    user_type_filter = request.GET.get('user_type', '')
    transaction_type_filter = request.GET.get('transaction_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # 構建查詢
    transactions = PointTransaction.objects.select_related('user', 'user__individual_profile', 'user__enterprise_profile')
    
    # 搜尋過濾
    if search_query:
        transactions = transactions.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__individual_profile__real_name__icontains=search_query) |
            Q(user__enterprise_profile__company_name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # 用戶類型過濾
    if user_type_filter:
        transactions = transactions.filter(user__user_type=user_type_filter)
    
    # 交易類型過濾
    if transaction_type_filter:
        transactions = transactions.filter(transaction_type=transaction_type_filter)
    
    # 日期過濾
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            transactions = transactions.filter(created_at__date__gte=date_from_obj.date())
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            transactions = transactions.filter(created_at__date__lte=date_to_obj.date())
        except ValueError:
            pass
    
    # 按時間排序
    transactions = transactions.order_by('-created_at')
    
    # 分頁
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 獲取統計數據
    stats = {
        'total_transactions': transactions.count(),
        'total_points_issued': UserPointBalance.objects.aggregate(
            total=Sum('total_earned')
        )['total'] or 0,
        'total_points_consumed': UserPointBalance.objects.aggregate(
            total=Sum('total_consumed')
        )['total'] or 0,
        'system_balance': UserPointBalance.objects.aggregate(
            total=Sum('balance')
        )['total'] or 0,
    }
    
    # 交易類型選項
    transaction_types = [
        ('', '全部交易'),
        ('registration_bonus', '註冊獎勵'),
        ('consumption', '消費'),
        ('purchase', '購買'),
        ('admin_adjust', '管理員調整'),
        ('refund', '退款'),
    ]
    
    # 用戶類型選項
    user_types = [
        ('', '全部學員'),
        ('individual', '個人用戶'),
        ('enterprise', '企業用戶'),
    ]
    
    context = {
        'stats': stats,
        'page_obj': page_obj,
        'transaction_types': transaction_types,
        'user_types': user_types,
        'current_filters': {
            'search': search_query,
            'user_type': user_type_filter,
            'transaction_type': transaction_type_filter,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'admin/point_management.html', context)

@login_required
@require_POST
def admin_adjust_points(request):
    """管理員調整用戶點數"""
    if not (request.user.is_staff or request.user.user_type == 'admin'):
        return JsonResponse({'status': 'error', 'message': '權限不足'})
    
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        adjust_type = data.get('type')
        amount = int(data.get('amount', 0))
        reason = data.get('reason', '')
        
        if not user_id or not adjust_type or amount <= 0 or not reason:
            return JsonResponse({'status': 'error', 'message': '請填寫所有必填欄位'})
        
        user = get_object_or_404(User, id=user_id)
        current_balance = PointService.get_user_balance(user)
        
        # 根據調整類型執行不同操作
        if adjust_type == 'add':
            # 增加點數
            PointService.add_points(
                user=user,
                amount=amount,
                description=f"管理員增加：{reason}",
                transaction_type='admin_adjust'
            )
            adjusted_amount = amount
            
        elif adjust_type == 'subtract':
            # 扣除點數
            if current_balance < amount:
                return JsonResponse({'status': 'error', 'message': f'用戶點數不足，目前餘額：{current_balance} 點'})
            
            PointService.consume_points(
                user=user,
                action_type='admin_adjust',
                quantity=amount,
                description=f"管理員扣除：{reason}",
                reference_id=f"admin_{request.user.id}_{timezone.now().timestamp()}"
            )
            adjusted_amount = -amount
            
        elif adjust_type == 'set':
            # 設定點數（先計算差額）
            difference = amount - current_balance
            if difference > 0:
                # 需要增加點數
                PointService.add_points(
                    user=user,
                    amount=difference,
                    description=f"管理員設定為{amount}點：{reason}",
                    transaction_type='admin_adjust'
                )
            elif difference < 0:
                # 需要扣除點數
                PointService.consume_points(
                    user=user,
                    action_type='admin_adjust',
                    quantity=abs(difference),
                    description=f"管理員設定為{amount}點：{reason}",
                    reference_id=f"admin_{request.user.id}_{timezone.now().timestamp()}"
                )
            adjusted_amount = difference
        else:
            return JsonResponse({'status': 'error', 'message': '無效的調整類型'})
        
        new_balance = PointService.get_user_balance(user)
        
        logger.info(f"管理員 {request.user.username} 調整用戶 {user.username} 點數：{adjust_type} {amount}點，原因：{reason}")
        
        return JsonResponse({
            'status': 'success',
            'message': f'點數調整成功！{user.username} 的點數已更新為 {new_balance} 點',
            'data': {
                'new_balance': new_balance,
                'adjusted_amount': adjusted_amount,
                'previous_balance': current_balance
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'JSON 格式錯誤'})
    except ValueError:
        return JsonResponse({'status': 'error', 'message': '點數數量必須是有效數字'})
    except Exception as e:
        logger.error(f"管理員調整點數失敗：{str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'操作失敗：{str(e)}'})

# ==================== 測試功能（開發環境使用） ====================

@login_required
def test_point_functions(request):
    """測試點數功能（僅開發環境）"""
    if not settings.DEBUG:
        messages.error(request, '此功能僅在開發環境可用')
        return redirect('point_dashboard')
    
    user = request.user
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_bonus':
            PointService.give_bonus_points(user, 'registration', '測試註冊獎勵')
            messages.success(request, '已增加註冊獎勵點數')
            
        elif action == 'test_consume':
            from utils.point_service import check_and_consume_points
            success, message = check_and_consume_points(user, 'test_execution', 1, '測試消費')
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
                
        elif action == 'simulate_purchase':
            # 模擬購買100點
            PointService.add_points(user, 100, '測試購買', transaction_type='purchase')
            messages.success(request, '已模擬購買100點數')
            
        return redirect('test_point_functions')
    
    balance_summary = PointService.get_balance_summary(user)
    recent_transactions = PointService.get_transaction_history(user, limit=5)
    
    context = {
        'balance_summary': balance_summary,
        'recent_transactions': recent_transactions,
        'point_costs': PointService.POINT_COSTS,
    }
    
    return render(request, 'points/test_functions.html', context)

@login_required
def point_history(request):
    """點數 / 份數歷史記錄"""
    user = request.user

    if user.user_type == 'enterprise':
        return _admin_purchase_history(request)

    # 一般用戶既有流程
    transaction_type = request.GET.get('type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    transactions = PointTransaction.objects.filter(user=user)

    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)

    if date_from:
        try:
            from datetime import datetime
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            transactions = transactions.filter(created_at__date__gte=date_from_obj.date())
        except ValueError:
            pass

    if date_to:
        try:
            from datetime import datetime
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            transactions = transactions.filter(created_at__date__lte=date_to_obj.date())
        except ValueError:
            pass

    paginator = Paginator(transactions.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    transaction_types = PointTransaction.TRANSACTION_TYPES

    context = {
        'page_obj': page_obj,
        'transaction_types': transaction_types,
        'current_filters': {
            'type': transaction_type,
            'date_from': date_from,
            'date_to': date_to,
        }
    }

    return render(request, 'points/history.html', context)


def _admin_purchase_history(request):
    user = request.user
    is_admin = user.is_staff or user.user_type == 'admin'

    project_id = request.GET.get('project', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_name = request.GET.get('name', '')
    search_email = request.GET.get('email', '')

    purchase_qs = EnterprisePurchaseRecord.objects.select_related(
        'enterprise_user__enterprise_profile', 'test_project'
    )

    if not is_admin:
        purchase_qs = purchase_qs.filter(enterprise_user=user)

    if project_id:
        purchase_qs = purchase_qs.filter(test_project_id=project_id)

    from datetime import datetime

    if date_from:
        try:
            purchase_qs = purchase_qs.filter(payment_date__date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass

    if date_to:
        try:
            purchase_qs = purchase_qs.filter(payment_date__date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    purchase_page_number = request.GET.get('purchase_page')
    purchase_paginator = Paginator(purchase_qs.order_by('-payment_date', '-id'), 10)
    purchase_page_obj = purchase_paginator.get_page(purchase_page_number)

    usage_qs = EnterpriseQuotaUsageLog.objects.select_related(
        'enterprise_user__enterprise_profile', 'test_project', 'invitation__invitee'
    )

    if not is_admin:
        usage_qs = usage_qs.filter(enterprise_user=user)

    if search_name:
        usage_qs = usage_qs.filter(Q(invitee_name__icontains=search_name))

    if search_email:
        usage_qs = usage_qs.filter(Q(invitee_email__icontains=search_email))

    usage_page_number = request.GET.get('usage_page')
    usage_paginator = Paginator(usage_qs.order_by('-action_time', '-id'), 10)
    usage_page_obj = usage_paginator.get_page(usage_page_number)

    projects = TestProject.objects.order_by('name')

    context = {
        'purchase_page_obj': purchase_page_obj,
        'usage_page_obj': usage_page_obj,
        'projects': projects,
        'filters': {
            'project': project_id,
            'date_from': date_from,
            'date_to': date_to,
            'name': search_name,
            'email': search_email,
        },
    }

    return render(request, 'points/admin_history.html', context)

@login_required
def point_purchase(request):
    """點數購買頁面"""
    packages = PointPackage.objects.filter(is_active=True).order_by('sort_order', 'price')
    
    context = {
        'packages': packages,
        'current_balance': PointService.get_user_balance(request.user),
    }
    
    return render(request, 'points/purchase.html', context)

@login_required
@require_POST
def create_point_order(request):
    """建立點數購買訂單"""
    try:
        package_id = request.POST.get('package_id')
        package = get_object_or_404(PointPackage, id=package_id, is_active=True)
        
        # 建立訂單
        order = PointOrder.objects.create(
            user=request.user,
            package=package,
            points=package.points,
            bonus_points=package.bonus_points,
            amount=package.price,
            status='pending'
        )
        
        logger.info(f"建立點數訂單：{order.order_number}，用戶：{request.user.username}")
        
        # 如果是無限制模式，直接完成訂單
        if getattr(settings, 'UNLIMITED_POINTS_MODE', True):
            return complete_point_order_demo(request, order)
        
        # 正式模式：跳轉到付款頁面
        messages.success(request, f'訂單 {order.order_number} 已建立，請前往付款')
        return redirect('point_payment', order_number=order.order_number)
        
    except Exception as e:
        logger.error(f"建立點數訂單失敗：{str(e)}")
        messages.error(request, '建立訂單失敗，請稍後再試')
        return redirect('point_purchase')

def complete_point_order_demo(request, order):
    """完成點數訂單（演示模式）"""
    try:
        with transaction.atomic():
            # 更新訂單狀態
            order.status = 'completed'
            order.paid_at = timezone.now()
            order.completed_at = timezone.now()
            order.payment_method = 'demo'
            order.payment_reference = f'DEMO_{order.order_number}'
            order.save()
            
            # 添加除錯輸出
            logger.info(f"訂單保存成功：{order.order_number}，狀態：{order.status}，用戶：{order.user.username}")
            print(f"DEBUG: 訂單保存 - ID: {order.id}, 狀態: {order.status}, 用戶: {order.user.username}")

            # 驗證訂單是否真的保存到資料庫
            saved_order = PointOrder.objects.filter(order_number=order.order_number).first()
            if saved_order:
                print(f"DEBUG: 資料庫中找到訂單 - {saved_order.order_number}, 狀態: {saved_order.status}")
            else:
                print(f"DEBUG: 資料庫中未找到訂單 - {order.order_number}")

            # 增加點數
            total_points = order.total_points
            PointService.add_points(
                user=order.user,
                amount=total_points,
                description=f'購買點數套餐：{order.package.name}',
                reference_id=order.order_number,
                transaction_type='purchase'
            )
            
            logger.info(f"點數訂單完成：{order.order_number}，增加點數：{total_points}")
            messages.success(request, f'點數購買成功！獲得 {total_points} 點數')
            
    except Exception as e:
        logger.error(f"完成點數訂單失敗：{str(e)}")
        messages.error(request, '點數發放失敗，請聯繫客服')
    
    return redirect('point_orders')

@login_required
def point_payment(request, order_number):
    """點數付款頁面"""
    order = get_object_or_404(PointOrder, order_number=order_number, user=request.user)
    
    if order.status != 'pending':
        messages.info(request, '此訂單已處理完成')
        return redirect('point_dashboard')
    
    context = {
        'order': order,
    }
    
    return render(request, 'points/payment.html', context)

@login_required
def point_orders(request):
    """點數訂單列表"""
    orders = PointOrder.objects.filter(user=request.user).order_by('-created_at')
    
    # 添加除錯資訊
    print(f"DEBUG: 查詢用戶 {request.user.username} 的訂單")
    print(f"DEBUG: 找到 {orders.count()} 個訂單")
    for order in orders[:3]:  # 只打印前3個
        print(f"DEBUG: 訂單 {order.order_number}, 狀態: {order.status}, 時間: {order.created_at}")
    
    # 分頁
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'points/orders.html', context)

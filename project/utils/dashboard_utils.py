# utils/dashboard_utils.py
from datetime import datetime, timedelta
import random
import json

def generate_dashboard_stats():
    """生成儀表板統計數據"""
    # 今日數據
    today_users = random.randint(10, 50)
    today_orders = random.randint(5, 30)
    today_revenue = random.randint(50000, 500000)
    
    # 本週數據
    week_users = today_users + random.randint(20, 100)
    week_orders = today_orders + random.randint(20, 70)
    week_revenue = today_revenue + random.randint(100000, 1000000)
    
    # 本月數據
    month_users = week_users + random.randint(50, 200)
    month_orders = week_orders + random.randint(50, 150)
    month_revenue = week_revenue + random.randint(500000, 2000000)
    
    # 待處理項目
    pending_quotes = random.randint(3, 15)
    pending_orders = random.randint(2, 10)
    pending_shipments = random.randint(1, 8)
    
    # 系統概況
    system_stats = {
        'today': {
            'users': today_users,
            'orders': today_orders,
            'revenue': today_revenue,
            'revenue_formatted': format_currency(today_revenue)
        },
        'week': {
            'users': week_users,
            'orders': week_orders,
            'revenue': week_revenue,
            'revenue_formatted': format_currency(week_revenue)
        },
        'month': {
            'users': month_users,
            'orders': month_orders,
            'revenue': month_revenue,
            'revenue_formatted': format_currency(month_revenue)
        },
        'pending': {
            'quotes': pending_quotes,
            'orders': pending_orders,
            'shipments': pending_shipments,
            'total': pending_quotes + pending_orders + pending_shipments
        }
    }
    
    return system_stats

def generate_recent_activities(count=10):
    """生成最近活動數據"""
    activity_types = ['login', 'create', 'update', 'delete', 'approve', 'reject', 'export']
    users = ['admin', '王小明', '李小華', '張經理', '陳主管']
    targets = ['報價單', '訂單', '出貨單', '客戶', '產品']
    
    activities = []
    now = datetime.now()
    
    for i in range(count):
        activity_type = random.choice(activity_types)
        user = random.choice(users)
        target = random.choice(targets)
        
        # 生成隨機時間 (過去24小時內)
        minutes_ago = random.randint(1, 24 * 60)
        activity_time = now - timedelta(minutes=minutes_ago)
        
        # 格式化時間
        if minutes_ago < 60:
            time_text = f"{minutes_ago} 分鐘前"
        elif minutes_ago < 24 * 60:
            hours_ago = minutes_ago // 60
            time_text = f"{hours_ago} 小時前"
        else:
            time_text = activity_time.strftime('%Y-%m-%d %H:%M')
        
        # 生成活動描述
        if activity_type == 'login':
            description = f"{user} 登入系統"
            icon = 'bi-box-arrow-in-right'
            color = 'primary'
        elif activity_type == 'create':
            description = f"{user} 創建了新的 {target}"
            icon = 'bi-plus-circle'
            color = 'success'
        elif activity_type == 'update':
            description = f"{user} 更新了 {target}"
            icon = 'bi-pencil'
            color = 'info'
        elif activity_type == 'delete':
            description = f"{user} 刪除了 {target}"
            icon = 'bi-trash'
            color = 'danger'
        elif activity_type == 'approve':
            description = f"{user} 核准了 {target}"
            icon = 'bi-check-circle'
            color = 'success'
        elif activity_type == 'reject':
            description = f"{user} 拒絕了 {target}"
            icon = 'bi-x-circle'
            color = 'warning'
        elif activity_type == 'export':
            description = f"{user} 匯出了 {target} 數據"
            icon = 'bi-download'
            color = 'secondary'
            
        activities.append({
            'id': i + 1,
            'user': user,
            'description': description,
            'time': activity_time,
            'time_text': time_text,
            'icon': icon,
            'color': color
        })
        
    # 按時間排序 (最新的在前)
    activities.sort(key=lambda x: x['time'], reverse=True)
    
    return activities

def generate_sales_chart_data():
    """生成銷售圖表數據"""
    months = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月']
    
    # 銷售數據
    sales_data = []
    for i in range(12):
        base_amount = random.randint(30, 70) * 10000
        sales_data.append(base_amount)
    
    # 利潤數據 (約為銷售的30-45%)
    profit_data = []
    for sales in sales_data:
        profit_ratio = random.uniform(0.3, 0.45)
        profit_data.append(int(sales * profit_ratio))
    
    # 上年度銷售數據 (與今年相比有-10%到+15%的變化)
    last_year_sales = []
    for sales in sales_data:
        change_ratio = random.uniform(-0.1, 0.15)
        last_year_sales.append(int(sales / (1 + change_ratio)))
    
    chart_data = {
        'labels': months,
        'datasets': [
            {
                'label': '今年銷售額',
                'data': sales_data,
                'borderColor': '#4e73df',
                'backgroundColor': 'rgba(78, 115, 223, 0.05)',
                'pointBackgroundColor': '#4e73df',
                'tension': 0.3
            },
            {
                'label': '今年利潤',
                'data': profit_data,
                'borderColor': '#1cc88a',
                'backgroundColor': 'rgba(28, 200, 138, 0.05)',
                'pointBackgroundColor': '#1cc88a',
                'tension': 0.3
            },
            {
                'label': '去年銷售額',
                'data': last_year_sales,
                'borderColor': '#858796',
                'backgroundColor': 'rgba(133, 135, 150, 0.05)',
                'pointBackgroundColor': '#858796',
                'tension': 0.3,
                'borderDash': [5, 5]
            }
        ]
    }
    
    return chart_data

def generate_product_pie_chart():
    """生成產品分類佔比圖表數據"""
    categories = ['電子產品', '辦公用品', '家具', '日常用品', '其他']
    colors = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b']
    
    # 隨機生成各類別銷售佔比
    values = []
    remaining = 100
    for i in range(len(categories) - 1):
        if i == len(categories) - 2:
            # 倒數第二項，確保總和為100
            values.append(remaining)
        else:
            value = random.randint(5, remaining - 5)
            values.append(value)
            remaining -= value
    
    # 打亂順序，讓數據看起來更隨機
    combined = list(zip(categories, values, colors))
    random.shuffle(combined)
    categories, values, colors = zip(*combined)
    
    chart_data = {
        'labels': categories,
        'datasets': [{
            'data': values,
            'backgroundColor': colors,
            'hoverBackgroundColor': colors,
            'hoverBorderColor': "white"
        }]
    }
    
    return chart_data

def generate_order_status_chart():
    """生成訂單狀態圖表數據"""
    statuses = ['待處理', '處理中', '已完成', '已取消']
    colors = ['#f6c23e', '#36b9cc', '#1cc88a', '#e74a3b']
    
    # 生成訂單數據
    total_orders = random.randint(100, 300)
    
    completed = random.randint(int(total_orders * 0.4), int(total_orders * 0.6))
    processing = random.randint(int(total_orders * 0.1), int(total_orders * 0.3))
    pending = random.randint(int(total_orders * 0.1), int(total_orders * 0.2))
    cancelled = total_orders - completed - processing - pending
    
    values = [pending, processing, completed, cancelled]
    
    chart_data = {
        'labels': statuses,
        'datasets': [{
            'data': values,
            'backgroundColor': colors
        }]
    }
    
    return chart_data

def format_currency(amount):
    """格式化貨幣數值"""
    return f"NT$ {amount:,}"

def get_year_month_day():
    """獲取當前年月日"""
    now = datetime.now()
    return {
        'year': now.year,
        'month': now.month,
        'day': now.day,
        'month_name': ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月'][now.month - 1],
        'weekday': ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'][now.weekday()]
    }
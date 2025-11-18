# core/statistics_views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Q, Avg, Sum, Case, When, IntegerField, F
from django.utils import timezone
from datetime import datetime, timedelta
from .decorators import enterprise_required
from .models import (
    TestInvitation, TestInvitee, TestProject, TestProjectResult, 
    InvitationTemplate, PointTransaction
)
import json

@login_required
@enterprise_required
def statistics_dashboard(request):
    """測驗結果統計dashboard"""
    
    # 時間範圍篩選
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # 基本統計
    basic_stats = get_basic_statistics(request.user, start_date)
    
    # 圖表數據
    chart_data = get_chart_data(request.user, start_date, days)
    
    # 測驗項目統計
    project_stats = get_project_statistics(request.user, start_date)
    
    # 受測者表現統計
    invitee_stats = get_invitee_statistics(request.user, start_date)
    
    # 模板使用統計
    template_stats = get_template_statistics(request.user, start_date)
    
    context = {
        'basic_stats': basic_stats,
        'chart_data': json.dumps(chart_data),  # JSON序列化
        'project_stats': project_stats,
        'invitee_stats': invitee_stats,
        'template_stats': template_stats,
        'days': days,
    }
    
    return render(request, 'test_management/statistics_dashboard.html', context)

def get_basic_statistics(enterprise_user, start_date):
    """取得基本統計數據"""
    
    # 總邀請數
    total_invitations = TestInvitation.objects.filter(
        enterprise=enterprise_user,
        invited_at__gte=start_date
    ).order_by().count()
    
    # 完成數
    completed_invitations = TestInvitation.objects.filter(
        enterprise=enterprise_user,
        invited_at__gte=start_date,
        status='completed'
    ).order_by().count()
    
    # 進行中
    in_progress_invitations = TestInvitation.objects.filter(
        enterprise=enterprise_user,
        invited_at__gte=start_date,
        status='in_progress'
    ).order_by().count()
    
    # 過期數
    expired_invitations = TestInvitation.objects.filter(
        enterprise=enterprise_user,
        invited_at__gte=start_date,
        status='expired'
    ).order_by().count()
    
    # 完成率
    completion_rate = (completed_invitations / total_invitations * 100) if total_invitations > 0 else 0
    
    # 受測者數量
    total_invitees = TestInvitee.objects.filter(
        enterprise=enterprise_user,
        created_at__gte=start_date
    ).order_by().count()
    
    # 點數消費
    points_consumed = PointTransaction.objects.filter(
        user=enterprise_user,
        transaction_type='consumption',
        created_at__gte=start_date
    ).order_by().aggregate(total=Sum('amount'))['total'] or 0
    
    # 平均完成時間（模擬數據）
    avg_completion_time = "15.6分鐘"  # 可以根據實際數據計算
    
    return {
        'total_invitations': total_invitations,
        'completed_invitations': completed_invitations,
        'in_progress_invitations': in_progress_invitations,
        'expired_invitations': expired_invitations,
        'completion_rate': round(completion_rate, 1),
        'total_invitees': total_invitees,
        'points_consumed': abs(points_consumed),
        'avg_completion_time': avg_completion_time,
    }

def get_chart_data(enterprise_user, start_date, days):
    """取得圖表數據"""
    
    # 每日邀請趨勢
    daily_invitations = []
    daily_completions = []
    dates = []
    
    for i in range(days):
        date = start_date + timedelta(days=i)
        dates.append(date.strftime('%m/%d'))
        
        # 當日邀請數
        day_invitations = TestInvitation.objects.filter(
            enterprise=enterprise_user,
            invited_at__date=date.date()
        ).order_by().count()
        daily_invitations.append(day_invitations)
        
        # 當日完成數
        day_completions = TestInvitation.objects.filter(
            enterprise=enterprise_user,
            completed_at__date=date.date(),
            status='completed'
        ).order_by().count()
        daily_completions.append(day_completions)
    
    # 狀態分布
    status_distribution = TestInvitation.objects.filter(
        enterprise=enterprise_user,
        invited_at__gte=start_date
    ).values('status').annotate(count=Count('id')).order_by()
    
    status_labels = []
    status_data = []
    status_colors = {
        'completed': '#28a745',
        'pending': '#ffc107',
        'in_progress': '#17a2b8',
        'expired': '#dc3545',
        'cancelled': '#6c757d'
    }
    
    for item in status_distribution:
        status_labels.append({
            'completed': '已完成',
            'pending': '待執行',
            'in_progress': '進行中',
            'expired': '已過期',
            'cancelled': '已取消'
        }.get(item['status'], item['status']))
        status_data.append(item['count'])
    
    # 確保有顏色數組
    colors = []
    for item in status_distribution:
        colors.append(status_colors.get(item['status'], '#6c757d'))
    
    return {
        'daily_trend': {
            'dates': dates,
            'invitations': daily_invitations,
            'completions': daily_completions
        },
        'status_distribution': {
            'labels': status_labels,
            'data': status_data,
            'colors': colors
        }
    }

def get_project_statistics(enterprise_user, start_date):
    """取得測驗項目統計"""
    
    try:
        # 先獲取符合條件的邀請數據，然後按項目分組統計
        from django.db.models import Case, When, Value
        
        invitations = TestInvitation.objects.filter(
            enterprise=enterprise_user,
            invited_at__gte=start_date,
            test_project__isnull=False
        ).order_by()
        
        # 按測驗項目分組統計
        project_data = {}
        for invitation in invitations:
            project_id = invitation.test_project.id
            project_name = invitation.test_project.name
            
            if project_id not in project_data:
                project_data[project_id] = {
                    'name': project_name,
                    'total_invitations': 0,
                    'completed_count': 0,
                    'scores': []
                }
            
            project_data[project_id]['total_invitations'] += 1
            
            if invitation.status == 'completed':
                project_data[project_id]['completed_count'] += 1
                if invitation.score:
                    project_data[project_id]['scores'].append(invitation.score)
        
        # 轉換為統計結果
        project_stats = []
        for project_id, data in project_data.items():
            completion_rate = (data['completed_count'] / data['total_invitations'] * 100) if data['total_invitations'] > 0 else 0
            avg_score = sum(data['scores']) / len(data['scores']) if data['scores'] else 0
            
            project_stats.append({
                'name': data['name'],
                'total_invitations': data['total_invitations'],
                'completed_count': data['completed_count'],
                'completion_rate': round(completion_rate, 1),
                'avg_score': round(avg_score, 1)
            })
        
        # 按邀請數排序，取前5名
        project_stats.sort(key=lambda x: x['total_invitations'], reverse=True)
        return project_stats[:5]
        
    except Exception as e:
        return []

def get_invitee_statistics(enterprise_user, start_date):
    """取得受測者統計"""
    
    try:
        # 獲取最近的邀請記錄
        recent_invitations = TestInvitation.objects.filter(
            enterprise=enterprise_user,
            invited_at__gte=start_date
        ).order_by()
        
        # 按受測者分組統計
        invitee_data = {}
        for invitation in recent_invitations:
            invitee_id = invitation.invitee.id
            
            if invitee_id not in invitee_data:
                invitee_data[invitee_id] = {
                    'name': invitation.invitee.name,
                    'email': invitation.invitee.email,
                    'company': invitation.invitee.company,
                    'recent_invitations': 0,
                    'completed_tests': 0
                }
            
            invitee_data[invitee_id]['recent_invitations'] += 1
            
            if invitation.status == 'completed':
                invitee_data[invitee_id]['completed_tests'] += 1
        
        # 轉換為統計結果
        invitee_stats = []
        for invitee_id, data in invitee_data.items():
            completion_rate = (data['completed_tests'] / data['recent_invitations'] * 100) if data['recent_invitations'] > 0 else 0
            invitee_stats.append({
                'name': data['name'],
                'email': data['email'],
                'company': data['company'],
                'recent_invitations': data['recent_invitations'],
                'completed_tests': data['completed_tests'],
                'completion_rate': round(completion_rate, 1)
            })
        
        # 按邀請數排序，取前10名
        invitee_stats.sort(key=lambda x: x['recent_invitations'], reverse=True)
        return invitee_stats[:10]
        
    except Exception as e:
        return []

def get_template_statistics(enterprise_user, start_date):
    """取得模板使用統計"""
    
    try:
        from .models import InvitationTemplate
        
        templates = InvitationTemplate.objects.filter(
            enterprise=enterprise_user,
            is_active=True
        ).order_by('-usage_count')[:5]
        
        template_stats = []
        for template in templates:
            template_stats.append({
                'name': template.name,
                'template_type': template.get_template_type_display(),
                'usage_count': template.usage_count,
                'last_used_at': template.last_used_at,
                'is_default': template.is_default
            })
        
        return template_stats
    except Exception as e:
        # 如果模板表不存在或其他錯誤，返回空列表
        return []

@login_required
@enterprise_required
def statistics_api(request):
    """統計數據API"""
    
    data_type = request.GET.get('type')
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    if data_type == 'completion_trend':
        # 完成率趨勢
        data = get_completion_trend(request.user, start_date, days)
    elif data_type == 'score_distribution':
        # 分數分布
        data = get_score_distribution(request.user, start_date)
    elif data_type == 'project_comparison':
        # 測驗項目比較
        data = get_project_comparison(request.user, start_date)
    else:
        data = {'error': 'Invalid data type'}
    
    return JsonResponse(data)

def get_completion_trend(enterprise_user, start_date, days):
    """取得完成率趨勢"""
    
    trend_data = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        
        total = TestInvitation.objects.filter(
            enterprise=enterprise_user,
            invited_at__date=date.date()
        ).order_by().count()
        
        completed = TestInvitation.objects.filter(
            enterprise=enterprise_user,
            invited_at__date=date.date(),
            status='completed'
        ).order_by().count()
        
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        trend_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'completion_rate': round(completion_rate, 1),
            'total': total,
            'completed': completed
        })
    
    return trend_data

def get_score_distribution(enterprise_user, start_date):
    """取得分數分布"""
    
    scores = TestInvitation.objects.filter(
        enterprise=enterprise_user,
        invited_at__gte=start_date,
        status='completed',
        score__isnull=False
    ).order_by().values_list('score', flat=True)
    
    # 分數區間統計
    distribution = {
        '0-20': 0,
        '21-40': 0,
        '41-60': 0,
        '61-80': 0,
        '81-100': 0
    }
    
    for score in scores:
        if score <= 20:
            distribution['0-20'] += 1
        elif score <= 40:
            distribution['21-40'] += 1
        elif score <= 60:
            distribution['41-60'] += 1
        elif score <= 80:
            distribution['61-80'] += 1
        else:
            distribution['81-100'] += 1
    
    return {
        'labels': list(distribution.keys()),
        'data': list(distribution.values())
    }

def get_project_comparison(enterprise_user, start_date):
    """取得測驗項目比較數據"""
    
    try:
        # 獲取符合條件的邀請記錄
        invitations = TestInvitation.objects.filter(
            enterprise=enterprise_user,
            invited_at__gte=start_date,
            test_project__isnull=False
        ).order_by()
        
        # 按測驗項目分組統計
        project_data = {}
        for invitation in invitations:
            project_id = invitation.test_project.id
            project_name = invitation.test_project.name
            
            if project_id not in project_data:
                project_data[project_id] = {
                    'name': project_name,
                    'total_invitations': 0,
                    'completed_count': 0,
                    'scores': []
                }
            
            project_data[project_id]['total_invitations'] += 1
            
            if invitation.status == 'completed':
                project_data[project_id]['completed_count'] += 1
                if invitation.score:
                    project_data[project_id]['scores'].append(invitation.score)
        
        # 轉換為比較數據
        comparison_data = []
        for project_id, data in project_data.items():
            completion_rate = (data['completed_count'] / data['total_invitations'] * 100) if data['total_invitations'] > 0 else 0
            avg_score = sum(data['scores']) / len(data['scores']) if data['scores'] else 0
            
            comparison_data.append({
                'name': data['name'],
                'total_invitations': data['total_invitations'],
                'completion_rate': round(completion_rate, 1),
                'avg_score': round(avg_score, 1)
            })
        
        return comparison_data
        
    except Exception as e:
        return []
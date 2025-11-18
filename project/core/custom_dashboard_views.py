# core/custom_dashboard_views.py

from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from types import SimpleNamespace
from .models import (
    TestInvitation, TestInvitee, TestProject, TestProjectResult,
    TestProjectAssignment, InvitationTemplate, PointTransaction, UserPointBalance, Notification, User
)
from django.urls import reverse
import json

class CustomDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/custom_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 根據用戶類型顯示不同的儀表板
        if user.user_type == 'enterprise':
            context.update(self.get_enterprise_dashboard_data(user))
        elif user.user_type == 'individual':
            context.update(self.get_individual_dashboard_data(user))
        else:  # admin
            context.update(self.get_admin_dashboard_data(user))
        
        # 通用數據
        context.update({
            'user_type': user.user_type,
            'current_date': timezone.now(),
            'notifications': self.get_recent_notifications(user)
        })
        
        return context
    
    def get_enterprise_dashboard_data(self, user):
        """企業用戶儀表板數據"""
        
        # 時間範圍
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # 基本統計
        stats = {
            'total_invitations': TestInvitation.objects.filter(enterprise=user).order_by().count(),
            'total_invitees': TestInvitee.objects.filter(enterprise=user).order_by().count(),
            'completed_tests': TestInvitation.objects.filter(enterprise=user, status='completed').order_by().count(),
            'pending_tests': TestInvitation.objects.filter(enterprise=user, status='pending').order_by().count(),
        }
        
        # 完成率
        stats['completion_rate'] = (stats['completed_tests'] / stats['total_invitations'] * 100) if stats['total_invitations'] > 0 else 0
        
        # 本週統計
        week_stats = {
            'invitations': TestInvitation.objects.filter(enterprise=user, invited_at__date__gte=week_ago).order_by().count(),
            'completions': TestInvitation.objects.filter(enterprise=user, completed_at__date__gte=week_ago, status='completed').order_by().count(),
            'new_invitees': TestInvitee.objects.filter(enterprise=user, created_at__date__gte=week_ago).order_by().count(),
        }
        
        # 點數資訊
        try:
            point_balance = UserPointBalance.objects.get(user=user)
            point_info = {
                'current_balance': point_balance.balance,
                'total_consumed': point_balance.total_consumed,
                'total_earned': point_balance.total_earned,
            }
        except UserPointBalance.DoesNotExist:
            point_info = {
                'current_balance': 0,
                'total_consumed': 0,
                'total_earned': 0,
            }
        
        # 最近邀請
        recent_invitations = TestInvitation.objects.filter(
            enterprise=user
        ).order_by('-invited_at')[:5]
        
        # 活躍受測者
        active_invitees = TestInvitee.objects.filter(
            enterprise=user,
            invited_count__gt=0
        ).order_by('-invited_count')[:5]
        
        # 模板統計
        template_count = 0
        try:
            template_count = InvitationTemplate.objects.filter(enterprise=user, is_active=True).order_by().count()
        except:
            pass
        
        # 測驗項目統計
        available_projects = TestProject.get_available_projects_for_user(user).order_by().count()

        project_blocks = []
        assignments = TestProjectAssignment.objects.filter(
            enterprise_user=user,
            is_active=True
        ).select_related('test_project')

        invitation_qs = TestInvitation.objects.filter(enterprise=user)

        for assignment in assignments:
            project = assignment.test_project
            project_invitations = invitation_qs.filter(test_project=project)
            pending_count = project_invitations.filter(status__in=['pending', 'in_progress']).order_by().count()
            completed_count = project_invitations.filter(status='completed').order_by().count()

            total_slots_display = '不限' if assignment.assigned_quota == 0 else assignment.assigned_quota
            remaining_slots_display = '不限' if assignment.assigned_quota == 0 else max(assignment.assigned_quota - assignment.used_quota, 0)

            project_blocks.append({
                'id': project.id,
                'name': project.name,
                'total_slots_display': total_slots_display,
                'remaining_slots_display': remaining_slots_display,
                'used_slots': assignment.used_quota,
                'pending_count': pending_count,
                'completed_count': completed_count,
                'stats_url': reverse('enterprise_test_project_stats', args=[project.id]),
            })
        
        # 圖表數據
        chart_data = self.get_enterprise_chart_data(user)
        
        return {
            'stats': stats,
            'week_stats': week_stats,
            'point_info': point_info,
            'recent_invitations': recent_invitations,
            'active_invitees': active_invitees,
            'template_count': template_count,
            'available_projects': available_projects,
            'project_blocks': project_blocks,
            'chart_data': json.dumps(chart_data),
        }
    
    def get_individual_dashboard_data(self, user):
        """個人用戶儀表板數據"""
        
        # 個人用戶的測驗記錄（如果有的話）
        # 這裡可以根據實際需求調整
        stats = {
            'available_tests': TestProject.get_available_projects_for_user(user).order_by().count(),
            'completed_tests': 0,  # 需要根據實際業務邏輯調整
            'pending_tests': 0,
            'total_score': 0,
        }
        
        # 點數資訊
        try:
            point_balance = UserPointBalance.objects.get(user=user)
            point_info = {
                'current_balance': point_balance.balance,
                'total_consumed': point_balance.total_consumed,
                'total_earned': point_balance.total_earned,
            }
        except UserPointBalance.DoesNotExist:
            point_info = {
                'current_balance': 0,
                'total_consumed': 0,
                'total_earned': 0,
            }
        
        # 可用測驗項目
        available_projects = TestProject.get_available_projects_for_user(user)[:5]
        
        return {
            'stats': stats,
            'point_info': point_info,
            'available_projects': available_projects,
        }
    
    def get_admin_dashboard_data(self, user):
        """管理員儀表板數據"""
        
        # 系統總覽統計
        stats = {
            'total_users': User.objects.order_by().count(),
            'enterprise_users': User.objects.filter(user_type='enterprise').order_by().count(),
            'individual_users': User.objects.filter(user_type='individual').order_by().count(),
            'total_projects': TestProject.objects.order_by().count(),
            'total_invitations': TestInvitation.objects.order_by().count(),
            'total_invitees': TestInvitee.objects.order_by().count(),
        }
        
        # 本月統計
        month_start = timezone.now().replace(day=1)
        month_stats = {
            'new_users': User.objects.filter(date_joined__gte=month_start).order_by().count(),
            'new_invitations': TestInvitation.objects.filter(invited_at__gte=month_start).order_by().count(),
            'completed_tests': TestInvitation.objects.filter(completed_at__gte=month_start, status='completed').order_by().count(),
        }
        
        # 待審核企業
        pending_enterprises = User.objects.filter(
            user_type='enterprise',
            enterprise_profile__verification_status='pending'
        ).order_by().count()
        
        # 最近註冊的用戶
        recent_users = User.objects.order_by('-date_joined')[:5]
        
        # 活躍企業排行
        top_enterprise_counts = list(
            User.objects.filter(user_type='enterprise')
            .values('id')
            .annotate(invitation_count=Count('sent_invitations'))
            .order_by('-invitation_count', 'id')[:5]
        )
        enterprise_map = User.objects.filter(
            id__in=[item['id'] for item in top_enterprise_counts]
        ).in_bulk()
        active_enterprises = []
        for entry in top_enterprise_counts:
            user_obj = enterprise_map.get(entry['id'])
            if not user_obj:
                continue
            active_enterprises.append(
                SimpleNamespace(
                    id=user_obj.id,
                    username=user_obj.username,
                    email=user_obj.email,
                    invitation_count=entry['invitation_count'],
                )
            )
        
        return {
            'stats': stats,
            'month_stats': month_stats,
            'pending_enterprises': pending_enterprises,
            'recent_users': recent_users,
            'active_enterprises': active_enterprises,
        }
    
    def get_enterprise_chart_data(self, user):
        """企業用戶圖表數據"""
        
        # 近7天的邀請趨勢
        days_data = []
        invitations_data = []
        completions_data = []
        
        for i in range(7):
            date = timezone.now().date() - timedelta(days=6-i)
            days_data.append(date.strftime('%m/%d'))
            
            day_invitations = TestInvitation.objects.filter(
                enterprise=user,
                invited_at__date=date
            ).order_by().count()
            invitations_data.append(day_invitations)
            
            day_completions = TestInvitation.objects.filter(
                enterprise=user,
                completed_at__date=date,
                status='completed'
            ).order_by().count()
            completions_data.append(day_completions)
        
        # 狀態分布
        status_distribution = TestInvitation.objects.filter(
            enterprise=user
        ).order_by().values('status').annotate(count=Count('id'))
        
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
        
        return {
            'daily_trend': {
                'labels': days_data,
                'invitations': invitations_data,
                'completions': completions_data
            },
            'status_distribution': {
                'labels': status_labels,
                'data': status_data,
                'colors': [status_colors.get(item['status'], '#6c757d') for item in status_distribution]
            }
        }
    
    def get_recent_notifications(self, user):
        """取得最近通知"""
        return Notification.objects.filter(
            recipient=user,
            is_read=False
        ).order_by('-created_at')[:5]

# 兼容舊的 DashboardView
DashboardView = CustomDashboardView

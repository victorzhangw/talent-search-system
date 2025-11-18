# api/views.py
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from core.models import (
    User, TestProject, TestInvitation, TestInvitee, 
    TestProjectResult, InvitationTemplate, UserPointBalance
)
from .serializers import (
    UserSerializer, UserRegistrationSerializer, LoginSerializer,
    TestProjectSerializer, TestInvitationSerializer, TestInviteeSerializer,
    TestProjectResultSerializer, InvitationTemplateSerializer,
    UserPointBalanceSerializer, PasswordChangeSerializer, StatisticsSerializer
)
from .permissions import IsOwnerOrReadOnly, IsEnterpriseUser, IsAdminUser

class UserRegistrationView(generics.CreateAPIView):
    """用戶註冊 API"""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='5/m', method='POST'))
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class LoginView(APIView):
    """登入 API"""
    permission_classes = [AllowAny]
    
    @method_decorator(ratelimit(key='ip', rate='10/m', method='POST'))
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    """登出 API"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "成功登出"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "登出失敗"}, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(generics.RetrieveUpdateAPIView):
    """用戶資料 API"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class PasswordChangeView(APIView):
    """密碼修改 API"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"detail": "密碼修改成功"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TestProjectListView(generics.ListAPIView):
    """測驗項目列表 API"""
    serializer_class = TestProjectSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return TestProject.get_available_projects_for_user(self.request.user)

class TestProjectDetailView(generics.RetrieveAPIView):
    """測驗項目詳情 API"""
    serializer_class = TestProjectSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return TestProject.get_available_projects_for_user(self.request.user)

class TestInviteeListCreateView(generics.ListCreateAPIView):
    """受測者列表和創建 API"""
    serializer_class = TestInviteeSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseUser]
    
    def get_queryset(self):
        return TestInvitee.objects.filter(enterprise=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(enterprise=self.request.user)

class TestInviteeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """受測者詳情 API"""
    serializer_class = TestInviteeSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseUser, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        return TestInvitee.objects.filter(enterprise=self.request.user)

class TestInvitationListCreateView(generics.ListCreateAPIView):
    """測驗邀請列表和創建 API"""
    serializer_class = TestInvitationSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseUser]
    
    def get_queryset(self):
        return TestInvitation.objects.filter(enterprise=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(enterprise=self.request.user)

class TestInvitationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """測驗邀請詳情 API"""
    serializer_class = TestInvitationSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseUser, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        return TestInvitation.objects.filter(enterprise=self.request.user)

class TestResultListView(generics.ListAPIView):
    """測驗結果列表 API"""
    serializer_class = TestProjectResultSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseUser]
    
    def get_queryset(self):
        return TestProjectResult.objects.filter(
            test_invitation__enterprise=self.request.user
        )

class TestResultDetailView(generics.RetrieveAPIView):
    """測驗結果詳情 API"""
    serializer_class = TestProjectResultSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseUser]
    
    def get_queryset(self):
        return TestProjectResult.objects.filter(
            test_invitation__enterprise=self.request.user
        )

class InvitationTemplateListCreateView(generics.ListCreateAPIView):
    """邀請模板列表和創建 API"""
    serializer_class = InvitationTemplateSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseUser]
    
    def get_queryset(self):
        return InvitationTemplate.objects.filter(enterprise=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(enterprise=self.request.user)

class InvitationTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """邀請模板詳情 API"""
    serializer_class = InvitationTemplateSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseUser, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        return InvitationTemplate.objects.filter(enterprise=self.request.user)

class UserPointBalanceView(generics.RetrieveAPIView):
    """用戶點數餘額 API"""
    serializer_class = UserPointBalanceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        balance, created = UserPointBalance.objects.get_or_create(
            user=self.request.user,
            defaults={'balance': 0, 'total_earned': 0, 'total_consumed': 0}
        )
        return balance

class StatisticsView(APIView):
    """統計數據 API"""
    permission_classes = [IsAuthenticated, IsEnterpriseUser]
    
    def get(self, request):
        user = request.user
        
        # 基本統計
        stats = {
            'total_invitations': TestInvitation.objects.filter(enterprise=user).count(),
            'total_invitees': TestInvitee.objects.filter(enterprise=user).count(),
            'completed_tests': TestInvitation.objects.filter(
                enterprise=user, status='completed'
            ).count(),
            'pending_tests': TestInvitation.objects.filter(
                enterprise=user, status='pending'
            ).count(),
        }
        
        # 完成率
        stats['completion_rate'] = (
            stats['completed_tests'] / stats['total_invitations'] * 100
        ) if stats['total_invitations'] > 0 else 0
        
        # 近7天趨勢
        daily_trend = self.get_daily_trend(user)
        status_distribution = self.get_status_distribution(user)
        
        stats['daily_trend'] = daily_trend
        stats['status_distribution'] = status_distribution
        
        serializer = StatisticsSerializer(stats)
        return Response(serializer.data)
    
    def get_daily_trend(self, user):
        """獲取每日趨勢數據"""
        days_data = []
        invitations_data = []
        completions_data = []
        
        for i in range(7):
            date = timezone.now().date() - timedelta(days=6-i)
            days_data.append(date.strftime('%m/%d'))
            
            day_invitations = TestInvitation.objects.filter(
                enterprise=user,
                invited_at__date=date
            ).count()
            invitations_data.append(day_invitations)
            
            day_completions = TestInvitation.objects.filter(
                enterprise=user,
                completed_at__date=date,
                status='completed'
            ).count()
            completions_data.append(day_completions)
        
        return {
            'labels': days_data,
            'invitations': invitations_data,
            'completions': completions_data
        }
    
    def get_status_distribution(self, user):
        """獲取狀態分佈數據"""
        status_distribution = TestInvitation.objects.filter(
            enterprise=user
        ).values('status').annotate(count=Count('id'))
        
        status_labels = []
        status_data = []
        
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
            'labels': status_labels,
            'data': status_data
        }

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_health_check(request):
    """API 健康檢查"""
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now(),
        'user': request.user.username if request.user.is_authenticated else None
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_statistics(request):
    """管理員統計數據"""
    stats = {
        'total_users': User.objects.count(),
        'enterprise_users': User.objects.filter(user_type='enterprise').count(),
        'individual_users': User.objects.filter(user_type='individual').count(),
        'total_projects': TestProject.objects.count(),
        'total_invitations': TestInvitation.objects.count(),
        'total_invitees': TestInvitee.objects.count(),
    }
    return Response(stats)
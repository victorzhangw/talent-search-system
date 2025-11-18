# tests/test_api.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import (
    TestProject, TestInvitee, TestInvitation, 
    InvitationTemplate, UserPointBalance
)

User = get_user_model()

class APIAuthTest(TestCase):
    """API 認證測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.client = APIClient()
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPassword123!',
            'user_type': 'individual'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.user.is_active = True
        self.user.save()
    
    def test_user_registration(self):
        """測試用戶註冊 API"""
        response = self.client.post('/api/auth/register/', {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'NewPassword123!',
            'password_confirm': 'NewPassword123!',
            'user_type': 'individual'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_user_login(self):
        """測試用戶登入 API"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'TestPassword123!'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
    
    def test_user_login_invalid(self):
        """測試無效登入 API"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_protected_endpoint_without_token(self):
        """測試未授權訪問受保護端點"""
        response = self.client.get('/api/user/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_protected_endpoint_with_token(self):
        """測試使用 Token 訪問受保護端點"""
        # 獲取 Token
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        response = self.client.get('/api/user/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')

class APITestProjectTest(TestCase):
    """API 測試項目測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Test123!',
            user_type='individual',
            is_active=True
        )
        
        self.test_project = TestProject.objects.create(
            name='測試項目',
            test_link='https://example.com/test',
            assignment_type='all_open'
        )
        
        # 設定認證
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_get_test_projects(self):
        """測試獲取測試項目列表"""
        response = self.client.get('/api/test-projects/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], '測試項目')
    
    def test_get_test_project_detail(self):
        """測試獲取測試項目詳情"""
        response = self.client.get(f'/api/test-projects/{self.test_project.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], '測試項目')

class APIInviteeTest(TestCase):
    """API 受測者測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.client = APIClient()
        self.enterprise_user = User.objects.create_user(
            username='enterprise',
            email='enterprise@example.com',
            password='Test123!',
            user_type='enterprise',
            is_active=True
        )
        
        self.invitee = TestInvitee.objects.create(
            name='測試受測者',
            email='invitee@example.com',
            enterprise=self.enterprise_user
        )
        
        # 設定認證
        refresh = RefreshToken.for_user(self.enterprise_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_get_invitees(self):
        """測試獲取受測者列表"""
        response = self.client.get('/api/invitees/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], '測試受測者')
    
    def test_create_invitee(self):
        """測試創建受測者"""
        response = self.client.post('/api/invitees/', {
            'name': '新受測者',
            'email': 'new@example.com',
            'phone': '0912345678',
            'department': '測試部門',
            'position': '測試職位'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(TestInvitee.objects.filter(email='new@example.com').exists())
    
    def test_update_invitee(self):
        """測試更新受測者"""
        response = self.client.put(f'/api/invitees/{self.invitee.id}/', {
            'name': '更新受測者',
            'email': 'updated@example.com',
            'phone': '0912345678',
            'department': '更新部門',
            'position': '更新職位'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.invitee.refresh_from_db()
        self.assertEqual(self.invitee.name, '更新受測者')
    
    def test_delete_invitee(self):
        """測試刪除受測者"""
        response = self.client.delete(f'/api/invitees/{self.invitee.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TestInvitee.objects.filter(id=self.invitee.id).exists())

class APIInvitationTest(TestCase):
    """API 測試邀請測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.client = APIClient()
        self.enterprise_user = User.objects.create_user(
            username='enterprise',
            email='enterprise@example.com',
            password='Test123!',
            user_type='enterprise',
            is_active=True
        )
        
        self.test_project = TestProject.objects.create(
            name='測試項目',
            test_link='https://example.com/test',
            assignment_type='all_open'
        )
        
        self.invitee = TestInvitee.objects.create(
            name='測試受測者',
            email='invitee@example.com',
            enterprise=self.enterprise_user
        )
        
        # 設定認證
        refresh = RefreshToken.for_user(self.enterprise_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_create_invitation(self):
        """測試創建邀請"""
        response = self.client.post('/api/invitations/', {
            'invitee_id': self.invitee.id,
            'test_project_id': self.test_project.id,
            'custom_message': '請完成測試',
            'expires_at': '2024-12-31T23:59:59Z'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(TestInvitation.objects.filter(
            invitee=self.invitee,
            test_project=self.test_project
        ).exists())
    
    def test_get_invitations(self):
        """測試獲取邀請列表"""
        # 創建測試邀請
        TestInvitation.objects.create(
            enterprise=self.enterprise_user,
            test_project=self.test_project,
            invitee=self.invitee,
            custom_message='測試訊息'
        )
        
        response = self.client.get('/api/invitations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

class APIStatisticsTest(TestCase):
    """API 統計測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.client = APIClient()
        self.enterprise_user = User.objects.create_user(
            username='enterprise',
            email='enterprise@example.com',
            password='Test123!',
            user_type='enterprise',
            is_active=True
        )
        
        self.test_project = TestProject.objects.create(
            name='測試項目',
            test_link='https://example.com/test',
            assignment_type='all_open'
        )
        
        self.invitee = TestInvitee.objects.create(
            name='測試受測者',
            email='invitee@example.com',
            enterprise=self.enterprise_user
        )
        
        # 創建測試邀請
        TestInvitation.objects.create(
            enterprise=self.enterprise_user,
            test_project=self.test_project,
            invitee=self.invitee,
            status='completed'
        )
        
        # 設定認證
        refresh = RefreshToken.for_user(self.enterprise_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_get_statistics(self):
        """測試獲取統計數據"""
        response = self.client.get('/api/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        self.assertIn('total_invitations', data)
        self.assertIn('completed_tests', data)
        self.assertIn('completion_rate', data)
        self.assertIn('daily_trend', data)
        self.assertIn('status_distribution', data)
        
        self.assertEqual(data['total_invitations'], 1)
        self.assertEqual(data['completed_tests'], 1)
        self.assertEqual(data['completion_rate'], 100.0)

class APIHealthCheckTest(TestCase):
    """API 健康檢查測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Test123!',
            user_type='individual',
            is_active=True
        )
        
        # 設定認證
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_health_check(self):
        """測試健康檢查"""
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
        self.assertIn('timestamp', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['status'], 'healthy')
        self.assertEqual(response.data['user'], 'testuser')
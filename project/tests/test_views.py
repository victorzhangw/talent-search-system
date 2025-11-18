# tests/test_views.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import json

from core.models import (
    TestProject, TestInvitee, TestInvitation, 
    InvitationTemplate, UserPointBalance
)

User = get_user_model()

class AuthViewsTest(TestCase):
    """認證視圖測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.client = Client()
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPassword123!',
            'user_type': 'individual'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.user.is_active = True
        self.user.save()
    
    def test_login_view_get(self):
        """測試登入頁面 GET 請求"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '登入')
    
    def test_login_view_post_valid(self):
        """測試有效登入"""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'TestPassword123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))
    
    def test_login_view_post_invalid(self):
        """測試無效登入"""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '帳號或密碼錯誤')
    
    def test_logout_view(self):
        """測試登出"""
        self.client.login(username='testuser', password='TestPassword123!')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))

class DashboardViewTest(TestCase):
    """儀表板視圖測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.client = Client()
        self.enterprise_user = User.objects.create_user(
            username='enterprise',
            email='enterprise@example.com',
            password='Test123!',
            user_type='enterprise',
            is_active=True
        )
        
        self.individual_user = User.objects.create_user(
            username='individual',
            email='individual@example.com',
            password='Test123!',
            user_type='individual',
            is_active=True
        )
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='Test123!',
            user_type='admin',
            is_active=True,
            is_staff=True
        )
    
    def test_dashboard_requires_login(self):
        """測試儀表板需要登入"""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/login/?next=/dashboard/')
    
    def test_enterprise_dashboard(self):
        """測試企業用戶儀表板"""
        self.client.login(username='enterprise', password='Test123!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '企業用戶儀表板')
    
    def test_individual_dashboard(self):
        """測試個人用戶儀表板"""
        self.client.login(username='individual', password='Test123!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '個人用戶儀表板')
    
    def test_admin_dashboard(self):
        """測試管理員儀表板"""
        self.client.login(username='admin', password='Test123!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '管理員儀表板')

class EnterpriseViewsTest(TestCase):
    """企業功能視圖測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.client = Client()
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
    
    def test_invitee_list_requires_enterprise_user(self):
        """測試受測者列表需要企業用戶"""
        # 未登入
        response = self.client.get(reverse('invitee_list'))
        self.assertEqual(response.status_code, 302)
        
        # 個人用戶
        individual_user = User.objects.create_user(
            username='individual',
            email='individual@example.com',
            password='Test123!',
            user_type='individual',
            is_active=True
        )
        self.client.login(username='individual', password='Test123!')
        response = self.client.get(reverse('invitee_list'))
        self.assertEqual(response.status_code, 302)
    
    def test_invitee_list_for_enterprise(self):
        """測試企業用戶受測者列表"""
        self.client.login(username='enterprise', password='Test123!')
        response = self.client.get(reverse('invitee_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '測試受測者')
    
    def test_create_invitee(self):
        """測試創建受測者"""
        self.client.login(username='enterprise', password='Test123!')
        response = self.client.post(reverse('create_invitee'), {
            'name': '新受測者',
            'email': 'new@example.com',
            'phone': '0912345678',
            'department': '測試部門',
            'position': '測試職位'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TestInvitee.objects.filter(email='new@example.com').exists())
    
    def test_invitation_list(self):
        """測試邀請列表"""
        # 創建測試邀請
        TestInvitation.objects.create(
            enterprise=self.enterprise_user,
            test_project=self.test_project,
            invitee=self.invitee,
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        self.client.login(username='enterprise', password='Test123!')
        response = self.client.get(reverse('invitation_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '測試項目')
        self.assertContains(response, '測試受測者')

class InvitationTemplateViewsTest(TestCase):
    """邀請模板視圖測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.client = Client()
        self.enterprise_user = User.objects.create_user(
            username='enterprise',
            email='enterprise@example.com',
            password='Test123!',
            user_type='enterprise',
            is_active=True
        )
        
        self.template = InvitationTemplate.objects.create(
            enterprise=self.enterprise_user,
            name='測試模板',
            template_type='general',
            subject='測試主題',
            message='測試訊息'
        )
    
    def test_template_list(self):
        """測試模板列表"""
        self.client.login(username='enterprise', password='Test123!')
        response = self.client.get(reverse('invitation_template_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '測試模板')
    
    def test_create_template(self):
        """測試創建模板"""
        self.client.login(username='enterprise', password='Test123!')
        response = self.client.post(reverse('invitation_template_create'), {
            'name': '新模板',
            'template_type': 'general',
            'subject': '新主題',
            'message': '新訊息'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(InvitationTemplate.objects.filter(name='新模板').exists())
    
    def test_edit_template(self):
        """測試編輯模板"""
        self.client.login(username='enterprise', password='Test123!')
        response = self.client.post(reverse('invitation_template_edit', args=[self.template.id]), {
            'name': '編輯後模板',
            'template_type': 'general',
            'subject': '編輯後主題',
            'message': '編輯後訊息'
        })
        self.assertEqual(response.status_code, 302)
        
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, '編輯後模板')
    
    def test_delete_template(self):
        """測試刪除模板"""
        self.client.login(username='enterprise', password='Test123!')
        response = self.client.post(reverse('invitation_template_delete', args=[self.template.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(InvitationTemplate.objects.filter(id=self.template.id).exists())

class StatisticsViewsTest(TestCase):
    """統計視圖測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.client = Client()
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
            status='completed',
            expires_at=timezone.now() + timedelta(days=7)
        )
    
    def test_statistics_dashboard(self):
        """測試統計儀表板"""
        self.client.login(username='enterprise', password='Test123!')
        response = self.client.get(reverse('statistics_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '統計分析')
    
    def test_statistics_api(self):
        """測試統計 API"""
        self.client.login(username='enterprise', password='Test123!')
        response = self.client.get(reverse('statistics_api'))
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('total_invitations', data)
        self.assertIn('completed_tests', data)
        self.assertEqual(data['total_invitations'], 1)
        self.assertEqual(data['completed_tests'], 1)
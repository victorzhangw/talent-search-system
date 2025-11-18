# tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta

from core.models import (
    User, TestProject, TestInvitee, TestInvitation, 
    TestProjectResult, InvitationTemplate, UserPointBalance
)

User = get_user_model()

class UserModelTest(TestCase):
    """用戶模型測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPassword123!',
            'user_type': 'individual'
        }
    
    def test_create_user(self):
        """測試創建用戶"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.user_type, 'individual')
        self.assertFalse(user.is_email_verified)
        self.assertFalse(user.is_active)
    
    def test_create_superuser(self):
        """測試創建超級用戶"""
        admin_data = {
            'username': 'admin',
            'email': 'admin@example.com',
            'password': 'AdminPassword123!'
        }
        admin = User.objects.create_superuser(**admin_data)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.user_type, 'admin')
        self.assertTrue(admin.is_email_verified)
        self.assertTrue(admin.is_active)
    
    def test_user_string_representation(self):
        """測試用戶字符串表示"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), 'testuser')
    
    def test_unique_email(self):
        """測試電子郵件唯一性"""
        User.objects.create_user(**self.user_data)
        
        # 嘗試創建相同電子郵件的用戶
        duplicate_data = self.user_data.copy()
        duplicate_data['username'] = 'testuser2'
        
        with self.assertRaises(IntegrityError):
            User.objects.create_user(**duplicate_data)

class TestProjectModelTest(TestCase):
    """測試項目模型測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.project_data = {
            'name': '測試項目',
            'description': '這是一個測試項目',
            'test_link': 'https://example.com/test',
            'score_field': 'total_score',
            'prediction_field': 'prediction',
            'is_active': True
        }
    
    def test_create_test_project(self):
        """測試創建測試項目"""
        project = TestProject.objects.create(**self.project_data)
        self.assertEqual(project.name, '測試項目')
        self.assertEqual(project.description, '這是一個測試項目')
        self.assertTrue(project.is_active)
        self.assertIsNotNone(project.created_at)
        self.assertIsNotNone(project.updated_at)
    
    def test_test_project_string_representation(self):
        """測試測試項目字符串表示"""
        project = TestProject.objects.create(**self.project_data)
        self.assertEqual(str(project), '測試項目')
    
    def test_get_available_projects_for_user(self):
        """測試獲取用戶可用的測試項目"""
        # 創建測試項目
        project1 = TestProject.objects.create(
            name='開放項目',
            test_link='https://example.com/test1',
            assignment_type='all_open'
        )
        project2 = TestProject.objects.create(
            name='企業項目',
            test_link='https://example.com/test2',
            assignment_type='enterprise_only'
        )
        project3 = TestProject.objects.create(
            name='個人項目',
            test_link='https://example.com/test3',
            assignment_type='individual_only'
        )
        
        # 創建用戶
        enterprise_user = User.objects.create_user(
            username='enterprise',
            email='enterprise@example.com',
            password='Test123!',
            user_type='enterprise'
        )
        
        individual_user = User.objects.create_user(
            username='individual',
            email='individual@example.com',
            password='Test123!',
            user_type='individual'
        )
        
        # 測試企業用戶可用項目
        enterprise_projects = TestProject.get_available_projects_for_user(enterprise_user)
        self.assertIn(project1, enterprise_projects)
        self.assertIn(project2, enterprise_projects)
        self.assertNotIn(project3, enterprise_projects)
        
        # 測試個人用戶可用項目
        individual_projects = TestProject.get_available_projects_for_user(individual_user)
        self.assertIn(project1, individual_projects)
        self.assertNotIn(project2, individual_projects)
        self.assertIn(project3, individual_projects)

class TestInviteeModelTest(TestCase):
    """受測者模型測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.enterprise_user = User.objects.create_user(
            username='enterprise',
            email='enterprise@example.com',
            password='Test123!',
            user_type='enterprise'
        )
        
        self.invitee_data = {
            'name': '測試受測者',
            'email': 'invitee@example.com',
            'phone': '0912345678',
            'department': '測試部門',
            'position': '測試職位',
            'enterprise': self.enterprise_user
        }
    
    def test_create_test_invitee(self):
        """測試創建受測者"""
        invitee = TestInvitee.objects.create(**self.invitee_data)
        self.assertEqual(invitee.name, '測試受測者')
        self.assertEqual(invitee.email, 'invitee@example.com')
        self.assertEqual(invitee.enterprise, self.enterprise_user)
        self.assertEqual(invitee.invited_count, 0)
    
    def test_test_invitee_string_representation(self):
        """測試受測者字符串表示"""
        invitee = TestInvitee.objects.create(**self.invitee_data)
        self.assertEqual(str(invitee), '測試受測者 (invitee@example.com)')

class TestInvitationModelTest(TestCase):
    """測試邀請模型測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.enterprise_user = User.objects.create_user(
            username='enterprise',
            email='enterprise@example.com',
            password='Test123!',
            user_type='enterprise'
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
    
    def test_create_test_invitation(self):
        """測試創建測試邀請"""
        invitation = TestInvitation.objects.create(
            enterprise=self.enterprise_user,
            test_project=self.test_project,
            invitee=self.invitee,
            custom_message='請完成測試',
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        self.assertEqual(invitation.enterprise, self.enterprise_user)
        self.assertEqual(invitation.test_project, self.test_project)
        self.assertEqual(invitation.invitee, self.invitee)
        self.assertEqual(invitation.status, 'pending')
        self.assertIsNotNone(invitation.invitation_code)
    
    def test_invitation_string_representation(self):
        """測試邀請字符串表示"""
        invitation = TestInvitation.objects.create(
            enterprise=self.enterprise_user,
            test_project=self.test_project,
            invitee=self.invitee,
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        expected_str = f"測試項目 -> 測試受測者 ({invitation.get_status_display()})"
        self.assertEqual(str(invitation), expected_str)
    
    def test_invitation_is_expired(self):
        """測試邀請過期檢查"""
        # 創建已過期的邀請
        expired_invitation = TestInvitation.objects.create(
            enterprise=self.enterprise_user,
            test_project=self.test_project,
            invitee=self.invitee,
            expires_at=timezone.now() - timedelta(days=1)
        )
        
        # 創建未過期的邀請
        valid_invitation = TestInvitation.objects.create(
            enterprise=self.enterprise_user,
            test_project=self.test_project,
            invitee=self.invitee,
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        self.assertTrue(expired_invitation.is_expired())
        self.assertFalse(valid_invitation.is_expired())

class InvitationTemplateModelTest(TestCase):
    """邀請模板模型測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.enterprise_user = User.objects.create_user(
            username='enterprise',
            email='enterprise@example.com',
            password='Test123!',
            user_type='enterprise'
        )
    
    def test_create_invitation_template(self):
        """測試創建邀請模板"""
        template = InvitationTemplate.objects.create(
            enterprise=self.enterprise_user,
            name='測試模板',
            template_type='general',
            subject='測試主題',
            message='親愛的 {{invitee_name}}，請完成測試',
            is_active=True
        )
        
        self.assertEqual(template.name, '測試模板')
        self.assertEqual(template.template_type, 'general')
        self.assertEqual(template.usage_count, 0)
        self.assertTrue(template.is_active)
    
    def test_template_string_representation(self):
        """測試模板字符串表示"""
        template = InvitationTemplate.objects.create(
            enterprise=self.enterprise_user,
            name='測試模板',
            template_type='general',
            subject='測試主題',
            message='測試訊息'
        )
        
        self.assertEqual(str(template), '測試模板 (general)')

class UserPointBalanceModelTest(TestCase):
    """用戶點數餘額模型測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Test123!',
            user_type='enterprise'
        )
    
    def test_create_point_balance(self):
        """測試創建點數餘額"""
        balance = UserPointBalance.objects.create(
            user=self.user,
            balance=1000,
            total_earned=1000,
            total_consumed=0
        )
        
        self.assertEqual(balance.user, self.user)
        self.assertEqual(balance.balance, 1000)
        self.assertEqual(balance.total_earned, 1000)
        self.assertEqual(balance.total_consumed, 0)
    
    def test_point_balance_string_representation(self):
        """測試點數餘額字符串表示"""
        balance = UserPointBalance.objects.create(
            user=self.user,
            balance=1000
        )
        
        expected_str = f"testuser - 1000 點"
        self.assertEqual(str(balance), expected_str)
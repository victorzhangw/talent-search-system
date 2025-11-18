# core/invitation_forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from .models import TestInvitation, TestInvitee, TestProject
import re

class TestInvitationForm(forms.Form):
    """測驗邀請表單"""
    
    # 受測人員選擇（多選）
    invitees = forms.ModelMultipleChoiceField(
        queryset=TestInvitee.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='選擇受測人員',
        help_text='請選擇要邀請的受測人員'
    )
    
    # 過期時間設定
    expires_in_days = forms.ChoiceField(
        choices=[
            (7, '7 天後'),
            (14, '14 天後'),
            (30, '30 天後'),
            (60, '60 天後'),
            (90, '90 天後'),
            ('custom', '自訂時間'),
        ],
        initial=14,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='邀請有效期限'
    )
    
    # 自訂過期時間
    custom_expires_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        label='自訂過期時間'
    )
    
    # 自訂邀請訊息
    custom_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': '輸入自訂邀請訊息（選填）'
        }),
        label='自訂邀請訊息',
        max_length=1000,
        help_text='可以在邀請郵件中加入特殊說明或注意事項'
    )
    
    # 立即發送選項
    send_immediately = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='立即發送邀請郵件'
    )

    def __init__(self, enterprise_user=None, test_project=None, *args, **kwargs):
        self.enterprise_user = enterprise_user
        self.test_project = test_project
        super().__init__(*args, **kwargs)
        
        # 設定受測人員查詢集
        if enterprise_user:
            queryset = TestInvitee.objects.filter(enterprise=enterprise_user).order_by('name')
            self.fields['invitees'].queryset = queryset

            # Debug 輸出
            print(f"設定受測人員查詢集，企業: {enterprise_user}, 數量: {queryset.count()}")
        
    def clean_invitees(self):
        """驗證受測人員選擇"""
        invitees = self.cleaned_data.get('invitees')
        
        if not invitees:
            raise ValidationError('請至少選擇一位受測人員')
        
        # 檢查是否已有進行中的邀請
        if self.test_project:
            existing_invitations = TestInvitation.objects.filter(
                test_project=self.test_project,
                invitee__in=invitees,
                status__in=['pending', 'in_progress']
            ).select_related('invitee')
            
            if existing_invitations.exists():
                existing_names = [inv.invitee.name for inv in existing_invitations[:3]]
                error_msg = f"以下受測人員已有進行中的邀請：{', '.join(existing_names)}"
                if existing_invitations.count() > 3:
                    error_msg += f" 等 {existing_invitations.count()} 人"
                raise ValidationError(error_msg)
        
        return invitees
    
    def clean(self):
        """表單整體驗證"""
        cleaned_data = super().clean()
        expires_in_days = cleaned_data.get('expires_in_days')
        custom_expires_at = cleaned_data.get('custom_expires_at')
        
        # 計算過期時間
        if expires_in_days == 'custom':
            if not custom_expires_at:
                self.add_error('custom_expires_at', '請設定自訂過期時間')
            elif custom_expires_at <= timezone.now():
                self.add_error('custom_expires_at', '過期時間必須是未來時間')
            else:
                cleaned_data['expires_at'] = custom_expires_at
        else:
            try:
                days = int(expires_in_days)
                cleaned_data['expires_at'] = timezone.now() + timedelta(days=days)
            except (ValueError, TypeError):
                self.add_error('expires_in_days', '無效的過期時間設定')
        
        return cleaned_data

class BulkInvitationForm(forms.Form):
    """批量邀請表單（從測驗項目頁面發起）"""
    
    # 測驗項目（隱藏欄位，從URL傳入）
    test_project = forms.ModelChoiceField(
        queryset=TestProject.objects.all(),
        widget=forms.HiddenInput()
    )
    
    # 受測人員搜尋
    search_invitees = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '搜尋受測人員姓名或email...',
            'onkeyup': 'filterInvitees()'
        }),
        label='搜尋受測人員'
    )
    
    # 全選/取消全選
    select_all = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'onchange': 'toggleSelectAll()'
        }),
        label='全選'
    )
    
    # 過期時間（簡化版）
    expires_in_days = forms.ChoiceField(
        choices=[
            (7, '7 天'),
            (14, '14 天'),
            (30, '30 天'),
            (60, '60 天'),
        ],
        initial=14,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        }),
        label='邀請有效期'
    )
    
    # 自訂訊息
    custom_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '可加入特殊說明（選填）'
        }),
        label='邀請訊息',
        max_length=500
    )

    def __init__(self, enterprise_user=None, *args, **kwargs):
        self.enterprise_user = enterprise_user
        super().__init__(*args, **kwargs)
        
        # 限制測驗項目選擇範圍
        if enterprise_user:
            self.fields['test_project'].queryset = TestProject.get_available_projects_for_user(enterprise_user)

class QuickInvitationForm(forms.Form):
    """快速邀請表單（新增受測人員並立即邀請）"""
    
    # 受測人員資訊
    name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入姓名'
        }),
        label='姓名'
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入電子郵件'
        }),
        label='電子郵件'
    )
    
    phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入聯絡電話（選填）'
        }),
        label='聯絡電話'
    )
    
    position = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '請輸入職位（選填）'
        }),
        label='職位'
    )
    
    # 邀請設定
    expires_in_days = forms.ChoiceField(
        choices=[
            (7, '7 天後'),
            (14, '14 天後'),
            (30, '30 天後'),
            (60, '60 天後'),
            (90, '90 天後'),
            ('custom', '自訂時間'),
        ],
        initial=14,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='邀請有效期'
    )
    
    # 自訂過期時間
    custom_expires_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        label='自訂過期時間'
    )
    
    custom_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': '邀請訊息（選填）'
        }),
        label='邀請訊息',
        max_length=300
    )

    def __init__(self, enterprise_user=None, test_project=None, *args, **kwargs):
        self.enterprise_user = enterprise_user
        self.test_project = test_project
        super().__init__(*args, **kwargs)

    def clean_email(self):
        """驗證電子郵件是否已存在"""
        email = self.cleaned_data.get('email')
        
        if self.enterprise_user and email:
            existing_invitee = TestInvitee.objects.filter(
                enterprise=self.enterprise_user,
                email=email
            ).first()
            
            if existing_invitee:
                # 檢查是否已有進行中的邀請
                if self.test_project:
                    existing_invitation = TestInvitation.objects.filter(
                        test_project=self.test_project,
                        invitee=existing_invitee,
                        status__in=['pending', 'in_progress']
                    ).exists()
                    
                    if existing_invitation:
                        raise ValidationError(f'「{existing_invitee.name}」已有此測驗的進行中邀請')
                
                # 如果受測人員存在但沒有進行中邀請，可以繼續
                self.existing_invitee = existing_invitee
            
        return email

    def clean(self):
        """表單整體驗證"""
        cleaned_data = super().clean()
        expires_in_days = cleaned_data.get('expires_in_days')
        custom_expires_at = cleaned_data.get('custom_expires_at')
        
        # 計算過期時間
        if expires_in_days == 'custom':
            if not custom_expires_at:
                self.add_error('custom_expires_at', '請設定自訂過期時間')
            elif custom_expires_at <= timezone.now():
                self.add_error('custom_expires_at', '過期時間必須是未來時間')
            else:
                cleaned_data['expires_at'] = custom_expires_at
        else:
            try:
                days = int(expires_in_days)
                cleaned_data['expires_at'] = timezone.now() + timedelta(days=days)
            except (ValueError, TypeError):
                self.add_error('expires_in_days', '無效的過期時間設定')
        
        return cleaned_data
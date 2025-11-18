# core/invitee_forms.py

from django import forms
from django.core.exceptions import ValidationError
from .models import TestInvitee
import re

class TestInviteeForm(forms.ModelForm):
    """新增/編輯受測人員表單"""
    
    class Meta:
        model = TestInvitee
        fields = ['name', 'email', 'phone', 'status', 'position', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入姓名',
                'maxlength': '50'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入電子郵件',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入聯絡電話（選填）',
                'maxlength': '20'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'position': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入職位（選填）',
                'maxlength': '50'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '備註（選填）',
                'rows': 3,
                'maxlength': '500'
            }),
        }
        labels = {
            'name': '姓名',
            'email': '電子郵件',
            'phone': '聯絡電話',
            'status': '狀態',
            'position': '職位',
            'notes': '備註',
        }

    def __init__(self, enterprise_user=None, *args, **kwargs):
        self.enterprise_user = enterprise_user
        super().__init__(*args, **kwargs)
        
        # 設定必填欄位的標記
        self.fields['name'].required = True
        self.fields['email'].required = True
        
        # 為必填欄位加上紅色星號
        for field_name in ['name', 'email']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['required'] = True

    def clean_email(self):
        """驗證電子郵件"""
        email = self.cleaned_data.get('email')
        if not email:
            return email
            
        # 檢查同一企業內是否有重複的email
        if self.enterprise_user:
            existing_invitee = TestInvitee.objects.filter(
                enterprise=self.enterprise_user,
                email=email
            )
            
            # 如果是編輯模式，排除當前記錄
            if self.instance and self.instance.pk:
                existing_invitee = existing_invitee.exclude(pk=self.instance.pk)
            
            if existing_invitee.exists():
                raise ValidationError('此電子郵件已存在於您的受測人員名單中')
        
        return email

    def clean_phone(self):
        """驗證聯絡電話"""
        phone = self.cleaned_data.get('phone')
        if not phone:
            return phone
            
        # 移除空格和連字符
        phone = re.sub(r'[\s\-]', '', phone)
        
        # 台灣手機號碼：09開頭，10位數字
        # 台灣市話：0開頭，9-10位數字
        if not re.match(r'^(09\d{8}|0[2-8]\d{7,8})$', phone):
            raise ValidationError('請輸入有效的台灣電話號碼格式')
        
        return phone

    def clean_name(self):
        """驗證姓名"""
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError('姓名為必填欄位')
            
        # 移除前後空白
        name = name.strip()
        
        if len(name) < 2:
            raise ValidationError('姓名至少需要2個字元')
            
        return name

    def save(self, commit=True):
        invitee = super().save(commit=False)
        
        # 設定企業
        if self.enterprise_user:
            invitee.enterprise = self.enterprise_user
            
        if commit:
            invitee.save()
            
        return invitee
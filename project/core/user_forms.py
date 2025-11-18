from django import forms
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import ValidationError
from .models import User, IndividualProfile, EnterpriseProfile

class IndividualProfileForm(forms.ModelForm):
    """個人用戶資料表單"""
    class Meta:
        model = IndividualProfile
        fields = ['real_name', 'id_number', 'birth_date', 'test_platform_username', 'test_platform_password']
        widgets = {
            'real_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入真實姓名'
            }),
            'id_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入身分證字號（選填）'
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'test_platform_username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '測驗平台帳號（選填）'
            }),
            'test_platform_password': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': '測驗平台密碼（留空保持不變）'
            }),
        }
    
    def clean_test_platform_password(self):
        """處理測驗平台密碼欄位，如果為空則保持原值"""
        password = self.cleaned_data.get('test_platform_password')
        
        # 如果密碼欄位為空且實例已存在，保持原有密碼
        if not password and self.instance and self.instance.pk:
            return self.instance.test_platform_password
        
        return password

class EnterpriseProfileForm(forms.ModelForm):
    """企業用戶資料表單"""
    class Meta:
        model = EnterpriseProfile
        fields = ['company_name', 'contact_person', 'contact_phone', 'address']
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入公司名稱'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入聯絡人姓名'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入聯絡電話'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '請輸入公司地址'
            }),
        }

class UserBasicInfoForm(forms.ModelForm):
    """用戶基本資料表單"""
    class Meta:
        model = User
        fields = ['username', 'email', 'phone']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True  # 用戶名不允許修改
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入電子郵件'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入聯絡電話'
            }),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # 檢查是否有其他用戶使用此 email（排除自己）
        if User.objects.filter(email=email).exclude(id=self.instance.id).exists():
            raise ValidationError('此電子郵件已被其他用戶使用')
        return email

class CustomPasswordChangeForm(SetPasswordForm):
    """自定義密碼修改表單（不需輸入舊密碼）"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '請輸入新密碼'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '請再次輸入新密碼'
        })

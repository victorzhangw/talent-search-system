from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
import re
from .models import User, IndividualProfile, EnterpriseProfile

class IndividualRegistrationForm(UserCreationForm):
    """個人用戶註冊表單"""
    real_name = forms.CharField(
        max_length=50,
        label='真實姓名 *',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '請輸入真實姓名'})
    )
    email = forms.EmailField(
        label='電子郵件 *',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '請輸入電子郵件'})
    )
    phone = forms.CharField(
        max_length=20,
        label='聯絡電話',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '請輸入聯絡電話'})
    )

    class Meta:
        model = User
        fields = ('username', 'real_name', 'email', 'phone', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = '用戶名 *'
        self.fields['password1'].label = '密碼 *'
        self.fields['password2'].label = '確認密碼 *'
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': '請輸入用戶名'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': '請輸入密碼'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': '請再次輸入密碼'})

    def clean_username(self):
        username = self.cleaned_data.get('username')
        # 檢查使用者名稱字元是否合法
        if not re.match(r'^[a-zA-Z0-9@.+\-_]+$', username):
            raise ValidationError('輸入合法的使用者名稱．只能包含字母、數字和@/./+/-/_字元')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('此電子郵件已被註冊')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data.get('phone')
        user.user_type = 'individual'
        user.is_active = False  # 需要Email驗證
        
        if commit:
            user.save()
            # 建立個人資料
            IndividualProfile.objects.create(
                user=user,
                real_name=self.cleaned_data['real_name']
            )
        return user

class EnterpriseRegistrationForm(UserCreationForm):
    """企業用戶註冊表單"""
    tax_id = forms.CharField(
        max_length=8,
        label='統一編號 *',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '請輸入8位統一編號',
            'id': 'id_tax_id'
        })
    )
    company_name = forms.CharField(
        max_length=100,
        label='公司名稱 *',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'readonly': False,
            'id': 'id_company_name'
        })
    )
    contact_person = forms.CharField(
        max_length=50,
        label='聯絡人姓名 *',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '請輸入中文姓名'})
    )
    contact_phone = forms.CharField(
        max_length=20,
        label='聯絡電話 *',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        label='登入信箱 *',
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        error_messages={
            'invalid': '請輸入正確、可聯繫的Email，以利報告與通知收發',
            'required': '登入信箱為必填欄位'
        }
    )

    class Meta:
        model = User
        fields = ('username', 'tax_id', 'company_name', 'contact_person', 'contact_phone', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 調整使用者名稱欄位為隱藏並於驗證階段自動帶入
        self.fields['username'].required = False
        self.fields['username'].widget = forms.HiddenInput()
        self.fields['password1'].label = '密碼 *'
        self.fields['password2'].label = '密碼確認 *'
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

        # 移除不必要的 placeholder（統一編號、聯絡人姓名除外）
        self.fields['company_name'].widget.attrs.pop('placeholder', None)

    def clean_username(self):
        email = self.cleaned_data.get('email') or self.data.get('email')
        if not email:
            raise ValidationError('請先輸入登入信箱')

        base_username = email.split('@')[0]
        # 轉換為合法使用者名稱字元
        base_username = re.sub(r'[^a-zA-Z0-9@.+\-_]', '_', base_username).strip('_') or 'user'
        base_username = base_username[:150]

        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            suffix = f"_{counter}"
            username = f"{base_username[:150-len(suffix)]}{suffix}"
            counter += 1

        self.cleaned_data['username'] = username
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # 檢查是否已被註冊
        if User.objects.filter(email=email).exists():
            raise ValidationError('此電子郵件已被註冊')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.user_type = 'enterprise'
        user.is_active = False  # 需要Email驗證和企業審核
        
        if commit:
            user.save()
            # 建立企業資料
            EnterpriseProfile.objects.create(
                user=user,
                company_name=self.cleaned_data['company_name'],
                tax_id=self.cleaned_data['tax_id'],
                contact_person=self.cleaned_data['contact_person'],
                contact_phone=self.cleaned_data['contact_phone']
            )
        return user
class EmailAuthenticationForm(AuthenticationForm):
    """使用 Email 作為登入憑證的表單"""
    username = forms.EmailField(
        label='電子郵件',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '請輸入電子郵件', 'autofocus': True})
    )

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if email and password:
            try:
                user = User.objects.get(email__iexact=email)
                username = user.get_username()
            except User.DoesNotExist:
                username = None

            if username:
                self.user_cache = authenticate(self.request, username=username, password=password)
                self.cleaned_data['login_email'] = email
                self.cleaned_data['username'] = username
            else:
                self.user_cache = None

            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

from django import forms
from django.utils import timezone

from .models import EnterprisePurchaseRecord, TestProject, User


class EnterprisePurchaseRecordForm(forms.ModelForm):
    quantity = forms.IntegerField(
        min_value=1,
        label='購買份數',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '輸入正整數'})
    )
    payment_date = forms.DateTimeField(
        label='付款日期',
        input_formats=['%Y-%m-%d %H:%M:%S'],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'yyyy-mm-dd HH:MM:SS'})
    )
    payment_method = forms.ChoiceField(
        label='付款方式',
        choices=[('', '---'), *EnterprisePurchaseRecord.PAYMENT_METHOD_CHOICES],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = EnterprisePurchaseRecord
        fields = [
            'enterprise_user',
            'test_project',
            'order_number',
            'quantity',
            'payment_date',
            'payment_method',
            'payment_amount',
            'invoice_number',
            'invoice_random_code',
            'invoice_info',
            'coupon_code',
            'notes',
        ]
        widgets = {
            'enterprise_user': forms.Select(attrs={'class': 'form-select'}),
            'test_project': forms.Select(attrs={'class': 'form-select'}),
            'order_number': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
            'payment_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
            'invoice_random_code': forms.TextInput(attrs={'class': 'form-control'}),
            'invoice_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'coupon_code': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['enterprise_user'].label = '公司名稱'
        self.fields['test_project'].label = '購買評鑑項目'
        self.fields['order_number'].label = '訂單編號'
        self.fields['quantity'].label = '購買份數'
        self.fields['payment_amount'].label = '付款金額'
        self.fields['invoice_number'].label = '發票號碼'
        self.fields['invoice_random_code'].label = '發票隨機碼'
        self.fields['invoice_info'].label = '發票資訊'
        self.fields['coupon_code'].label = '優惠券'
        self.fields['notes'].label = '備註'

        self.fields['enterprise_user'].queryset = User.objects.filter(
            user_type='enterprise'
        ).select_related('enterprise_profile').order_by('enterprise_profile__company_name')
        self.fields['enterprise_user'].label_from_instance = lambda obj: (
            f"{getattr(obj.enterprise_profile, 'company_name', obj.username)}"
            f" ({getattr(obj.enterprise_profile, 'contact_person', obj.username)})"
            if hasattr(obj, 'enterprise_profile') and obj.enterprise_profile
            else obj.username
        )

        self.fields['test_project'].queryset = TestProject.objects.order_by('name')

        if not self.initial.get('payment_date'):
            self.initial['payment_date'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity <= 0:
            raise forms.ValidationError('購買份數必須為正整數')
        return quantity

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        if payment_method == '':
            cleaned_data['payment_method'] = ''
        return cleaned_data

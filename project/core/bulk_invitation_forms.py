# core/bulk_invitation_forms.py

from django import forms
from django.core.exceptions import ValidationError
from .models import TestProject, TestInvitee, TestInvitation
from datetime import datetime, timedelta
from django.utils import timezone
import csv
import io
import re

class BulkInvitationForm(forms.Form):
    """批量邀請表單"""
    
    test_project = forms.ModelChoiceField(
        queryset=TestProject.objects.none(),
        label='測驗項目',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    csv_file = forms.FileField(
        label='CSV檔案',
        help_text='請上傳包含受測者資料的CSV檔案（支援UTF-8編碼）',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv',
        })
    )
    
    expires_in_days = forms.IntegerField(
        label='有效期限（天）',
        initial=7,
        min_value=1,
        max_value=30,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    custom_message = forms.CharField(
        label='自訂邀請訊息',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '可輸入額外的邀請說明...'
        })
    )
    
    send_immediately = forms.BooleanField(
        label='立即發送邀請信',
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    skip_duplicates = forms.BooleanField(
        label='跳過重複的受測者',
        initial=False,
        required=False,
        help_text='如果受測者已存在，是否跳過而不是更新資料',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, enterprise_user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enterprise_user = enterprise_user
        
        # 設定可用的測驗項目 - 使用新的方法
        self.fields['test_project'].queryset = TestProject.get_available_projects_for_user(enterprise_user).order_by('name')
    
    def clean_csv_file(self):
        """驗證CSV檔案"""
        csv_file = self.cleaned_data['csv_file']
        
        if not csv_file:
            raise ValidationError('請選擇CSV檔案')
        
        if not csv_file.name.endswith('.csv'):
            raise ValidationError('請上傳CSV格式的檔案')
        
        if csv_file.size > 5 * 1024 * 1024:  # 5MB限制
            raise ValidationError('檔案大小不能超過5MB')
        
        # 驗證CSV內容
        try:
            csv_file.seek(0)
            content = csv_file.read().decode('utf-8-sig')  # 支援BOM
            csv_file.seek(0)
            
            csv_reader = csv.DictReader(io.StringIO(content))
            
            # 檢查必要欄位
            required_fields = ['name', 'email']
            fieldnames = csv_reader.fieldnames or []
            
            missing_fields = [field for field in required_fields if field not in fieldnames]
            if missing_fields:
                raise ValidationError(f'CSV檔案缺少必要欄位：{", ".join(missing_fields)}')
            
            # 驗證數據行數
            rows = list(csv_reader)
            if len(rows) == 0:
                raise ValidationError('CSV檔案沒有數據行')
            
            if len(rows) > 500:  # 限制批量處理數量
                raise ValidationError('一次最多只能處理500筆資料')
            
            # 驗證每行數據
            errors = []
            for i, row in enumerate(rows, 1):
                if not row.get('name', '').strip():
                    errors.append(f'第{i}行：姓名不能為空')
                
                email = row.get('email', '').strip()
                if not email:
                    errors.append(f'第{i}行：Email不能為空')
                elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                    errors.append(f'第{i}行：Email格式不正確')
            
            if errors:
                raise ValidationError(errors[:10])  # 最多顯示10個錯誤
            
            # 儲存解析後的數據供後續使用
            self.parsed_data = rows
            
        except UnicodeDecodeError:
            raise ValidationError('CSV檔案編碼錯誤，請使用UTF-8編碼')
        except csv.Error as e:
            raise ValidationError(f'CSV檔案格式錯誤：{str(e)}')
        except Exception as e:
            raise ValidationError(f'處理CSV檔案時發生錯誤：{str(e)}')
        
        return csv_file
    
    def get_parsed_data(self):
        """獲取解析後的CSV數據"""
        return getattr(self, 'parsed_data', [])
    
    def clean(self):
        """表單整體驗證"""
        cleaned_data = super().clean()
        
        if not self.errors:
            # 檢查測驗項目權限
            test_project = cleaned_data.get('test_project')
            if test_project and not test_project.get_available_for_user(self.enterprise_user):
                raise ValidationError('您沒有權限使用此測驗項目')
        
        return cleaned_data


class CSVTemplateForm(forms.Form):
    """CSV範本下載表單"""
    
    template_type = forms.ChoiceField(
        label='範本類型',
        choices=[
            ('basic', '基本範本（姓名、Email）'),
            ('complete', '完整範本（包含職位、電話）'),
        ],
        initial='basic',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )

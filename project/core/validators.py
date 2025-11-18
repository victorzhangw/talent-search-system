# core/validators.py
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class CustomPasswordValidator:
    """自定義密碼驗證器"""
    
    def validate(self, password, user=None):
        """驗證密碼強度"""
        errors = []
        
        # 檢查最小長度
        if len(password) < 8:
            errors.append(_("密碼長度至少8個字符"))
        
        # 檢查是否包含數字
        if not re.search(r'\d', password):
            errors.append(_("密碼必須包含至少一個數字"))
        
        # 檢查是否包含小寫字母
        if not re.search(r'[a-z]', password):
            errors.append(_("密碼必須包含至少一個小寫字母"))
        
        # 檢查是否包含大寫字母
        if not re.search(r'[A-Z]', password):
            errors.append(_("密碼必須包含至少一個大寫字母"))
        
        # 檢查是否包含特殊字符
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append(_("密碼必須包含至少一個特殊字符"))
        
        # 檢查是否包含常見弱密碼
        common_passwords = [
            'password', '123456', 'admin', 'root', 'user',
            'password123', 'admin123', 'qwerty', 'letmein'
        ]
        
        if password.lower() in common_passwords:
            errors.append(_("密碼不能是常見的弱密碼"))
        
        # 檢查是否與用戶信息相似
        if user:
            user_info = [
                user.username,
                user.email.split('@')[0] if user.email else '',
                user.first_name,
                user.last_name,
            ]
            
            for info in user_info:
                if info and info.lower() in password.lower():
                    errors.append(_("密碼不能包含用戶信息"))
                    break
        
        if errors:
            raise ValidationError(errors)
    
    def get_help_text(self):
        return _(
            "密碼必須符合以下要求：\n"
            "• 至少8個字符\n"
            "• 包含數字\n"
            "• 包含小寫字母\n"
            "• 包含大寫字母\n"
            "• 包含特殊字符\n"
            "• 不能是常見弱密碼\n"
            "• 不能包含用戶信息"
        )

class NoSequentialPasswordValidator:
    """禁止順序密碼驗證器"""
    
    def validate(self, password, user=None):
        # 檢查數字順序
        if self.has_sequential_numbers(password):
            raise ValidationError(_("密碼不能包含連續的數字"))
        
        # 檢查字母順序
        if self.has_sequential_letters(password):
            raise ValidationError(_("密碼不能包含連續的字母"))
        
        # 檢查重複字符
        if self.has_repeated_characters(password):
            raise ValidationError(_("密碼不能包含過多重複字符"))
    
    def has_sequential_numbers(self, password):
        """檢查是否包含連續數字"""
        for i in range(len(password) - 2):
            if password[i:i+3].isdigit():
                nums = [int(x) for x in password[i:i+3]]
                if nums == list(range(nums[0], nums[0] + 3)) or nums == list(range(nums[0], nums[0] - 3, -1)):
                    return True
        return False
    
    def has_sequential_letters(self, password):
        """檢查是否包含連續字母"""
        for i in range(len(password) - 2):
            if password[i:i+3].isalpha():
                chars = password[i:i+3].lower()
                if ord(chars[1]) == ord(chars[0]) + 1 and ord(chars[2]) == ord(chars[1]) + 1:
                    return True
                if ord(chars[1]) == ord(chars[0]) - 1 and ord(chars[2]) == ord(chars[1]) - 1:
                    return True
        return False
    
    def has_repeated_characters(self, password):
        """檢查是否包含過多重複字符"""
        for i in range(len(password) - 2):
            if password[i] == password[i+1] == password[i+2]:
                return True
        return False
    
    def get_help_text(self):
        return _("密碼不能包含連續的數字、字母或重複字符")

def validate_email_format(email):
    """驗證電子郵件格式"""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        raise ValidationError(_("請輸入有效的電子郵件地址"))

def validate_phone_format(phone):
    """驗證電話格式"""
    # 台灣手機號碼格式
    phone_regex = r'^09\d{8}$'
    if not re.match(phone_regex, phone):
        raise ValidationError(_("請輸入有效的手機號碼格式 (09xxxxxxxx)"))

def validate_company_name(company_name):
    """驗證公司名稱"""
    if len(company_name) < 2:
        raise ValidationError(_("公司名稱至少需要2個字符"))
    
    if len(company_name) > 100:
        raise ValidationError(_("公司名稱不能超過100個字符"))
    
    # 檢查是否包含特殊字符
    if re.search(r'[<>"\']', company_name):
        raise ValidationError(_("公司名稱不能包含特殊字符"))

def validate_invitation_message(message):
    """驗證邀請訊息"""
    if len(message) > 1000:
        raise ValidationError(_("邀請訊息不能超過1000個字符"))
    
    # 檢查是否包含惡意內容
    malicious_patterns = [
        r'<script',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe',
        r'<embed',
        r'<object',
    ]
    
    for pattern in malicious_patterns:
        if re.search(pattern, message, re.IGNORECASE):
            raise ValidationError(_("邀請訊息包含不允許的內容"))

def validate_file_size(file):
    """驗證檔案大小"""
    max_size = 5 * 1024 * 1024  # 5MB
    if file.size > max_size:
        raise ValidationError(_("檔案大小不能超過5MB"))

def validate_file_extension(file):
    """驗證檔案副檔名"""
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.doc', '.docx', '.csv', '.xlsx']
    ext = file.name.lower().split('.')[-1]
    if f'.{ext}' not in allowed_extensions:
        raise ValidationError(_("不支援的檔案格式"))
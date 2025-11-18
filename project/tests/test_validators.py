# tests/test_validators.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from core.validators import (
    CustomPasswordValidator, NoSequentialPasswordValidator,
    validate_email_format, validate_phone_format, 
    validate_company_name, validate_invitation_message,
    validate_file_size, validate_file_extension
)

User = get_user_model()

class CustomPasswordValidatorTest(TestCase):
    """自定義密碼驗證器測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.validator = CustomPasswordValidator()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TempPassword123!',
            first_name='Test',
            last_name='User'
        )
    
    def test_valid_password(self):
        """測試有效密碼"""
        valid_passwords = [
            'ValidPass123!',
            'MySecure@Pass2024',
            'Strong#Password99'
        ]
        
        for password in valid_passwords:
            try:
                self.validator.validate(password, self.user)
            except ValidationError:
                self.fail(f"Password '{password}' should be valid")
    
    def test_too_short_password(self):
        """測試過短密碼"""
        with self.assertRaises(ValidationError):
            self.validator.validate('Pass1!', self.user)
    
    def test_no_digit_password(self):
        """測試沒有數字的密碼"""
        with self.assertRaises(ValidationError):
            self.validator.validate('Password!', self.user)
    
    def test_no_lowercase_password(self):
        """測試沒有小寫字母的密碼"""
        with self.assertRaises(ValidationError):
            self.validator.validate('PASSWORD123!', self.user)
    
    def test_no_uppercase_password(self):
        """測試沒有大寫字母的密碼"""
        with self.assertRaises(ValidationError):
            self.validator.validate('password123!', self.user)
    
    def test_no_special_char_password(self):
        """測試沒有特殊字符的密碼"""
        with self.assertRaises(ValidationError):
            self.validator.validate('Password123', self.user)
    
    def test_common_password(self):
        """測試常見弱密碼"""
        common_passwords = ['password', '123456', 'admin', 'password123']
        
        for password in common_passwords:
            with self.assertRaises(ValidationError):
                self.validator.validate(password, self.user)
    
    def test_user_info_in_password(self):
        """測試密碼包含用戶信息"""
        user_info_passwords = [
            'testuser123!',
            'Test123!User',
            'test@example.com1!'
        ]
        
        for password in user_info_passwords:
            with self.assertRaises(ValidationError):
                self.validator.validate(password, self.user)

class NoSequentialPasswordValidatorTest(TestCase):
    """禁止順序密碼驗證器測試"""
    
    def setUp(self):
        """設定測試數據"""
        self.validator = NoSequentialPasswordValidator()
    
    def test_sequential_numbers(self):
        """測試連續數字"""
        sequential_passwords = [
            'password123',
            'test321pass',
            'abc456def',
            'pass987word'
        ]
        
        for password in sequential_passwords:
            with self.assertRaises(ValidationError):
                self.validator.validate(password)
    
    def test_sequential_letters(self):
        """測試連續字母"""
        sequential_passwords = [
            'passabc123',
            'testxyz456',
            'cbaabc789',
            'defghijk12'
        ]
        
        for password in sequential_passwords:
            with self.assertRaises(ValidationError):
                self.validator.validate(password)
    
    def test_repeated_characters(self):
        """測試重複字符"""
        repeated_passwords = [
            'passaaa123',
            'test111word',
            'abc...def',
            'pass!!!word'
        ]
        
        for password in repeated_passwords:
            with self.assertRaises(ValidationError):
                self.validator.validate(password)
    
    def test_valid_passwords(self):
        """測試有效密碼"""
        valid_passwords = [
            'Password123!',
            'MySecure@Pass',
            'Strong#Word99',
            'Valid1Pass!'
        ]
        
        for password in valid_passwords:
            try:
                self.validator.validate(password)
            except ValidationError:
                self.fail(f"Password '{password}' should be valid")

class EmailValidatorTest(TestCase):
    """電子郵件驗證器測試"""
    
    def test_valid_emails(self):
        """測試有效電子郵件"""
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'user+tag@example.org',
            'user_name@example-domain.com'
        ]
        
        for email in valid_emails:
            try:
                validate_email_format(email)
            except ValidationError:
                self.fail(f"Email '{email}' should be valid")
    
    def test_invalid_emails(self):
        """測試無效電子郵件"""
        invalid_emails = [
            'invalid-email',
            '@example.com',
            'user@',
            'user@.com',
            'user@domain',
            'user name@example.com'
        ]
        
        for email in invalid_emails:
            with self.assertRaises(ValidationError):
                validate_email_format(email)

class PhoneValidatorTest(TestCase):
    """電話驗證器測試"""
    
    def test_valid_phones(self):
        """測試有效電話"""
        valid_phones = [
            '0912345678',
            '0987654321',
            '0923456789'
        ]
        
        for phone in valid_phones:
            try:
                validate_phone_format(phone)
            except ValidationError:
                self.fail(f"Phone '{phone}' should be valid")
    
    def test_invalid_phones(self):
        """測試無效電話"""
        invalid_phones = [
            '123456789',
            '09123456789',
            '091234567',
            '0812345678',
            '09-123-456-78'
        ]
        
        for phone in invalid_phones:
            with self.assertRaises(ValidationError):
                validate_phone_format(phone)

class CompanyNameValidatorTest(TestCase):
    """公司名稱驗證器測試"""
    
    def test_valid_company_names(self):
        """測試有效公司名稱"""
        valid_names = [
            '台灣科技有限公司',
            'ABC Technology Co., Ltd.',
            '測試公司',
            'Tech Solutions Inc.'
        ]
        
        for name in valid_names:
            try:
                validate_company_name(name)
            except ValidationError:
                self.fail(f"Company name '{name}' should be valid")
    
    def test_invalid_company_names(self):
        """測試無效公司名稱"""
        # 太短
        with self.assertRaises(ValidationError):
            validate_company_name('A')
        
        # 太長
        with self.assertRaises(ValidationError):
            validate_company_name('A' * 101)
        
        # 包含特殊字符
        invalid_names = [
            'Company<script>',
            'Test"Company',
            "Test'Company",
            'Test>Company'
        ]
        
        for name in invalid_names:
            with self.assertRaises(ValidationError):
                validate_company_name(name)

class InvitationMessageValidatorTest(TestCase):
    """邀請訊息驗證器測試"""
    
    def test_valid_messages(self):
        """測試有效邀請訊息"""
        valid_messages = [
            '親愛的受測者，請完成測試。',
            'Hello, please complete the test.',
            '測試訊息' * 100  # 300字符，在限制內
        ]
        
        for message in valid_messages:
            try:
                validate_invitation_message(message)
            except ValidationError:
                self.fail(f"Message should be valid")
    
    def test_too_long_message(self):
        """測試過長訊息"""
        with self.assertRaises(ValidationError):
            validate_invitation_message('A' * 1001)
    
    def test_malicious_content(self):
        """測試惡意內容"""
        malicious_messages = [
            '<script>alert("xss")</script>',
            'javascript:alert("xss")',
            '<iframe src="malicious.com"></iframe>',
            'onclick="alert()"',
            '<embed src="malicious.com">',
            '<object data="malicious.com">'
        ]
        
        for message in malicious_messages:
            with self.assertRaises(ValidationError):
                validate_invitation_message(message)

# 檔案驗證器測試需要模擬檔案物件
class MockFile:
    """模擬檔案物件"""
    def __init__(self, name, size):
        self.name = name
        self.size = size

class FileValidatorTest(TestCase):
    """檔案驗證器測試"""
    
    def test_valid_file_size(self):
        """測試有效檔案大小"""
        file = MockFile('test.jpg', 1024 * 1024)  # 1MB
        try:
            validate_file_size(file)
        except ValidationError:
            self.fail("File size should be valid")
    
    def test_invalid_file_size(self):
        """測試無效檔案大小"""
        file = MockFile('test.jpg', 6 * 1024 * 1024)  # 6MB
        with self.assertRaises(ValidationError):
            validate_file_size(file)
    
    def test_valid_file_extensions(self):
        """測試有效檔案副檔名"""
        valid_files = [
            MockFile('image.jpg', 1024),
            MockFile('document.pdf', 1024),
            MockFile('spreadsheet.xlsx', 1024),
            MockFile('photo.PNG', 1024)
        ]
        
        for file in valid_files:
            try:
                validate_file_extension(file)
            except ValidationError:
                self.fail(f"File extension for '{file.name}' should be valid")
    
    def test_invalid_file_extensions(self):
        """測試無效檔案副檔名"""
        invalid_files = [
            MockFile('script.js', 1024),
            MockFile('executable.exe', 1024),
            MockFile('unknown.xyz', 1024)
        ]
        
        for file in invalid_files:
            with self.assertRaises(ValidationError):
                validate_file_extension(file)
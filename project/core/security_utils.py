"""
安全性工具模組
提供密碼加密、解密等安全功能
"""

from django.conf import settings
from cryptography.fernet import Fernet
import base64
import os
import logging

logger = logging.getLogger(__name__)

class PasswordEncryption:
    """密碼加密解密工具"""
    
    def __init__(self):
        self.cipher_suite = None
        self._setup_encryption()
    
    def _setup_encryption(self):
        """設置加密套件"""
        try:
            # 嘗試從設定檔獲取加密密鑰
            if hasattr(settings, 'ENCRYPTION_KEY'):
                key = settings.ENCRYPTION_KEY.encode()
            else:
                # 如果沒有設定密鑰，生成一個新的（僅開發環境）
                key = Fernet.generate_key()
                logger.warning("未設定加密密鑰，使用臨時密鑰（僅開發環境）")
            
            self.cipher_suite = Fernet(key)
            
        except Exception as e:
            logger.error(f"設置加密套件失敗: {e}")
            self.cipher_suite = None
    
    def encrypt_password(self, password):
        """加密密碼"""
        if not self.cipher_suite:
            # 如果加密套件未設定，返回原始密碼（向後兼容）
            logger.warning("加密套件未設定，密碼未加密")
            return password
        
        try:
            encrypted = self.cipher_suite.encrypt(password.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"密碼加密失敗: {e}")
            return password
    
    def decrypt_password(self, encrypted_password):
        """解密密碼"""
        if not self.cipher_suite:
            # 如果加密套件未設定，返回原始密碼（向後兼容）
            return encrypted_password
        
        try:
            # 檢查是否為加密格式
            if not self._is_encrypted_format(encrypted_password):
                return encrypted_password
            
            encrypted_bytes = base64.b64decode(encrypted_password.encode())
            decrypted = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"密碼解密失敗: {e}")
            return encrypted_password
    
    def _is_encrypted_format(self, password):
        """檢查密碼是否為加密格式"""
        try:
            # 嘗試解碼 base64，如果成功可能是加密的
            base64.b64decode(password.encode())
            return True
        except:
            return False

# 全局加密工具實例
password_encryption = PasswordEncryption()

def encrypt_test_platform_password(password):
    """加密測驗平台密碼"""
    return password_encryption.encrypt_password(password)

def decrypt_test_platform_password(encrypted_password):
    """解密測驗平台密碼"""
    return password_encryption.decrypt_password(encrypted_password)

def log_auto_login_attempt(user, success, error_message=None):
    """記錄自動登入嘗試"""
    try:
        from core.models import ActivityLog
        
        action = "自動登入成功" if success else "自動登入失敗"
        details = {
            'user_id': user.id,
            'username': user.username,
            'success': success,
            'timestamp': str(timezone.now()),
        }
        
        if error_message:
            details['error'] = error_message
        
        ActivityLog.objects.create(
            user=user,
            action=action,
            details=details,
            ip_address=getattr(user, '_request_ip', '127.0.0.1')
        )
        
    except Exception as e:
        logger.error(f"記錄自動登入日誌失敗: {e}")

def validate_test_platform_credentials(username, password):
    """驗證測驗平台登入資訊"""
    errors = []
    
    if not username or not username.strip():
        errors.append("測驗平台帳號不能為空")
    
    if not password or not password.strip():
        errors.append("測驗平台密碼不能為空")
    
    if len(password) < 6:
        errors.append("測驗平台密碼長度不能少於6位")
    
    # 基本格式驗證
    if username and '@' not in username:
        logger.warning("測驗平台帳號似乎不是電子郵件格式")
    
    return errors
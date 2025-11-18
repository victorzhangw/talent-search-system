# core/middleware.py
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import re

logger = logging.getLogger(__name__)

class SecurityMiddleware(MiddlewareMixin):
    """安全中間件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        # 記錄可疑的請求
        self.log_suspicious_requests(request)
        
        # 檢查IP黑名單
        if self.is_ip_blocked(request):
            logger.warning(f"Blocked request from IP: {self.get_client_ip(request)}")
            return HttpResponseForbidden("IP 被封鎖")
        
        # 檢查用戶代理
        if self.is_suspicious_user_agent(request):
            logger.warning(f"Suspicious user agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}")
            return HttpResponseForbidden("可疑的用戶代理")
        
        return None
    
    def process_response(self, request, response):
        # 添加安全標頭
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # 如果是 HTTPS，添加 HSTS 標頭
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    def get_client_ip(self, request):
        """獲取客戶端真實 IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_ip_blocked(self, request):
        """檢查 IP 是否被封鎖"""
        client_ip = self.get_client_ip(request)
        blocked_ips = cache.get('blocked_ips', [])
        return client_ip in blocked_ips
    
    def is_suspicious_user_agent(self, request):
        """檢查是否為可疑的用戶代理"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # 常見的惡意用戶代理模式
        suspicious_patterns = [
            r'sqlmap',
            r'nmap',
            r'nikto',
            r'curl.*bot',
            r'python-requests',
            r'wget',
            r'<script',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, user_agent, re.IGNORECASE):
                return True
        
        return False
    
    def log_suspicious_requests(self, request):
        """記錄可疑請求"""
        # 檢查是否包含惡意參數
        suspicious_params = ['<script', 'javascript:', 'union select', 'drop table']
        
        for param_name, param_value in request.GET.items():
            for suspicious in suspicious_params:
                if suspicious.lower() in str(param_value).lower():
                    logger.warning(f"Suspicious GET parameter: {param_name}={param_value} from IP: {self.get_client_ip(request)}")
        
        if request.method == 'POST':
            for param_name, param_value in request.POST.items():
                for suspicious in suspicious_params:
                    if suspicious.lower() in str(param_value).lower():
                        logger.warning(f"Suspicious POST parameter: {param_name}={param_value} from IP: {self.get_client_ip(request)}")

class RateLimitMiddleware(MiddlewareMixin):
    """速率限制中間件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        # 對於某些敏感端點進行額外的速率限制
        sensitive_paths = [
            '/auth/login/',
            '/auth/register/',
            '/api/auth/login/',
            '/api/auth/register/',
            '/forgot-password/',
        ]
        
        for path in sensitive_paths:
            if request.path.startswith(path):
                if self.is_rate_limited(request, path):
                    logger.warning(f"Rate limit exceeded for path: {path} from IP: {self.get_client_ip(request)}")
                    return HttpResponseForbidden("請求過於頻繁，請稍後再試")
        
        return None
    
    def get_client_ip(self, request):
        """獲取客戶端真實 IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_rate_limited(self, request, path):
        """檢查是否達到速率限制"""
        client_ip = self.get_client_ip(request)
        cache_key = f"rate_limit:{client_ip}:{path}"
        
        # 每分鐘最多 5 次請求
        current_count = cache.get(cache_key, 0)
        if current_count >= 5:
            return True
        
        # 增加計數
        cache.set(cache_key, current_count + 1, timeout=60)
        return False

class AuditMiddleware(MiddlewareMixin):
    """審計中間件"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        # 記錄重要操作
        if request.method in ['POST', 'PUT', 'DELETE']:
            self.log_important_action(request)
        
        return None
    
    def log_important_action(self, request):
        """記錄重要操作"""
        important_paths = [
            '/admin/',
            '/api/',
            '/management/',
            '/enterprise/',
        ]
        
        for path in important_paths:
            if request.path.startswith(path):
                logger.info(f"Important action: {request.method} {request.path} by user: {request.user.username if request.user.is_authenticated else 'Anonymous'} from IP: {self.get_client_ip(request)}")
                break
    
    def get_client_ip(self, request):
        """獲取客戶端真實 IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
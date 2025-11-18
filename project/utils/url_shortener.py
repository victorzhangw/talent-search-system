# utils/url_shortener.py

import hashlib
import string
import random
from django.conf import settings
from django.core.cache import cache
from core.models import TestInvitation
import logging

logger = logging.getLogger(__name__)

class URLShortenerService:
    """短網址生成服務"""
    
    # 短碼字符集（避免容易混淆的字符）
    CHARSET = string.ascii_lowercase + string.ascii_uppercase + string.digits
    CHARSET = CHARSET.replace('0', '').replace('O', '').replace('l', '').replace('I', '')  # 移除容易混淆的字符
    
    SHORT_CODE_LENGTH = 8  # 短碼長度
    CACHE_TIMEOUT = 60 * 60 * 24 * 30  # 快取30天
    
    @classmethod
    def generate_short_url(cls, original_url, invitation_id=None):
        """
        生成短網址
        
        Args:
            original_url: 原始測驗連結
            invitation_id: 邀請ID（可選，用於生成唯一性）
            
        Returns:
            dict: {
                'short_code': '短碼',
                'short_url': '完整短網址',
                'original_url': '原始網址'
            }
        """
        try:
            # 生成短碼
            short_code = cls._generate_short_code(original_url, invitation_id)
            
            # 建立完整短網址
            base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
            short_url = f"{base_url}/s/{short_code}"
            
            # 快取映射關係
            cache_key = f"short_url:{short_code}"
            cache.set(cache_key, original_url, cls.CACHE_TIMEOUT)
            
            # 如果有邀請ID，也存儲邀請ID映射
            if invitation_id:
                invitation_cache_key = f"short_url_invitation:{short_code}"
                cache.set(invitation_cache_key, invitation_id, cls.CACHE_TIMEOUT)
            
            # 反向快取（用於查找是否已存在）
            reverse_cache_key = f"reverse_short_url:{cls._hash_url(original_url, invitation_id)}"
            cache.set(reverse_cache_key, short_code, cls.CACHE_TIMEOUT)
            
            logger.info(f"生成短網址成功：{short_code} -> {original_url}")
            
            return {
                'short_code': short_code,
                'short_url': short_url,
                'original_url': original_url
            }
            
        except Exception as e:
            logger.error(f"生成短網址失敗：{str(e)}")
            # 如果短網址生成失敗，返回原始網址
            return {
                'short_code': None,
                'short_url': original_url,
                'original_url': original_url
            }
    
    @classmethod
    def _generate_short_code(cls, original_url, invitation_id=None):
        """生成短碼"""
        # 先檢查是否已經有對應的短碼
        url_hash = cls._hash_url(original_url, invitation_id)
        reverse_cache_key = f"reverse_short_url:{url_hash}"
        existing_code = cache.get(reverse_cache_key)
        
        if existing_code:
            return existing_code
        
        # 生成新的短碼
        max_attempts = 10
        for attempt in range(max_attempts):
            if invitation_id:
                # 基於邀請ID生成，確保同一邀請有固定短碼
                seed = f"{original_url}:{invitation_id}:{attempt}"
                hash_obj = hashlib.md5(seed.encode())
                hash_hex = hash_obj.hexdigest()
                
                # 將16進制轉換為我們的字符集
                short_code = cls._hex_to_charset(hash_hex[:cls.SHORT_CODE_LENGTH])
            else:
                # 隨機生成
                short_code = ''.join(random.choices(cls.CHARSET, k=cls.SHORT_CODE_LENGTH))
            
            # 檢查是否衝突
            cache_key = f"short_url:{short_code}"
            if not cache.get(cache_key):
                return short_code
        
        # 如果嘗試多次仍衝突，使用時間戳確保唯一性
        import time
        timestamp = str(int(time.time()))[-4:]  # 取時間戳後4位
        return cls._hex_to_charset(timestamp) + ''.join(random.choices(cls.CHARSET, k=4))
    
    @classmethod
    def _hash_url(cls, url, invitation_id=None):
        """計算URL的hash值"""
        content = f"{url}:{invitation_id}" if invitation_id else url
        return hashlib.md5(content.encode()).hexdigest()
    
    @classmethod
    def _hex_to_charset(cls, hex_string):
        """將16進制字符串轉換為我們的字符集"""
        result = ""
        for char in hex_string:
            if char.isdigit():
                index = int(char) % len(cls.CHARSET)
            else:
                index = (ord(char.lower()) - ord('a') + 10) % len(cls.CHARSET)
            result += cls.CHARSET[index]
        return result
    
    @classmethod
    def resolve_short_url(cls, short_code):
        """
        解析短網址
        
        Args:
            short_code: 短碼
            
        Returns:
            str: 原始網址，如果不存在返回None
        """
        cache_key = f"short_url:{short_code}"
        original_url = cache.get(cache_key)
        
        if original_url:
            cache.set(cache_key, original_url, cls.CACHE_TIMEOUT)
            return original_url

        invitation = TestInvitation.objects.filter(result_data__short_code=short_code).select_related('test_project').first()
        if not invitation:
            return None

        original_url = invitation.result_data.get('original_url') if invitation.result_data else None
        if not original_url and invitation.test_project:
            original_url = invitation.test_project.test_link

        if original_url:
            cache.set(cache_key, original_url, cls.CACHE_TIMEOUT)
            invitation_cache_key = f"short_url_invitation:{short_code}"
            cache.set(invitation_cache_key, invitation.id, cls.CACHE_TIMEOUT)
        return original_url
    
    @classmethod
    def get_short_url_stats(cls, short_code):
        """
        獲取短網址統計（可以擴展記錄點擊次數等）
        
        Args:
            short_code: 短碼
            
        Returns:
            dict: 統計資訊
        """
        cache_key = f"short_url:{short_code}"
        original_url = cache.get(cache_key)
        
        if not original_url:
            return None
            
        # 可以擴展記錄點擊次數、訪問時間等
        stats_key = f"short_url_stats:{short_code}"
        stats = cache.get(stats_key, {'clicks': 0, 'created_at': None})
        
        return {
            'short_code': short_code,
            'original_url': original_url,
            'clicks': stats.get('clicks', 0),
            'created_at': stats.get('created_at'),
        }
    
    @classmethod
    def increment_click_count(cls, short_code):
        """增加點擊計數"""
        stats_key = f"short_url_stats:{short_code}"
        stats = cache.get(stats_key, {'clicks': 0})
        stats['clicks'] = stats.get('clicks', 0) + 1
        
        # 設定較長的快取時間用於統計
        cache.set(stats_key, stats, cls.CACHE_TIMEOUT * 2)
        
        return stats['clicks']
    
    @classmethod
    def get_invitation_id(cls, short_code):
        """
        從短碼獲取邀請ID
        
        Args:
            short_code: 短碼
            
        Returns:
            int: 邀請ID，如果不存在返回None
        """
        invitation_cache_key = f"short_url_invitation:{short_code}"
        invitation_id = cache.get(invitation_cache_key)
        
        if invitation_id:
            cache.set(invitation_cache_key, invitation_id, cls.CACHE_TIMEOUT)
            return invitation_id

        invitation = TestInvitation.objects.filter(result_data__short_code=short_code).first()
        if not invitation:
            return None

        cache.set(invitation_cache_key, invitation.id, cls.CACHE_TIMEOUT)
        original_url = invitation.result_data.get('original_url') if invitation.result_data else None
        if not original_url and invitation.test_project:
            original_url = invitation.test_project.test_link
        if original_url:
            cache_key = f"short_url:{short_code}"
            cache.set(cache_key, original_url, cls.CACHE_TIMEOUT)

        return invitation.id

# 短網址重定向視圖
from django.shortcuts import redirect
from django.http import Http404

def short_url_redirect(request, short_code):
    """短網址重定向視圖 - 支援多種重定向邏輯"""
    from django.http import HttpResponse
    from django.utils import timezone
    
    # 獲取原始網址
    original_url = URLShortenerService.resolve_short_url(short_code)
    if not original_url:
        raise Http404("短網址不存在或已過期")
    
    # 獲取邀請ID
    invitation_id = URLShortenerService.get_invitation_id(short_code)
    
    if not invitation_id:
        # 如果沒有邀請ID，使用原始邏輯
        URLShortenerService.increment_click_count(short_code)
        return redirect(original_url)
    
    try:
        # 獲取邀請記錄
        invitation = TestInvitation.objects.get(id=invitation_id)
        
        # 檢查截止日期
        if invitation.expires_at and timezone.now() > invitation.expires_at:
            return HttpResponse("""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <title>測驗已截止</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                        .message { background: #f8d7da; color: #721c24; padding: 20px; border-radius: 5px; display: inline-block; }
                    </style>
                </head>
                <body>
                    <div class="message">
                        <h2>測驗已截止</h2>
                        <p>很抱歉，此測驗邀請已過期，無法繼續進行測驗。</p>
                        <p>如有疑問，請聯繫邀請方。</p>
                    </div>
                </body>
                </html>
            """, content_type='text/html; charset=utf-8')
        
        # 如果已完成就導向固定頁面
        if invitation.is_completed:
            redirect_url = "https://pi.perception-group.com/"
            return redirect(redirect_url)
        
        # 記錄點擊並獲取點擊次數
        click_count = URLShortenerService.increment_click_count(short_code)
        
        # 第一次點擊時更新邀請狀態
        if click_count == 1 and invitation.status == 'pending':
            invitation.status = 'in_progress'
            invitation.started_at = timezone.now()
            invitation.save()
            logger.info(f"邀請 {invitation.id} 狀態更新為進行中")

        return redirect(invitation.test_project.test_link)

        # # 根據點擊次數決定重定向邏輯
        # if click_count == 1:
        #     # 第一次點擊：導向測驗項目的測驗連結
        #     redirect_url = invitation.test_project.test_link
        # else:
        #     # 第二次以後點擊：導向固定頁面
        #     redirect_url = "https://pi.perception-group.com/"
        
        # return redirect(redirect_url)
        
    except TestInvitation.DoesNotExist:
        # 如果邀請不存在，使用原始邏輯
        URLShortenerService.increment_click_count(short_code)
        return redirect(original_url)

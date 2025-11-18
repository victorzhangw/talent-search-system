"""
Django 管理命令：測試自動登入服務
使用方法：python manage.py test_auto_login
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.auto_login_service import AutoLoginService

User = get_user_model()

class Command(BaseCommand):
    help = '測試 Selenium 自動登入服務'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='指定用戶名來測試該用戶的登入資訊'
        )
        parser.add_argument(
            '--headless',
            action='store_true',
            help='使用無頭模式運行（不顯示瀏覽器視窗）'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 開始測試 Selenium 自動登入服務'))
        
        username = options.get('username')
        headless = options.get('headless', False)
        
        if username:
            self.test_user_auto_login(username, headless)
        else:
            self.test_basic_functionality(headless)

    def test_basic_functionality(self, headless):
        """測試基本功能"""
        self.stdout.write("📱 測試基本 Selenium 功能...")
        
        service = AutoLoginService()
        
        if service.setup_driver(headless=headless):
            self.stdout.write(self.style.SUCCESS("✅ Chrome 瀏覽器啟動成功"))
            
            try:
                service.driver.get("https://whohire.ai")
                self.stdout.write(f"✅ 成功訪問 whohire.ai")
                self.stdout.write(f"   當前 URL: {service.driver.current_url}")
                self.stdout.write(f"   頁面標題: {service.driver.title}")
                
                import time
                time.sleep(3)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ 訪問失敗: {e}"))
            
            finally:
                service.driver.quit()
                self.stdout.write("🔚 瀏覽器已關閉")
        else:
            self.stdout.write(self.style.ERROR("❌ Chrome 瀏覽器啟動失敗"))

    def test_user_auto_login(self, username, headless):
        """測試特定用戶的自動登入"""
        self.stdout.write(f"🔐 測試用戶 '{username}' 的自動登入...")
        
        try:
            user = User.objects.get(username=username)
            
            if user.user_type != 'individual':
                self.stdout.write(self.style.ERROR("❌ 只有個人用戶可以使用自動登入功能"))
                return
                
            if not hasattr(user, 'individual_profile'):
                self.stdout.write(self.style.ERROR("❌ 用戶沒有個人資料"))
                return
                
            profile = user.individual_profile
            
            if not profile.test_platform_username or not profile.test_platform_password:
                self.stdout.write(self.style.ERROR("❌ 用戶尚未設定測驗平台登入資訊"))
                return
            
            self.stdout.write(f"   測驗平台帳號: {profile.test_platform_username}")
            self.stdout.write(f"   測驗平台密碼: {'*' * len(profile.test_platform_password)}")
            
            # 進行自動登入測試
            service = AutoLoginService()
            success, result = service.auto_login_whohire(
                profile.test_platform_username,
                profile.test_platform_password
            )
            
            if success:
                self.stdout.write(self.style.SUCCESS("✅ 自動登入測試成功"))
                self.stdout.write(f"   結果: {result}")
            else:
                self.stdout.write(self.style.ERROR(f"❌ 自動登入測試失敗: {result}"))
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ 找不到用戶 '{username}'"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ 測試過程中發生錯誤: {e}"))

    def list_users_with_login_info(self):
        """列出所有設定了登入資訊的用戶"""
        users = User.objects.filter(
            user_type='individual',
            individual_profile__test_platform_username__isnull=False,
            individual_profile__test_platform_password__isnull=False
        ).exclude(
            individual_profile__test_platform_username='',
            individual_profile__test_platform_password=''
        )
        
        if users.exists():
            self.stdout.write("📋 已設定測驗平台登入資訊的用戶:")
            for user in users:
                self.stdout.write(f"   - {user.username} ({user.individual_profile.test_platform_username})")
        else:
            self.stdout.write("❓ 沒有用戶設定測驗平台登入資訊")
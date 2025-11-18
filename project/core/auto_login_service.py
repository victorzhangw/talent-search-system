# core/auto_login_service.py
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import logging

logger = logging.getLogger(__name__)

class AutoLoginService:
    """自動登入服務，使用爬蟲技術實現真正的自動登入"""
    
    def __init__(self):
        self.driver = None
        self.session = requests.Session()
    
    def setup_driver(self, headless=True):
        """設置瀏覽器驅動"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            # 使用 webdriver-manager 自動管理 ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            return True
        except Exception as e:
            logger.error(f"無法啟動Chrome驅動: {e}")
            return False
    
    def auto_login_whohire(self, username, password):
        """自動登入 whohire.ai"""
        try:
            if not self.setup_driver():
                return False, "無法啟動瀏覽器驅動"
            
            logger.info("開始自動登入 whohire.ai")
            
            # 前往登入頁面
            login_url = "https://whohire.ai"
            self.driver.get(login_url)
            
            # 等待頁面載入
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            logger.info(f"頁面載入完成，當前URL: {self.driver.current_url}")
            
            # 等待登入表單元素出現
            try:
                email_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "Email"))
                )
                password_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "Password"))
                )
                login_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "btnLogin"))
                )
                
                logger.info("找到登入表單元素")
                
            except Exception as e:
                logger.error(f"找不到登入表單元素: {e}")
                return False, "找不到登入表單，請檢查網站狀態"
            
            # 填入登入資訊
            logger.info("填入登入資訊")
            email_field.clear()
            email_field.send_keys(username)
            
            password_field.clear()
            password_field.send_keys(password)
            
            # 等待一下讓頁面處理輸入
            time.sleep(1)
            
            # 點擊登入按鈕
            logger.info("點擊登入按鈕")
            login_button.click()
            
            # 等待登入處理
            time.sleep(5)
            
            # 檢查是否登入成功
            current_url = self.driver.current_url
            logger.info(f"登入後URL: {current_url}")
            
            # 檢查是否有錯誤訊息
            error_elements = self.driver.find_elements(By.CLASS_NAME, "alert-danger")
            if error_elements:
                error_text = error_elements[0].text
                logger.error(f"登入錯誤: {error_text}")
                return False, f"登入失敗: {error_text}"
            
            # 檢查是否有具體的登入錯誤訊息
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            error_keywords = ["Sorry! You must log in to continue", "Invalid username", "Invalid password", "incorrect credentials"]
            
            found_error = False
            for keyword in error_keywords:
                if keyword in body_text:
                    logger.error(f"發現登入錯誤訊息: {keyword}")
                    found_error = True
                    break
            
            if found_error:
                return False, "登入失敗，請檢查帳號密碼是否正確"
            
            # 檢查是否有二步驗證
            two_factor_elements = self.driver.find_elements(By.ID, "CodeDigit")
            if two_factor_elements:
                return False, "需要二步驗證，請手動完成登入"
            
            # 檢查是否跳轉到登入成功的頁面
            if current_url != login_url and not self.driver.find_elements(By.ID, "Email"):
                logger.info(f"登入成功，已跳轉到: {current_url}")
                
                # 取得登入後的cookies
                cookies = self.driver.get_cookies()
                
                return True, {
                    'success': True,
                    'redirect_url': current_url,
                    'cookies': cookies,
                    'message': '登入成功'
                }
            
            # 如果仍在登入頁面，檢查是否有具體的錯誤訊息
            error_alerts = self.driver.find_elements(By.CLASS_NAME, "alert-danger")
            if error_alerts:
                error_text = error_alerts[0].text
                logger.error(f"登入失敗，錯誤訊息: {error_text}")
                return False, f"登入失敗: {error_text}"
            else:
                logger.error("登入失敗，仍在登入頁面")
                return False, "登入失敗，請檢查帳號密碼"
            
        except Exception as e:
            logger.error(f"自動登入失敗: {e}")
            return False, f"自動登入過程中發生錯誤: {str(e)}"
        
        finally:
            if self.driver:
                self.driver.quit()
    
    def find_username_field(self):
        """尋找用戶名輸入框"""
        possible_selectors = [
            "input[name='username']",
            "input[name='email']",
            "input[name='user']",
            "input[name='login']",
            "input[id='username']",
            "input[id='email']",
            "input[id='user']",
            "input[id='login']",
            "input[type='email']",
            "input[placeholder*='用戶']",
            "input[placeholder*='帳號']",
            "input[placeholder*='郵箱']",
            "input[placeholder*='email']",
        ]
        
        for selector in possible_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.is_displayed():
                    return element
            except:
                continue
        return None
    
    def find_password_field(self):
        """尋找密碼輸入框"""
        possible_selectors = [
            "input[name='password']",
            "input[name='pass']",
            "input[name='pwd']",
            "input[id='password']",
            "input[id='pass']",
            "input[id='pwd']",
            "input[type='password']",
        ]
        
        for selector in possible_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.is_displayed():
                    return element
            except:
                continue
        return None
    
    def find_submit_button(self):
        """尋找提交按鈕"""
        possible_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:contains('登入')",
            "button:contains('登錄')",
            "button:contains('Login')",
            "button:contains('Sign in')",
            ".login-btn",
            ".submit-btn",
            "#login-button",
            "#submit-button",
        ]
        
        for selector in possible_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.is_displayed():
                    return element
            except:
                continue
        return None
    
    def is_login_successful(self):
        """檢查是否登入成功"""
        try:
            # 檢查URL是否改變
            current_url = self.driver.current_url
            if 'login' not in current_url.lower():
                return True
            
            # 檢查是否有錯誤訊息
            error_selectors = [
                ".error",
                ".alert-danger",
                ".login-error",
                "[class*='error']",
                "[class*='invalid']"
            ]
            
            for selector in error_selectors:
                try:
                    error_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if error_element and error_element.is_displayed():
                        return False
                except:
                    continue
            
            # 檢查是否有登入成功的指示
            success_selectors = [
                ".dashboard",
                ".user-menu",
                ".logout",
                "[class*='dashboard']",
                "[class*='profile']"
            ]
            
            for selector in success_selectors:
                try:
                    success_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if success_element and success_element.is_displayed():
                        return True
                except:
                    continue
            
            return True  # 如果沒有錯誤訊息，假設成功
            
        except Exception as e:
            logger.error(f"檢查登入狀態失敗: {e}")
            return False
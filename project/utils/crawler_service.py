# utils/crawler_service.py - 更新版本，整合完整的數據提取功能

import time
import logging
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from core.models import CrawlerConfig, TestInvitation, TestProjectResult
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import datetime
import os
import shutil
from glob import glob
import json

logger = logging.getLogger(__name__)

class PITestResultCrawler:
    """PI 測驗結果爬蟲 - 包含完整的登入、搜尋、點擊和數據提取功能"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        
    def setup_driver(self, headless=True):
        """設置 Chrome 瀏覽器驅動"""
        try:
            chrome_options = Options()
            if headless:
                chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            chrome_binary = self._locate_chrome_binary()
            if chrome_binary:
                chrome_options.binary_location = chrome_binary
                logger.info(f"使用瀏覽器執行檔：{chrome_binary}")
            else:
                logger.error("找不到 Chrome/Chromium 瀏覽器執行檔，請確認已安裝。")
                return False

            driver_path = self._locate_chromedriver()
            if driver_path:
                logger.info(f"使用系統 chromedriver：{driver_path}")
                service = Service(driver_path)
            else:
                logger.info("找不到系統 chromedriver，嘗試使用 webdriver-manager 下載")
                try:
                    driver_path = ChromeDriverManager().install()
                    logger.info(f"webdriver-manager 下載 chromedriver：{driver_path}")
                    service = Service(driver_path)
                except Exception as install_error:
                    logger.error(f"下載 chromedriver 失敗：{install_error}")
                    return False

            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)

            logger.info("Chrome 瀏覽器驅動設置完成")
            return True

        except Exception as e:
            logger.error(f"設置瀏覽器驅動失敗：{str(e)}")
            return False

    @staticmethod
    def _locate_chrome_binary():
        """尋找系統上的 Chrome/Chromium 執行檔"""
        env_path = os.environ.get('CHROME_BINARY')
        if env_path and os.path.isfile(env_path):
            return env_path

        candidates = [
            shutil.which('google-chrome'),
            shutil.which('google-chrome-stable'),
            shutil.which('chromium'),
            shutil.which('chromium-browser'),
            shutil.which('chrome'),
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/Applications/Chromium.app/Contents/MacOS/Chromium',
            '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
        ]

        # Playwright 下載的 Chromium
        playwright_globs = glob(os.path.expanduser('~/.cache/ms-playwright/chromium-*/chrome*/chrome'))
        candidates.extend(playwright_globs)

        for path in candidates:
            if path and os.path.isfile(path):
                return path

        return None

    @staticmethod
    def _locate_chromedriver():
        """尋找系統上的 chromedriver 執行檔"""
        env_path = os.environ.get('CHROMEDRIVER_PATH')
        if env_path and os.path.isfile(env_path):
            return env_path

        candidates = [
            shutil.which('chromedriver'),
            '/usr/lib/chromium/chromedriver',
            '/usr/lib/chromium-browser/chromedriver',
            '/usr/bin/chromedriver'
        ]

        for path in candidates:
            if path and os.path.isfile(path):
                return path

        return None
    
    def login_to_system(self):
        """登入 PI 系統"""
        try:
            # 獲取爬蟲配置
            config = CrawlerConfig.objects.filter(is_active=True).first()
            if not config:
                logger.error("沒有找到啟用的爬蟲配置")
                return False
            
            logger.info(f"訪問 PI 系統：{config.base_url}")
            self.driver.get(config.base_url)
            time.sleep(3)
            
            # 輸入帳號
            username_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "Email"))
            )
            username_field.clear()
            username_field.send_keys(config.username)
            
            # 輸入密碼
            password_field = self.driver.find_element(By.NAME, "Password")
            password_field.clear()
            password_field.send_keys(config.password)
            
            # 點擊登入按鈕
            login_button = self.driver.find_element(By.XPATH, "//input[@value='Login']")
            login_button.click()
            
            # 等待登入完成
            time.sleep(5)
            
            # 檢查登入是否成功（URL 應該會改變）
            if self.driver.current_url != config.base_url:
                logger.info("登入 PI 系統成功")
                
                # 確保使用 English 語系
                self.ensure_english_language()
                
                return True
            else:
                logger.error("登入失敗，URL 未改變")
                return False
                
        except Exception as e:
            logger.error(f"登入 PI 系統失敗：{str(e)}")
            return False
    
    def ensure_english_language(self):
        """確保系統使用 English 語系"""
        try:
            logger.info("檢查並設定系統語系為 English")
            
            # 等待頁面完全載入
            time.sleep(5)
            
            # 更寬鬆的語系選擇器搜尋
            language_selectors = [
                ".drplanguages .dropdown-toggle",
                ".Navbar_Right.dropdown.drplanguages a.dropdown-toggle", 
                ".dropdown.drplanguages a.dropdown-toggle",
                "[class*='drplanguages'] [class*='dropdown-toggle']",
                ".navbar [class*='language'] a",
                ".navbar .dropdown-toggle"
            ]
            
            language_dropdown = None
            for selector in language_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        # 檢查元素是否包含語言相關內容
                        element_text = element.text.strip()
                        if any(lang in element_text.lower() for lang in ['english', 'chinese', '中文', 'español', 'français']):
                            language_dropdown = element
                            logger.info(f"找到語系選擇器: {selector} - 內容: {element_text}")
                            break
                    if language_dropdown:
                        break
                except Exception as e:
                    logger.debug(f"選擇器 {selector} 失敗: {str(e)}")
                    continue
            
            if not language_dropdown:
                logger.warning("找不到語系選擇器，嘗試通過URL參數切換")
                # 嘗試通過URL參數切換語系
                try:
                    current_url = self.driver.current_url
                    if 'LanguageCode=' not in current_url:
                        new_url = current_url + ('&' if '?' in current_url else '?') + 'LanguageCode=eng'
                        self.driver.get(new_url)
                        time.sleep(5)
                        logger.info("✅ 通過URL參數切換到English語系")
                        return True
                except Exception as url_error:
                    logger.error(f"URL參數切換失敗: {str(url_error)}")
                return False
            
            # 檢查當前語系
            current_lang_text = language_dropdown.text.strip()
            logger.info(f"當前語系顯示: '{current_lang_text}'")
            
            # 如果已經是 English，直接返回
            if "english" in current_lang_text.lower():
                logger.info("✅ 系統已使用 English 語系")
                return True
            
            # 滾動到語系選擇器位置
            self.driver.execute_script("arguments[0].scrollIntoView(true);", language_dropdown)
            time.sleep(1)
            
            # 點擊語系下拉選單
            logger.info("嘗試點擊語系下拉選單")
            try:
                # 嘗試直接點擊
                language_dropdown.click()
            except:
                # 如果直接點擊失敗，使用JavaScript點擊
                self.driver.execute_script("arguments[0].click();", language_dropdown)
            
            time.sleep(3)
            logger.info("已點擊語系下拉選單")
            
            # 尋找 English 選項 - 使用更全面的搜尋
            english_selectors = [
                ".js-langCode[data-languagecode='eng']",
                "a[data-languagecode='eng']",
                "[data-languagecode='eng']",
                "a[data-culturecode='en-US']",
                "[data-culturecode='en-US']"
            ]
            
            english_option = None
            for selector in english_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            english_option = element
                            logger.info(f"找到English選項: {selector}")
                            break
                    if english_option:
                        break
                except Exception as e:
                    logger.debug(f"English選擇器 {selector} 失敗: {str(e)}")
                    continue
            
            # 如果找不到特定選擇器，嘗試通過文字搜尋
            if not english_option:
                try:
                    xpath_selectors = [
                        "//a[contains(text(), 'English')]",
                        "//li[contains(text(), 'English')]//a",
                        "//*[contains(text(), 'English') and contains(@class, 'js-langCode')]"
                    ]
                    
                    for xpath in xpath_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, xpath)
                            for element in elements:
                                if element.is_displayed():
                                    english_option = element
                                    logger.info(f"通過XPath找到English選項: {xpath}")
                                    break
                            if english_option:
                                break
                        except Exception as e:
                            logger.debug(f"XPath {xpath} 失敗: {str(e)}")
                            continue
                except Exception as xpath_error:
                    logger.debug(f"XPath搜尋失敗: {str(xpath_error)}")
            
            if english_option:
                try:
                    # 滾動到English選項位置
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", english_option)
                    time.sleep(1)
                    
                    # 嘗試點擊English選項
                    try:
                        english_option.click()
                    except:
                        # 如果直接點擊失敗，使用JavaScript點擊
                        self.driver.execute_script("arguments[0].click();", english_option)
                    
                    logger.info("✅ 已點擊 English 語系選項")
                    
                    # 等待頁面重新載入
                    time.sleep(8)
                    logger.info("✅ 語系切換完成，等待頁面載入")
                    
                    # 驗證切換是否成功
                    try:
                        time.sleep(2)
                        # 重新檢查語系
                        current_elements = self.driver.find_elements(By.CSS_SELECTOR, ".drplanguages .dropdown-toggle")
                        if current_elements:
                            new_lang_text = current_elements[0].text.strip()
                            logger.info(f"切換後語系顯示: '{new_lang_text}'")
                            if "english" in new_lang_text.lower():
                                logger.info("✅ 語系切換驗證成功")
                                return True
                    except Exception as verify_error:
                        logger.debug(f"語系切換驗證失敗: {str(verify_error)}")
                    
                    return True
                    
                except Exception as click_error:
                    logger.error(f"點擊English選項失敗: {str(click_error)}")
                    return False
            else:
                logger.warning("找不到 English 語系選項")
                # 嘗試刷新頁面重試
                try:
                    logger.info("嘗試刷新頁面後重試")
                    self.driver.refresh()
                    time.sleep(5)
                    return self.ensure_english_language_simple()
                except:
                    return False
                
        except Exception as e:
            logger.error(f"設定 English 語系失敗：{str(e)}")
            return False
    
    def ensure_english_language_simple(self):
        """簡化版語系切換"""
        try:
            # 直接通過URL添加語言參數
            current_url = self.driver.current_url
            if 'LanguageCode=' not in current_url:
                separator = '&' if '?' in current_url else '?'
                new_url = f"{current_url}{separator}LanguageCode=eng"
                logger.info(f"通過URL切換語系: {new_url}")
                self.driver.get(new_url)
                time.sleep(5)
                return True
            return True
        except Exception as e:
            logger.error(f"簡化語系切換失敗: {str(e)}")
            return False
    
    def search_user(self, email):
        """搜尋指定的用戶"""
        try:
            logger.info(f"搜尋用戶：{email}")
            
            # 等待頁面完全載入
            time.sleep(5)
            
            # 嘗試多種搜尋框定位方式（基於實際HTML結構）
            search_input = None
            selectors = [
                "#AssessmentDTDashbord_filter input[type='search']",  # 最精確的選擇器
                "input[aria-controls='AssessmentDTDashbord']",        # 基於aria-controls屬性
                ".dataTables_filter input[type='search']",           # 基於class
                "input.form-control.input-sm[placeholder='Search']", # 基於多個class和placeholder
                "input[placeholder*='Search']",                      # 原始選擇器
                "input[type='search']",                              # 通用選擇器
            ]
            
            for selector in selectors:
                try:
                    search_input = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"找到搜尋框，使用選擇器: {selector}")
                    break
                except:
                    continue
            
            if not search_input:
                raise Exception("無法找到搜尋框")
            
            # 清空並輸入搜尋內容
            search_input.clear()
            time.sleep(2)
            search_input.send_keys(email)
            time.sleep(1)
            search_input.send_keys(Keys.RETURN)
            
            # 等待搜尋結果載入
            time.sleep(8)
            
            logger.info(f"用戶搜尋完成：{email}")
            return True
            
        except Exception as e:
            logger.error(f"搜尋用戶失敗：{str(e)}")
            return False
    
    def apply_job_role_filter(self, job_role_name):
        """驗證搜尋結果中的 Job Role 是否匹配"""
        try:
            logger.info(f"驗證 Job Role：{job_role_name}")
            
            # 等待搜尋結果載入
            time.sleep(3)
            
            # 查找包含 Job Role 的表格行
            job_role_cells = self.driver.find_elements(By.CSS_SELECTOR, "td.JobRoles")
            
            if not job_role_cells:
                logger.warning("未找到 Job Role 欄位，嘗試其他選擇器")
                # 嘗試其他可能的選擇器
                job_role_cells = self.driver.find_elements(By.CSS_SELECTOR, "td[data-thf='Job Role']")
            
            if not job_role_cells:
                logger.warning("仍未找到 Job Role 欄位，檢查所有表格行")
                # 檢查所有表格行是否包含目標文字
                all_cells = self.driver.find_elements(By.CSS_SELECTOR, "td")
                for cell in all_cells:
                    if job_role_name in cell.text:
                        logger.info(f"在表格中找到匹配的 Job Role: {job_role_name}")
                        return True
                
                logger.error("未在搜尋結果中找到匹配的 Job Role")
                return False
            
            # 檢查 Job Role 欄位中是否包含目標值
            for cell in job_role_cells:
                cell_text = cell.text
                logger.info(f"檢查 Job Role 欄位內容: {cell_text}")
                
                if job_role_name in cell_text:
                    logger.info(f"✅ Job Role 驗證成功: {job_role_name}")
                    return True
            
            logger.warning(f"Job Role 不匹配。期望: {job_role_name}")
            return False
            
        except Exception as e:
            logger.error(f"Job Role 驗證失敗：{str(e)}")
            return False
    
    def check_ci_completion(self):
        """檢查是否有 CI 元素，判斷測驗是否已完成"""
        try:
            logger.info("檢查 CI 元素是否存在，確認測驗完成狀態")
            
            # 等待頁面完全載入
            time.sleep(3)
            
            # 檢查 PredictorChart 容器是否存在
            predictor_charts = self.driver.find_elements(By.CSS_SELECTOR, ".PedictorChart")
            
            if not predictor_charts:
                logger.warning("未找到 PredictorChart 容器")
                return False
            
            logger.info(f"找到 {len(predictor_charts)} 個 PredictorChart 容器")
            
            # 檢查是否存在包含 "CI" 文字的 ProgressText 元素
            for chart in predictor_charts:
                try:
                    # 查找 ProgressText 元素
                    progress_text_elements = chart.find_elements(By.CSS_SELECTOR, ".ProgressText")
                    
                    for text_element in progress_text_elements:
                        text_content = text_element.text.strip()
                        logger.info(f"檢查 ProgressText 內容: '{text_content}'")
                        
                        if text_content == "CI":
                            logger.info("✅ 找到 CI 元素，測驗已完成，可以繼續爬蟲流程")
                            return True
                    
                    # 檢查是否存在 InviteAssessmentProgress（表示測驗進行中）
                    in_progress_elements = chart.find_elements(By.CSS_SELECTOR, ".InviteAssessmentProgress")
                    if in_progress_elements:
                        for progress_element in in_progress_elements:
                            progress_per = progress_element.find_elements(By.CSS_SELECTOR, ".ProgressPer")
                            if progress_per:
                                progress_text = progress_per[0].text.strip()
                                logger.warning(f"❌ 測驗尚未完成，當前進度: {progress_text}")
                                return False
                    
                except Exception as chart_error:
                    logger.debug(f"檢查 PredictorChart 失敗：{str(chart_error)}")
                    continue
            
            logger.warning("❌ 未找到 CI 元素，測驗可能尚未完成")
            return False
                
        except Exception as e:
            logger.error(f"CI 完成狀態檢查失敗：{str(e)}")
            return False
    
    def expand_test_results(self):
        """展開測驗結果詳情 - 點擊 View Results 按鈕"""
        try:
            logger.info("開始展開測驗結果")
            
            # 使用正確的選擇器：ScoreUp (View Results)
            view_results_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#ScoreUp"))
            )
            
            # 滾動到按鈕位置並點擊
            self.driver.execute_script("arguments[0].scrollIntoView(true);", view_results_button)
            time.sleep(1)
            view_results_button.click()
            
            logger.info("成功點擊 View Results 按鈕")
            time.sleep(3)
            
            # 強化展開檢查 - 等待特質分數元素出現
            max_wait_attempts = 10
            for attempt in range(max_wait_attempts):
                try:
                    # 檢查是否成功展開（ScoreDown 應該變為可見）
                    hide_button = self.driver.find_element(By.CSS_SELECTOR, "#ScoreDown")
                    if hide_button.is_displayed():
                        logger.info("✅ ScoreDown按鈕已可見")
                        
                        # 進一步檢查特質分數元素是否已加載
                        trait_elements = self.driver.find_elements(By.CSS_SELECTOR, "[id^='lbl_bizform_']")
                        percentage_elements = self.driver.find_elements(By.CSS_SELECTOR, ".kp-per-value")
                        
                        logger.info(f"找到 {len(trait_elements)} 個特質標籤元素")
                        logger.info(f"找到 {len(percentage_elements)} 個百分比元素")
                        
                        if len(trait_elements) > 0 and len(percentage_elements) > 0:
                            logger.info("✅ 測驗結果已完全展開，特質元素已可見")
                            return True
                        else:
                            logger.warning(f"⚠️ 頁面已展開但特質元素不足，嘗試 {attempt+1}/{max_wait_attempts}")
                            time.sleep(2)
                            continue
                except Exception as check_error:
                    logger.debug(f"展開檢查嘗試 {attempt+1}: {str(check_error)}")
                    time.sleep(2)
                    continue
            
            # 如果仍然找不到足夠的元素，記錄警告但繼續
            logger.warning("⚠️ 無法確認所有特質元素已完全加載，但將繼續嘗試提取")
            return True
            
        except Exception as e:
            logger.error(f"展開測驗結果失敗：{str(e)}")
            return False
    
    def check_results_expanded(self):
        """檢查測驗結果是否已展開"""
        try:
            # 檢查特質分數相關元素
            trait_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 
                ".val-aptitudes, .kp-per-value, .ProgressPer"
            )
            
            if len(trait_elements) > 0:
                logger.info(f"檢測到 {len(trait_elements)} 個特質分數元素")
                return True
            
            # 檢查頁面中的百分比內容
            page_text = self.driver.page_source.lower()
            if "%" in page_text and any(keyword in page_text for keyword in ["desire", "efficacy", "innovation"]):
                logger.info("檢測到百分比和特質關鍵字")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"檢查結果展開狀態失敗：{str(e)}")
            return False
    
    def extract_test_data(self, test_project):
        """提取測驗數據 - 整合成功的邏輯"""
        try:
            logger.info("開始提取測驗數據")
            
            # 初始化結果數據結構
            result_data = {
                'user_info': {},
                'performance_metrics': {},
                'trait_scores': {},
                'raw_elements': [],
                'extraction_metadata': {
                    'timestamp': timezone.now().isoformat(),
                    'page_url': self.driver.current_url,
                    'page_title': self.driver.title,
                    'test_project_id': test_project.id
                }
            }
            
            # 1. 提取用戶基本資訊
            try:
                user_selectors = ["#userName", ".user-name", ".name"]
                for selector in user_selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if element.text.strip():
                            result_data['user_info']['name'] = element.text.strip()
                            logger.info(f"提取用戶名：{result_data['user_info']['name']}")
                            break
                    except:
                        continue
            except Exception as e:
                logger.warning(f"提取用戶資訊失敗：{str(e)}")
            
            # 2. 提取性能指標 (Performance Potential)
            try:
                logger.info("開始提取性能指標")
                
                # 方法1: 通過 PredictorProgressDiv 提取性能指標
                performance_containers = self.driver.find_elements(By.CSS_SELECTOR, ".PredictorProgressDiv")
                logger.info(f"找到 {len(performance_containers)} 個性能指標容器")
                
                for container in performance_containers:
                    try:
                        # 獲取指標名稱
                        metric_name = container.get_attribute('data-short-desc')
                        if not metric_name:
                            # 嘗試從其他屬性獲取
                            metric_name = container.get_attribute('title') or container.get_attribute('data-title')
                        
                        # 獲取指標值
                        value_selectors = ['.ProgressPer', '.kp-per-value', '.progress-value', '[class*="per"]']
                        metric_value = None
                        
                        for selector in value_selectors:
                            try:
                                value_element = container.find_element(By.CSS_SELECTOR, selector)
                                potential_value = value_element.text.strip()
                                if potential_value and potential_value != "0" and potential_value != "0.0":
                                    metric_value = potential_value
                                    break
                            except:
                                continue
                        
                        if metric_name and metric_value:
                            result_data['performance_metrics'][metric_name] = metric_value
                            logger.info(f"✅ 提取性能指標：{metric_name} = {metric_value}")
                            
                    except Exception as container_error:
                        logger.warning(f"處理性能指標容器失敗：{str(container_error)}")
                        continue
                
                # 專門處理 Composite Index
                try:
                    logger.info("開始專門提取 Composite Index")
                    
                    # 查找 Composite Index 相關元素
                    composite_selectors = [
                        ".EmployabilityIndex",
                        "#EmployabilityIndex", 
                        "[data-th='Performance Predictor']",
                        "[data-en_scalename='Composite Index']",
                        "[data-header*='Composite Index']"
                    ]
                    
                    composite_found = False
                    for selector in composite_selectors:
                        try:
                            composite_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for element in composite_elements:
                                # 提取 CI 百分比值
                                ci_percent_element = element.find_element(By.CSS_SELECTOR, ".ProgressPer")
                                ci_percent = ci_percent_element.text.strip()
                                
                                # 提取 Composite Index 文字描述
                                ci_description_element = element.find_element(By.CSS_SELECTOR, ".CI")
                                ci_description = ci_description_element.text.strip()
                                
                                if ci_percent:
                                    result_data['performance_metrics']['CI'] = ci_percent
                                    logger.info(f"✅ 提取 Composite Index 百分比：{ci_percent}")
                                
                                if ci_description:
                                    result_data['performance_metrics']['Composite_Index_Description'] = ci_description
                                    logger.info(f"✅ 提取 Composite Index 描述：{ci_description}")
                                
                                # 提取其他相關屬性
                                data_value = element.get_attribute('data-value')
                                data_percentile = element.get_attribute('data-percentile')
                                if data_value:
                                    result_data['performance_metrics']['CI_Raw_Value'] = data_value
                                if data_percentile:
                                    result_data['performance_metrics']['CI_Percentile'] = data_percentile
                                
                                composite_found = True
                                break
                        except Exception as ci_error:
                            logger.debug(f"使用選擇器 {selector} 提取 Composite Index 失敗：{str(ci_error)}")
                            continue
                    
                    # 備用策略: 如果原始方法失敗，使用XPath搜索
                    if not composite_found:
                        try:
                            logger.info("原始Composite Index提取失敗，嘗試備用XPath策略")
                            xpath_selectors = [
                                "//*[contains(text(), 'Composite Index')]",
                                "//*[contains(text(), 'Composite Index:')]"
                            ]
                            
                            for xpath in xpath_selectors:
                                try:
                                    elements = self.driver.find_elements(By.XPATH, xpath)
                                    for element in elements:
                                        element_text = element.text.strip()
                                        if 'Composite Index' in element_text:
                                            result_data['performance_metrics']['Composite_Index_Description'] = element_text
                                            logger.info(f"✅ XPath備用策略提取 Composite Index 描述：{element_text}")
                                            composite_found = True
                                            break
                                except Exception as xpath_inner_error:
                                    logger.debug(f"XPath元素處理失敗：{str(xpath_inner_error)}")
                                    continue
                                
                                if composite_found:
                                    break
                        except Exception as xpath_error:
                            logger.debug(f"XPath備用策略失敗：{str(xpath_error)}")
                            
                except Exception as composite_error:
                    logger.warning(f"提取 Composite Index 失敗：{str(composite_error)}")
                
                
                # 方法2: 專門搜尋 CI 值
                ci_selectors = [
                    "//*[contains(text(), 'CI')]/following-sibling::*[contains(text(), '%')]",
                    "//*[contains(text(), 'CI')]/*[contains(text(), '%')]",
                    "//*[contains(@class, 'ci') or contains(@id, 'ci')]//text()[contains(., '%')]",
                    "//span[contains(text(), 'CI')]/following-sibling::span",
                    "//div[contains(text(), 'CI')]//*[contains(text(), '%')]"
                ]
                
                for selector in ci_selectors:
                    try:
                        ci_elements = self.driver.find_elements(By.XPATH, selector)
                        for element in ci_elements:
                            text = element.text.strip()
                            if '%' in text and text != "0%" and text != "0.0%":
                                result_data['performance_metrics']['CI'] = text
                                logger.info(f"✅ 提取CI值：{text}")
                                break
                        if 'CI' in result_data['performance_metrics']:
                            break
                    except:
                        continue
                
                # 方法3: 搜尋所有可能的分數相關元素
                score_keywords = ['score', 'potential', 'performance', 'rating', 'index']
                for keyword in score_keywords:
                    try:
                        keyword_elements = self.driver.find_elements(
                            By.XPATH, 
                            f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]//*[contains(text(), '%') or contains(text(), '/')]"
                        )
                        
                        for element in keyword_elements:
                            try:
                                text = element.text.strip()
                                parent_text = element.find_element(By.XPATH, "../..").text.strip()
                                
                                if any(char.isdigit() for char in text) and text != "0" and text != "0.0":
                                    metric_key = f"{keyword}_value"
                                    result_data['performance_metrics'][metric_key] = text
                                    logger.info(f"✅ 提取{keyword}指標：{text}")
                                    break
                            except:
                                continue
                    except:
                        continue
                        
            except Exception as e:
                logger.warning(f"提取性能指標失敗：{str(e)}")
            
            # 3. 提取特質分數 - 多種方法並行嘗試
            try:
                logger.info("開始提取特質分數 - 使用多種策略")
                
                # 策略1: 通過 lbl_bizform 找到特質名稱和對應分數
                trait_labels = self.driver.find_elements(By.CSS_SELECTOR, "[id^='lbl_bizform_']")
                logger.info(f"策略1: 找到 {len(trait_labels)} 個特質標籤")
                
                for label in trait_labels:
                    try:
                        # 提取特質名稱
                        trait_name_element = label.find_element(By.CSS_SELECTOR, ".tooltips.assessmentTooltips")
                        trait_name = trait_name_element.text.strip()
                        
                        # 獲取對應的ID
                        label_id = label.get_attribute('id')
                        trait_id = label_id.replace('lbl_bizform_', '')
                        
                        # 多種分數選擇器嘗試
                        score_selectors = [
                            f"#lbl_bizform_{trait_id} + .val-aptitudes .kp-per-value",
                            f"#lbl_bizform_{trait_id} + .val-aptitudes .ProgressPer",
                            f"#lbl_bizform_{trait_id} + div .kp-per-value",
                            f"#lbl_bizform_{trait_id} ~ .val-aptitudes .kp-per-value",
                            f"[data-trait-id='{trait_id}'] .kp-per-value",
                            f"[data-trait-id='{trait_id}'] .ProgressPer"
                        ]
                        
                        score_found = False
                        for selector in score_selectors:
                            try:
                                score_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                                score_text = score_element.text.strip()
                                
                                if score_text and score_text != "0" and score_text != "0.0":
                                    # 提取數字 (支援百分比和純數字)
                                    score_match = re.search(r'(\d+(?:\.\d+)?)', score_text)
                                    if score_match:
                                        score_value = float(score_match.group(1))
                                        
                                        # 提取 data-headsupflag 屬性
                                        headsupflag = None
                                        try:
                                            # 方法1: 從分數元素本身獲取
                                            headsupflag = score_element.get_attribute('data-headsupflag')
                                            
                                            # 方法2: 從直接父元素獲取
                                            if not headsupflag:
                                                parent_element = score_element.find_element(By.XPATH, "..")
                                                headsupflag = parent_element.get_attribute('data-headsupflag')
                                            
                                            # 方法3: 向上查找多層父元素，找到包含data-headsupflag的元素
                                            if not headsupflag:
                                                current_element = score_element
                                                for i in range(5):  # 最多向上查找5層
                                                    try:
                                                        current_element = current_element.find_element(By.XPATH, "..")
                                                        headsupflag = current_element.get_attribute('data-headsupflag')
                                                        if headsupflag:
                                                            logger.debug(f"找到 data-headsupflag 在第 {i+2} 層父元素: {headsupflag}")
                                                            break
                                                    except:
                                                        break
                                            
                                            # 方法4: 通過trait_id直接查找Rating元素
                                            if not headsupflag and trait_id:
                                                try:
                                                    rating_selector = f"div[id*='Rating_{trait_id}']"
                                                    rating_elements = self.driver.find_elements(By.CSS_SELECTOR, rating_selector)
                                                    for rating_element in rating_elements:
                                                        headsupflag = rating_element.get_attribute('data-headsupflag')
                                                        if headsupflag:
                                                            logger.debug(f"通過Rating元素找到 data-headsupflag: {headsupflag}")
                                                            break
                                                except:
                                                    pass
                                            
                                            # 轉換字符串為整數
                                            if headsupflag:
                                                try:
                                                    headsupflag = int(headsupflag)
                                                except:
                                                    pass
                                                
                                        except Exception as flag_error:
                                            logger.debug(f"無法獲取 data-headsupflag for {trait_name}: {str(flag_error)}")
                                        
                                        result_data['trait_scores'][trait_name] = {
                                            'score': score_value,
                                            'raw_text': score_text,
                                            'trait_id': trait_id,
                                            'chinese_name': trait_name,
                                            'selector_used': selector,
                                            'headsupflag': headsupflag  # 添加 headsupflag
                                        }
                                        
                                        log_message = f"✅ 提取特質：{trait_name} = {score_value}"
                                        if headsupflag:
                                            log_message += f" (headsupflag: {headsupflag})"
                                        log_message += f" (使用選擇器: {selector})"
                                        logger.info(log_message)
                                        
                                        score_found = True
                                        break
                                        
                            except Exception:
                                continue
                        
                        if not score_found:
                            logger.warning(f"⚠️ 無法找到 {trait_name} 的分數")
                            
                    except Exception as trait_error:
                        logger.warning(f"❌ 處理特質標籤失敗：{str(trait_error)}")
                        continue
                
                # 策略2: 直接搜尋所有包含百分比的元素並與特質名稱匹配
                if len(result_data['trait_scores']) == 0:
                    logger.info("策略1無效果，嘗試策略2: 搜尋所有百分比元素")
                    
                    # 獲取所有可能的特質名稱
                    trait_names = []
                    for label in trait_labels:
                        try:
                            trait_name_element = label.find_element(By.CSS_SELECTOR, ".tooltips.assessmentTooltips")
                            trait_names.append(trait_name_element.text.strip())
                        except:
                            continue
                    
                    # 搜尋所有包含數字的元素
                    score_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '%') or contains(@class, 'per') or contains(@class, 'score')]")
                    
                    for element in score_elements:
                        try:
                            element_text = element.text.strip()
                            parent_text = element.find_element(By.XPATH, "../..").text.strip()
                            
                            # 提取數字
                            score_match = re.search(r'(\d+(?:\.\d+)?)', element_text)
                            if score_match and element_text != "0" and element_text != "0.0":
                                score_value = float(score_match.group(1))
                                
                                # 嘗試匹配特質名稱
                                for trait_name in trait_names:
                                    if trait_name in parent_text or any(word in parent_text for word in trait_name.split()):
                                        # 提取 data-headsupflag 屬性
                                        headsupflag = None
                                        try:
                                            # 方法1: 從當前元素獲取
                                            headsupflag = element.get_attribute('data-headsupflag')
                                            
                                            # 方法2: 從父元素獲取
                                            if not headsupflag:
                                                parent_element = element.find_element(By.XPATH, "..")
                                                headsupflag = parent_element.get_attribute('data-headsupflag')
                                            
                                            # 方法3: 向上查找多層父元素
                                            if not headsupflag:
                                                current_element = element
                                                for i in range(5):  # 最多向上查找5層
                                                    try:
                                                        current_element = current_element.find_element(By.XPATH, "..")
                                                        headsupflag = current_element.get_attribute('data-headsupflag')
                                                        if headsupflag:
                                                            break
                                                    except:
                                                        break
                                            
                                            # 轉換字符串為整數
                                            if headsupflag:
                                                try:
                                                    headsupflag = int(headsupflag)
                                                except:
                                                    pass
                                        except:
                                            pass
                                        
                                        result_data['trait_scores'][trait_name] = {
                                            'score': score_value,
                                            'raw_text': element_text,
                                            'trait_id': f"extracted_{len(result_data['trait_scores'])}",
                                            'chinese_name': trait_name,
                                            'extraction_method': 'strategy_2',
                                            'headsupflag': headsupflag
                                        }
                                        
                                        log_message = f"✅ 策略2提取：{trait_name} = {score_value}"
                                        if headsupflag:
                                            log_message += f" (headsupflag: {headsupflag})"
                                        logger.info(log_message)
                                        break
                                        
                        except:
                            continue
                            
            except Exception as e:
                logger.error(f"提取特質分數失敗：{str(e)}")
            
            # 4. 提取所有百分比元素作為備用
            try:
                percentage_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '%')]")
                for element in percentage_elements:
                    try:
                        element_data = {
                            'text': element.text.strip(),
                            'tag_name': element.tag_name,
                            'id': element.get_attribute('id') or '',
                            'class': element.get_attribute('class') or ''
                        }
                        if element_data['text'] and '%' in element_data['text']:
                            result_data['raw_elements'].append(element_data)
                    except:
                        continue
                logger.info(f"提取了 {len(result_data['raw_elements'])} 個包含百分比的元素")
            except Exception as e:
                logger.warning(f"提取百分比元素失敗：{str(e)}")
            
            # 數據提取完成後的檢查和調試
            total_meaningful_data = len(result_data['performance_metrics']) + len(result_data['trait_scores'])
            
            logger.info(f"測驗數據提取完成，共提取：")
            logger.info(f"  - 用戶資訊：{len(result_data['user_info'])} 項")
            logger.info(f"  - 性能指標：{len(result_data['performance_metrics'])} 項")
            logger.info(f"  - 特質分數：{len(result_data['trait_scores'])} 項")
            logger.info(f"  - 原始元素：{len(result_data['raw_elements'])} 個")
            
            # 如果沒有提取到有意義的數據，進行調試
            if total_meaningful_data == 0:
                logger.warning("⚠️ 未提取到有意義的數據，啟動調試模式")
                
                try:
                    # 保存頁面截圖
                    screenshot_path = f"debug_screenshot_{timezone.now().strftime('%Y%m%d_%H%M%S')}.png"
                    self.driver.save_screenshot(screenshot_path)
                    logger.info(f"頁面截圖已保存：{screenshot_path}")
                    
                    # 保存頁面HTML源碼
                    html_path = f"debug_page_source_{timezone.now().strftime('%Y%m%d_%H%M%S')}.html"
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    logger.info(f"頁面HTML已保存：{html_path}")
                    
                    # 記錄當前頁面URL和標題
                    result_data['debug_info'] = {
                        'current_url': self.driver.current_url,
                        'page_title': self.driver.title,
                        'screenshot_path': screenshot_path,
                        'html_path': html_path,
                        'page_text_preview': self.driver.page_source[:1000]  # 前1000字符預覽
                    }
                    
                except Exception as debug_error:
                    logger.error(f"調試信息保存失敗：{str(debug_error)}")
            
            return result_data
            
        except Exception as e:
            logger.error(f"提取測驗數據失敗：{str(e)}")
            return None
    
    def extract_user_info(self, data):
        """提取用戶基本資訊"""
        try:
            # 嘗試多種用戶名選擇器
            user_selectors = ["#userName", ".user-name", ".name", "#lblUserName"]
            
            for selector in user_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element.text.strip():
                        data['user_info']['name'] = element.text.strip()
                        logger.info(f"提取用戶名：{data['user_info']['name']}")
                        break
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"提取用戶資訊失敗：{str(e)}")
    
    def extract_performance_metrics(self, data, test_project):
        """提取性能指標"""
        try:
            # 根據測驗項目配置提取評分和預測欄位
            
            # 提取評分欄位 (score_field_system)
            if test_project.score_field_system:
                try:
                    score_element = self.driver.find_element(
                        By.CSS_SELECTOR, 
                        f".PredictorProgressDiv[data-short-desc*='{test_project.score_field_system}'] .ProgressPer"
                    )
                    score_value = score_element.text.strip()
                    data['performance_metrics']['score_value'] = score_value
                    logger.info(f"提取評分值：{score_value}")
                    
                except Exception as e:
                    logger.warning(f"提取評分欄位失敗：{str(e)}")
            
            # 提取預測欄位 (prediction_field_system)
            if test_project.prediction_field_system:
                try:
                    prediction_element = self.driver.find_element(
                        By.CSS_SELECTOR, 
                        f".PredictorProgressDiv[data-short-desc*='{test_project.prediction_field_system}'] .ProgressPer"
                    )
                    prediction_value = prediction_element.text.strip()
                    data['performance_metrics']['prediction_value'] = prediction_value
                    logger.info(f"提取預測值：{prediction_value}")
                    
                except Exception as e:
                    logger.warning(f"提取預測欄位失敗：{str(e)}")
            
            # 通用方法：搜尋所有 Performance Potential 相關元素
            try:
                performance_containers = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    ".PredictorProgressDiv"
                )
                
                for container in performance_containers:
                    try:
                        metric_name = container.get_attribute('data-short-desc')
                        value_element = container.find_element(By.CSS_SELECTOR, '.ProgressPer')
                        metric_value = value_element.text.strip()
                        
                        if metric_name and metric_value:
                            data['performance_metrics'][metric_name] = metric_value
                            logger.info(f"提取性能指標：{metric_name} = {metric_value}")
                            
                    except:
                        continue
                        
            except Exception as e:
                logger.warning(f"通用性能指標提取失敗：{str(e)}")
                
        except Exception as e:
            logger.error(f"提取性能指標失敗：{str(e)}")
    
    def extract_trait_scores(self):
        """提取特質分數 - 改良版"""
        print("📊 開始提取特質分數...")
        
        # 保存頁面以供檢查
        with open('trait_scores_page.html', 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        print("💾 特質分數頁面已保存")
        
        trait_data = {}
        
        # 方法1: 通過 lbl_bizform 找到特質名稱和對應分數
        try:
            # 找到所有特質標籤元素
            trait_labels = self.driver.find_elements(By.CSS_SELECTOR, "[id^='lbl_bizform_']")
            print(f"找到 {len(trait_labels)} 個特質標籤")
            
            for label in trait_labels:
                try:
                    # 提取特質名稱
                    trait_name_element = label.find_element(By.CSS_SELECTOR, ".tooltips.assessmentTooltips")
                    trait_name = trait_name_element.text.strip()
                    
                    # 獲取對應的ID
                    label_id = label.get_attribute('id')
                    trait_id = label_id.replace('lbl_bizform_', '')
                    
                    # 尋找對應的分數元素
                    score_selector = f"#lbl_bizform_{trait_id} + .val-aptitudes .kp-per-value"
                    try:
                        score_element = self.driver.find_element(By.CSS_SELECTOR, score_selector)
                        score_text = score_element.text.strip()
                        
                        # 提取數字
                        import re
                        score_match = re.search(r'(\d+)', score_text)
                        if score_match:
                            score_value = int(score_match.group(1))
                            
                            trait_data[trait_name] = {
                                'score': score_value,
                                'raw_text': score_text,
                                'trait_id': trait_id
                            }
                            print(f"✅ {trait_name}: {score_value}%")
                            
                            # 高亮顯示
                            self.driver.execute_script("arguments[0].style.border='2px solid yellow'", score_element)
                            
                    except Exception as score_error:
                        print(f"❌ 無法找到 {trait_name} 的分數: {score_error}")
                        
                except Exception as trait_error:
                    print(f"❌ 處理特質標籤失敗: {trait_error}")
                    continue
                    
        except Exception as e:
            print(f"❌ 方法1失敗: {e}")
    
    def extract_percentage_elements(self, data):
        """提取所有包含百分比的元素作為備用數據"""
        try:
            percentage_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '%')]")
            
            for element in percentage_elements:
                try:
                    element_data = {
                        'text': element.text.strip(),
                        'tag_name': element.tag_name,
                        'id': element.get_attribute('id') or '',
                        'class': element.get_attribute('class') or '',
                        'parent_text': element.find_element(By.XPATH, "./..").text.strip()[:100]
                    }
                    
                    if element_data['text'] and '%' in element_data['text']:
                        data['raw_elements'].append(element_data)
                        
                except:
                    continue
            
            logger.info(f"提取了 {len(data['raw_elements'])} 個包含百分比的元素")
            
        except Exception as e:
            logger.warning(f"提取百分比元素失敗：{str(e)}")
    
    def save_extracted_data(self, raw_data, test_invitation):
        """保存提取的數據到數據庫"""
        try:
            logger.info("開始保存測驗數據到數據庫")
            
            # 創建或更新 TestProjectResult
            test_result, created = TestProjectResult.objects.get_or_create(
                test_invitation=test_invitation,
                defaults={
                    'test_project': test_invitation.test_project,
                    'crawl_status': 'completed',
                    'crawled_at': timezone.now()
                }
            )
            
            if not created:
                # 如果已存在，更新數據
                test_result.crawl_status = 'completed'
                test_result.crawled_at = timezone.now()
            
            # 保存原始數據，確保不為 None
            raw_data = raw_data or {}
            logger.info(f"原始數據內容：{raw_data}")
            test_result.raw_data = raw_data

            def _parse_completion_time(value):
                if not value:
                    return None
                if isinstance(value, datetime):
                    dt = value
                    return dt if timezone.is_aware(dt) else timezone.make_aware(dt, timezone.get_current_timezone())
                if isinstance(value, (int, float)):
                    try:
                        tz = timezone.get_current_timezone()
                        dt = datetime.fromtimestamp(value, tz=timezone.utc)
                        return dt.astimezone(tz)
                    except Exception:
                        return None
                if isinstance(value, str):
                    candidate = value.strip()
                    if not candidate:
                        return None
                    dt = parse_datetime(candidate)
                    if not dt:
                        # 嘗試常見格式
                        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M'):
                            try:
                                dt = datetime.strptime(candidate, fmt)
                                break
                            except ValueError:
                                continue
                    if dt:
                        return dt if timezone.is_aware(dt) else timezone.make_aware(dt, timezone.get_current_timezone())
                return None

            completion_candidates = []

            completion_candidates.append(raw_data.get('completion_time'))
            completion_candidates.append(raw_data.get('test_completion_time'))

            details_data = raw_data.get('details') or {}
            if isinstance(details_data, dict):
                completion_candidates.extend([
                    details_data.get('test_completion_time'),
                    details_data.get('completion_time'),
                    details_data.get('completed_time'),
                ])

            performance_metrics = raw_data.get('performance_metrics') or {}
            if isinstance(performance_metrics, dict):
                for key in ('test_completion_time', 'completion_time', 'completed_time', 'Completion Time'):
                    completion_candidates.append(performance_metrics.get(key))

            extraction_metadata = raw_data.get('extraction_metadata') or {}
            if isinstance(extraction_metadata, dict):
                completion_candidates.append(extraction_metadata.get('completion_time'))

            parsed_completion = None
            for candidate in completion_candidates:
                parsed_completion = _parse_completion_time(candidate)
                if parsed_completion:
                    break

            if parsed_completion:
                if not test_invitation.completed_at or parsed_completion != test_invitation.completed_at:
                    test_invitation.completed_at = parsed_completion
            elif not test_invitation.completed_at:
                test_invitation.completed_at = timezone.now()

            performance_metrics = raw_data.get('performance_metrics', {}) or {}
            logger.info(f"性能指標內容：{performance_metrics}")
            trait_scores = raw_data.get('trait_scores', {}) or {}

            has_ci_score = False
            has_prediction_score = False

            # 處理性能指標
            if performance_metrics:
                # 提取評分值
                for key, value in performance_metrics.items():
                    logger.debug(f"檢查性能指標鍵值對：{key} = {value}")
                    logger.debug(f"鍵小寫形式：{key.lower()}")
                    if any(keyword in key.lower() for keyword in ['score', 'vehicles', 'ci', 'composite_index', 'ci_raw', 'ci value']):
                        score_match = re.search(r'(\d+)', str(value))
                        logger.debug(f"嘗試從值中提取分數，結果：{score_match} {str(value)}")
                        if score_match:
                            test_result.score_value = float(score_match.group(1))
                            has_ci_score = True
                            break
                # 如果沒有在性能指標找到，檢查主 raw_data
                if not has_ci_score and test_invitation.test_project:
                    score_field = getattr(test_invitation.test_project, 'score_field_system', None)
                    if score_field:
                        score_value = raw_data.get(score_field)
                        if score_value is not None:
                            try:
                                test_result.score_value = float(score_value)
                                has_ci_score = True
                            except (TypeError, ValueError):
                                pass
                
                # 提取預測值
                for key, value in performance_metrics.items():
                    if any(keyword in key.lower() for keyword in ['prediction', 'ci']):
                        test_result.prediction_value = str(value)
                        has_prediction_score = True
                        break
                if not has_prediction_score and test_invitation.test_project:
                    prediction_field = getattr(test_invitation.test_project, 'prediction_field_system', None)
                    if prediction_field:
                        prediction_value = raw_data.get(prediction_field)
                        if prediction_value is not None:
                            test_result.prediction_value = str(prediction_value)
                            has_prediction_score = True
            
            # 處理特質分數
            if trait_scores:
                test_result.trait_results = trait_scores
                # category_results 保留為空，避免重複顯示
                # test_result.category_results = {}
            
            # 保存處理後的數據
            test_result.processed_data = {
                'extraction_summary': {
                    'user_info_count': len(raw_data.get('user_info', {})),
                    'performance_metrics_count': len(raw_data.get('performance_metrics', {})),
                    'trait_scores_count': len(raw_data.get('trait_scores', {})),
                    'raw_elements_count': len(raw_data.get('raw_elements', []))
                },
                'extraction_metadata': raw_data.get('extraction_metadata', {}),
                'processing_time': timezone.now().isoformat()
            }

            # 根據資料完整度設定狀態
            if has_ci_score:
                test_result.crawl_status = 'completed'
            else:
                test_result.crawl_status = 'pending'
                logger.info("偵測到結果資料尚未完整（缺少 CI 分數），將保持 pending 以便後續重新爬取。")
            
            test_result.save()
            
            # 更新邀請狀態
            test_invitation.status = 'completed'
            test_invitation.save(update_fields=['status', 'completed_at'])
            
            logger.info(f"測驗數據保存完成 (結果ID: {test_result.id})")
            return test_result
            
        except Exception as e:
            logger.error(f"保存測驗數據失敗：{str(e)}")
            return None
    
    def crawl_test_result(self, invitation_id):
        """爬取指定邀請的測驗結果 - 主要入口方法"""
        driver_setup = False
        test_result = None  # 初始化變數
        
        try:
            logger.info(f"開始爬取測驗結果，邀請ID: {invitation_id}")
            
            # 獲取測驗邀請
            test_invitation = TestInvitation.objects.select_related('test_project', 'invitee').get(
                id=invitation_id
            )
            
            # 檢查邀請狀態 (暫時忽略此檢查以便測試)
            # if test_invitation.status != 'completed':
            #     raise Exception(f"測驗邀請狀態不正確：{test_invitation.status}")
            
            # 更新爬蟲狀態
            test_result = TestProjectResult.objects.filter(
                test_invitation=test_invitation
            ).first()
            
            if test_result:
                test_result.crawl_status = 'crawling'
                test_result.save()
            
            # 執行真實爬蟲操作
            logger.info("真實模式：開始爬取PI平台數據")
            
            # 0. 設置瀏覽器驅動
            if not self.setup_driver(headless=True):
                raise Exception("設置瀏覽器驅動失敗")
            
            # 1. 登入PI系統
            if not self.login_to_system():
                raise Exception("登入PI系統失敗")
            
            # 2. 搜尋受測者
            if not self.search_user(test_invitation.invitee.email):
                raise Exception(f"搜尋用戶失敗：{test_invitation.invitee.email}")
            
            # 3. 應用職位篩選
            job_role_name = test_invitation.test_project.job_role_system_name
            if job_role_name and not self.apply_job_role_filter(job_role_name):
                raise Exception(f"應用職位篩選失敗：{job_role_name}")
            
            # 3.5. 檢查 CI 是否存在，確認測驗已完成
            if not self.check_ci_completion():
                logger.warning("測驗尚未完成或仍在進行中，結束爬蟲流程，狀態保持不變")
                # 更新爬蟲狀態為待處理，不改為 completed
                if test_result:
                    test_result.crawl_status = 'pending'
                    test_result.save()
                return {
                    'success': False,
                    'message': '測驗尚未完成，CI 值不存在',
                    'status': 'incomplete_test'
                }
            
            # 4. 展開測驗結果詳情
            if not self.expand_test_results():
                raise Exception("展開測驗結果失敗")
            
            # 5. 檢查結果是否已展開
            if not self.check_results_expanded():
                logger.warning("測驗結果可能未完全展開，但繼續提取數據")
            
            # 6. 提取測驗數據
            raw_data = self.extract_test_data(test_invitation.test_project)
            if not raw_data:
                raise Exception("提取測驗數據失敗，未找到相關數據")
            
            # 保存數據
            result = self.save_extracted_data(raw_data, test_invitation)
            if not result:
                raise Exception("保存測驗數據失敗")
            
            logger.info(f"測驗結果爬取完成，結果ID: {result.id}")
            return result
            
        except Exception as e:
            logger.error(f"爬取測驗結果失敗：{str(e)}")
            
            # 更新失敗狀態
            if test_result:
                test_result.crawl_status = 'failed'
                test_result.save()
            
            raise e
            
        finally:
            # 清理資源
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                    logger.info("瀏覽器已關閉")
                except Exception as e:
                    logger.warning(f"關閉瀏覽器時發生錯誤：{e}")
            logger.info("爬蟲作業清理完成")
    
    def __del__(self):
        """確保瀏覽器驅動被正確關閉"""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except:
                pass

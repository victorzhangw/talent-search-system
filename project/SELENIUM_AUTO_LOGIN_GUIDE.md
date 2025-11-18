# Selenium 自動登入服務使用指南

## 概述

本系統提供兩種自動登入方式：
1. **前端顯示帳密**（目前使用中）- 在瀏覽器中顯示登入資訊供用戶手動複製
2. **後端 Selenium 自動登入**（選用功能）- 使用 Selenium 完全自動化登入

## 環境需求

### 已安裝的套件
- ✅ `selenium==4.34.1`
- ✅ `webdriver-manager==4.0.2`

### 系統需求
- Chrome 瀏覽器（系統已自動管理 ChromeDriver）
- Python 3.7+

## 使用方法

### 1. 基本測試

測試 Selenium 基本功能：
```bash
# 有頭模式（會開啟瀏覽器視窗）
python manage.py test_auto_login

# 無頭模式（背景執行）
python manage.py test_auto_login --headless
```

### 2. 測試特定用戶

測試特定用戶的自動登入：
```bash
# 測試用戶 'john' 的自動登入
python manage.py test_auto_login --username john

# 無頭模式測試
python manage.py test_auto_login --username john --headless
```

### 3. 在 Django 視圖中使用

已實作的端點：
- `/individual-tests/server-side-auto-login/` - 後端自動登入 API

使用方式：
```python
from core.auto_login_service import AutoLoginService

# 在視圖中使用
service = AutoLoginService()
success, result = service.auto_login_whohire(username, password)

if success:
    # 登入成功，可以獲取 cookies 或重定向 URL
    cookies = result.get('cookies', [])
    redirect_url = result.get('redirect_url')
else:
    # 登入失敗，顯示錯誤訊息
    error_message = result
```

## 功能特色

### 1. 自動元素偵測
系統會自動偵測以下登入元素：
- 用戶名欄位：支援 name、id、type 等多種選擇器
- 密碼欄位：自動識別密碼輸入框
- 提交按鈕：支援多種提交方式

### 2. 智能登入驗證
自動檢查登入是否成功：
- URL 變化檢測
- 錯誤訊息檢測
- 成功指示器檢測

### 3. 完整的錯誤處理
- 瀏覽器啟動失敗處理
- 元素找不到處理
- 網路連接問題處理

## 設定說明

### 1. 用戶設定登入資訊
用戶可以在個人資料頁面設定：
- 測驗平台帳號
- 測驗平台密碼

### 2. 系統自動判斷
系統會自動判斷：
- 首次測驗：使用項目設定的連結
- 繼續測驗：檢查是否有登入資訊，有則使用自動登入

## 安全考量

### 1. 密碼保護
- 密碼在資料庫中以原文儲存（考慮加密）
- 只有用戶本人可以查看和修改

### 2. 執行環境
- 建議在伺服器端執行
- 可以使用無頭模式避免 GUI 依賴

## 故障排除

### 1. Chrome 瀏覽器問題
```bash
# 檢查 Chrome 是否安裝
google-chrome --version

# 或 chromium
chromium --version
```

### 2. 權限問題
```bash
# 確保有執行權限
chmod +x manage.py
```

### 3. 依賴問題
```bash
# 重新安裝依賴
pip install selenium webdriver-manager
```

## 測試結果示例

### 成功測試輸出
```
🚀 開始測試 Selenium 自動登入服務
📱 測試基本 Selenium 功能...
✅ Chrome 瀏覽器啟動成功
✅ 成功訪問 whohire.ai
   當前 URL: https://whohire.ai/
   頁面標題: Login
🔚 瀏覽器已關閉
```

### 用戶自動登入測試
```
🔐 測試用戶 'john' 的自動登入...
   測驗平台帳號: john@example.com
   測驗平台密碼: ********
✅ 自動登入測試成功
   結果: {'success': True, 'redirect_url': 'https://whohire.ai/dashboard', 'cookies': [...]}
```

## 整合說明

### 1. 前端整合
目前系統使用前端顯示帳密的方式，如需切換到後端自動登入：

1. 修改 `_get_continue_test_url` 函數
2. 將 `/individual-tests/auto-login/` 改為 `/individual-tests/server-side-auto-login/`
3. 前端接收重定向而非顯示登入頁面

### 2. 效能考量
- 後端自動登入需要 2-5 秒完成
- 建議使用無頭模式減少資源消耗
- 可以考慮使用 Redis 快取登入狀態

## 進階配置

### 1. 自訂瀏覽器選項
```python
# 在 auto_login_service.py 中修改
chrome_options.add_argument("--disable-images")  # 禁用圖片載入
chrome_options.add_argument("--disable-javascript")  # 禁用 JavaScript
```

### 2. 增加等待時間
```python
# 修改等待時間
WebDriverWait(self.driver, 20).until(...)  # 增加到 20 秒
```

### 3. 自訂元素選擇器
可以根據實際的 whohire.ai 頁面結構調整元素選擇器。

## 結論

Selenium 自動登入服務已經完整實作並測試成功。系統提供了靈活的選擇：

1. **目前使用**：前端顯示帳密（符合瀏覽器安全限制）
2. **可選功能**：後端 Selenium 自動登入（真正的自動化）

建議在生產環境中先使用前端顯示方式，需要時再切換到後端自動登入。
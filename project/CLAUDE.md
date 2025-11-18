# CLAUDE.md - Django CPDS 專案開發指南

## 專案概述

這是一個基於 Django 的企業人格測驗系統 (CPDS - Corporate Personality Development System)，提供個人和企業用戶進行人格特質測驗、結果分析、PDF報告生成等功能。

## 技術架構

### 核心技術棧
- **後端框架**: Django 5.1
- **資料庫**: SQLite (開發環境)
- **API框架**: Django REST Framework
- **前端**: Django Templates + Bootstrap
- **認證**: JWT + Session-based
- **PDF生成**: ReportLab
- **字體支援**: Microsoft JhengHei (繁體中文)
- **爬蟲功能**: Selenium WebDriver
- **快取**: Local Memory Cache
- **郵件**: SMTP (Gmail)

### 專案結構
```
project/
├── project/                 # Django 專案設定
│   ├── settings.py         # 主要設定檔
│   ├── urls.py            # 根路由配置
│   └── wsgi.py
├── core/                   # 核心應用程式
│   ├── models.py          # 資料模型
│   ├── views.py           # 視圖邏輯
│   ├── urls.py            # 路由配置
│   ├── middleware.py      # 中間件
│   └── validators.py      # 自定義驗證器
├── api/                   # REST API 應用程式
├── utils/                 # 工具模組
│   ├── pdf_report_generator.py  # PDF報告生成器
│   └── url_shortener.py   # 短網址服務
├── templates/             # HTML 模板
├── static/               # 靜態檔案
├── media/                # 媒體檔案
└── manage.py
```

## 核心功能模組

### 1. 用戶系統
- **模型**: `User`, `IndividualProfile`, `EnterpriseProfile`
- **功能**: 註冊、登入、郵件驗證、密碼重設
- **用戶類型**: 個人用戶、企業用戶、管理員
- **企業審核**: 企業用戶需要管理員審核才能啟用

### 2. 測驗系統
- **測驗項目**: 由管理員建立和管理
- **邀請機制**: 企業可邀請用戶參與測驗
- **結果爬取**: 使用 Selenium 從外部測驗平台爬取結果
- **批量處理**: 支援批量邀請和結果處理

### 3. PDF報告生成系統
- **檔案位置**: `utils/pdf_report_generator.py`
- **重要設定**:
  - 字體: Microsoft JhengHei (優先) → DejaVu Sans (備用)
  - 頁面邊距: `self.top_margin = 3.5 * cm`
  - 頁首圖片: Header_img.png (全寬度)
  - 頁尾圖片: Footer_img.png (僅最後一頁)

#### PDF報告結構
1. **第一頁**: 封面頁
   - 頁首圖片 (全寬度)
   - 測驗項目標題
   - 受測人資訊表格 (支援自動換行)

2. **第二頁**: 測驗說明頁
   - 測驗簡介 (來自資料庫)
   - 使用指南 (來自資料庫)
   - 注意事項 (來自資料庫)

3. **第三頁及後續**: 結果分析頁
   - 特質向度雷達圖
   - 各向度數值與說明
   - 綜合分析
   - 發展建議

#### 重要技術細節
- **關鍵修復**: 使用 `drawCentredString` 而非 `drawCentredText`
- **圖片處理**: `preserveAspectRatio=False` 確保圖片填滿指定區域
- **頁面計數**: 固定使用頁碼 7 作為最後一頁判斷
- **文字換行**: 使用 `Paragraph` 包裝長文字內容
- **對齊設定**: 表格內容左對齊 `('ALIGN', (1, 0), (1, -1), 'LEFT')`

### 4. 點數系統
- **點數管理**: 用戶點數餘額、消費記錄
- **購買功能**: 點數購買和訂單管理
- **消費控制**: 測驗邀請需要消費點數
- **管理功能**: 管理員可調整用戶點數

### 5. 企業管理功能
- **測驗邀請**: 企業可邀請特定用戶參與測驗
- **邀請模板**: 可建立和管理邀請郵件模板
- **統計報表**: 企業測驗使用統計
- **批量操作**: 支援批量邀請和結果處理
- **智能短網址**: 支援多階段重定向邏輯的短網址系統

### 6. 短網址系統
- **檔案位置**: `utils/url_shortener.py`
- **路由**: `/s/<short_code>/`
- **智能重定向邏輯**:
  - **第一次點擊**: 導向測驗項目設定的測驗連結
  - **第二次以後點擊**: 導向 `https://pi.perception-group.com/`
  - **截止日期後**: 顯示過期通知頁面，不重定向
- **統計功能**: 自動記錄點擊次數與訪問統計
- **快取機制**: 使用 Redis/Memory Cache 存儲映射關係

## 開發規範

### 代碼風格
- 使用繁體中文註解和文件字串
- 模型欄位使用 `verbose_name` 提供中文說明
- 遵循 Django 最佳實踐
- 使用類別視圖 (Class-Based Views)

### 安全考量
- 實作了多層安全中間件
- 登入嘗試限制
- CSRF 保護
- XSS 過濾
- 速率限制

### 資料庫設計
- 使用 UUID 作為敏感令牌
- 適當的外鍵關係和索引
- 支援軟刪除機制
- 完整的審計追蹤

## 重要設定

### 郵件設定
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
```

### 點數系統設定
```python
POINT_SYSTEM_ENABLED = True
DEFAULT_POINTS_FOR_INDIVIDUAL = 2
DEFAULT_POINTS_FOR_ENTERPRISE = 4
```

### 爬蟲設定
```python
CRAWLER_SETTINGS = {
    'TIMEOUT': 30,
    'RETRY_TIMES': 3,
    'DELAY_BETWEEN_REQUESTS': 2,
    'HEADLESS': True,
}

# 自動爬蟲排程
CELERY_BEAT_SCHEDULE = {
    'crawl-pending-test-results': {
        'task': 'core.tasks.crawl_all_pending_results',
        'schedule': crontab(minute=0, hour='*/1'),  # 每1小時執行一次
        'options': {'queue': 'crawler'},
    }
}
```

## 常用命令

### 開發環境啟動
```bash
python manage.py runserver
```

### 資料庫遷移
```bash
python manage.py makemigrations
python manage.py migrate
```

### 建立超級用戶
```bash
python manage.py createsuperuser
```

### 靜態檔案收集
```bash
python manage.py collectstatic
```

## 故障排除

### PDF 生成問題
1. **PDF 檔案過小 (<1KB)**: 檢查 ReportLab 方法名稱是否正確
2. **中文字體問題**: 確認 Microsoft JhengHei 字體已註冊
3. **圖片顯示問題**: 檢查圖片路徑和 `preserveAspectRatio` 設定
4. **頁面計數錯誤**: 使用固定頁碼而非動態計算

### 爬蟲問題
1. **頁面加載失敗**: 增加 `TIMEOUT` 時間
2. **反爬蟲機制**: 調整 `DELAY_BETWEEN_REQUESTS`
3. **元素定位失敗**: 檢查目標網站是否更新了 HTML 結構

### 郵件發送問題
1. 檢查 Gmail 應用程式密碼設定
2. 確認防火牆未阻擋 SMTP 連接
3. 驗證 `DEFAULT_FROM_EMAIL` 設定

## 部署注意事項

### 生產環境設定
- 將 `DEBUG = False`
- 設定正確的 `ALLOWED_HOSTS`
- 使用 PostgreSQL 或 MySQL 替代 SQLite
- 啟用 HTTPS 相關安全設定
- 設定專用的郵件服務
- 配置 Redis 作為快取後端

### 媒體檔案處理
- 設定 Web 服務器 (Nginx/Apache) 直接服務靜態檔案
- 考慮使用 CDN 加速靜態資源
- 定期備份媒體檔案

## API 文檔

### 認證
系統支援 JWT 和 Session 兩種認證方式：
- JWT: 用於 API 訪問
- Session: 用於 Web 介面

### 重要端點
- `/api/`: REST API 根路徑
- `/admin/`: Django 管理後台
- `/enterprise/`: 企業功能
- `/points/`: 點數系統

## 聯絡資訊

如有開發相關問題，請聯繫專案負責人或查閱 Django 官方文檔。

---
*此文檔最後更新: 2025-07-15*
*Django 版本: 5.1*
*Python 版本: 3.8+*
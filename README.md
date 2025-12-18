# 人才搜索系統

一個基於 AI 的智能人才搜索和匹配系統，支持自然語言查詢和多維度特質分析。

---

## 🚀 快速開始

### 最簡單的方式

#### Windows 用戶

1. **檢查環境**（首次使用）

   ```batch
   check-environment.bat
   ```

2. **啟動系統**

   ```batch
   start.bat
   ```

   或直接雙擊 `start.bat`

3. **等待** 瀏覽器自動打開

4. **開始使用**！

#### Linux/Mac 用戶

1. **設置權限**（首次使用）

   ```bash
   chmod +x start.sh stop.sh
   ```

2. **啟動系統**

   ```bash
   ./start.sh
   ```

3. **開始使用**！

就這麼簡單！✨

### 停止系統

```batch
# Windows
stop.bat

# Linux/Mac
./stop.sh
```

---

## 📋 系統要求

- Windows 10/11
- Python 3.10+
- 網絡連接（需連接數據庫）

---

## 🎯 主要功能

- ✅ **自然語言搜索** - 用對話方式搜索人才
- ✅ **特質分析** - 基於 JSONB 存儲的多維度特質評分
- ✅ **智能匹配** - AI 驅動的候選人匹配算法
- ✅ **實時查詢** - 快速的數據庫查詢和結果展示
- ✅ **友好界面** - 直觀的聊天式用戶界面

---

## 📁 啟動腳本

| 文件                      | 說明                | 平台      |
| ------------------------- | ------------------- | --------- |
| **start.bat** ⭐          | 啟動前端 + 後端服務 | Windows   |
| **start.sh** ⭐           | 啟動前端 + 後端服務 | Linux/Mac |
| **stop.bat**              | 停止所有服務        | Windows   |
| **stop.sh**               | 停止所有服務        | Linux/Mac |
| **check-environment.bat** | 環境檢查            | Windows   |

詳細使用說明請查看：[啟動腳本使用指南](docs/guides/STARTUP_SCRIPTS.md)

---

## 🌐 訪問地址

啟動後可以訪問：

### 前端界面

- **主界面**: http://localhost:5173

### 後端 API

- **API 文檔**: http://localhost:8000/docs
- **健康檢查**: http://localhost:8000/health
- **人才搜索**: http://localhost:8000/api/talent
- **HR 諮詢**: http://localhost:8000/api/hr-consult

---

## 💬 使用聊天界面

### 為什麼需要 HTTP 服務器？

聊天界面是一個 HTML 文件，需要通過 HTTP 服務器訪問才能正常工作（避免 CORS 錯誤）。

### 系統架構

```
瀏覽器 (http://localhost:8080)
    ↓
前端 HTTP 服務器 (端口 8080) - 提供 HTML/CSS/JS
    ↓
後端 API 服務 (端口 8000) - 提供數據 API
    ↓
PostgreSQL 數據庫 (通過 SSH 隧道)
```

### 查詢範例

- "列出所有人"
- "找到 admin"
- "找到 Howard"
- "找一個溝通能力強的人"

---

## 📖 文檔

### 📚 完整文檔中心

查看 **[docs/README.md](./docs/README.md)** 獲取完整的文檔索引和系統說明。

### 🚀 快速入門

- **[快速開始指南](./docs/guides/GETTING_STARTED.md)** - 安裝和基本設置
- **[環境變數配置](./docs/configuration/README_ENV.md)** - 配置系統環境
- **[Prompt 配置](./docs/configuration/PROMPT_CONFIGURATION.md)** - 自定義 AI 回答風格

### 🔧 操作指南

- **[部署指南](./docs/guides/DEPLOYMENT.md)** - 生產環境部署
- **[故障排除](./docs/guides/TROUBLESHOOTING.md)** - 常見問題解決

### 🧪 測試

- **[測試說明](./docs/tests/README.md)** - 測試腳本使用指南
- 運行測試：`cd docs/tests && python test_env_config.py`

### 📊 遷移報告

- [配置遷移總結](./docs/migration-reports/CONFIGURATION_MIGRATION_SUMMARY.md)
- [LLM 配置遷移](./docs/migration-reports/LLM_CONFIG_MIGRATION_COMPLETE.md)
- [Prompt 配置遷移](./docs/migration-reports/PROMPT_CONFIG_MIGRATION_COMPLETE.md)

---

## 🔧 開發

### 項目結構

```
AI-Character-Chatbot/
├── BackEnd/                    # 後端代碼
│   ├── start_fixed_api.py     # API 啟動腳本
│   ├── talent_search_engine_fixed.py  # 搜索引擎
│   └── venv/                  # 虛擬環境
├── docs/                      # 文檔
│   └── backend/              # 後端文檔
├── tests/                     # 測試腳本
├── talent-chat-frontend.html # 聊天界面
├── test_api.html             # 測試頁面
└── *.bat                     # 啟動腳本
```

### 手動啟動

```bash
# 啟動後端 API
cd BackEnd
.\venv\Scripts\python.exe start_fixed_api.py

# 啟動前端服務器（新視窗）
python -m http.server 8080
```

### 運行測試

```bash
cd tests
python test_fixed_search.py
python test_jsonb_queries.py
```

---

## 🐛 常見問題

### Q: 雙擊 bat 文件後閃退

**解決**: 右鍵點擊 → 編輯，或在 cmd 中運行查看錯誤

### Q: 端口被占用

**解決**:

```bash
# 檢查端口
netstat -ano | find "8000"
netstat -ano | find "8080"

# 停止服務
停止所有服務.bat
```

### Q: 看到 CORS 錯誤

**解決**: 確保通過 HTTP 服務器訪問（http://localhost:8080/...），不要直接打開文件

### Q: 無法連接數據庫

**解決**:

1. 檢查 SSH 私鑰文件
2. 檢查網絡連接
3. 查看服務日誌

更多問題請查看 [快速啟動指南.md](./快速啟動指南.md)

---

## 🎯 核心技術

- **後端**: FastAPI + Python
- **數據庫**: PostgreSQL (JSONB)
- **前端**: Vue.js 3 + Axios
- **搜索引擎**: 自定義特質匹配算法
- **AI**: LLM 意圖識別（可選）

---

## 📊 數據結構

測試數據以 **JSONB** 格式存儲在 PostgreSQL 中：

```json
{
  "communication": {
    "chinese_name": "溝通能力",
    "score": 82.5,
    "percentile": 75,
    "level": "高"
  },
  "leadership": {
    "chinese_name": "領導力",
    "score": 78.0,
    "percentile": 68,
    "level": "中等"
  }
}
```

詳見 [JSONB 存儲方案總結](./docs/backend/JSONB存儲方案總結.md)

---

## 🔄 版本歷史

### v2.0.0 (2025-11-15)

- ✅ 修正數據庫查詢邏輯
- ✅ 使用正確的表結構（core_user + individual_test_result）
- ✅ 創建完整的啟動腳本
- ✅ 添加前端 HTTP 服務器支持
- ✅ 完善文檔系統

### v1.0.0

- 初始版本

---

## 📞 獲取幫助

1. 查看 [快速啟動指南](./快速啟動指南.md)
2. 查看 [如何使用聊天界面](./如何使用聊天界面.md)
3. 查看 [docs/backend/](./docs/backend/) 中的技術文檔

---

## 📄 授權

本項目為內部使用。

---

## 🙏 致謝

感謝所有貢獻者和測試人員。

---

**最後更新**: 2025-11-15  
**版本**: 2.0.0  
**狀態**: ✅ 已測試通過

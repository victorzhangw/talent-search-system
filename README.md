# 人才搜索系統

一個基於 AI 的智能人才搜索和匹配系統，支持自然語言查詢和多維度特質分析。

---

## 🚀 快速開始

### 最簡單的方式

1. **雙擊運行** `啟動完整系統.bat`
2. **等待** 瀏覽器自動打開
3. **開始使用** 聊天界面！

就這麼簡單！✨

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

| 文件                    | 說明                  | 適合         |
| ----------------------- | --------------------- | ------------ |
| **啟動完整系統.bat** ⭐ | 啟動 API + 前端服務器 | **推薦使用** |
| 啟動人才搜索服務.bat    | 只啟動 API 服務       | 開發調試     |
| 啟動並測試.bat          | 啟動 API + 測試頁面   | 快速測試     |
| 停止所有服務.bat        | 停止所有服務          | 清理進程     |
| 人才搜索系統.bat        | 控制面板（選單）      | 完整管理     |

---

## 🌐 訪問地址

啟動後可以訪問：

- **聊天界面**: http://localhost:8080/talent-chat-frontend.html
- **測試頁面**: http://localhost:8080/test_api.html
- **API 文檔**: http://localhost:8000/docs
- **健康檢查**: http://localhost:8000/health

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

### 快速入門

- [README-快速開始.md](./README-快速開始.md) - 最簡單的開始方式
- [快速啟動指南.md](./快速啟動指南.md) - 詳細的啟動說明
- [如何使用聊天界面.md](./如何使用聊天界面.md) - 聊天界面使用說明
- [使用說明-圖解.txt](./使用說明-圖解.txt) - 圖解版說明

### 技術文檔

- [搜索功能修正總結](./docs/backend/搜索功能修正總結-2025-11-15.md)
- [JSONB 存儲方案總結](./docs/backend/JSONB存儲方案總結.md)
- [JSON 數據結構說明](./docs/backend/JSON數據結構說明.md)
- [數據庫修正說明](./docs/backend/數據庫修正說明.md)

### 完整文檔索引

查看 [docs/backend/README.md](./docs/backend/README.md) 獲取所有文檔列表。

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

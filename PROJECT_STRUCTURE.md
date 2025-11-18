# 專案結構說明

本專案已重新整理，將文檔和測試代碼分別放置在獨立的資料夾中。

## 資料夾結構

```
AI-Character-Chatbot/
├── BackEnd/                    # 後端核心代碼
│   ├── conversation_enhanced_search.py
│   ├── conversation_manager.py
│   ├── query_traits.py
│   ├── talent_search_api.py
│   ├── talent_search_api_v2.py
│   ├── requirements.txt
│   ├── requirements_api.txt
│   └── *.bat                   # 批次執行檔
│
├── tests/                      # 測試代碼
│   ├── test_*.py              # 各種測試腳本
│   ├── check_*.py             # 檢查腳本
│   ├── create_howard_*.py     # Howard 用戶創建腳本
│   ├── diagnose_*.py          # 診斷腳本
│   └── db_schema_analyzer.py  # 資料庫架構分析
│
├── docs/                       # 文檔資料夾
│   ├── *.md                   # 根目錄文檔
│   ├── *.pdf                  # PDF 文件
│   ├── *.pptx                 # 簡報文件
│   └── backend/               # 後端相關文檔
│       ├── *.md               # Markdown 文檔
│       ├── *.json             # JSON 配置文檔
│       ├── *.sql              # SQL 架構文檔
│       ├── *.txt              # 文字文檔
│       ├── 數據庫修正說明.md  # 數據庫結構修正說明
│       ├── 搜索功能修正總結-2025-11-15.md  # 搜索功能修正
│       ├── JSON數據結構說明.md  # JSONB 數據結構詳解
│       └── JSONB存儲方案總結.md  # JSONB 存儲方案總結
│
├── assets/                     # 資源文件
│   ├── *.png                  # 圖片文件
│   └── *.svg                  # SVG 圖檔
│
├── .kiro/                      # Kiro 配置
├── project/                    # 專案相關文件
├── talent-chat-frontend.html  # 前端頁面
└── *.bat                       # 啟動腳本
```

## 主要變更

1. **測試代碼** → `tests/` 資料夾

   - 所有 `test_*.py` 測試腳本
   - 所有 `check_*.py` 檢查腳本
   - 所有 `create_howard_*.py` 創建腳本
   - 所有 `diagnose_*.py` 診斷腳本

2. **文檔** → `docs/` 資料夾

   - 根目錄的所有 `.md` 文件
   - 所有 `.pdf` 和 `.pptx` 文件
   - `docs/backend/` 包含所有後端相關文檔

3. **資源文件** → `assets/` 資料夾

   - 所有圖片文件 (`.png`, `.svg`)

4. **核心代碼** → `BackEnd/` 資料夾
   - 保留核心 API 和功能代碼
   - 保留配置文件和批次腳本

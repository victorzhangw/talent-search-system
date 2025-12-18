# 人才管理系統文檔

## 歡迎

歡迎使用人才管理系統文檔中心。本文檔提供完整的系統設置、配置和使用指南。

## 文檔結構

```
docs/
├── README.md                          # 本文件
├── guides/                            # 操作指南
│   ├── GETTING_STARTED.md            # 快速開始指南
│   ├── DEPLOYMENT.md                 # 部署指南
│   └── TROUBLESHOOTING.md            # 故障排除指南
├── configuration/                     # 配置文檔
│   ├── README_ENV.md                 # 環境變數配置
│   └── PROMPT_CONFIGURATION.md       # Prompt 配置說明
├── tests/                            # 測試腳本
│   ├── test_env_config.py           # 環境變數測試
│   ├── test_consecutive_calls.py    # 連續調用測試
│   ├── test_candidate_79.py         # 候選人測試
│   └── test_prompt_modification.py  # Prompt 修改測試
└── migration-reports/                # 遷移報告
    ├── LLM_CONFIG_MIGRATION_COMPLETE.md
    ├── PROMPT_CONFIG_MIGRATION_COMPLETE.md
    ├── CONFIGURATION_MIGRATION_SUMMARY.md
    ├── ENTERPRISE_ID_FIX.md
    ├── FINAL_FIX_INSTRUCTIONS.md
    └── HR_CONSULTATION_FIX_SUMMARY.md
```

## 快速導航

### 🚀 新手入門

如果您是第一次使用本系統，請從這裡開始：

1. [快速開始指南](guides/GETTING_STARTED.md) - 安裝和基本設置
2. [環境變數配置](configuration/README_ENV.md) - 配置系統環境
3. [API 文檔](http://localhost:8000/docs) - 了解 API 端點

### 📝 配置指南

系統配置相關文檔：

- [環境變數配置](configuration/README_ENV.md) - 資料庫、LLM API 等配置
- [Prompt 配置](configuration/PROMPT_CONFIGURATION.md) - 自定義 AI 回答風格

### 🔧 操作指南

日常操作和維護：

- [部署指南](guides/DEPLOYMENT.md) - 生產環境部署
- [故障排除](guides/TROUBLESHOOTING.md) - 常見問題解決

### 🧪 測試

運行測試以驗證系統配置：

```bash
cd docs/tests

# 測試環境變數配置
python test_env_config.py

# 測試連續 API 調用
python test_consecutive_calls.py

# 測試 Prompt 動態修改
python test_prompt_modification.py
```

### 📊 遷移報告

查看系統升級和遷移記錄：

- [配置遷移總結](migration-reports/CONFIGURATION_MIGRATION_SUMMARY.md)
- [LLM 配置遷移](migration-reports/LLM_CONFIG_MIGRATION_COMPLETE.md)
- [Prompt 配置遷移](migration-reports/PROMPT_CONFIG_MIGRATION_COMPLETE.md)

## 系統架構

### 核心組件

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue.js)                         │
│  - 候選人管理界面                                         │
│  - HR 諮詢界面                                           │
│  - 人才搜索界面                                           │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP/REST API
                      ▼
┌─────────────────────────────────────────────────────────┐
│                 後端 API (FastAPI)                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │  人才搜索模組                                     │   │
│  │  - 對話式搜索                                     │   │
│  │  - 意圖識別                                       │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  HR 諮詢模組                                      │   │
│  │  - 候選人分析                                     │   │
│  │  - 職業建議                                       │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │  面試模組                                         │   │
│  │  - 面試問題生成                                   │   │
│  │  - 回答評估                                       │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
┌──────────────────┐      ┌──────────────────┐
│  PostgreSQL      │      │  LLM API         │
│  資料庫           │      │  (SiliconFlow)   │
└──────────────────┘      └──────────────────┘
```

### 配置管理

```
┌─────────────────────────────────────────────────────────┐
│                    應用層                                │
│  - main_api.py                                          │
│  - hr_consultation_routes.py                            │
│  - hr_consultation_service.py                           │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  配置管理層                              │
│  - prompt_manager.py (Prompt 管理)                      │
│  - python-dotenv (環境變數管理)                          │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   配置文件層                             │
│  - .env.local (環境變數)                                │
│  - prompts/hr_consultation_prompts.json (Prompt 模板)   │
└─────────────────────────────────────────────────────────┘
```

## 主要功能

### 1. 人才搜索

- 對話式搜索界面
- 智能意圖識別
- 多維度篩選
- 相似度匹配

### 2. HR 諮詢

- 候選人特定諮詢
- 通用 HR 問題解答
- 基於測評數據的建議
- 職業發展規劃

### 3. 面試管理

- 自動生成面試問題
- 回答評估和打分
- 面試記錄管理

### 4. 候選人管理

- 候選人檔案管理
- 測評結果查看
- 特質分析
- 歷史記錄追蹤

## 技術棧

### 後端

- **框架**: FastAPI
- **語言**: Python 3.10+
- **資料庫**: PostgreSQL
- **ORM**: psycopg2
- **LLM**: SiliconFlow API (DeepSeek-V3)

### 前端

- **框架**: Vue.js 3
- **構建工具**: Vite
- **狀態管理**: Pinia
- **UI 組件**: Element Plus

### 部署

- **容器化**: Docker
- **雲平台**: Render
- **反向代理**: Nginx

## 環境要求

- Python 3.10+
- Node.js 16+
- PostgreSQL 12+
- 4GB+ RAM
- 10GB+ 磁碟空間

## 安全性

### 資料保護

- 環境變數管理敏感資訊
- SSH 隧道加密資料庫連接
- HTTPS 加密傳輸

### 訪問控制

- API 身份驗證
- 企業數據隔離
- 角色權限管理

### 合規性

- GDPR 合規
- 數據加密存儲
- 審計日誌

## 性能優化

- 資料庫查詢優化
- 連接池管理
- API 響應快取
- 靜態資源 CDN

## 監控和日誌

- 應用日誌記錄
- 錯誤追蹤
- 性能監控
- 使用統計

## 支援和社群

### 獲取幫助

1. 查看 [故障排除指南](guides/TROUBLESHOOTING.md)
2. 搜索已知問題
3. 聯繫開發團隊

### 貢獻

歡迎貢獻代碼、文檔或報告問題。

### 授權

本專案採用 MIT 授權。

## 更新日誌

### v2.0.0 (2025-12-17)

- ✅ LLM 配置遷移到環境變數
- ✅ Prompt 配置遷移到 JSON 文件
- ✅ 支援動態重新載入配置
- ✅ 完整的文檔和測試

### v1.0.0 (2025-12-11)

- ✅ HR 諮詢模組重構
- ✅ 企業數據隔離
- ✅ 連續 API 調用修復

## 路線圖

### 短期計劃

- [ ] 多語言支援
- [ ] A/B 測試框架
- [ ] 性能優化

### 長期計劃

- [ ] 機器學習模型整合
- [ ] 移動應用
- [ ] 高級分析儀表板

## 相關連結

- [專案 GitHub](https://github.com/your-repo)
- [API 文檔](http://localhost:8000/docs)
- [問題追蹤](https://github.com/your-repo/issues)

---

**最後更新**: 2025-12-17  
**文檔版本**: 2.0.0

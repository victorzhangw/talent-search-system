# API 配置說明

## 問題診斷：雲端和本地搜索結果差異

### 根本原因

前端 HTML 文件中的 API URL 配置問題導致雲端環境無法正確連接到後端 API。

### 已修正的問題

#### 1. 自動環境檢測

現在前端會自動檢測運行環境並使用正確的 API URL：

- **本地開發**: `http://localhost:8000`
- **Render 部署**: `https://talent-search-api.onrender.com`
- **Vercel 部署**: `https://talent-search-api.onrender.com`
- **Netlify 部署**: `https://talent-search-api.onrender.com`

#### 2. 重新開始按鈕

在聊天輸入區域新增了「重新開始」按鈕，功能包括：

- 清除所有對話記錄
- 重置搜索結果
- 清空已選擇的候選人
- 關閉面試問題對話框
- 恢復初始歡迎訊息

### 部署檢查清單

#### 後端 API (Render)

確保以下環境變數已設定：

```bash
ENVIRONMENT=production
DB_SSH_HOST=54.199.255.239
DB_SSH_PORT=22
DB_SSH_USERNAME=victor_cheng
DB_SSH_PRIVATE_KEY=<your-private-key-content>
DB_HOST=localhost
DB_PORT=5432
DB_NAME=projectdb
DB_USER=projectuser
DB_PASSWORD=projectpass
LLM_API_KEY=<your-llm-api-key>
LLM_API_HOST=https://api.siliconflow.cn
LLM_MODEL=deepseek-ai/DeepSeek-V3
```

#### 前端 (Vercel/Netlify/Render)

無需額外配置，前端會自動檢測環境。

### 測試步驟

1. **本地測試**

   ```bash
   # 啟動後端
   cd BackEnd
   python app.py

   # 在瀏覽器打開
   # file:///path/to/talent-chat-frontend.html
   ```

2. **雲端測試**
   - 訪問部署的前端 URL
   - 打開瀏覽器開發者工具 (F12)
   - 查看 Console 確認 API URL
   - 測試搜索功能

### 常見問題

#### Q: 雲端搜索沒有結果

**A**: 檢查以下項目：

1. 後端 API 是否正常運行 (訪問 `/health` 端點)
2. CORS 設定是否正確
3. 資料庫連接是否成功
4. SSH 隧道是否建立

#### Q: 本地可以搜索，雲端不行

**A**:

1. 確認前端正在使用正確的 API URL (查看瀏覽器 Console)
2. 確認後端 CORS 允許前端域名
3. 檢查後端日誌查看錯誤訊息

#### Q: 重新開始按鈕沒有反應

**A**:

1. 檢查瀏覽器 Console 是否有 JavaScript 錯誤
2. 確認 Vue.js 已正確載入
3. 清除瀏覽器快取後重試

### 監控和調試

#### 前端調試

```javascript
// 在瀏覽器 Console 中執行
console.log("API URL:", app.apiBaseUrl);
console.log("環境:", window.location.hostname);
```

#### 後端調試

查看 Render 日誌：

```bash
# 在 Render Dashboard 中查看 Logs
# 或使用 Render CLI
render logs -s <service-name>
```

### 更新記錄

- **2024-11-18**:
  - ✅ 新增自動環境檢測
  - ✅ 新增重新開始按鈕
  - ✅ 修正 API URL 配置問題
  - ✅ 改善錯誤處理和日誌輸出

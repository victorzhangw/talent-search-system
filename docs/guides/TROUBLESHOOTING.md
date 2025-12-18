# 故障排除指南

## 概述

本指南提供常見問題的解決方案。

## 資料庫相關問題

### 問題 1: 無法連接到資料庫

**錯誤訊息：**

```
connection to server at "localhost", port 5432 failed: Connection refused
```

**可能原因：**

1. SSH 隧道未建立
2. 資料庫服務未運行
3. 防火牆阻擋連接

**解決方案：**

1. 檢查 SSH 金鑰權限：

```bash
chmod 600 BackEnd/private-key-openssh.pem
```

2. 測試 SSH 連接：

```bash
ssh -i BackEnd/private-key-openssh.pem user@host
```

3. 檢查資料庫配置：

```bash
# 確認 .env.local 中的配置正確
cat BackEnd/.env.local | grep DB_
```

### 問題 2: 資料庫查詢超時

**錯誤訊息：**

```
psycopg2.OperationalError: timeout expired
```

**解決方案：**

1. 增加查詢超時時間
2. 優化查詢語句
3. 添加適當的索引

## LLM API 相關問題

### 問題 3: LLM API 返回 401 錯誤

**錯誤訊息：**

```
{"detail": "Unauthorized"}
```

**可能原因：**

1. API Key 無效或過期
2. API Key 未正確設置

**解決方案：**

1. 檢查環境變數：

```bash
# 在 BackEnd 目錄
python -c "import os; from dotenv import load_dotenv; load_dotenv('.env.local'); print('API Key:', os.getenv('LLM_API_KEY')[:10] + '...')"
```

2. 驗證 API Key：

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.siliconflow.cn/v1/models
```

3. 更新 API Key：
   編輯 `BackEnd/.env.local`，更新 `LLM_API_KEY`

### 問題 4: LLM API 返回 429 錯誤

**錯誤訊息：**

```
{"detail": "Rate limit exceeded"}
```

**解決方案：**

1. 檢查 API 配額
2. 實施請求限流
3. 考慮升級 API 計劃

### 問題 5: LLM 回答質量差

**可能原因：**

1. Prompt 設計不當
2. Temperature 設置不合適
3. Max tokens 太少

**解決方案：**

1. 調整 Prompt 模板：
   編輯 `BackEnd/prompts/hr_consultation_prompts.json`

2. 調整 LLM 參數：

```bash
# 在 .env.local 中
LLM_TEMPERATURE=0.7  # 降低以獲得更確定的回答
LLM_MAX_TOKENS=800   # 增加以獲得更長的回答
```

3. 重新載入 Prompt：

```python
from prompt_manager import get_prompt_manager
prompt_manager = get_prompt_manager()
prompt_manager.reload_prompts()
```

## 應用啟動問題

### 問題 6: 後端啟動失敗

**錯誤訊息：**

```
ModuleNotFoundError: No module named 'xxx'
```

**解決方案：**

1. 安裝缺少的依賴：

```bash
cd BackEnd
pip install -r requirements.txt
```

2. 檢查 Python 版本：

```bash
python --version  # 應該是 3.10+
```

3. 使用虛擬環境：

```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 問題 7: 前端啟動失敗

**錯誤訊息：**

```
Error: Cannot find module 'xxx'
```

**解決方案：**

1. 清除 node_modules 並重新安裝：

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

2. 檢查 Node.js 版本：

```bash
node --version  # 應該是 16+
```

### 問題 8: 端口已被佔用

**錯誤訊息：**

```
Error: listen EADDRINUSE: address already in use :::8000
```

**解決方案：**

1. 查找佔用端口的進程：

```bash
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000
```

2. 終止進程：

```bash
# Windows
taskkill /PID <PID> /F

# Linux/Mac
kill -9 <PID>
```

3. 或更改端口：
   在 `.env.local` 中修改 `PORT=8001`

## API 請求問題

### 問題 9: API 返回 404 錯誤

**錯誤訊息：**

```
{"detail": "Not Found"}
```

**可能原因：**

1. API 路徑錯誤
2. 候選人不存在
3. 企業 ID 不匹配

**解決方案：**

1. 檢查 API 路徑：
   訪問 `http://localhost:8000/docs` 查看正確的 API 路徑

2. 驗證候選人 ID：

```bash
curl http://localhost:8000/api/hr-consult/candidates?limit=10
```

3. 檢查請求 payload：

```json
{
  "query": "候選人適合什麼職位？",
  "candidate_id": 79,
  "candidate_name": "候選人姓名"
}
```

### 問題 10: API 返回 500 錯誤

**錯誤訊息：**

```
{"detail": "Internal Server Error"}
```

**解決方案：**

1. 查看後端日誌：

```bash
# 查看最近的錯誤
tail -f logs/app.log
```

2. 檢查資料庫連接狀態

3. 驗證環境變數配置

4. 運行測試腳本：

```bash
cd docs/tests
python test_env_config.py
```

### 問題 11: 連續 API 調用失敗

**症狀：**
第一次調用成功，第二次調用失敗

**可能原因：**
資料庫連接狀態管理問題

**解決方案：**

已在代碼中修復，確保使用最新版本：

```bash
git pull origin main
```

## 前端相關問題

### 問題 12: 前端無法連接後端

**錯誤訊息：**

```
Network Error
```

**解決方案：**

1. 確認後端正在運行：

```bash
curl http://localhost:8000/health
```

2. 檢查 CORS 配置：
   後端應該允許前端域名

3. 檢查前端 API 配置：
   查看 `frontend/src/api/` 中的 API 端點配置

### 問題 13: 前端顯示空白頁面

**可能原因：**

1. JavaScript 錯誤
2. 路由配置問題
3. 構建錯誤

**解決方案：**

1. 打開瀏覽器開發者工具查看錯誤

2. 重新構建前端：

```bash
cd frontend
npm run build
```

3. 清除瀏覽器快取

## 配置相關問題

### 問題 14: Prompt 修改未生效

**可能原因：**

1. JSON 格式錯誤
2. 未重新載入 Prompt
3. 變數名錯誤

**解決方案：**

1. 驗證 JSON 格式：

```bash
python -m json.tool BackEnd/prompts/hr_consultation_prompts.json
```

2. 重新啟動應用或重新載入 Prompt：

```python
from prompt_manager import get_prompt_manager
prompt_manager = get_prompt_manager()
prompt_manager.reload_prompts()
```

3. 檢查變數名是否正確：
   參考 [Prompt 配置文檔](../configuration/PROMPT_CONFIGURATION.md)

### 問題 15: 環境變數未生效

**可能原因：**

1. 文件名錯誤（應該是 `.env.local`）
2. 格式錯誤
3. 未重新啟動應用

**解決方案：**

1. 確認文件名：

```bash
ls -la BackEnd/.env.local
```

2. 檢查格式：

```bash
# 每行格式應該是 KEY=VALUE
# 不要有多餘的空格
cat BackEnd/.env.local
```

3. 重新啟動應用

## 性能問題

### 問題 16: API 響應緩慢

**可能原因：**

1. 資料庫查詢慢
2. LLM API 調用慢
3. 網絡延遲

**解決方案：**

1. 添加資料庫索引

2. 實施快取策略

3. 優化查詢語句

4. 使用連接池

### 問題 17: 記憶體使用過高

**解決方案：**

1. 檢查是否有記憶體洩漏

2. 限制並發請求數

3. 增加伺服器記憶體

## 測試相關問題

### 問題 18: 測試腳本失敗

**解決方案：**

1. 確認後端正在運行：

```bash
curl http://localhost:8000/health
```

2. 檢查測試配置：
   測試腳本中的 API 端點是否正確

3. 查看詳細錯誤訊息

## 獲取更多幫助

如果以上解決方案無法解決您的問題：

1. 查看完整日誌
2. 運行診斷腳本
3. 聯繫開發團隊

## 相關資源

- [快速開始指南](GETTING_STARTED.md)
- [環境變數配置](../configuration/README_ENV.md)
- [Prompt 配置](../configuration/PROMPT_CONFIGURATION.md)
- [API 文檔](http://localhost:8000/docs)

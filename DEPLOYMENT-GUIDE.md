# Render 部署指南

本指南將幫助你將人才搜索系統部署到 Render 免費平台。

## 📋 部署前準備

### 1. 創建 GitHub Repository

```bash
# 初始化 Git（如果還沒有）
git init
git add .
git commit -m "Initial commit"

# 推送到 GitHub
git remote add origin https://github.com/你的用戶名/talent-search-system.git
git branch -M main
git push -u origin main
```

### 2. 準備環境變數

你需要準備以下環境變數（部署時會用到）：

**數據庫連接**：

- `DB_SSH_HOST`: SSH 主機地址（例如：54.199.255.239）
- `DB_SSH_USERNAME`: SSH 用戶名
- `DB_SSH_PRIVATE_KEY`: SSH 私鑰內容（完整的 PEM 文件內容）
- `DB_NAME`: 數據庫名稱
- `DB_USER`: 數據庫用戶名
- `DB_PASSWORD`: 數據庫密碼

**LLM API**：

- `LLM_API_KEY`: LLM API 密鑰

## 🚀 部署步驟

### 方法 1: 使用 render.yaml（推薦）

1. **登入 Render**

   - 訪問 https://render.com
   - 使用 GitHub 帳號登入

2. **創建新的 Blueprint**

   - 點擊 "New +" → "Blueprint"
   - 連接你的 GitHub repository
   - Render 會自動檢測 `render.yaml` 文件

3. **配置環境變數**

   - 在 Blueprint 設定頁面，填入所有環境變數
   - 特別注意 `DB_SSH_PRIVATE_KEY` 需要填入完整的私鑰內容

4. **部署**
   - 點擊 "Apply" 開始部署
   - 等待 5-10 分鐘完成建置

### 方法 2: 手動創建服務

#### 步驟 1: 部署後端 API

1. 點擊 "New +" → "Web Service"
2. 連接 GitHub repository
3. 配置：

   - **Name**: `talent-search-api`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r BackEnd/requirements.txt`
   - **Start Command**: `cd BackEnd && python start_fixed_api.py`
   - **Plan**: Free

4. 添加環境變數（見上方列表）

5. 點擊 "Create Web Service"

#### 步驟 2: 部署前端

1. 點擊 "New +" → "Static Site"
2. 連接同一個 GitHub repository
3. 配置：

   - **Name**: `talent-search-frontend`
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Publish Directory**: `frontend/dist`

4. 添加環境變數：

   - `VITE_API_URL`: 後端 API 的 URL（從步驟 1 獲取）

5. 點擊 "Create Static Site"

## 🔧 代碼調整

### 1. 修改後端配置為環境變數

需要修改 `BackEnd/start_fixed_api.py`，將硬編碼的配置改為環境變數：

```python
import os

DB_CONFIG = {
    'ssh_host': os.getenv('DB_SSH_HOST', '54.199.255.239'),
    'ssh_port': int(os.getenv('DB_SSH_PORT', '22')),
    'ssh_username': os.getenv('DB_SSH_USERNAME', 'victor_cheng'),
    'ssh_private_key': os.getenv('DB_SSH_PRIVATE_KEY', 'private-key-openssh.pem'),
    'db_host': os.getenv('DB_HOST', 'localhost'),
    'db_port': int(os.getenv('DB_PORT', '5432')),
    'db_name': os.getenv('DB_NAME', 'projectdb'),
    'db_user': os.getenv('DB_USER', 'projectuser'),
    'db_password': os.getenv('DB_PASSWORD', 'projectpass')
}

LLM_CONFIG = {
    'api_key': os.getenv('LLM_API_KEY', 'sk-xxx'),
    'api_host': os.getenv('LLM_API_HOST', 'https://api.siliconflow.cn'),
    'model': os.getenv('LLM_MODEL', 'deepseek-ai/DeepSeek-V3'),
    'endpoint': os.getenv('LLM_API_HOST', 'https://api.siliconflow.cn') + '/v1/chat/completions'
}
```

### 2. 修改前端 API 配置

修改 `frontend/src/api/talent.js`：

```javascript
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
```

### 3. 添加 requirements.txt（如果缺少）

確保 `BackEnd/requirements.txt` 包含所有依賴：

```txt
fastapi==0.104.1
uvicorn==0.24.0
psycopg2-binary==2.9.9
sshtunnel==0.4.0
paramiko==3.4.0
httpx==0.25.1
pydantic==2.5.0
```

## 📊 部署後檢查

### 1. 檢查後端健康狀態

訪問：`https://你的後端URL.onrender.com/health`

應該看到：

```json
{
  "status": "healthy",
  "database": "connected",
  "version": "2.0.0"
}
```

### 2. 檢查前端

訪問：`https://你的前端URL.onrender.com`

應該能看到聊天界面。

### 3. 測試搜索功能

在聊天界面輸入：

- "列出所有人"
- "找到 admin"
- "找一個溝通能力強的人"

## ⚠️ 注意事項

### 免費方案限制

1. **休眠機制**

   - 閒置 15 分鐘後服務會休眠
   - 首次喚醒需要 30-60 秒
   - 解決方案：使用 UptimeRobot 等服務定期 ping

2. **運行時間**

   - 每月 750 小時免費（約 31 天）
   - 足夠單個服務全天候運行

3. **數據庫**
   - Render 免費 PostgreSQL 只有 90 天
   - 建議使用 Supabase 或保持 SSH 隧道連接現有數據庫

### SSH 私鑰處理

在 Render 環境變數中設定 `DB_SSH_PRIVATE_KEY` 時：

1. 複製完整的私鑰文件內容（包括 `-----BEGIN OPENSSH PRIVATE KEY-----` 和 `-----END OPENSSH PRIVATE KEY-----`）
2. 在代碼中需要將字符串寫入臨時文件：

```python
import tempfile
import os

def get_ssh_key_path():
    """將環境變數中的私鑰寫入臨時文件"""
    private_key_content = os.getenv('DB_SSH_PRIVATE_KEY')

    if private_key_content and not os.path.exists(private_key_content):
        # 如果是私鑰內容而不是文件路徑
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as f:
            f.write(private_key_content)
            os.chmod(f.name, 0o600)
            return f.name

    return private_key_content
```

## 🔄 持續部署

Render 支持自動部署：

1. 每次推送到 GitHub main 分支
2. Render 會自動重新建置和部署
3. 無需手動操作

## 💡 優化建議

### 1. 使用 Supabase 數據庫

如果不想使用 SSH 隧道，可以：

1. 在 Supabase 創建免費 PostgreSQL
2. 遷移數據
3. 移除 SSH 隧道相關代碼
4. 直接連接 Supabase

### 2. 添加日誌監控

在 Render Dashboard 可以查看：

- 實時日誌
- 部署歷史
- 性能指標

### 3. 自定義域名

Render 免費方案支持自定義域名：

- 前端：`talent.你的域名.com`
- 後端：`api.你的域名.com`

## 🆘 常見問題

### Q: 部署失敗怎麼辦？

1. 檢查 Render 日誌
2. 確認所有環境變數正確設定
3. 確認 requirements.txt 包含所有依賴

### Q: 數據庫連接失敗？

1. 檢查 SSH 私鑰格式
2. 確認 SSH 主機可以從 Render 訪問
3. 檢查防火牆設定

### Q: 前端無法連接後端？

1. 確認 `VITE_API_URL` 設定正確
2. 檢查 CORS 設定
3. 確認後端服務正在運行

## 📞 獲取幫助

- Render 文檔：https://render.com/docs
- Render 社區：https://community.render.com
- GitHub Issues：在你的 repository 創建 issue

---

**部署完成後，你的系統將可以通過以下 URL 訪問**：

- 前端：`https://talent-search-frontend.onrender.com`
- 後端：`https://talent-search-api.onrender.com`

祝部署順利！🎉

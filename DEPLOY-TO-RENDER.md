# 🚀 快速部署到 Render

## 5 分鐘部署指南

### 步驟 1: 準備 GitHub Repository

```bash
# 如果還沒有 Git repository
git init
git add .
git commit -m "Ready for deployment"

# 推送到 GitHub
git remote add origin https://github.com/你的用戶名/你的repo名稱.git
git push -u origin main
```

### 步驟 2: 登入 Render

1. 訪問 https://render.com
2. 使用 GitHub 帳號登入
3. 授權 Render 訪問你的 repository

### 步驟 3: 創建 Blueprint

1. 點擊 **"New +"** → **"Blueprint"**
2. 選擇你的 GitHub repository
3. Render 會自動檢測 `render.yaml` 文件

### 步驟 4: 設定環境變數

在 Blueprint 設定頁面，添加以下環境變數：

#### 必填項目：

| 變數名稱             | 說明         | 範例值              |
| -------------------- | ------------ | ------------------- |
| `DB_SSH_HOST`        | SSH 主機地址 | `54.199.255.239`    |
| `DB_SSH_USERNAME`    | SSH 用戶名   | `victor_cheng`      |
| `DB_SSH_PRIVATE_KEY` | SSH 私鑰內容 | 完整的 PEM 文件內容 |
| `DB_NAME`            | 數據庫名稱   | `projectdb`         |
| `DB_USER`            | 數據庫用戶   | `projectuser`       |
| `DB_PASSWORD`        | 數據庫密碼   | `你的密碼`          |
| `LLM_API_KEY`        | LLM API 密鑰 | `sk-xxx...`         |

#### 如何複製 SSH 私鑰：

**Windows (PowerShell)**:

```powershell
Get-Content BackEnd\private-key-openssh.pem | clip
```

**Windows (CMD)**:

```cmd
type BackEnd\private-key-openssh.pem
```

然後複製完整內容（包括 `-----BEGIN OPENSSH PRIVATE KEY-----` 和 `-----END OPENSSH PRIVATE KEY-----`）

### 步驟 5: 部署

1. 點擊 **"Apply"** 開始部署
2. 等待 5-10 分鐘
3. 完成！

## 📊 部署後檢查

### 檢查後端

訪問：`https://talent-search-api.onrender.com/health`

應該看到：

```json
{
  "status": "healthy",
  "database": "connected"
}
```

### 檢查前端

訪問：`https://talent-search-frontend.onrender.com`

應該能看到聊天界面。

## ⚠️ 重要提醒

### 免費方案限制

1. **服務會休眠**

   - 閒置 15 分鐘後休眠
   - 首次喚醒需 30-60 秒
   - 解決方案：使用 [UptimeRobot](https://uptimerobot.com) 定期 ping

2. **運行時間**
   - 每月 750 小時免費
   - 足夠單個服務全天候運行

### 保持服務活躍

使用 UptimeRobot 免費監控：

1. 註冊 https://uptimerobot.com
2. 添加監控：
   - URL: `https://talent-search-api.onrender.com/health`
   - 監控間隔: 5 分鐘
3. 這樣服務就不會休眠了

## 🔄 自動部署

設定完成後：

- 每次推送到 GitHub main 分支
- Render 會自動重新部署
- 無需手動操作

## 🆘 遇到問題？

### 部署失敗

1. 檢查 Render Dashboard 的日誌
2. 確認所有環境變數正確設定
3. 確認 GitHub repository 包含所有文件

### 數據庫連接失敗

1. 檢查 SSH 私鑰是否完整複製
2. 確認 SSH 主機可以從外部訪問
3. 檢查數據庫用戶名和密碼

### 前端無法連接後端

1. 確認後端服務正在運行
2. 檢查 `VITE_API_URL` 環境變數
3. 查看瀏覽器控制台錯誤

## 📞 獲取幫助

- 查看完整指南：[DEPLOYMENT-GUIDE.md](./DEPLOYMENT-GUIDE.md)
- Render 文檔：https://render.com/docs
- 創建 GitHub Issue

---

**部署成功後，你的系統將可以在全球任何地方訪問！** 🎉

# 🚀 Fly.io 部署指南

## 為什麼選擇 Fly.io？

✅ **優點**：

- 不會休眠（比 Render 好）
- 全球 CDN（速度快）
- 免費 PostgreSQL
- 3 個免費應用
- 配置靈活

⚠️ **注意**：

- 需要信用卡驗證
- 配置稍微複雜

---

## 📋 準備工作

### 1. 安裝 Fly CLI

**Windows (PowerShell)**:

```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

安裝後，重新打開終端機。

### 2. 驗證安裝

```bash
fly version
```

應該看到版本號。

---

## 🎯 部署步驟

### 步驟 1: 登入 Fly.io

```bash
fly auth login
```

這會打開瀏覽器，使用 GitHub 或 Email 登入。

### 步驟 2: 創建應用

```bash
# 在專案根目錄執行
fly launch --no-deploy
```

**配置選項**：

- App Name: `talent-search-api`（或自動生成）
- Region: 選擇 `nrt` (Tokyo, Japan) - 離台灣最近
- PostgreSQL: 選擇 `No`（我們使用現有數據庫）
- Redis: 選擇 `No`

### 步驟 3: 設定環境變數

```bash
# 數據庫配置
fly secrets set DB_SSH_HOST=54.199.255.239
fly secrets set DB_SSH_USERNAME=victor_cheng
fly secrets set DB_NAME=projectdb
fly secrets set DB_USER=projectuser
fly secrets set DB_PASSWORD=你的密碼

# SSH 私鑰（需要特殊處理）
# 方法 1: 從文件讀取
fly secrets set DB_SSH_PRIVATE_KEY="$(cat BackEnd/private-key-openssh.pem)"

# 方法 2: 手動複製貼上（Windows）
# 先運行: type BackEnd\private-key-openssh.pem
# 然後: fly secrets set DB_SSH_PRIVATE_KEY="貼上私鑰內容"

# LLM API
fly secrets set LLM_API_KEY=你的LLM密鑰
```

### 步驟 4: 部署

```bash
fly deploy
```

等待 3-5 分鐘，應用會自動建置和部署。

### 步驟 5: 檢查狀態

```bash
# 查看應用狀態
fly status

# 查看日誌
fly logs

# 打開應用
fly open
```

---

## 🌐 部署前端

### 方法 1: 使用 Vercel（推薦）

前端建議使用 Vercel，因為：

- ✅ 完全免費
- ✅ 全球 CDN
- ✅ 自動部署

**步驟**：

1. **訪問 Vercel**

   - https://vercel.com
   - 使用 GitHub 登入

2. **導入專案**

   - 選擇 `victorzhangw/talent-search-system`

3. **配置**

   - Framework: Vite
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`

4. **環境變數**

   - `VITE_API_URL`: `https://你的應用名稱.fly.dev`

5. **部署**
   - 點擊 "Deploy"

### 方法 2: 也部署到 Fly.io

如果想全部在 Fly.io：

1. **創建前端配置**

創建 `frontend/fly.toml`:

```toml
app = "talent-search-frontend"
primary_region = "nrt"

[build]
  [build.args]
    NODE_VERSION = "18"

[env]
  PORT = "8080"

[[statics]]
  guest_path = "/app/dist"
  url_prefix = "/"
```

2. **部署前端**

```bash
cd frontend
fly launch --no-deploy
fly deploy
```

---

## 📊 免費額度

### Fly.io 免費方案

- ✅ **3 個應用**（你可以部署前端+後端）
- ✅ **共享 CPU**: 3 個 shared-cpu-1x
- ✅ **記憶體**: 256MB per app
- ✅ **流量**: 160GB/月
- ✅ **PostgreSQL**: 3GB 存儲

### 你的使用

- 後端 API: 1 個應用
- 前端: 1 個應用（或用 Vercel）
- **總計**: 2 個應用 < 3 個 ✅

---

## 🔧 常用命令

### 管理應用

```bash
# 查看所有應用
fly apps list

# 查看應用狀態
fly status

# 查看日誌
fly logs

# 實時日誌
fly logs -f

# SSH 進入容器
fly ssh console

# 重啟應用
fly apps restart talent-search-api
```

### 管理環境變數

```bash
# 查看所有 secrets
fly secrets list

# 設定 secret
fly secrets set KEY=VALUE

# 刪除 secret
fly secrets unset KEY
```

### 擴展應用

```bash
# 增加記憶體
fly scale memory 512

# 增加 CPU
fly scale vm shared-cpu-2x

# 增加實例數量
fly scale count 2
```

---

## ⚠️ 重要提醒

### SSH 私鑰設定

由於私鑰包含換行符，設定時需要特別處理：

**Windows PowerShell**:

```powershell
# 讀取文件並設定
$key = Get-Content BackEnd\private-key-openssh.pem -Raw
fly secrets set "DB_SSH_PRIVATE_KEY=$key"
```

**或者手動**:

1. 複製私鑰內容（包括 BEGIN 和 END 行）
2. 使用引號包裹：
   ```bash
   fly secrets set DB_SSH_PRIVATE_KEY="-----BEGIN OPENSSH PRIVATE KEY-----
   ...完整內容...
   -----END OPENSSH PRIVATE KEY-----"
   ```

### 信用卡驗證

- Fly.io 需要信用卡驗證
- 不會自動扣款
- 只有超過免費額度才會收費
- 可以設定消費上限

---

## 🔄 更新部署

### 自動部署

設定 GitHub Actions 自動部署：

創建 `.github/workflows/fly-deploy.yml`:

```yaml
name: Deploy to Fly.io

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

### 手動部署

```bash
# 修改代碼後
git add .
git commit -m "更新說明"
git push

# 部署到 Fly.io
fly deploy
```

---

## 📈 監控和日誌

### 查看指標

```bash
# 查看應用指標
fly dashboard

# 查看實時日誌
fly logs -f

# 查看特定時間的日誌
fly logs --since 1h
```

### 設定告警

在 Fly.io Dashboard:

- 設定 CPU 使用率告警
- 設定記憶體使用率告警
- 設定錯誤率告警

---

## 💰 成本估算

### 免費方案（推薦）

```
後端 (Fly.io): $0/月
前端 (Vercel): $0/月
監控 (UptimeRobot): $0/月
─────────────────────
總計: $0/月
```

### 如果需要擴展

```
後端 (更多記憶體): ~$5/月
前端 (Vercel Pro): $20/月
數據庫 (Fly.io): ~$5/月
─────────────────────
總計: ~$30/月
```

---

## 🆘 故障排除

### 部署失敗

```bash
# 查看詳細日誌
fly logs

# 檢查配置
fly config validate

# 重新部署
fly deploy --force
```

### 應用無法啟動

```bash
# SSH 進入容器檢查
fly ssh console

# 查看環境變數
fly secrets list

# 檢查健康檢查
fly checks list
```

### 連接數據庫失敗

1. 檢查 SSH 私鑰是否正確設定
2. 檢查數據庫連接資訊
3. 查看應用日誌

---

## 📞 獲取幫助

- **Fly.io 文檔**: https://fly.io/docs
- **Fly.io 社群**: https://community.fly.io
- **本專案文檔**: [FREE-HOSTING-OPTIONS.md](./FREE-HOSTING-OPTIONS.md)

---

## 🎯 快速開始

```bash
# 1. 安裝 Fly CLI
iwr https://fly.io/install.ps1 -useb | iex

# 2. 登入
fly auth login

# 3. 創建應用
fly launch --no-deploy

# 4. 設定環境變數
fly secrets set DB_SSH_HOST=54.199.255.239
fly secrets set DB_SSH_USERNAME=victor_cheng
# ... 其他環境變數

# 5. 部署
fly deploy

# 6. 檢查
fly status
fly open
```

---

**準備好了嗎？開始部署到 Fly.io 吧！** 🚀

---

**最後更新**: 2025-11-18  
**版本**: 1.0  
**狀態**: ✅ 已測試

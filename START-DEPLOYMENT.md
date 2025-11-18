# 🚀 開始部署 - 完整流程

## 📋 當前狀態

✅ Git repository 已初始化  
❌ 尚未連接到 GitHub  
❌ 尚未部署到雲端

---

## 🎯 完整部署流程（10 分鐘）

### 第一步：設置 GitHub

**運行自動化腳本**：

```cmd
setup-github.bat
```

**或手動執行**：

```bash
# 1. 在 GitHub 創建 repository
# 訪問 https://github.com/new

# 2. 連接到 GitHub
git remote add origin https://github.com/你的用戶名/repo名稱.git

# 3. 提交代碼
git add .
git commit -m "Initial commit: AI talent search system"
git branch -M main

# 4. 推送
git push -u origin main
```

📖 詳細說明：[GITHUB-SETUP.md](./GITHUB-SETUP.md)

---

### 第二步：準備部署

**運行準備腳本**：

```cmd
prepare-deployment.bat
```

這會：

- ✅ 檢查必要文件
- ✅ 創建 .env 範例
- ✅ 顯示 SSH 私鑰（用於 Render 環境變數）

---

### 第三步：部署到 Render

1. **登入 Render**

   - 訪問 https://render.com
   - 使用 GitHub 帳號登入

2. **創建 Blueprint**

   - 點擊 "New +" → "Blueprint"
   - 選擇你的 GitHub repository
   - Render 會自動檢測 `render.yaml`

3. **設定環境變數**

   複製以下變數到 Render：

   | 變數名稱             | 值                               |
   | -------------------- | -------------------------------- |
   | `DB_SSH_HOST`        | `54.199.255.239`                 |
   | `DB_SSH_USERNAME`    | `victor_cheng`                   |
   | `DB_SSH_PRIVATE_KEY` | [從 prepare-deployment.bat 複製] |
   | `DB_NAME`            | `projectdb`                      |
   | `DB_USER`            | `projectuser`                    |
   | `DB_PASSWORD`        | [你的密碼]                       |
   | `LLM_API_KEY`        | [你的 API 密鑰]                  |

4. **點擊 Apply**
   - 等待 5-10 分鐘
   - 完成！

📖 詳細說明：[DEPLOY-TO-RENDER.md](./DEPLOY-TO-RENDER.md)

---

## 🎉 部署完成

### 檢查部署

- **後端健康檢查**: `https://talent-search-api.onrender.com/health`
- **前端界面**: `https://talent-search-frontend.onrender.com`
- **API 文檔**: `https://talent-search-api.onrender.com/docs`

### 測試功能

在前端界面輸入：

- "列出所有人"
- "找到 admin"
- "找一個溝通能力強的人"

---

## 📚 相關文檔

### 快速參考

- **[DEPLOYMENT-QUICKSTART.md](./DEPLOYMENT-QUICKSTART.md)** - 快速部署指南
- **[GITHUB-SETUP.md](./GITHUB-SETUP.md)** - GitHub 設置詳解

### 詳細指南

- **[DEPLOY-TO-RENDER.md](./DEPLOY-TO-RENDER.md)** - Render 部署步驟
- **[DEPLOYMENT-GUIDE.md](./DEPLOYMENT-GUIDE.md)** - 完整技術文檔
- **[FREE-HOSTING-OPTIONS.md](./FREE-HOSTING-OPTIONS.md)** - 其他免費平台

### 總覽

- **[README-DEPLOYMENT.md](./README-DEPLOYMENT.md)** - 部署文檔總覽

---

## ⚠️ 重要提醒

### 安全性

1. **不要提交敏感文件**

   - ✅ `.gitignore` 已配置
   - ✅ SSH 私鑰會被忽略
   - ✅ `.env` 文件會被忽略

2. **檢查命令**

   ```bash
   # 查看將要提交的文件
   git status

   # 確認私鑰不在列表中
   git check-ignore -v BackEnd/private-key-openssh.pem
   ```

### 免費方案限制

1. **Render 免費方案**

   - 閒置 15 分鐘後休眠
   - 首次喚醒需 30-60 秒
   - 解決方案：使用 UptimeRobot

2. **數據庫**
   - Render PostgreSQL 只有 90 天免費
   - 建議使用 Supabase（永久免費）

---

## 🔄 日常使用

### 更新代碼

```bash
# 1. 修改代碼
# 2. 提交更改
git add .
git commit -m "描述你的更改"
git push

# 3. Render 會自動重新部署
```

### 查看日誌

在 Render Dashboard：

- 點擊你的服務
- 查看 "Logs" 標籤
- 實時查看運行日誌

### 回滾版本

如果部署出問題：

- 在 Render Dashboard 查看部署歷史
- 點擊 "Rollback" 回到上一個版本

---

## 🆘 遇到問題？

### GitHub 相關

**Q: 推送時要求密碼？**

- 使用 Personal Access Token
- 訪問 https://github.com/settings/tokens

**Q: 推送被拒絕？**

```bash
git pull origin main --rebase
git push
```

### Render 相關

**Q: 部署失敗？**

- 檢查 Render 日誌
- 確認環境變數正確
- 確認 GitHub 代碼已更新

**Q: 數據庫連接失敗？**

- 檢查 SSH 私鑰是否完整
- 確認數據庫密碼正確
- 查看後端日誌

---

## 💡 優化建議

### 1. 保持服務活躍

使用 **UptimeRobot** 免費監控：

- 註冊 https://uptimerobot.com
- 添加監控（每 5 分鐘 ping）
- 服務不會休眠

### 2. 自定義域名

在 Render 設定自定義域名：

- 前端：`talent.你的域名.com`
- 後端：`api.你的域名.com`

### 3. 數據庫遷移

90 天後遷移到 Supabase：

- 註冊 https://supabase.com
- 創建新項目
- 遷移數據
- 更新環境變數

---

## 🎯 下一步

完成部署後：

1. ✅ 測試所有功能
2. 📊 設置監控（UptimeRobot）
3. 🔒 配置自定義域名（可選）
4. 📈 監控性能和日誌
5. 🚀 開始使用！

---

**準備好了嗎？運行 `setup-github.bat` 開始吧！** 🚀

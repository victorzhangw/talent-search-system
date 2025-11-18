# 🚀 部署快速開始

## 最快 5 分鐘部署到 Render

### 準備工作

1. **設置 GitHub（首次）**

   ```cmd
   setup-github.bat
   ```

   這會：

   - 初始化 Git repository
   - 連接到 GitHub
   - 推送代碼

   詳細說明：[GITHUB-SETUP.md](./GITHUB-SETUP.md)

2. **準備部署配置**

   ```cmd
   prepare-deployment.bat
   ```

   這會檢查所有必要文件並顯示 SSH 私鑰

### 部署步驟

1. **登入 Render**

   - 訪問 https://render.com
   - 使用 GitHub 登入

2. **創建 Blueprint**

   - 點擊 "New +" → "Blueprint"
   - 選擇你的 repository
   - Render 會檢測到 `render.yaml`

3. **設定環境變數**

   複製以下變數到 Render：

   ```
   DB_SSH_HOST=54.199.255.239
   DB_SSH_USERNAME=victor_cheng
   DB_SSH_PRIVATE_KEY=[從 prepare-deployment.bat 複製]
   DB_NAME=projectdb
   DB_USER=projectuser
   DB_PASSWORD=[你的密碼]
   LLM_API_KEY=[你的 API 密鑰]
   ```

4. **點擊 Apply**
   - 等待 5-10 分鐘
   - 完成！

### 檢查部署

- **後端**: https://talent-search-api.onrender.com/health
- **前端**: https://talent-search-frontend.onrender.com

---

## 📚 詳細文檔

- **完整部署指南**: [DEPLOYMENT-GUIDE.md](./DEPLOYMENT-GUIDE.md)
- **快速部署**: [DEPLOY-TO-RENDER.md](./DEPLOY-TO-RENDER.md)
- **其他平台選項**: [FREE-HOSTING-OPTIONS.md](./FREE-HOSTING-OPTIONS.md)

---

## 🆘 遇到問題？

### 常見問題

**Q: 部署失敗？**

- 檢查 Render 日誌
- 確認環境變數正確
- 確認 SSH 私鑰完整

**Q: 數據庫連接失敗？**

- 檢查 SSH 私鑰格式
- 確認數據庫密碼正確
- 查看後端日誌

**Q: 前端無法連接後端？**

- 確認後端服務運行中
- 檢查 CORS 設定
- 查看瀏覽器控制台

### 獲取幫助

1. 查看詳細文檔
2. 檢查 Render Dashboard 日誌
3. 創建 GitHub Issue

---

**祝部署順利！** 🎉

# 🚀 Render 部署步驟（更新版）

## 📋 部署策略

由於 Render 的 Blueprint 限制，我們採用**分步部署**策略：

1. **步驟 1**: 使用 Blueprint 部署後端 API
2. **步驟 2**: 手動創建前端 Static Site

---

## 🎯 步驟 1: 部署後端 API

### 1.1 使用 Blueprint

1. **在 Render Dashboard**

   - 點擊 "New +" → "Blueprint"

2. **連接 GitHub**

   - 選擇 repository: `victorzhangw/talent-search-system`
   - Render 會檢測到 `render.yaml`

3. **設定環境變數**

   填入以下環境變數：

   | 變數名稱             | 值               | 如何獲取                                    |
   | -------------------- | ---------------- | ------------------------------------------- |
   | `DB_SSH_HOST`        | `54.199.255.239` | 已提供                                      |
   | `DB_SSH_USERNAME`    | `victor_cheng`   | 已提供                                      |
   | `DB_SSH_PRIVATE_KEY` | [私鑰內容]       | 運行 `type BackEnd\private-key-openssh.pem` |
   | `DB_NAME`            | `projectdb`      | 已提供                                      |
   | `DB_USER`            | `projectuser`    | 已提供                                      |
   | `DB_PASSWORD`        | [你的密碼]       | 你的數據庫密碼                              |
   | `LLM_API_KEY`        | [你的密鑰]       | 你的 LLM API 密鑰                           |

4. **點擊 "Apply"**

   - 等待 5-10 分鐘
   - 後端 API 開始建置

5. **獲取後端 URL**
   - 建置完成後，複製後端 URL
   - 格式：`https://talent-search-api.onrender.com`

---

## 🎯 步驟 2: 部署前端 Static Site

### 2.1 創建 Static Site

1. **在 Render Dashboard**

   - 點擊 "New +" → "Static Site"

2. **連接 GitHub**

   - 選擇同一個 repository: `victorzhangw/talent-search-system`

3. **配置設定**

   | 設定項                | 值                                            |
   | --------------------- | --------------------------------------------- |
   | **Name**              | `talent-search-frontend`                      |
   | **Branch**            | `main`                                        |
   | **Root Directory**    | 留空                                          |
   | **Build Command**     | `cd frontend && npm install && npm run build` |
   | **Publish Directory** | `frontend/dist`                               |

4. **設定環境變數**

   添加一個環境變數：

   | 變數名稱       | 值                      |
   | -------------- | ----------------------- |
   | `VITE_API_URL` | [步驟 1 獲取的後端 URL] |

   例如：`https://talent-search-api.onrender.com`

5. **點擊 "Create Static Site"**
   - 等待 3-5 分鐘
   - 前端開始建置

---

## ✅ 部署完成

### 檢查部署

1. **後端健康檢查**

   - 訪問：`https://talent-search-api.onrender.com/health`
   - 應該看到：
     ```json
     {
       "status": "healthy",
       "database": "connected"
     }
     ```

2. **前端界面**

   - 訪問：`https://talent-search-frontend.onrender.com`
   - 應該能看到聊天界面

3. **測試功能**
   - 在聊天界面輸入：
     - "列出所有人"
     - "找到 admin"
     - "找一個溝通能力強的人"

---

## 📊 部署狀態

### 你的服務

| 服務         | URL                                           | 狀態      |
| ------------ | --------------------------------------------- | --------- |
| **後端 API** | `https://talent-search-api.onrender.com`      | ⏳ 建置中 |
| **前端**     | `https://talent-search-frontend.onrender.com` | ⏳ 待創建 |
| **API 文檔** | `https://talent-search-api.onrender.com/docs` | ⏳ 建置中 |

---

## ⚠️ 重要提醒

### 免費方案限制

1. **服務休眠**

   - 閒置 15 分鐘後休眠
   - 首次喚醒需 30-60 秒
   - **解決方案**: 使用 UptimeRobot

2. **運行時間**
   - 後端: ~720 小時/月
   - 前端: 不計費（Static Site）
   - **總計**: 在 750 小時免費額度內 ✅

### 設置 UptimeRobot（避免休眠）

1. **註冊 UptimeRobot**

   - 訪問 https://uptimerobot.com
   - 免費註冊

2. **添加監控**

   - Monitor Type: HTTP(s)
   - URL: `https://talent-search-api.onrender.com/health`
   - Monitoring Interval: 5 分鐘

3. **完成**
   - 服務不會休眠了！

---

## 🔧 故障排除

### 後端建置失敗

**可能原因**：

1. 環境變數未設定
2. SSH 私鑰格式錯誤
3. 依賴安裝失敗

**解決方案**：

1. 檢查 Render 日誌
2. 確認所有環境變數正確
3. 確認 SSH 私鑰包含完整內容（包括 BEGIN 和 END 行）

### 前端建置失敗

**可能原因**：

1. `VITE_API_URL` 未設定
2. Node.js 版本不兼容
3. 依賴安裝失敗

**解決方案**：

1. 確認 `VITE_API_URL` 設定正確
2. 檢查 Render 日誌
3. 確認 `frontend/package.json` 存在

### 前端無法連接後端

**可能原因**：

1. CORS 設定問題
2. 後端 URL 錯誤
3. 後端服務未運行

**解決方案**：

1. 檢查瀏覽器控制台錯誤
2. 確認 `VITE_API_URL` 正確
3. 確認後端健康檢查通過

---

## 🔄 更新部署

### 更新代碼

```bash
# 1. 修改代碼
# 2. 提交
git add .
git commit -m "你的更改說明"

# 3. 推送
git push origin main
```

### 自動重新部署

- Render 會自動檢測 GitHub 更新
- 自動重新建置和部署
- 無需手動操作

---

## 💡 優化建議

### 1. 自定義域名

在 Render 設定自定義域名：

- 前端：`talent.你的域名.com`
- 後端：`api.你的域名.com`

### 2. 環境變數管理

使用 Render 的環境變數組：

- 開發環境
- 生產環境
- 測試環境

### 3. 監控和日誌

在 Render Dashboard：

- 查看實時日誌
- 監控性能指標
- 設置告警

---

## 📞 獲取幫助

### 文檔資源

- **Render 文檔**: https://render.com/docs
- **本專案文檔**:
  - [DEPLOYMENT-GUIDE.md](./DEPLOYMENT-GUIDE.md)
  - [FREE-HOSTING-OPTIONS.md](./FREE-HOSTING-OPTIONS.md)

### 常見問題

查看 [DEPLOY-TO-RENDER.md](./DEPLOY-TO-RENDER.md) 的常見問題章節

---

## 🎉 下一步

完成部署後：

1. ✅ 測試所有功能
2. 📊 設置 UptimeRobot 監控
3. 🔒 配置自定義域名（可選）
4. 📈 監控性能和日誌
5. 🚀 開始使用！

---

**最後更新**: 2025-11-18  
**版本**: 2.0  
**狀態**: ✅ 已測試

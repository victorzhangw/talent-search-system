# Render 手動重新部署指南

## 問題描述

推送代碼到 GitHub 後，Render 顯示 404 錯誤，因為服務還在使用舊版本的 API。

**當前狀態：**

- ✅ 代碼已推送到 GitHub/Bitbucket
- ✅ `render.yaml` 已更新為使用 `main_api:app`
- ❌ Render 服務還在運行 `talent_search_api:app`（舊版本）

**證據：**

```bash
curl https://talent-search-system.onrender.com/health
# 返回: {"version":"2.1.0"} ← 舊版本

curl https://talent-search-system.onrender.com/api/hr-consult/candidates
# 返回: 404 Not Found ← HR 諮詢路由不存在
```

---

## 解決方案：手動觸發 Render 重新部署

### 步驟 1: 登入 Render Dashboard

1. 訪問：https://dashboard.render.com
2. 使用 **GitHub 帳號登入**（最常見）
   - 或使用 Email: 檢查是否有來自 `@render.com` 的郵件

### 步驟 2: 找到服務

1. 在 Dashboard 中找到服務：**`talent-search-api`**
2. 點擊進入服務詳情頁面

### 步驟 3: 查看當前部署狀態

1. 點擊左側的 **"Events"** 標籤
2. 查看最近的部署記錄：

   - ✅ 綠色勾號 = 部署成功
   - ❌ 紅色叉號 = 部署失敗
   - 🔄 藍色圓圈 = 部署中

3. 檢查是否有最新的提交（`b18745c`）
   - 如果沒有，說明 Render 沒有自動檢測到 Git 推送

### 步驟 4: 手動觸發部署

1. 點擊右上角的 **"Manual Deploy"** 按鈕
2. 選擇部署選項：

   - **推薦**：選擇 **"Clear build cache & deploy"**
   - 這會清除緩存並重新構建，確保使用最新代碼

3. 點擊 **"Deploy"** 確認

### 步驟 5: 監控部署過程

1. 點擊左側的 **"Logs"** 標籤
2. 實時查看部署日誌：

   **預期看到的日誌：**

   ```
   ==> Checking Python version...
   Python 3.11.x

   ==> Upgrading pip...

   ==> Installing dependencies...
   Installing fastapi==0.115.0
   Installing uvicorn[standard]==0.32.0
   ...

   ==> Starting service...
   cd BackEnd && uvicorn main_api:app --host 0.0.0.0 --port 8000

   🚀 人才管理系統 API 啟動中...
   ✅ 資料庫連接成功
   ✅ HR 諮詢模組載入成功
   🎉 人才管理系統 API 啟動成功！
   ```

3. **如果看到錯誤**：
   - 紅色文字表示錯誤
   - 常見錯誤：
     - `ModuleNotFoundError` → 依賴未安裝
     - `Connection refused` → 資料庫連接失敗
     - `ImportError` → 模組導入失敗

### 步驟 6: 驗證部署成功

部署完成後（通常 3-5 分鐘），測試端點：

```bash
# 1. 測試健康檢查（應該返回新版本）
curl https://talent-search-system.onrender.com/health
# 預期: {"status":"healthy","service":"Main API","version":"2.0.0"}

# 2. 測試根路徑（應該顯示模組列表）
curl https://talent-search-system.onrender.com/
# 預期: {"modules":[{"name":"人才搜索","path":"/api/talent"},{"name":"HR 諮詢","path":"/api/hr-consult"}]}

# 3. 測試 HR 諮詢端點（應該返回候選人列表）
curl "https://talent-search-system.onrender.com/api/hr-consult/candidates?has_test_data=true&limit=10"
# 預期: {"success":true,"data":[...]}
```

---

## 常見問題排查

### Q1: 部署失敗 - ModuleNotFoundError

**原因**：依賴未正確安裝

**解決**：

1. 檢查 `requirements.txt` 是否包含所有依賴
2. 確認 `render.yaml` 的 `buildCommand` 正確
3. 清除緩存重新部署

### Q2: 部署失敗 - 資料庫連接錯誤

**原因**：環境變數未設置

**解決**：

1. 在 Render Dashboard 中點擊 **"Environment"** 標籤
2. 確認以下環境變數已設置：

   - `DB_SSH_HOST`
   - `DB_SSH_USERNAME`
   - `DB_SSH_PRIVATE_KEY`（完整私鑰內容）
   - `DB_NAME`
   - `DB_USER`
   - `DB_PASSWORD`
   - `LLM_API_KEY`

3. 如果缺少，點擊 **"Add Environment Variable"** 添加

### Q3: 部署成功但仍然 404

**原因**：路由未正確註冊

**檢查**：

1. 查看日誌中是否有：

   ```
   ✅ HR 諮詢模組載入成功
   ```

2. 如果看到：

   ```
   ❌ HR 諮詢模組載入失敗
   ```

   說明模組導入有問題，查看詳細錯誤訊息

### Q4: Render 沒有自動部署

**原因**：Webhook 未配置或失效

**解決**：

1. 在 Render Dashboard 中，點擊服務的 **"Settings"** 標籤
2. 找到 **"Build & Deploy"** 區域
3. 確認 **"Auto-Deploy"** 已啟用
4. 檢查 **"Branch"** 是否設置為 `main`

5. 如果需要重新連接 GitHub：
   - 點擊 **"Disconnect"**
   - 重新連接 GitHub repository

---

## 檢查清單

部署前確認：

- [ ] 代碼已推送到 GitHub（`git push origin main`）
- [ ] `render.yaml` 使用 `main_api:app`
- [ ] `requirements.txt` 包含所有依賴
- [ ] Render 環境變數已設置
- [ ] 手動觸發部署（Clear build cache & deploy）
- [ ] 查看部署日誌確認無錯誤
- [ ] 測試所有端點確認正常

---

## 相關文件

- [render.yaml](../render.yaml) - Render 部署配置
- [main_api.py](../BackEnd/main_api.py) - 主 API 入口
- [hr_consultation_routes.py](../BackEnd/hr_consultation_routes.py) - HR 諮詢路由

---

**最後更新**: 2025-12-19  
**狀態**: 等待 Render 重新部署

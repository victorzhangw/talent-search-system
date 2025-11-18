# Render 部署快速修復指南

## 🚨 當前錯誤

```
ModuleNotFoundError: No module named 'fastapi'
```

---

## ✅ 已完成的修復

### 1. 更新 requirements.txt

已將 `BackEnd/requirements.txt` 更新為：

```txt
# Core dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0

# Database
psycopg2-binary==2.9.9

# SSH Tunnel
sshtunnel==0.4.0
paramiko==3.4.0

# HTTP Client
httpx==0.25.1

# Python version compatibility
python-multipart==0.0.6
```

---

## 🚀 立即執行的步驟

### 步驟 1: 提交更新到 Git

```bash
git add BackEnd/requirements.txt
git commit -m "Fix: Add FastAPI and all required dependencies"
git push origin main
```

### 步驟 2: 在 Render 設定環境變數

登入 Render Dashboard，設定以下環境變數：

#### 必須立即設定：

1. **LLM_API_KEY**

   ```
   sk-xmwxrtsxgsjwuyeceydoyuopezzlqresdjyvlzrbbjeejiff
   ```

2. **DB_SSH_HOST**

   ```
   54.199.255.239
   ```

3. **DB_SSH_USERNAME**

   ```
   victor_cheng
   ```

4. **DB_NAME**

   ```
   projectdb
   ```

5. **DB_USER**

   ```
   projectuser
   ```

6. **DB_PASSWORD**

   ```
   projectpass
   ```

7. **DB_SSH_PRIVATE_KEY**
   - 打開 `BackEnd/private-key-openssh.pem`
   - 複製完整內容（包括 BEGIN 和 END 行）
   - 貼到環境變數中

### 步驟 3: 觸發重新部署

在 Render Dashboard 中：

1. 找到你的服務
2. 點擊 "Manual Deploy"
3. 選擇 "Deploy latest commit"

---

## 📋 環境變數設定截圖指南

### 在 Render Dashboard 中：

1. 點擊你的服務名稱
2. 點擊左側的 "Environment" 標籤
3. 點擊 "Add Environment Variable"
4. 輸入 Key 和 Value
5. 點擊 "Save Changes"

### 設定 SSH 私鑰的注意事項：

私鑰格式應該像這樣：

```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
...（中間省略）...
AAAAAAEC
-----END OPENSSH PRIVATE KEY-----
```

**重要**：

- 必須包含 `-----BEGIN OPENSSH PRIVATE KEY-----` 開頭
- 必須包含 `-----END OPENSSH PRIVATE KEY-----` 結尾
- 中間的內容不要有額外的空格或換行

---

## 🔍 驗證部署

### 1. 檢查 Build Log

在 Render Dashboard 的 "Logs" 標籤中，應該看到：

```
==> Installing dependencies
Collecting fastapi==0.104.1
  Downloading fastapi-0.104.1-py3-none-any.whl
...
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 ...
```

### 2. 檢查 Runtime Log

應該看到：

```
正在初始化資料庫連接...
✓ 資料庫連接完成！
✓ 特質定義載入完成！
✓ LLM 智能搜索已啟用！
✓ 初始化完成！
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 3. 測試 API

訪問：`https://your-app.onrender.com/health`

應該返回：

```json
{
  "status": "healthy",
  "database": "connected",
  "traits_loaded": 50,
  "llm_enabled": true,
  "version": "2.1.0"
}
```

---

## ⚠️ 如果還是失敗

### 檢查清單：

- [ ] `BackEnd/requirements.txt` 已更新並提交
- [ ] Git push 成功
- [ ] Render 已觸發重新部署
- [ ] 所有環境變數已設定
- [ ] SSH 私鑰格式正確（包含 BEGIN/END）
- [ ] Build Log 顯示成功安裝所有依賴

### 常見錯誤：

**錯誤 1**: 仍然顯示 `ModuleNotFoundError`

- **原因**: requirements.txt 未更新或未提交
- **解決**: 確認 Git 提交並 push

**錯誤 2**: SSH 連接失敗

- **原因**: 私鑰格式錯誤或環境變數未設定
- **解決**: 重新複製私鑰，確保格式正確

**錯誤 3**: 資料庫連接失敗

- **原因**: 資料庫環境變數錯誤
- **解決**: 檢查所有 DB\_\* 環境變數

---

## 📞 需要幫助？

如果問題持續存在，請提供：

1. Render Build Log 的完整輸出
2. Render Runtime Log 的錯誤訊息
3. 環境變數設定截圖（隱藏敏感資訊）

---

## ✅ 成功標誌

當你看到以下內容時，表示部署成功：

1. ✅ Render 服務狀態顯示 "Live" (綠色)
2. ✅ `/health` 端點返回 `"status": "healthy"`
3. ✅ 日誌中沒有錯誤訊息
4. ✅ 可以正常調用 `/api/search` 端點

恭喜！你的 API 已成功部署到 Render！🎉

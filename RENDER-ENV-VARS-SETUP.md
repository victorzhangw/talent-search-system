# 🔑 Render 環境變數設定指南

## 🎉 好消息

Python 和依賴安裝都成功了！現在只需要設定環境變數。

---

## ❌ 當前錯誤

```
ValueError: No password or public key available!
```

**原因**: SSH 私鑰環境變數 `DB_SSH_PRIVATE_KEY` 沒有設定。

---

## ✅ 需要設定的環境變數

### 必須設定的變數（7 個）

在 Render Dashboard 中設定以下環境變數：

#### 1. LLM_API_KEY

```
sk-xmwxrtsxgsjwuyeceydoyuopezzlqresdjyvlzrbbjeejiff
```

#### 2. DB_SSH_HOST

```
54.199.255.239
```

#### 3. DB_SSH_USERNAME

```
victor_cheng
```

#### 4. DB_NAME

```
projectdb
```

#### 5. DB_USER

```
projectuser
```

#### 6. DB_PASSWORD

```
projectpass
```

#### 7. DB_SSH_PRIVATE_KEY（最重要！）

這個需要從 `BackEnd/private-key-openssh.pem` 文件中複製完整內容。

---

## 📋 設定 SSH 私鑰的詳細步驟

### 步驟 1: 獲取私鑰內容

在本地執行：

```bash
# Windows (PowerShell)
Get-Content BackEnd/private-key-openssh.pem | clip

# 或者直接打開文件複製
notepad BackEnd/private-key-openssh.pem
```

### 步驟 2: 複製完整內容

私鑰格式應該像這樣：

```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
NhAAAAAwEAAQAAAYEAyJ8Zx... (很多行)
...
AAAAAAEC
-----END OPENSSH PRIVATE KEY-----
```

**重要**：

- ✅ 必須包含 `-----BEGIN OPENSSH PRIVATE KEY-----`
- ✅ 必須包含 `-----END OPENSSH PRIVATE KEY-----`
- ✅ 包含所有中間的內容
- ✅ 保持原始的換行格式

### 步驟 3: 在 Render Dashboard 設定

1. 登入 https://dashboard.render.com
2. 選擇 `talent-search-api` 服務
3. 點擊左側的 **"Environment"** 標籤
4. 找到 `DB_SSH_PRIVATE_KEY` 或點擊 **"Add Environment Variable"**
5. 設定：
   - **Key**: `DB_SSH_PRIVATE_KEY`
   - **Value**: 貼上完整的私鑰內容
6. 點擊 **"Save Changes"**

---

## 🖼️ 設定截圖指南

### 1. 進入 Environment 設定

```
Dashboard → Services → talent-search-api → Environment
```

### 2. 添加環境變數

點擊 **"Add Environment Variable"** 按鈕

### 3. 輸入 Key 和 Value

```
Key:   DB_SSH_PRIVATE_KEY
Value: -----BEGIN OPENSSH PRIVATE KEY-----
       b3BlbnNzaC1rZXktdjEAAAAA...
       ...
       -----END OPENSSH PRIVATE KEY-----
```

### 4. 保存

點擊 **"Save Changes"**，服務會自動重啟。

---

## 📊 完整的環境變數列表

| 變數名               | 值                                                    | 狀態                |
| -------------------- | ----------------------------------------------------- | ------------------- |
| `LLM_API_KEY`        | `sk-xmwxrtsxgsjwuyeceydoyuopezzlqresdjyvlzrbbjeejiff` | ⚠️ 需設定           |
| `DB_SSH_HOST`        | `54.199.255.239`                                      | ⚠️ 需設定           |
| `DB_SSH_USERNAME`    | `victor_cheng`                                        | ⚠️ 需設定           |
| `DB_SSH_PRIVATE_KEY` | `<私鑰內容>`                                          | ❌ **必須設定**     |
| `DB_NAME`            | `projectdb`                                           | ⚠️ 需設定           |
| `DB_USER`            | `projectuser`                                         | ⚠️ 需設定           |
| `DB_PASSWORD`        | `projectpass`                                         | ⚠️ 需設定           |
| `LLM_API_HOST`       | `https://api.siliconflow.cn`                          | ✅ 已在 render.yaml |
| `LLM_MODEL`          | `deepseek-ai/DeepSeek-V3`                             | ✅ 已在 render.yaml |
| `DB_HOST`            | `localhost`                                           | ✅ 已在 render.yaml |
| `DB_PORT`            | `5432`                                                | ✅ 已在 render.yaml |
| `DB_SSH_PORT`        | `22`                                                  | ✅ 已在 render.yaml |

---

## 🔍 驗證設定

### 設定完成後

1. Render 會自動重啟服務
2. 查看 Runtime Log

### 成功的 Log 應該顯示

```
============================================================
人才聊天搜索 API (修正版)
============================================================
正在建立 SSH 隧道...
SSH 隧道已建立！
正在連接資料庫...
✓ 資料庫連接成功！
正在載入特質定義...
✓ 載入 50 個特質定義
============================================================
啟動服務...
API 文檔: http://localhost:8000/docs
健康檢查: http://localhost:8000/health
============================================================
INFO:     Started server process [38]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:10000
```

### 失敗的 Log 會顯示

```
ERROR: ValueError: No password or public key available!
```

這表示 `DB_SSH_PRIVATE_KEY` 還沒設定或格式錯誤。

---

## ⚠️ 常見問題

### 問題 1: 私鑰格式錯誤

**症狀**: 還是顯示 `No password or public key available!`

**解決**:

1. 確認私鑰包含 BEGIN 和 END 行
2. 確認沒有多餘的空格
3. 確認換行符正確（Unix 格式 LF，不是 Windows 的 CRLF）

### 問題 2: 私鑰權限問題

**症狀**: `Permission denied` 或 `Bad permissions`

**解決**:

- Render 會自動處理權限，不需要手動設定

### 問題 3: SSH 連接超時

**症狀**: `Connection timeout`

**解決**:

1. 確認 `DB_SSH_HOST` 是 `54.199.255.239`
2. 確認 `DB_SSH_USERNAME` 是 `victor_cheng`
3. 確認 SSH 伺服器允許來自 Render 的連接

---

## 🎯 快速設定檢查清單

設定前檢查：

- [ ] 已登入 Render Dashboard
- [ ] 已找到 `talent-search-api` 服務
- [ ] 已進入 "Environment" 標籤
- [ ] 已準備好所有環境變數的值
- [ ] 已複製完整的 SSH 私鑰

設定步驟：

- [ ] 設定 `LLM_API_KEY`
- [ ] 設定 `DB_SSH_HOST`
- [ ] 設定 `DB_SSH_USERNAME`
- [ ] 設定 `DB_SSH_PRIVATE_KEY` ← **最重要**
- [ ] 設定 `DB_NAME`
- [ ] 設定 `DB_USER`
- [ ] 設定 `DB_PASSWORD`
- [ ] 點擊 "Save Changes"

設定後驗證：

- [ ] 服務自動重啟
- [ ] 查看 Runtime Log
- [ ] 確認沒有 "No password or public key" 錯誤
- [ ] 確認看到 "SSH 隧道已建立"
- [ ] 確認看到 "資料庫連接成功"
- [ ] 確認看到 "Uvicorn running on..."

---

## 📞 需要幫助？

如果設定後還是失敗，請提供：

1. Runtime Log 的完整錯誤訊息
2. 確認 `DB_SSH_PRIVATE_KEY` 已設定（不要貼出私鑰內容）
3. 確認私鑰的第一行和最後一行（BEGIN 和 END）

---

## ✅ 成功標誌

當你看到以下內容時，表示設定成功：

1. ✅ Runtime Log 顯示 "SSH 隧道已建立"
2. ✅ Runtime Log 顯示 "資料庫連接成功"
3. ✅ Runtime Log 顯示 "Uvicorn running on..."
4. ✅ 服務狀態顯示 "Live" (綠色)
5. ✅ `/health` 端點返回 `"status": "healthy"`

---

## 🚀 設定完成後

1. 測試 Health Check：

   ```bash
   curl https://your-app.onrender.com/health
   ```

2. 測試 API：

   ```bash
   curl https://your-app.onrender.com/
   ```

3. 測試搜索功能：
   ```bash
   curl -X POST https://your-app.onrender.com/api/search \
     -H "Content-Type: application/json" \
     -d '{"query": "找溝通能力強的人", "session_id": "test"}'
   ```

恭喜！你的 API 已成功部署到 Render！🎉

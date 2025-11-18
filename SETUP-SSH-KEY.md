# 🔑 SSH 私鑰設定指南

## 📍 私鑰位置

文件路徑：`BackEnd\private-key-openssh.pem`

---

## 🔍 查看私鑰

### 方法 1: 使用腳本（推薦）

```cmd
show-ssh-key.bat
```

### 方法 2: 手動查看

```cmd
type BackEnd\private-key-openssh.pem
```

---

## 🚀 在 Fly.io 設定

### 方法 1: PowerShell（推薦）

```powershell
# 讀取私鑰文件
$key = Get-Content BackEnd\private-key-openssh.pem -Raw

# 設定到 Fly.io
fly secrets set "DB_SSH_PRIVATE_KEY=$key"
```

### 方法 2: 一行命令

```powershell
fly secrets set "DB_SSH_PRIVATE_KEY=$(Get-Content BackEnd\private-key-openssh.pem -Raw)"
```

### 方法 3: 手動複製貼上

1. 運行 `show-ssh-key.bat` 或 `type BackEnd\private-key-openssh.pem`
2. 複製完整內容（包括 `-----BEGIN RSA PRIVATE KEY-----` 和 `-----END RSA PRIVATE KEY-----`）
3. 執行：
   ```bash
   fly secrets set DB_SSH_PRIVATE_KEY="貼上私鑰內容"
   ```

---

## 🎨 在 Render 設定

### 步驟

1. **在 Render Dashboard**

   - 進入你的服務設定
   - 找到 "Environment" 或 "Environment Variables"

2. **添加環境變數**

   - Key: `DB_SSH_PRIVATE_KEY`
   - Value: [複製完整私鑰內容]

3. **複製私鑰**

   - 運行 `show-ssh-key.bat`
   - 複製完整內容（包括 BEGIN 和 END 行）
   - 貼到 Render 的 Value 欄位

4. **保存**
   - 點擊 "Save" 或 "Add"

---

## ⚠️ 重要提醒

### 私鑰格式

確保複製時包含：

- ✅ `-----BEGIN RSA PRIVATE KEY-----`（開始行）
- ✅ 中間的所有內容
- ✅ `-----END RSA PRIVATE KEY-----`（結束行）

### 換行符

- 私鑰包含換行符，這是正常的
- 不要移除換行符
- 不要修改任何內容

### 安全性

- ⚠️ 不要將私鑰提交到 Git
- ⚠️ 不要分享私鑰
- ⚠️ 不要在公開場合顯示私鑰
- ✅ 已在 `.gitignore` 中排除 `*.pem` 文件

---

## 🔧 驗證設定

### Fly.io

```bash
# 查看已設定的 secrets（不會顯示實際值）
fly secrets list

# 應該看到 DB_SSH_PRIVATE_KEY 在列表中
```

### Render

在 Render Dashboard 的 Environment Variables 中應該能看到 `DB_SSH_PRIVATE_KEY`。

---

## 🆘 常見問題

### Q: 私鑰設定後連接失敗？

**檢查**：

1. 確認私鑰完整（包括 BEGIN 和 END 行）
2. 確認沒有多餘的空格或換行
3. 確認其他數據庫連接資訊正確

### Q: PowerShell 命令失敗？

**解決**：

```powershell
# 確認文件存在
Test-Path BackEnd\private-key-openssh.pem

# 如果返回 True，再執行設定命令
$key = Get-Content BackEnd\private-key-openssh.pem -Raw
fly secrets set "DB_SSH_PRIVATE_KEY=$key"
```

### Q: 如何更新私鑰？

**Fly.io**:

```bash
# 重新設定即可覆蓋
fly secrets set "DB_SSH_PRIVATE_KEY=$(Get-Content BackEnd\private-key-openssh.pem -Raw)"
```

**Render**:

- 在 Dashboard 編輯環境變數
- 更新 `DB_SSH_PRIVATE_KEY` 的值

---

## 📝 完整環境變數列表

設定 SSH 私鑰時，確保也設定了其他相關變數：

| 變數名稱             | 值               |
| -------------------- | ---------------- |
| `DB_SSH_HOST`        | `54.199.255.239` |
| `DB_SSH_PORT`        | `22`             |
| `DB_SSH_USERNAME`    | `victor_cheng`   |
| `DB_SSH_PRIVATE_KEY` | [私鑰內容]       |
| `DB_HOST`            | `localhost`      |
| `DB_PORT`            | `5432`           |
| `DB_NAME`            | `projectdb`      |
| `DB_USER`            | `projectuser`    |
| `DB_PASSWORD`        | [你的密碼]       |

---

## 🎯 快速設定（Fly.io）

```powershell
# 一次設定所有環境變數
fly secrets set DB_SSH_HOST=54.199.255.239
fly secrets set DB_SSH_PORT=22
fly secrets set DB_SSH_USERNAME=victor_cheng
fly secrets set "DB_SSH_PRIVATE_KEY=$(Get-Content BackEnd\private-key-openssh.pem -Raw)"
fly secrets set DB_HOST=localhost
fly secrets set DB_PORT=5432
fly secrets set DB_NAME=projectdb
fly secrets set DB_USER=projectuser
fly secrets set DB_PASSWORD=你的密碼
fly secrets set LLM_API_KEY=你的LLM密鑰
```

---

**準備好了嗎？開始設定 SSH 私鑰吧！** 🔑

---

**最後更新**: 2025-11-18  
**私鑰文件**: `BackEnd\private-key-openssh.pem`  
**狀態**: ✅ 已找到

# 🔧 GitHub 設置指南

## 📋 當前狀態

✅ Git repository 已初始化  
⏳ 尚未連接到 GitHub  
⏳ 尚未推送代碼

---

## 🚀 快速設置步驟

### 步驟 1: 在 GitHub 創建 Repository

1. **訪問 GitHub**

   - 登入 https://github.com
   - 點擊右上角 "+" → "New repository"

2. **填寫資訊**

   - **Repository name**: `talent-search-system` (或你喜歡的名稱)
   - **Description**: `AI 人才搜索系統 - 基於自然語言的智能人才匹配平台`
   - **Visibility**:
     - ✅ Private (推薦，因為包含敏感配置)
     - ⚠️ Public (如果要開源)
   - **不要勾選** "Initialize this repository with a README"
   - 點擊 "Create repository"

3. **複製 Repository URL**
   - 創建後會看到 repository URL
   - 格式：`https://github.com/你的用戶名/talent-search-system.git`

### 步驟 2: 連接到 GitHub

在專案目錄執行：

```bash
# 添加遠端 repository（替換為你的 URL）
git remote add origin https://github.com/你的用戶名/talent-search-system.git

# 檢查遠端連接
git remote -v
```

### 步驟 3: 提交代碼

```bash
# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: AI talent search system with deployment configs"

# 設置主分支名稱
git branch -M main
```

### 步驟 4: 推送到 GitHub

```bash
# 首次推送
git push -u origin main
```

如果遇到認證問題，可能需要：

- 使用 Personal Access Token (推薦)
- 或配置 SSH key

---

## 🔐 GitHub 認證設置

### 方法 1: Personal Access Token (推薦)

1. **創建 Token**

   - 訪問 https://github.com/settings/tokens
   - 點擊 "Generate new token" → "Generate new token (classic)"
   - 勾選 `repo` 權限
   - 點擊 "Generate token"
   - **複製 token**（只會顯示一次！）

2. **使用 Token**

   ```bash
   # 推送時會要求輸入用戶名和密碼
   # 用戶名: 你的 GitHub 用戶名
   # 密碼: 貼上剛才複製的 token
   git push -u origin main
   ```

3. **保存認證（可選）**
   ```bash
   # Windows 會自動保存到 Credential Manager
   # 下次推送就不需要再輸入
   ```

### 方法 2: SSH Key

1. **生成 SSH Key**

   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```

2. **添加到 GitHub**

   - 複製公鑰：`cat ~/.ssh/id_ed25519.pub`
   - 訪問 https://github.com/settings/keys
   - 點擊 "New SSH key"
   - 貼上公鑰

3. **修改遠端 URL**
   ```bash
   git remote set-url origin git@github.com:你的用戶名/talent-search-system.git
   ```

---

## 📝 一鍵執行腳本

我已經為你準備好了自動化腳本：

### Windows 批次腳本

運行 `setup-github.bat`：

```batch
@echo off
echo ========================================
echo GitHub 設置助手
echo ========================================
echo.

echo 請先在 GitHub 創建 repository，然後輸入 URL
echo 格式: https://github.com/用戶名/repo名稱.git
echo.
set /p REPO_URL="請輸入 GitHub Repository URL: "

echo.
echo 正在設置 Git...
git remote add origin %REPO_URL%
git add .
git commit -m "Initial commit: AI talent search system"
git branch -M main

echo.
echo 正在推送到 GitHub...
git push -u origin main

echo.
echo ========================================
echo ✅ 完成！
echo ========================================
pause
```

---

## ⚠️ 重要提醒

### 檢查敏感文件

在推送前，確認以下文件**不會**被提交：

✅ 已在 `.gitignore` 中排除：

- `*.pem` - SSH 私鑰
- `*.key` - 其他私鑰
- `.env` - 環境變數
- `private-key*` - 私鑰文件
- `venv/` - Python 虛擬環境
- `node_modules/` - Node.js 依賴

### 檢查命令

```bash
# 查看將要提交的文件
git status

# 查看 .gitignore 是否生效
git check-ignore -v BackEnd/private-key-openssh.pem
```

如果私鑰文件出現在 `git status` 中：

```bash
# 從暫存區移除
git rm --cached BackEnd/private-key-openssh.pem

# 確認 .gitignore 包含 *.pem
echo "*.pem" >> .gitignore

# 重新提交
git add .gitignore
git commit -m "Add .gitignore to exclude sensitive files"
```

---

## 🔄 日常使用

### 提交更改

```bash
# 查看更改
git status

# 添加文件
git add .

# 提交
git commit -m "描述你的更改"

# 推送
git push
```

### 查看歷史

```bash
# 查看提交歷史
git log --oneline

# 查看遠端連接
git remote -v
```

### 拉取更新

```bash
# 如果在其他地方修改了代碼
git pull
```

---

## 📊 Repository 設置建議

### 1. 添加 README Badge

在 GitHub repository 頁面會顯示：

```markdown
# AI 人才搜索系統

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

一個基於 AI 的智能人才搜索和匹配系統。
```

### 2. 設置 Branch Protection

在 GitHub repository 設置中：

- Settings → Branches → Add rule
- Branch name pattern: `main`
- 勾選 "Require pull request reviews before merging"

### 3. 添加 Topics

在 repository 頁面點擊 "Add topics"：

- `ai`
- `talent-search`
- `fastapi`
- `vue`
- `postgresql`
- `nlp`

---

## 🎯 下一步

完成 GitHub 設置後：

1. ✅ 代碼已在 GitHub
2. 🚀 可以開始部署到 Render
3. 📖 查看 [DEPLOY-TO-RENDER.md](./DEPLOY-TO-RENDER.md)

---

## 🆘 常見問題

### Q: 推送時要求輸入密碼？

使用 Personal Access Token 而不是 GitHub 密碼。

### Q: 推送被拒絕？

```bash
# 先拉取遠端更改
git pull origin main --rebase

# 再推送
git push
```

### Q: 不小心提交了敏感文件？

```bash
# 從歷史中移除（危險操作！）
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch BackEnd/private-key-openssh.pem" \
  --prune-empty --tag-name-filter cat -- --all

# 強制推送
git push origin --force --all
```

### Q: 想要重新開始？

```bash
# 刪除 .git 目錄
rm -rf .git

# 重新初始化
git init
```

---

**準備好了嗎？開始設置 GitHub 吧！** 🚀

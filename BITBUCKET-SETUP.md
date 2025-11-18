# 🔵 Bitbucket 設置指南

## 📋 當前狀態

✅ 代碼已在 GitHub: https://github.com/victorzhangw/talent-search-system  
⏳ 準備推送到 Bitbucket

---

## 🚀 推送到 Bitbucket

### 步驟 1: 在 Bitbucket 創建 Repository

1. **訪問 Bitbucket**

   - 打開 https://bitbucket.org
   - 登入你的 Bitbucket 帳號

2. **創建新 Repository**

   - 點擊左側 "+" → "Repository"
   - 或訪問 https://bitbucket.org/repo/create

3. **填寫資訊**

   - **Project**: 選擇或創建一個 Project
   - **Repository name**: `talent-search-system`
   - **Access level**:
     - ✅ Private (推薦)
     - ⚠️ Public
   - **Include a README?**: No
   - **Include .gitignore?**: No
   - 點擊 **"Create repository"**

4. **複製 Repository URL**
   - 創建後會看到 repository URL
   - 格式：`https://bitbucket.org/你的用戶名/talent-search-system.git`

### 步驟 2: 添加 Bitbucket 為第二個遠端

```bash
# 添加 Bitbucket 遠端（命名為 bitbucket）
git remote add bitbucket https://bitbucket.org/你的用戶名/talent-search-system.git

# 檢查遠端設置
git remote -v
```

你會看到：

```
bitbucket  https://bitbucket.org/你的用戶名/talent-search-system.git (fetch)
bitbucket  https://bitbucket.org/你的用戶名/talent-search-system.git (push)
origin     https://github.com/victorzhangw/talent-search-system.git (fetch)
origin     https://github.com/victorzhangw/talent-search-system.git (push)
```

### 步驟 3: 推送到 Bitbucket

```bash
# 推送到 Bitbucket
git push -u bitbucket main
```

### 步驟 4: 輸入認證

推送時會要求輸入：

- **用戶名**: 你的 Bitbucket 用戶名
- **密碼**: 使用 **App Password**（不是 Bitbucket 密碼）

#### 如何創建 App Password:

1. 訪問 https://bitbucket.org/account/settings/app-passwords/
2. 點擊 "Create app password"
3. Label: `Git Push`
4. 勾選權限：
   - ✅ Repositories: Read
   - ✅ Repositories: Write
5. 點擊 "Create"
6. **複製 password**（只會顯示一次！）
7. 在推送時，密碼欄位貼上這個 app password

---

## 🔄 同時維護兩個遠端

### 推送到兩個平台

```bash
# 推送到 GitHub
git push origin main

# 推送到 Bitbucket
git push bitbucket main

# 或一次推送到所有遠端
git push --all
```

### 設置自動推送到兩個平台

如果你想每次 `git push` 都推送到兩個平台：

```bash
# 添加第二個 push URL 到 origin
git remote set-url --add --push origin https://bitbucket.org/你的用戶名/talent-search-system.git
git remote set-url --add --push origin https://github.com/victorzhangw/talent-search-system.git
```

之後每次 `git push` 會自動推送到兩個平台。

---

## 📝 日常使用

### 更新代碼

```bash
# 1. 修改代碼
# 2. 提交更改
git add .
git commit -m "描述你的更改"

# 3. 推送到 GitHub
git push origin main

# 4. 推送到 Bitbucket
git push bitbucket main
```

### 從 Bitbucket 拉取

```bash
git pull bitbucket main
```

### 查看遠端狀態

```bash
# 查看所有遠端
git remote -v

# 查看遠端詳細信息
git remote show origin
git remote show bitbucket
```

---

## 🔧 進階設置

### 方法 1: 使用別名簡化推送

在 `.git/config` 添加：

```ini
[alias]
    pushall = !git push origin main && git push bitbucket main
```

使用：

```bash
git pushall
```

### 方法 2: 創建批次腳本

創建 `push-all.bat`：

```batch
@echo off
echo 推送到 GitHub...
git push origin main
echo.
echo 推送到 Bitbucket...
git push bitbucket main
echo.
echo ✅ 完成！
pause
```

使用：

```cmd
push-all.bat
```

---

## 🆘 常見問題

### Q: 推送時要求密碼？

使用 Bitbucket App Password：

1. 訪問 https://bitbucket.org/account/settings/app-passwords/
2. 創建新的 app password
3. 使用這個 password 而不是帳號密碼

### Q: 如何移除 Bitbucket 遠端？

```bash
git remote remove bitbucket
```

### Q: 如何更改 Bitbucket URL？

```bash
git remote set-url bitbucket https://新的URL.git
```

### Q: 推送衝突怎麼辦？

```bash
# 先拉取遠端更改
git pull bitbucket main --rebase

# 解決衝突後推送
git push bitbucket main
```

---

## 📊 比較 GitHub vs Bitbucket

| 功能              | GitHub         | Bitbucket           |
| ----------------- | -------------- | ------------------- |
| **免費私有 repo** | ✅ 無限        | ✅ 無限             |
| **協作者**        | ✅ 無限        | ✅ 5 人             |
| **CI/CD**         | GitHub Actions | Bitbucket Pipelines |
| **整合**          | 更多第三方     | Jira, Trello        |
| **介面**          | 更友善         | 較複雜              |
| **適合**          | 開源、展示     | 企業、私有          |

---

## 💡 為什麼使用兩個平台？

### 優點

1. **備份**: 代碼存在兩個地方
2. **靈活性**: 可以選擇不同平台的功能
3. **團隊協作**: GitHub 給外部，Bitbucket 給內部
4. **CI/CD**: 使用不同平台的 CI/CD 功能

### 缺點

1. **維護**: 需要推送到兩個地方
2. **同步**: 可能出現不一致
3. **複雜**: 管理兩個平台

---

## 🎯 推薦使用方式

### 方案 A: 主要使用 GitHub

- **GitHub**: 主要開發、部署、展示
- **Bitbucket**: 備份、內部協作

```bash
# 日常推送到 GitHub
git push

# 定期備份到 Bitbucket
git push bitbucket main
```

### 方案 B: 同時使用

- **GitHub**: 開源部分、文檔
- **Bitbucket**: 私有代碼、敏感配置

```bash
# 每次都推送到兩個平台
git push --all
```

---

## 📞 獲取幫助

- **Bitbucket 文檔**: https://support.atlassian.com/bitbucket-cloud/
- **Git 文檔**: https://git-scm.com/doc

---

**準備好了嗎？現在去 Bitbucket 創建 repository 吧！** 🚀

創建後，回來執行：

```bash
git remote add bitbucket https://bitbucket.org/你的用戶名/talent-search-system.git
git push -u bitbucket main
```

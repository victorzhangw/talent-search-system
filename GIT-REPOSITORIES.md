# 🔗 Git Repositories 總覽

## ✅ 已配置的遠端

你的代碼現在同時存在於兩個平台：

### 1. GitHub

- **URL**: https://github.com/victorzhangw/talent-search-system
- **用途**: 主要開發、部署、公開展示
- **遠端名稱**: `origin`

### 2. Bitbucket

- **URL**: https://bitbucket.org/800adplus/talent-search-system
- **用途**: 備份、團隊協作
- **遠端名稱**: `bitbucket`

---

## 📊 當前狀態

✅ 代碼已推送到 GitHub  
✅ 代碼已推送到 Bitbucket  
✅ 兩個平台已同步

---

## 🔄 日常使用

### 更新代碼並推送到兩個平台

#### 方法 1: 使用自動化腳本（推薦）

```cmd
# 修改代碼後
git add .
git commit -m "你的更改說明"

# 一鍵推送到兩個平台
push-all.bat
```

#### 方法 2: 手動推送

```bash
# 修改代碼後
git add .
git commit -m "你的更改說明"

# 推送到 GitHub
git push origin main

# 推送到 Bitbucket
git push bitbucket main
```

---

## 📝 常用命令

### 查看遠端設置

```bash
git remote -v
```

輸出：

```
bitbucket  https://bitbucket.org/800adplus/talent-search-system.git (fetch)
bitbucket  https://bitbucket.org/800adplus/talent-search-system.git (push)
origin     https://github.com/victorzhangw/talent-search-system.git (fetch)
origin     https://github.com/victorzhangw/talent-search-system.git (push)
```

### 查看分支狀態

```bash
git status
```

### 查看提交歷史

```bash
git log --oneline --graph --all
```

### 從特定平台拉取

```bash
# 從 GitHub 拉取
git pull origin main

# 從 Bitbucket 拉取
git pull bitbucket main
```

---

## 🛠️ 可用的腳本

### 1. push-all.bat

一鍵推送到 GitHub 和 Bitbucket

```cmd
push-all.bat
```

### 2. setup-github.bat

設置 GitHub 連接（已完成）

### 3. setup-bitbucket.bat

設置 Bitbucket 連接（已完成）

---

## ⚠️ 重要提醒

### Bitbucket App Password 即將變更

根據推送時的提示：

- ⚠️ **2025 年 9 月 9 日**: 停止創建 App Passwords
- ⚠️ **2026 年 6 月 9 日**: 所有 App Passwords 將失效
- ✅ **建議**: 改用 API Tokens

**如何創建 API Token**:

1. 訪問 https://bitbucket.org/account/settings/api-tokens/
2. 點擊 "Create API token"
3. 設定權限
4. 使用 token 替代 app password

---

## 🔐 認證管理

### GitHub

- **方法**: Personal Access Token
- **獲取**: https://github.com/settings/tokens
- **權限**: `repo`

### Bitbucket

- **當前方法**: App Password
- **未來方法**: API Token（2025 年 9 月後）
- **獲取**: https://bitbucket.org/account/settings/app-passwords/

---

## 📦 備份策略

### 自動備份

每次推送時，代碼會自動備份到兩個平台：

- GitHub: 主要平台
- Bitbucket: 備份平台

### 手動備份

如果需要額外備份：

```bash
# 克隆到本地
git clone https://github.com/victorzhangw/talent-search-system.git backup

# 或從 Bitbucket
git clone https://bitbucket.org/800adplus/talent-search-system.git backup
```

---

## 🚀 部署相關

### 從 GitHub 部署

- **Render**: 支援 ✅
- **Vercel**: 支援 ✅
- **Netlify**: 支援 ✅

### 從 Bitbucket 部署

- **Render**: 支援 ✅
- **Bitbucket Pipelines**: 支援 ✅

---

## 🔄 同步檢查

### 檢查兩個平台是否同步

```bash
# 查看本地分支
git branch -vv

# 查看遠端分支
git remote show origin
git remote show bitbucket
```

### 如果不同步

```bash
# 從 GitHub 拉取最新
git pull origin main

# 推送到 Bitbucket
git push bitbucket main
```

---

## 📊 統計信息

- **總文件數**: 610+ 個文件
- **代碼行數**: 169,000+ 行
- **Repository 大小**: ~14 MB
- **主要語言**: Python, JavaScript, Vue.js
- **數據庫**: PostgreSQL

---

## 🎯 最佳實踐

### 1. 定期推送

每次完成功能後立即推送到兩個平台

### 2. 使用有意義的提交訊息

```bash
git commit -m "feat: 添加用戶認證功能"
git commit -m "fix: 修復搜索 API 錯誤"
git commit -m "docs: 更新部署文檔"
```

### 3. 定期檢查同步狀態

```bash
git remote show origin
git remote show bitbucket
```

### 4. 保持分支整潔

```bash
# 查看所有分支
git branch -a

# 刪除不需要的本地分支
git branch -d 分支名稱
```

---

## 🆘 常見問題

### Q: 推送失敗怎麼辦？

```bash
# 先拉取遠端更改
git pull origin main --rebase

# 解決衝突後推送
git push origin main
git push bitbucket main
```

### Q: 如何切換主要平台？

如果想讓 Bitbucket 成為主要平台：

```bash
git remote rename origin github
git remote rename bitbucket origin
```

### Q: 如何移除某個遠端？

```bash
# 移除 Bitbucket
git remote remove bitbucket

# 移除 GitHub
git remote remove origin
```

---

## 📞 獲取幫助

- **GitHub 文檔**: https://docs.github.com
- **Bitbucket 文檔**: https://support.atlassian.com/bitbucket-cloud/
- **Git 文檔**: https://git-scm.com/doc

---

**最後更新**: 2025-11-18  
**狀態**: ✅ 兩個平台已同步  
**GitHub**: https://github.com/victorzhangw/talent-search-system  
**Bitbucket**: https://bitbucket.org/800adplus/talent-search-system

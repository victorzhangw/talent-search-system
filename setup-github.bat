@echo off
chcp 65001 >nul
echo ========================================
echo GitHub 設置助手
echo ========================================
echo.

echo 📋 當前狀態檢查...
echo.

REM 檢查 Git 是否已初始化
git status >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Git repository 尚未初始化
    echo 正在初始化...
    git init
    echo ✅ Git repository 已初始化
) else (
    echo ✅ Git repository 已存在
)

echo.
echo ========================================
echo 步驟 1: 檢查敏感文件
echo ========================================
echo.

REM 檢查 .gitignore 是否存在
if not exist ".gitignore" (
    echo ❌ 缺少 .gitignore 文件
    echo 請先運行 prepare-deployment.bat
    pause
    exit /b 1
)

echo ✅ .gitignore 文件存在
echo.
echo 以下文件將被忽略（不會上傳到 GitHub）：
echo   • *.pem (SSH 私鑰)
echo   • *.key (其他私鑰)
echo   • .env (環境變數)
echo   • venv/ (Python 虛擬環境)
echo   • node_modules/ (Node.js 依賴)
echo.

echo ========================================
echo 步驟 2: 連接到 GitHub
echo ========================================
echo.
echo 請先在 GitHub 創建一個新的 repository：
echo 1. 訪問 https://github.com/new
echo 2. Repository name: talent-search-system (或其他名稱)
echo 3. 選擇 Private (推薦) 或 Public
echo 4. 不要勾選 "Initialize this repository with a README"
echo 5. 點擊 "Create repository"
echo.
echo 創建後，複製 repository URL
echo 格式: https://github.com/你的用戶名/repo名稱.git
echo.

set /p REPO_URL="請輸入 GitHub Repository URL: "

if "%REPO_URL%"=="" (
    echo ❌ URL 不能為空
    pause
    exit /b 1
)

echo.
echo 正在連接到 GitHub...
git remote add origin %REPO_URL% 2>nul
if errorlevel 1 (
    echo ⚠️  遠端 origin 已存在，正在更新...
    git remote set-url origin %REPO_URL%
)

echo ✅ 已連接到: %REPO_URL%
echo.

echo ========================================
echo 步驟 3: 提交代碼
echo ========================================
echo.

echo 正在添加文件...
git add .

echo 正在提交...
git commit -m "Initial commit: AI talent search system with deployment configs"

echo 正在設置主分支...
git branch -M main

echo ✅ 代碼已提交到本地 repository
echo.

echo ========================================
echo 步驟 4: 推送到 GitHub
echo ========================================
echo.
echo 即將推送代碼到 GitHub...
echo 如果是第一次推送，可能需要輸入 GitHub 認證：
echo   • 用戶名: 你的 GitHub 用戶名
echo   • 密碼: Personal Access Token (不是 GitHub 密碼)
echo.
echo 如何獲取 Personal Access Token:
echo 1. 訪問 https://github.com/settings/tokens
echo 2. 點擊 "Generate new token (classic)"
echo 3. 勾選 "repo" 權限
echo 4. 複製生成的 token
echo.
pause

echo 正在推送...
git push -u origin main

if errorlevel 1 (
    echo.
    echo ❌ 推送失敗
    echo.
    echo 可能的原因：
    echo 1. 認證失敗 - 請確認使用 Personal Access Token
    echo 2. 網絡問題 - 請檢查網絡連接
    echo 3. Repository URL 錯誤 - 請檢查 URL 是否正確
    echo.
    echo 手動推送命令:
    echo git push -u origin main
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ 成功！
echo ========================================
echo.
echo 你的代碼已經推送到 GitHub！
echo.
echo 📍 Repository URL: %REPO_URL%
echo.
echo 下一步：
echo 1. 訪問你的 GitHub repository 確認代碼已上傳
echo 2. 開始部署到 Render: 查看 DEPLOY-TO-RENDER.md
echo 3. 或比較其他平台: 查看 FREE-HOSTING-OPTIONS.md
echo.
echo 日常使用：
echo   git add .
echo   git commit -m "你的更改說明"
echo   git push
echo.
pause

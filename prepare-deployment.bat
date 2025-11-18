@echo off
chcp 65001 >nul
echo ========================================
echo 準備部署到 Render
echo ========================================
echo.

echo [1/4] 檢查必要文件...
if not exist "render.yaml" (
    echo ❌ 缺少 render.yaml
    exit /b 1
)
if not exist "BackEnd\requirements.txt" (
    echo ❌ 缺少 BackEnd\requirements.txt
    exit /b 1
)
if not exist "frontend\package.json" (
    echo ❌ 缺少 frontend\package.json
    exit /b 1
)
echo ✅ 所有必要文件都存在

echo.
echo [2/4] 檢查 Git repository...
git status >nul 2>&1
if errorlevel 1 (
    echo ⚠️  尚未初始化 Git repository
    echo 執行: git init
    git init
)
echo ✅ Git repository 已就緒

echo.
echo [3/4] 創建 .env 文件範例...
if not exist ".env" (
    copy .env.example .env >nul
    echo ✅ 已創建 .env 文件，請填入實際值
) else (
    echo ℹ️  .env 文件已存在
)

if not exist "frontend\.env" (
    copy frontend\.env.example frontend\.env >nul
    echo ✅ 已創建 frontend\.env 文件
) else (
    echo ℹ️  frontend\.env 文件已存在
)

echo.
echo [4/4] 顯示 SSH 私鑰內容...
echo.
echo 複製以下內容到 Render 的 DB_SSH_PRIVATE_KEY 環境變數：
echo ----------------------------------------
type BackEnd\private-key-openssh.pem
echo ----------------------------------------
echo.

echo.
echo ========================================
echo ✅ 準備完成！
echo ========================================
echo.
echo 下一步：
echo 1. 推送代碼到 GitHub:
echo    git add .
echo    git commit -m "Ready for deployment"
echo    git push origin main
echo.
echo 2. 訪問 https://render.com 並登入
echo.
echo 3. 創建 Blueprint 並設定環境變數
echo.
echo 4. 查看完整指南: DEPLOY-TO-RENDER.md
echo.
pause

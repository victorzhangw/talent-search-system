@echo off
chcp 65001 >nul
echo ========================================
echo 部署前端到 Vercel
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 檢查 Vercel CLI...
where vercel >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未安裝 Vercel CLI
    echo 正在安裝...
    npm install -g vercel
)

echo.
echo [2/3] 建置專案...
call npm run build
if %errorlevel% neq 0 (
    echo ❌ 建置失敗
    pause
    exit /b 1
)

echo.
echo [3/3] 部署到 Vercel...
echo.
echo 提示：
echo - 第一次部署會要求登入
echo - 選擇專案設定（通常直接按 Enter）
echo - 記得在 Vercel Dashboard 設定環境變數 VITE_API_BASE_URL
echo.
vercel --prod

echo.
echo ========================================
echo ✅ 部署完成！
echo ========================================
echo.
echo 下一步：
echo 1. 複製 Vercel 提供的 URL
echo 2. 前往 Vercel Dashboard 設定環境變數
echo 3. 測試前端功能
echo.
pause

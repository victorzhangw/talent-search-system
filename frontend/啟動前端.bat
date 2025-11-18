@echo off
chcp 65001 >nul
echo ========================================
echo   AI 人才搜索系統 - 前端啟動
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] 檢查 Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未安裝 Node.js！
    echo.
    echo 請先安裝 Node.js: https://nodejs.org/
    pause
    exit /b 1
)

echo ✓ Node.js 已安裝
echo.

echo [2/2] 啟動開發服務器...
echo.
echo 前端將在 http://localhost:3000 啟動
echo 請確保後端服務在 http://localhost:8000 運行
echo.
echo ========================================
echo.

npm run dev

pause

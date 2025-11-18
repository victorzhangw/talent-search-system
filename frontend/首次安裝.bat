@echo off
chcp 65001 >nul
echo ========================================
echo   AI 人才搜索系統 - 首次安裝
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 檢查 Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未安裝 Node.js！
    echo.
    echo 請先安裝 Node.js: https://nodejs.org/
    pause
    exit /b 1
)

echo ✓ Node.js 已安裝
node --version
npm --version
echo.

echo [2/3] 安裝依賴包...
echo 這可能需要幾分鐘...
echo.

npm install

if errorlevel 1 (
    echo.
    echo ❌ 安裝失敗！
    pause
    exit /b 1
)

echo.
echo [3/3] 安裝完成！
echo.
echo ========================================
echo   下一步：
echo   1. 運行 "啟動前端.bat" 啟動開發服務器
echo   2. 確保後端服務在 http://localhost:8000 運行
echo ========================================
echo.

pause

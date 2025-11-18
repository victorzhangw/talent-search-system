@echo off
chcp 65001 >nul
echo ========================================
echo 啟動本地開發環境
echo ========================================
echo.

cd /d "%~dp0"

REM 載入本地環境變數
for /f "tokens=1,* delims==" %%a in (.env.local) do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" (
        set "%%a=%%b"
    )
)

echo ✅ 環境變數已載入
echo 🚀 啟動 API 服務...
echo.

python app.py

pause

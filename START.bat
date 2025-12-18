@echo off
chcp 65001 >nul
title 人才管理系統 - 啟動中...

echo.
echo ========================================
echo   人才管理系統 - 統一啟動腳本
echo ========================================
echo.

REM 檢查 Python 是否安裝
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 未找到 Python，請先安裝 Python 3.10+
    echo.
    pause
    exit /b 1
)

REM 檢查 Node.js 是否安裝
node --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 未找到 Node.js，請先安裝 Node.js 16+
    echo.
    pause
    exit /b 1
)

echo [1/4] 檢查環境...
echo.

REM 檢查後端環境變數文件
if not exist "BackEnd\.env.local" (
    echo [警告] 未找到 BackEnd\.env.local 文件
    echo [提示] 請複製 BackEnd\.env.example 為 BackEnd\.env.local 並配置
    echo.
    pause
    exit /b 1
)

REM 檢查後端依賴
if not exist "BackEnd\venv" (
    echo [提示] 未找到虛擬環境，正在創建...
    cd BackEnd
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
    cd ..
    echo [完成] 虛擬環境創建完成
    echo.
)

REM 檢查前端依賴
if not exist "frontend\node_modules" (
    echo [提示] 未找到前端依賴，正在安裝...
    cd frontend
    call npm install
    cd ..
    echo [完成] 前端依賴安裝完成
    echo.
)

echo [2/4] 啟動後端服務...
echo.

REM 啟動後端 API
start "人才管理系統 - 後端 API" cmd /k "cd BackEnd && venv\Scripts\python.exe main_api.py"

echo [等待] 等待後端服務啟動...
timeout /t 5 /nobreak >nul

REM 檢查後端是否啟動成功
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo [警告] 後端服務可能未成功啟動，請檢查後端窗口
    echo.
) else (
    echo [成功] 後端服務已啟動
    echo.
)

echo [3/4] 啟動前端服務...
echo.

REM 啟動前端開發服務器
start "人才管理系統 - 前端" cmd /k "cd frontend && npm run dev"

echo [等待] 等待前端服務啟動...
timeout /t 5 /nobreak >nul

echo.
echo [4/4] 啟動完成！
echo.
echo ========================================
echo   服務已啟動
echo ========================================
echo.
echo 後端 API:
echo   - API 文檔: http://localhost:8000/docs
echo   - 健康檢查: http://localhost:8000/health
echo   - 人才搜索: http://localhost:8000/api/talent
echo   - HR 諮詢: http://localhost:8000/api/hr-consult
echo.
echo 前端界面:
echo   - 主界面: http://localhost:3000
echo.
echo ========================================
echo.
echo [提示] 瀏覽器將在 3 秒後自動打開...
timeout /t 3 /nobreak >nul

REM 打開瀏覽器
start http://localhost:3000

echo.
echo [提示] 要停止服務，請關閉後端和前端的命令窗口
echo [提示] 或運行 stop.bat 腳本
echo.
pause

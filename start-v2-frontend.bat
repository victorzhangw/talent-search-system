@echo off
setlocal
title Widget Dev Server - Port 5300

cd /d "%~dp0\frontend\chat-widget"

if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERR] npm install failed.
        pause
        exit /b 1
    )
)

echo Starting Vite Dev Server on port 5300...
call npm run dev
pause

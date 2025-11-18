@echo off
chcp 65001 >nul
title Frontend Dev - Port 3000

cd /d "%~dp0frontend"

echo ========================================
echo   Starting Frontend Dev Server
echo ========================================
echo.
echo Port: 3000
echo URL: http://localhost:3000
echo.

npm run dev

pause

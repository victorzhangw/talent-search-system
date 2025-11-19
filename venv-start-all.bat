@echo off
chcp 65001 >nul
title AI Talent Search - Launcher

echo ========================================
echo   AI Talent Search System
echo   Starting Services...
echo ========================================
echo.

cd /d "%~dp0"

:: Start Backend
echo [1/2] Starting Backend (Port 8000)...
start "Backend API" cmd /k "cd /d "%~dp0BackEnd" && venv\Scripts\python.exe talent_search_api.py"
timeout /t 3 /nobreak >nul
echo ✓ Backend started

:: Start Frontend  
echo [2/2] Starting Frontend (Port 3000)...
start "Frontend Dev" cmd /k "cd /d "%~dp0frontend" && npm run dev"
timeout /t 3 /nobreak >nul
echo ✓ Frontend started

echo.
echo ========================================
echo   Services Started!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Opening browser...
timeout /t 2 /nobreak >nul
start http://localhost:3000

echo.
echo Services are running in separate windows.
echo Close those windows to stop services.
echo.
echo This window will close in 3 seconds...
timeout /t 3 /nobreak >nul

@echo off
chcp 65001 >nul
title AI Talent Search System - Full Stack Launcher

echo ========================================
echo   AI Talent Search System
echo   Full Stack Launcher
echo ========================================
echo.

cd /d "%~dp0"

:: Check Python
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not installed!
    echo.
    echo Please install Python: https://www.python.org/
    pause
    exit /b 1
)
echo ✓ Python installed
python --version
echo.

:: Check Node.js
echo [2/4] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not installed!
    echo.
    echo Please install Node.js: https://nodejs.org/
    pause
    exit /b 1
)
echo ✓ Node.js installed
node --version
npm --version
echo.

:: Check backend virtual environment
echo [3/5] Checking backend virtual environment...
if not exist "BackEnd\venv" (
    echo ❌ Backend virtual environment not found!
    echo.
    echo Please run "setup-first-time.bat" first to set up the environment.
    pause
    exit /b 1
)
echo ✓ Backend virtual environment found
echo.

:: Check frontend dependencies
echo [4/5] Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo ⚠ Frontend dependencies not installed
    echo Installing dependencies...
    cd frontend
    call npm install
    if errorlevel 1 (
        echo ❌ Failed to install frontend dependencies!
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo ✓ Frontend dependencies installed
) else (
    echo ✓ Frontend dependencies already installed
)
echo.

:: Start services
echo [5/5] Starting services...
echo.
echo ========================================
echo   Starting Backend (Port 8000)...
echo ========================================
start "Backend - FastAPI" cmd /k "cd /d "%~dp0BackEnd" && venv\Scripts\python.exe talent_search_api_v2.py"

:: Wait for backend to start
echo Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   Starting Frontend (Port 3000)...
echo ========================================
start "Frontend - Vite" cmd /k "cd /d "%~dp0frontend" && npm run dev"

:: Wait for frontend to start
echo Waiting for frontend to initialize...
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   ✓ All Services Started!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to open browser...
pause >nul

:: Open browser
start http://localhost:3000

echo.
echo ========================================
echo   Services are running in separate windows
echo   Close those windows to stop services
echo ========================================
echo.
pause

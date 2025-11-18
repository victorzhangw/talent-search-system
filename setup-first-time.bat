@echo off
chcp 65001 >nul
title AI Talent Search System - First Time Setup

echo ========================================
echo   AI Talent Search System
echo   First Time Setup
echo ========================================
echo.

cd /d "%~dp0"

:: Check Python
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not installed!
    echo.
    echo Please install Python 3.8 or higher: https://www.python.org/
    pause
    exit /b 1
)
echo ✓ Python installed
python --version
echo.

:: Check Node.js
echo [2/5] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not installed!
    echo.
    echo Please install Node.js 18 or higher: https://nodejs.org/
    pause
    exit /b 1
)
echo ✓ Node.js installed
node --version
npm --version
echo.

:: Setup Python virtual environment and install dependencies
echo [3/5] Setting up Python virtual environment...
cd BackEnd

:: Check if venv exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment!
        cd ..
        pause
        exit /b 1
    )
    echo ✓ Virtual environment created
)

:: Install dependencies in venv
if exist "requirements.txt" (
    echo Installing Python dependencies in virtual environment...
    call venv\Scripts\pip.exe install -r requirements.txt
    if errorlevel 1 (
        echo ⚠ Some Python packages may have failed to install
        echo You can continue, but some features may not work
    ) else (
        echo ✓ Python dependencies installed in venv
    )
) else (
    echo ⚠ requirements.txt not found
)

cd ..
echo.

:: Install Frontend dependencies
echo [4/5] Installing Frontend dependencies...
echo This may take a few minutes...
cd frontend
call npm install
if errorlevel 1 (
    echo ❌ Failed to install frontend dependencies!
    cd ..
    pause
    exit /b 1
)
echo ✓ Frontend dependencies installed
cd ..
echo.

:: Create .env file if not exists
echo [5/5] Checking configuration...
if not exist "frontend\.env" (
    if exist "frontend\.env.example" (
        copy "frontend\.env.example" "frontend\.env" >nul
        echo ✓ Created .env file from example
    )
)
echo.

echo ========================================
echo   ✓ Setup Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Run "start-all.bat" to start both services
echo   2. Open http://localhost:3000 in your browser
echo.
echo ========================================
echo.
pause

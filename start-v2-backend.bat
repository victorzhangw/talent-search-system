@echo off
setlocal
title Backend API - Port 5000

cd /d "%~dp0"
set "VENV=BackEnd\api_v2\.venv"

:: Check if venv Python is usable
"%VENV%\Scripts\python.exe" --version >nul 2>&1
if %errorlevel% equ 0 goto :activate

:: Venv missing or broken - recreate with system python
echo Recreating .venv with system Python...
python -m venv "%VENV%" --clear
if %errorlevel% neq 0 (
    echo [ERR] Failed to create venv. Make sure Python is installed.
    pause
    exit /b 1
)
echo Installing dependencies (this may take a few minutes)...
"%VENV%\Scripts\pip.exe" install -r BackEnd\api_v2\requirements.txt
if %errorlevel% neq 0 (
    echo [ERR] pip install failed. Check BackEnd\api_v2\requirements.txt
    pause
    exit /b 1
)
echo venv ready.

:activate
call "%VENV%\Scripts\activate.bat"

REM Port 5000 must be free. Flask does not fail loudly here: the second
REM instance starts, prints "Running on http://127.0.0.1:5000" and then serves
REM nothing, while the first one keeps answering with its own (older) code.
REM 2026-09-08 spent four UAT calls on exactly this.
powershell -NoProfile -Command "if(@(Get-NetTCPConnection -State Listen -LocalPort 5000 -EA 0).Count -gt 0){exit 1}"
if %errorlevel% neq 0 (
    echo [ERR] Port 5000 is already in use - another backend is still running.
    echo       Run stop-v2-all.bat first, then start again.
    pause
    exit /b 1
)

echo Starting Backend...
python run_backend.py
pause

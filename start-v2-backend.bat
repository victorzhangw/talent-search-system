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
echo Starting Backend...
python run_backend.py
pause

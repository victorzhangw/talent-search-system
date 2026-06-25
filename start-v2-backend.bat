@echo off
title Talent Search V2 - Backend API
echo ===========================================
echo Starting Talent Search V2 Backend (Port 5000)
echo ===========================================

cd /d "%~dp0"

set VENV=BackEnd\api_v2\.venv

REM ── Check if venv Python is usable ──────────────────────────────
%VENV%\Scripts\python.exe --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] .venv broken or missing. Recreating with Python 3.13...
    py -3.13 -m venv %VENV% --clear
    if errorlevel 1 (
        echo [ERR] py -3.13 not found. Install Python 3.13 and retry.
        pause & exit /b 1
    )
    echo [INFO] Installing dependencies...
    %VENV%\Scripts\pip install -r BackEnd\api_v2\requirements.txt
    if errorlevel 1 (
        echo [ERR] pip install failed.
        pause & exit /b 1
    )
    echo [OK] venv ready.
)

call %VENV%\Scripts\activate.bat

echo Starting Backend...
python run_backend.py

pause

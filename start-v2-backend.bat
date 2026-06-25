@echo off
title Talent Search V2 - Backend API
echo ===========================================
echo Starting Talent Search V2 Backend (Port 5000)
echo ===========================================

cd /d "%~dp0"

if exist "BackEnd\api_v2\.venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call BackEnd\api_v2\.venv\Scripts\activate.bat
) else (
    echo [WARN] .venv not found, using system Python...
)

echo Starting Backend via run_backend.py...
python run_backend.py

pause

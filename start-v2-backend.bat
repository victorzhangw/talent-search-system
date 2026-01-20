@echo off
title Talent Search V2 - Backend API
echo ===========================================
echo Starting Talent Search V2 Backend (Port 5000)
echo ===========================================

REM Ensure we are in the project root
cd /d "%~dp0"

if not exist ".venv" (
    echo Error: .venv not found in project root!
    echo Please run 'python -m uv venv' or ensure .venv exists.
    pause
    exit /b 1
)

echo Activating virtual environment...
call .venv\Scripts\activate

echo Starting Backend via run_backend.py...
python run_backend.py

pause

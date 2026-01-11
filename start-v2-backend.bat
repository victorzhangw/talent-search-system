@echo off
title Talent Search V2 - Backend API
echo ===========================================
echo Starting Talent Search V2 Backend (Port 5000)
echo ===========================================
cd BackEnd\api_v2
if not exist ".venv" (
    echo Error: .venv not found!
    echo Please make sure you are in the correct directory or have run 'python -m venv .venv'
    pause
    exit /b 1
)

echo Activating virtual environment...
call .venv\Scripts\activate

echo Starting Flask App...
python app.py

pause

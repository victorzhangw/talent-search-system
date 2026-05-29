@echo off
title Talent Search V2 - Backend API
echo ===========================================
echo Starting Talent Search V2 Backend (Port 5000)
echo ===========================================

REM Ensure we are in the project root
cd /d "%~dp0"

REM Try activating .venv; fall back to system Python if venv is broken
set PYTHON_CMD=python
if exist ".venv\Scripts\python.exe" (
    echo Activating virtual environment...
    call .venv\Scripts\activate
    REM Verify the activated Python works
    python -c "import sys; sys.exit(0)" >nul 2>&1
    if errorlevel 1 (
        echo [WARN] .venv Python is broken, falling back to system Python...
        deactivate >nul 2>&1
        set PYTHON_CMD=python
    )
) else (
    echo [WARN] .venv not found, using system Python...
)

echo Starting Backend via run_backend.py...
%PYTHON_CMD% run_backend.py

pause

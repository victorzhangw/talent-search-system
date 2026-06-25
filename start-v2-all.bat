@echo off
title Starting Talent Search V2 System
echo ===========================================
echo   Talent Search V2 - Combined Launcher
echo ===========================================
echo.

cd /d "%~dp0"

echo [1/3] Starting PostgreSQL...
cmd /c ""C:\Program Files\PostgreSQL\18\bin\pg_ctl" -D "C:\Program Files\PostgreSQL\18\data" restart"
if %errorlevel% neq 0 (
    echo Restart failed or service stopped. Attempting fresh start...
    cmd /c ""C:\Program Files\PostgreSQL\18\bin\pg_ctl" -D "C:\Program Files\PostgreSQL\18\data" start"
)
timeout /t 5 /nobreak >nul

echo [2/3] Starting Backend API...
start "TalentSearch V2 - Backend" cmd /k "call start-v2-backend.bat"

echo Waiting for Backend initialization...
timeout /t 5 /nobreak >nul

echo [3/3] Starting Frontend Widget...
start "TalentSearch V2 - Frontend" cmd /k "call start-v2-frontend.bat"

echo.
echo ===========================================
echo   All services initiated.
echo   - Backend:         http://localhost:5000
echo   - Frontend Widget: http://localhost:5300
echo   - API Docs:        http://localhost:5000/api/docs
echo ===========================================
echo.
timeout /t 10

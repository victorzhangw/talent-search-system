@echo off
title Starting Talent Search V2 System
echo ===========================================
echo   Talent Search V2 - Combined Launcher
echo ===========================================
echo.
echo [1/4] Starting PostgreSQL...
echo Attempting to restart PostgreSQL...
cmd /c ""C:\Program Files\PostgreSQL\18\bin\pg_ctl" -D "C:\Program Files\PostgreSQL\18\data" restart"
if %errorlevel% neq 0 (
    echo Restart failed or service stopped. Attempting fresh start...
    cmd /c ""C:\Program Files\PostgreSQL\18\bin\pg_ctl" -D "C:\Program Files\PostgreSQL\18\data" start"
)
timeout /t 5 /nobreak >nul

REM echo [2/4] Starting LLM Proxy (Port 4000)...
REM start "TalentSearch V2 - LLM Router" cmd /k "call start-llm-proxy-v2.bat"
REM timeout /t 3 /nobreak >nul

echo [2.5/4] Starting Backend API...
start "TalentSearch V2 - Backend" cmd /k "call start-v2-backend.bat"

echo [3/4] Waiting for Backend initialization...
timeout /t 3 /nobreak >nul

echo [4/4] Starting Frontend Widget...
start "TalentSearch V2 - Frontend" cmd /k "call start-v2-frontend.bat"

echo [Checking] Starting Admin Panel...
start "TalentSearch V2 - Admin Panel" cmd /k "call start-v2-admin.bat"

echo.
echo ===========================================
echo   All services initiated.
echo   - Backend: http://localhost:5000
echo   - Frontend Widget: http://localhost:5300
echo   - Admin Panel: http://localhost:5301
echo ===========================================
echo.
echo Opening Admin Panel in browser...
timeout /t 3 /nobreak >nul
start http://localhost:5301

echo.
echo Initial setup complete. You can close this window.
timeout /t 10

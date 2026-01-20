@echo off
title Starting Talent Search V2 System
echo ===========================================
echo   Talent Search V2 - Combined Launcher
echo ===========================================
echo.
echo [1/4] Checking PostgreSQL...
netstat -an | find "5432" >nul
if %errorlevel%==0 (
    echo PostgreSQL is already running.
) else (
    echo Starting PostgreSQL...
    "C:\Program Files\PostgreSQL\18\bin\pg_ctl" -D "C:\Program Files\PostgreSQL\18\data" start
    timeout /t 5 /nobreak >nul
)

echo [2/4] Starting Backend API...
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

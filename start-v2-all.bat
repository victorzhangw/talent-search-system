@echo off
setlocal
title Talent Search V2 Launcher

cd /d "%~dp0"

echo Starting PostgreSQL...
"C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -D "C:\Program Files\PostgreSQL\18\data" restart >nul 2>&1
if %errorlevel% neq 0 (
    "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" -D "C:\Program Files\PostgreSQL\18\data" start >nul 2>&1
)
timeout /t 5 /nobreak >nul

echo Starting Backend...
start "Backend API" cmd /k "call start-v2-backend.bat"
timeout /t 5 /nobreak >nul

echo Starting Widget...
start "Widget Dev" cmd /k "call start-v2-frontend.bat"

echo.
echo Backend:  http://localhost:5000
echo Widget:   http://localhost:5300
echo API Docs: http://localhost:5000/api/docs
echo.
timeout /t 10

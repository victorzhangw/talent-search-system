@echo off
setlocal
title Talent Search V2 Launcher

cd /d "%~dp0"

REM Clear whatever is still running first. Starting on top of a live backend
REM does not fail loudly -- the new process comes up but never binds, so the
REM OLD one keeps answering with whatever code it was started with.
call stop-v2-all.bat
title Talent Search V2 Launcher

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

timeout /t 5 /nobreak >nul
echo.
call :report 5000 Backend
call :report 5300 Widget
echo.
echo Backend:  http://localhost:5000
echo Widget:   http://localhost:5300
echo API Docs: http://localhost:5000/api/docs
echo.
timeout /t 10
exit /b 0


:report
REM Confirms the port is held by a process that started just now. Startup time
REM is the one thing that tells a fresh instance from a survivor.
for /f "usebackq delims=" %%L in (`powershell -NoProfile -Command "$ids=@(Get-NetTCPConnection -State Listen -LocalPort %~1 -EA 0).OwningProcess; if($ids.Count -gt 0){$p=Get-Process -Id $ids[0] -EA 0; 'PID ' + $ids[0] + ' started ' + $p.StartTime.ToString('HH:mm:ss')}else{'not listening yet'}"`) do (
    echo %~2 on port %~1: %%L
)
exit /b 0

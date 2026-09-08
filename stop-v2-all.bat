@echo off
setlocal
title Talent Search V2 - Stop

cd /d "%~dp0"

REM Frees the two ports this project uses and closes the leftover consoles.
REM
REM Why this exists: a second backend binds nothing when the port is already
REM taken, yet it starts up and looks healthy. On 2026-09-08 a backend left
REM running from the previous day kept serving every request while three
REM restarts appeared to succeed -- four UAT calls were spent before anyone
REM noticed the audit records were missing the new fields.
REM
REM Kill by PORT, never by image name: "taskkill /IM python.exe" would also
REM take down unrelated Python servers on this machine.

echo Stopping Talent Search V2...
call :free_port 5000 "Backend API - Port 5000"
call :free_port 5300 "Widget Dev Server - Port 5300"
echo Done.
exit /b 0


:free_port
set "PORT=%~1"
set "WTITLE=%~2"
set "FOUND="
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "$ids=@(Get-NetTCPConnection -State Listen -LocalPort %PORT% -EA 0).OwningProcess; foreach($i in $ids){$i}"`) do (
    set "FOUND=1"
    echo   port %PORT% held by PID %%P - killing process tree
    taskkill /PID %%P /T /F >nul 2>&1
)
if not defined FOUND echo   port %PORT% already free
REM "cmd /k" keeps the console open after the server dies, and a dead console
REM titled "Backend API" is exactly what makes a stale instance hard to spot.
taskkill /FI "WINDOWTITLE eq %WTITLE%" /T /F >nul 2>&1
exit /b 0

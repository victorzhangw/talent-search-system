@echo off
title Force Restart PostgreSQL
echo ===========================================
echo   Force Restart PostgreSQL Database
echo ===========================================
echo.

echo [1/2] Attempting to RESTART PostgreSQL service...
"C:\Program Files\PostgreSQL\18\bin\pg_ctl" -D "C:\Program Files\PostgreSQL\18\data" restart

if %errorlevel% neq 0 (
    echo.
    echo [Warning] Restart failed (Server might be stopped or permission denied).
    echo [2/2] Attempting to START PostgreSQL service directly...
    "C:\Program Files\PostgreSQL\18\bin\pg_ctl" -D "C:\Program Files\PostgreSQL\18\data" start
) else (
    echo.
    echo [Success] PostgreSQL restarted successfully.
)

echo.
echo ===========================================
echo   Operation Complete.
echo ===========================================
timeout /t 5

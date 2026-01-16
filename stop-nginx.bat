@echo off
REM Nginx 停止腳本

echo Stopping Nginx...
C:\nginx\nginx.exe -s stop

timeout /t 2 /nobreak >nul

tasklist /FI "IMAGENAME eq nginx.exe" 2>NUL | find /I /N "nginx.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Warning: Nginx is still running. Force killing...
    taskkill /F /IM nginx.exe
) else (
    echo Nginx stopped successfully.
)

pause

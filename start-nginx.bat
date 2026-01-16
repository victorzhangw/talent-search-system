@echo off
REM Nginx 啟動腳本

echo ========================================
echo   Starting Nginx for Traitty API
echo ========================================

REM 檢查 Nginx 是否已運行
tasklist /FI "IMAGENAME eq nginx.exe" 2>NUL | find /I /N "nginx.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Nginx is already running. Reloading configuration...
    C:\nginx\nginx.exe -s reload
    echo Configuration reloaded.
) else (
    echo Starting Nginx...
    start /B C:\nginx\nginx.exe
    echo Nginx started.
)

echo.
echo ========================================
echo   Nginx is running
echo   - HTTP: http://localhost
echo   - HTTPS: https://localhost (if configured)
echo ========================================
echo.
echo To stop Nginx: nginx -s stop
echo To reload config: nginx -s reload
echo.

pause

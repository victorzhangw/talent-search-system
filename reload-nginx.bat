@echo off
REM Nginx 重新載入配置（用於憑證更新後）

echo Reloading Nginx configuration...

REM 測試配置是否正確
C:\nginx\nginx.exe -t

if %ERRORLEVEL% EQU 0 (
    echo Configuration test passed. Reloading...
    C:\nginx\nginx.exe -s reload
    echo Nginx reloaded successfully.
) else (
    echo Configuration test failed! Please check nginx.conf
    exit /b 1
)

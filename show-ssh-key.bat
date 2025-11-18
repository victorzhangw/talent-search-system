@echo off
chcp 65001 >nul
echo ========================================
echo SSH 私鑰查看工具
echo ========================================
echo.

echo 📍 私鑰文件位置:
echo    BackEnd\private-key-openssh.pem
echo.

echo ========================================
echo SSH 私鑰內容:
echo ========================================
echo.

type BackEnd\private-key-openssh.pem

echo.
echo ========================================
echo 使用說明
echo ========================================
echo.
echo 1. 複製上面的完整內容（包括 BEGIN 和 END 行）
echo.
echo 2. 在 Fly.io 設定環境變數:
echo    PowerShell:
echo    $key = Get-Content BackEnd\private-key-openssh.pem -Raw
echo    fly secrets set "DB_SSH_PRIVATE_KEY=$key"
echo.
echo 3. 或在 Render 設定環境變數:
echo    直接複製貼上上面的內容
echo.
pause

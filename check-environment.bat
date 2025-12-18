@echo off
chcp 65001 >nul
title 人才管理系統 - 環境檢查

echo.
echo ========================================
echo   人才管理系統 - 環境檢查
echo ========================================
echo.

set ERROR_COUNT=0

echo [檢查 1/6] Python 版本...
python --version 2>nul
if errorlevel 1 (
    echo [錯誤] 未安裝 Python
    set /a ERROR_COUNT+=1
) else (
    echo [通過] Python 已安裝
)
echo.

echo [檢查 2/6] Node.js 版本...
node --version 2>nul
if errorlevel 1 (
    echo [錯誤] 未安裝 Node.js
    set /a ERROR_COUNT+=1
) else (
    echo [通過] Node.js 已安裝
)
echo.

echo [檢查 3/6] 後端環境變數文件...
if exist "BackEnd\.env.local" (
    echo [通過] BackEnd\.env.local 存在
) else (
    echo [錯誤] BackEnd\.env.local 不存在
    echo [提示] 請複製 BackEnd\.env.example 為 BackEnd\.env.local
    set /a ERROR_COUNT+=1
)
echo.

echo [檢查 4/6] 後端虛擬環境...
if exist "BackEnd\venv" (
    echo [通過] 虛擬環境存在
) else (
    echo [警告] 虛擬環境不存在
    echo [提示] 首次運行 start.bat 時會自動創建
)
echo.

echo [檢查 5/6] 前端依賴...
if exist "frontend\node_modules" (
    echo [通過] 前端依賴已安裝
) else (
    echo [警告] 前端依賴未安裝
    echo [提示] 首次運行 start.bat 時會自動安裝
)
echo.

echo [檢查 6/6] Prompt 配置文件...
if exist "BackEnd\prompts\hr_consultation_prompts.json" (
    echo [通過] Prompt 配置文件存在
) else (
    echo [錯誤] Prompt 配置文件不存在
    set /a ERROR_COUNT+=1
)
echo.

echo ========================================
if %ERROR_COUNT% EQU 0 (
    echo   環境檢查完成 - 一切正常！
    echo   可以運行 start.bat 啟動系統
) else (
    echo   環境檢查完成 - 發現 %ERROR_COUNT% 個錯誤
    echo   請修復錯誤後再啟動系統
)
echo ========================================
echo.

echo [提示] 詳細配置說明請查看:
echo   - docs/guides/GETTING_STARTED.md
echo   - docs/configuration/README_ENV.md
echo.

pause

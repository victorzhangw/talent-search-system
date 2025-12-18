@echo off
chcp 65001 >nul
title 人才管理系統 - 停止服務

echo.
echo ========================================
echo   人才管理系統 - 停止服務
echo ========================================
echo.

echo [1/3] 正在查找後端進程...

REM 查找並終止後端進程（端口 8000）
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo [找到] 後端進程 PID: %%a
    taskkill /PID %%a /F >nul 2>&1
    if not errorlevel 1 (
        echo [成功] 已停止後端服務
    )
)

echo.
echo [2/3] 正在查找前端進程...

REM 查找並終止前端進程（端口 5173）
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    echo [找到] 前端進程 PID: %%a
    taskkill /PID %%a /F >nul 2>&1
    if not errorlevel 1 (
        echo [成功] 已停止前端服務
    )
)

echo.
echo [3/3] 清理完成

REM 終止所有標題包含"人才管理系統"的命令窗口
taskkill /FI "WINDOWTITLE eq 人才管理系統*" /F >nul 2>&1

echo.
echo ========================================
echo   所有服務已停止
echo ========================================
echo.
pause

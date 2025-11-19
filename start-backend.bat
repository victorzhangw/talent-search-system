@echo off
chcp 65001 >nul
title Backend API - Port 8000

cd /d "%~dp0BackEnd"

echo ========================================
echo   Starting Backend API
echo ========================================
echo.
echo Port: 8000
echo API Docs: http://localhost:8000/docs
echo.

venv\Scripts\python.exe talent_search_api.py

pause

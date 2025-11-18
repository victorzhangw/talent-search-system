@echo off
chcp 65001 >nul
cls

echo.
echo ╔════════════════════════════════════════╗
echo ║   AI Talent Search System              ║
echo ║   Quick Start Launcher                 ║
echo ╚════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Start Backend
echo [1/2] Starting Backend...
start "Backend API (Port 8000)" cmd /c "cd /d "%~dp0BackEnd" && venv\Scripts\python.exe talent_search_api_v2.py"
timeout /t 2 /nobreak >nul

:: Start Frontend
echo [2/2] Starting Frontend...
start "Frontend Dev (Port 3000)" cmd /c "cd /d "%~dp0frontend" && npm run dev"
timeout /t 2 /nobreak >nul

echo.
echo ✓ Services started in separate windows
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo Opening browser in 3 seconds...
timeout /t 3 /nobreak >nul

start http://localhost:3000

echo.
echo Done! You can close this window.
timeout /t 2 /nobreak >nul

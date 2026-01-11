@echo off
title Starting Talent Search V2 System
echo ===========================================
echo   Talent Search V2 - Combined Launcher
echo ===========================================
echo.
echo [1/3] Starting Backend API...
start "TalentSearch V2 - Backend" cmd /k "call start-v2-backend.bat"

echo [2/3] Waiting for Backend initialization...
timeout /t 3 /nobreak >nul

echo [3/3] Starting Frontend Widget...
start "TalentSearch V2 - Frontend" cmd /k "call start-v2-frontend.bat"

echo.
echo ===========================================
echo   All services initiated.
echo   - Backend: http://localhost:5000
echo   - Frontend: (Check the frontend window for URL, usually http://localhost:5173)
echo ===========================================
echo.
echo Opening localhost:5173 in browser (assuming default Vite port)...
timeout /t 3 /nobreak >nul
start http://localhost:5173

echo.
echo Initial setup complete. You can close this window.
timeout /t 10

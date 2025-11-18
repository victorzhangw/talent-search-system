@echo off
chcp 65001 >nul
title AI Talent Search System - Stop All Services

echo ========================================
echo   AI Talent Search System
echo   Stopping All Services
echo ========================================
echo.

:: Kill Python processes (Backend)
echo [1/2] Stopping Backend (Python)...
taskkill /F /FI "WINDOWTITLE eq Backend - FastAPI*" >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Backend*" >nul 2>&1
echo ✓ Backend stopped

:: Kill Node processes (Frontend)
echo [2/2] Stopping Frontend (Node.js)...
taskkill /F /FI "WINDOWTITLE eq Frontend - Vite*" >nul 2>&1
taskkill /F /IM node.exe /FI "WINDOWTITLE eq Frontend*" >nul 2>&1
echo ✓ Frontend stopped

echo.
echo ========================================
echo   ✓ All Services Stopped
echo ========================================
echo.
pause

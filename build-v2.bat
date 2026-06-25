@echo off
title Build api_v2 + Widget
echo ============================================
echo  Building api_v2 + Chat Widget Docker Image
echo ============================================
cd /d "%~dp0"

REM ── 1. Build Widget locally for release artifacts ──
echo.
echo [1/3] Building chat widget...
cd frontend\chat-widget
call npm ci --prefer-offline
if errorlevel 1 ( echo [ERR] npm ci failed & pause & exit /b 1 )
call npm run build
if errorlevel 1 ( echo [ERR] Widget build failed & pause & exit /b 1 )
cd /d "%~dp0"
echo [OK] Widget built ^& release artifacts saved to frontend\chat-widget\releases\

REM ── 2. Build Docker image ──
echo.
echo [2/3] Building Docker image (api_v2 + widget)...
docker build -f Dockerfile.v2 -t ai-chatbot-v2:latest .
if errorlevel 1 ( echo [ERR] Docker build failed & pause & exit /b 1 )
echo [OK] Docker image: ai-chatbot-v2:latest

REM ── 3. Done ──
echo.
echo [3/3] Build complete!
echo.
echo To start the full stack (API + PostgreSQL):
echo   docker compose -f docker-compose.v2.yml up -d
echo.
echo Widget embed snippet (after container is running):
echo   ^<link rel="stylesheet" href="http://localhost:5000/widget/loader.css"^>
echo   ^<script src="http://localhost:5000/widget/loader.iife.js"^>^</script^>
echo.
pause

@echo off
echo.
echo ===========================================
echo       High Availability Launcher
echo ===========================================
echo.

cd /d %~dp0

REM 1. Start LLM Proxy in a new window
echo [Step 1] Starting LLM Router (LiteLLM)...
start "LLM Proxy - Dynamic Router" start-llm-proxy.bat

REM 2. Wait 5 seconds for proxy to initialize
echo       ... Waiting for Router to start
ping 127.0.0.1 -n 6 > nul

REM 3. Start Backend Optimized
echo [Step 2] Starting Optimized Backend Cluster...
start "Backend API Cluster" start-backend-optimized.bat

echo.
echo [System Ready]
echo - LLM Router: http://localhost:4000
echo - Backend API: http://localhost:8000
echo.
pause

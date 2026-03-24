@echo off
cd /d %~dp0
call .venv\Scripts\activate

echo [Backend Optimized] Starting Uvicorn with High Concurrency Settings...
echo Workers: 4
echo Max Connections: 100
echo LLM Router: http://localhost:4000 (Dynamic)
echo -------------------------------------------------------------------

REM Temporarily override LLM config to use Local Proxy
set LLM_API_BASE=http://localhost:4000
set LLM_API_KEY=sk-proxy-placeholder
set LLM_MODEL=optimized-router-model

uvicorn api_v2.asgi:application ^
    --host 0.0.0.0 ^
    --port 8000 ^
    --workers 4 ^
    --limit-concurrency 100 ^
    --timeout-keep-alive 75 ^
    --log-level warning

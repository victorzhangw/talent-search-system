@echo off
cd /d %~dp0
call .venv\Scripts\activate
echo [LiteLLM Proxy] Starting Dynamic LLM Router on Port 4000...
echo Primary: NVIDIA AI Foundation
echo Backup: DeepSeek Official API
echo Routing Strategy: Latency Based (Fastest Response)
echo ---------------------------------------------------
BackEnd\api_v2\.venv\Scripts\litellm --config BackEnd\api_v2\litellm_config.yaml --port 4000

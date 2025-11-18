@echo off
chcp 65001 >nul
echo ========================================
echo Fly.io 環境變數設定助手
echo ========================================
echo.

echo 正在設定環境變數...
echo.

echo [1/12] 設定 DB_SSH_HOST...
fly secrets set DB_SSH_HOST=54.199.255.239

echo [2/12] 設定 DB_SSH_PORT...
fly secrets set DB_SSH_PORT=22

echo [3/12] 設定 DB_SSH_USERNAME...
fly secrets set DB_SSH_USERNAME=victor_cheng

echo [4/12] 設定 DB_SSH_PRIVATE_KEY...
echo 正在讀取私鑰文件...
powershell -Command "$key = Get-Content BackEnd\private-key-openssh.pem -Raw; fly secrets set \"DB_SSH_PRIVATE_KEY=$key\""

echo [5/12] 設定 DB_HOST...
fly secrets set DB_HOST=localhost

echo [6/12] 設定 DB_PORT...
fly secrets set DB_PORT=5432

echo [7/12] 設定 DB_NAME...
fly secrets set DB_NAME=projectdb

echo [8/12] 設定 DB_USER...
fly secrets set DB_USER=projectuser

echo [9/12] 設定 DB_PASSWORD...
fly secrets set DB_PASSWORD=projectpass

echo [10/12] 設定 LLM_API_KEY...
fly secrets set LLM_API_KEY=sk-xmwxrtsxgsjwuyeceydoyuopezzlqresdjyvlzrbbjeejiff

echo [11/12] 設定 LLM_API_HOST...
fly secrets set LLM_API_HOST=https://api.siliconflow.cn

echo [12/12] 設定 LLM_MODEL...
fly secrets set LLM_MODEL=deepseek-ai/DeepSeek-V3

echo.
echo ========================================
echo ✅ 所有環境變數設定完成！
echo ========================================
echo.

echo 驗證設定:
fly secrets list

echo.
echo 下一步:
echo 1. 執行 fly deploy 開始部署
echo 2. 執行 fly status 查看狀態
echo 3. 執行 fly open 打開應用
echo.
pause

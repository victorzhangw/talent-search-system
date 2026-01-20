@echo off

REM 1. 切換到專案目錄 (如果從其他地方執行)
cd /d C:\inetpub\wwwroot\TalentChatAPI

REM 2. 啟動虛擬環境 (假設資料夾名稱為 .venv)
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] .venv not found, trying 'venv'...
    if exist venv\Scripts\activate.bat (
        call venv\Scripts\activate.bat
    ) else (
        echo [ERROR] Virtual environment not found! Please create .venv or venv.
        pause
        exit /b 1
    )
)

REM 3. 調整 Python Path (指向 BackEnd 上一層)
set PYTHONPATH=.

REM 4. 啟動 Uvicorn
echo Starting Uvicorn Server...
echo Host: 0.0.0.0
echo Port: 5000
echo Workers: 4

uvicorn asgi:app --host 0.0.0.0 --port 5000 --workers 4

pause

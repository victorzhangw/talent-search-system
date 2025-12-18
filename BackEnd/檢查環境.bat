@echo off
chcp 65001 >nul
echo ========================================
echo    檢查開發環境
echo ========================================
echo.

cd /d "%~dp0"

REM 檢查 Python
echo [1/5] 檢查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo    ❌ 未安裝 Python 或未加入 PATH
    echo    請安裝 Python 3.10+ 並加入系統 PATH
) else (
    python --version
    echo    ✅ Python 已安裝
)
echo.

REM 檢查虛擬環境
echo [2/5] 檢查虛擬環境...
if exist "venv\Scripts\activate.bat" (
    echo    ✅ 虛擬環境已存在
) else (
    echo    ❌ 虛擬環境不存在
    echo.
    echo    建議執行：
    echo    python -m venv venv
)
echo.

REM 檢查依賴
echo [3/5] 檢查 Python 依賴...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    
    echo    檢查關鍵套件...
    python -c "import fastapi" >nul 2>&1
    if errorlevel 1 (
        echo    ❌ fastapi 未安裝
    ) else (
        echo    ✅ fastapi 已安裝
    )
    
    python -c "import psycopg2" >nul 2>&1
    if errorlevel 1 (
        echo    ❌ psycopg2 未安裝
    ) else (
        echo    ✅ psycopg2 已安裝
    )
    
    python -c "import sshtunnel" >nul 2>&1
    if errorlevel 1 (
        echo    ❌ sshtunnel 未安裝
    ) else (
        echo    ✅ sshtunnel 已安裝
    )
) else (
    echo    ⚠️  無法檢查（虛擬環境不存在）
)
echo.

REM 檢查環境變數文件
echo [4/5] 檢查環境變數文件...
if exist ".env.local" (
    echo    ✅ .env.local 已存在
) else (
    echo    ⚠️  .env.local 不存在（可選）
)

if exist ".env.production.example" (
    echo    ✅ .env.production.example 已存在
) else (
    echo    ⚠️  .env.production.example 不存在
)
echo.

REM 檢查主要文件
echo [5/5] 檢查主要文件...
if exist "talent_search_api.py" (
    echo    ✅ talent_search_api.py 存在
) else (
    echo    ❌ talent_search_api.py 不存在
)

if exist "hr_consultation_api.py" (
    echo    ✅ hr_consultation_api.py 存在
) else (
    echo    ❌ hr_consultation_api.py 不存在
)

if exist "hr_consultation_service.py" (
    echo    ✅ hr_consultation_service.py 存在
) else (
    echo    ❌ hr_consultation_service.py 不存在
)
echo.

echo ========================================
echo  檢查完成！
echo ========================================
echo.

REM 提供建議
echo 💡 建議：
echo.
echo 如果虛擬環境或依賴缺失，請執行：
echo.
echo   cd BackEnd
echo   python -m venv venv
echo   venv\Scripts\activate
echo   pip install -r requirements.txt
echo.

pause

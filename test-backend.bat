@echo off
chcp 65001 >nul
title Test Backend

echo ========================================
echo   Testing Backend Setup
echo ========================================
echo.

cd /d "%~dp0"

echo [1] Checking Python in venv...
if exist "BackEnd\venv\Scripts\python.exe" (
    echo ✓ Python found in venv
    BackEnd\venv\Scripts\python.exe --version
) else (
    echo ❌ Python not found in venv
    goto :error
)
echo.

echo [2] Checking FastAPI...
BackEnd\venv\Scripts\python.exe -c "import fastapi; print('✓ FastAPI installed')" 2>nul
if errorlevel 1 (
    echo ❌ FastAPI not installed
    goto :error
)
echo.

echo [3] Checking API file...
if exist "BackEnd\talent_search_api_v2.py" (
    echo ✓ API file exists
) else (
    echo ❌ API file not found
    goto :error
)
echo.

echo [4] Testing API import...
cd BackEnd
venv\Scripts\python.exe -c "import talent_search_api_v2; print('✓ API can be imported')" 2>nul
if errorlevel 1 (
    echo ❌ API import failed
    echo.
    echo Trying to show error:
    venv\Scripts\python.exe -c "import talent_search_api_v2"
    cd ..
    goto :error
)
cd ..
echo.

echo ========================================
echo   ✓ All checks passed!
echo ========================================
echo.
echo You can now run: venv-start-all.bat
echo.
pause
exit /b 0

:error
echo.
echo ========================================
echo   ❌ Setup incomplete
echo ========================================
echo.
echo Please run: setup-first-time.bat
echo.
pause
exit /b 1

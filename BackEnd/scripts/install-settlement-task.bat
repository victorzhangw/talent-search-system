@echo off
setlocal
REM ============================================================================
REM  Daily settlement 補送作業 — 註冊到 Windows 工作排程器（單元 U3b / 決策 D4）
REM
REM  api_v2/scheduler.py 是 one-shot 批次作業：跑一輪就離開，週期由這裡決定。
REM
REM  為什麼設定要寫成腳本放進 repo：排程設定若只存在某台機器的 GUI 裡，就沒有人
REM  知道正式機到底幾分鐘跑一次、用哪個 Python、失敗會不會重疊執行。這支腳本本身
REM  就是那份設定的文件。
REM
REM  用法：
REM    install-settlement-task.bat            預設每 15 分鐘
REM    install-settlement-task.bat 30         改成每 30 分鐘
REM
REM  移除：uninstall-settlement-task.bat
REM  手動觸發一次：schtasks /Run /TN "TraittyDailySettlementRetry"
REM  看上次結果  ：schtasks /Query /TN "TraittyDailySettlementRetry" /V /FO LIST
REM  作業自己的紀錄：BackEnd/api_v2/logs/<日期>/settlement_scheduler.log
REM ============================================================================

set "TASK_NAME=TraittyDailySettlementRetry"

REM 這支腳本位於 <repo>\BackEnd\scripts\，往上兩層就是 repo 根目錄
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "BACKEND_DIR=%%~fI"

set "PYTHON=%BACKEND_DIR%\api_v2\.venv\Scripts\python.exe"
set "TARGET=%BACKEND_DIR%\api_v2\scheduler.py"

set "INTERVAL=%~1"
if "%INTERVAL%"=="" set "INTERVAL=15"

if not exist "%PYTHON%" (
    echo [ERR] 找不到虛擬環境的 Python: %PYTHON%
    echo       請先執行 start-v2-backend.bat 讓它建立 .venv，或手動建立。
    exit /b 1
)
if not exist "%TARGET%" (
    echo [ERR] 找不到作業程式: %TARGET%
    exit /b 1
)

echo 註冊工作排程...
echo   工作名稱 : %TASK_NAME%
echo   執行內容 : "%PYTHON%" "%TARGET%"
echo   執行頻率 : 每 %INTERVAL% 分鐘

schtasks /Create /F ^
  /TN "%TASK_NAME%" ^
  /TR "\"%PYTHON%\" \"%TARGET%\"" ^
  /SC MINUTE /MO %INTERVAL%

if %errorlevel% neq 0 (
    echo [ERR] 註冊失敗，錯誤碼 %errorlevel%
    exit /b %errorlevel%
)

echo.
echo [OK] 已註冊。確認重疊執行原則（必須是 IgnoreNew，否則前一輪還沒跑完就會再起一輪）：
schtasks /Query /TN "%TASK_NAME%" /XML | findstr /I "MultipleInstancesPolicy"
echo.
echo 手動觸發一次： schtasks /Run /TN "%TASK_NAME%"
echo 移除         ： uninstall-settlement-task.bat
endlocal

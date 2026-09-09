@echo off
setlocal
REM ============================================================================
REM  移除 Daily settlement 補送作業的工作排程（install-settlement-task.bat 的反向操作）
REM
REM  只移除排程，不動任何資料：daily_settlements 的 PENDING / FAILED 紀錄會留著，
REM  重新註冊後仍在 7 天視窗內的就會被接續補送。
REM ============================================================================

set "TASK_NAME=TraittyDailySettlementRetry"

schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %errorlevel% neq 0 (
    echo [OK] 工作排程 "%TASK_NAME%" 本來就不存在，不需要移除。
    exit /b 0
)

schtasks /Delete /F /TN "%TASK_NAME%"
if %errorlevel% neq 0 (
    echo [ERR] 移除失敗，錯誤碼 %errorlevel%
    exit /b %errorlevel%
)

echo [OK] 已移除工作排程 "%TASK_NAME%"。
echo      daily_settlements 的待補送紀錄未受影響。
endlocal

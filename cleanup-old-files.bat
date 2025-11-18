@echo off
chcp 65001 >nul
title Cleanup Old Files

echo ========================================
echo   Cleaning Up Old and Outdated Files
echo ========================================
echo.

cd /d "%~dp0"

echo This will delete the following:
echo.
echo [Root Directory]
echo   - Old BAT files (outdated launchers)
echo   - Old HTML files (backups)
echo   - Old documentation (✅ files)
echo   - Test files
echo.
echo [BackEnd Directory]
echo   - Test scripts
echo   - Debug scripts
echo   - Old API versions
echo   - Old BAT files
echo.
echo [Tests Directory]
echo   - Old test files
echo.

set /p confirm="Are you sure you want to continue? (Y/N): "
if /i not "%confirm%"=="Y" (
    echo Cancelled.
    pause
    exit /b 0
)

echo.
echo Starting cleanup...
echo.

:: Root directory - Old BAT files
echo [1/5] Cleaning root BAT files...
del /f /q "重啟API服務.bat" 2>nul
del /f /q "停止所有服務.bat" 2>nul
del /f /q "停止服務.bat" 2>nul
del /f /q "探索資料庫結構.bat" 2>nul
del /f /q "啟動人才搜索服務.bat" 2>nul
del /f /q "啟動完整系統-Vite版.bat" 2>nul
del /f /q "啟動完整系統.bat" 2>nul
del /f /q "啟動並測試.bat" 2>nul
del /f /q "啟動新版API.bat" 2>nul
del /f /q "診斷資料庫.bat" 2>nul
del /f /q "GStart.bat" 2>nul
del /f /q "start_all.bat" 2>nul
del /f /q "stop_all.bat" 2>nul
echo ✓ Old BAT files removed

:: Root directory - Old HTML and test files
echo [2/5] Cleaning old HTML and test files...
del /f /q "talent-chat-frontend-backup.html" 2>nul
del /f /q "test_api.html" 2>nul
del /f /q "測試修正-tooltip.html" 2>nul
del /f /q "index.html" 2>nul
echo ✓ Old HTML files removed

:: Root directory - Old documentation
echo [3/5] Cleaning old documentation...
del /f /q "✅中文特質名稱修正完成.md" 2>nul
del /f /q "✅完成-立即使用.md" 2>nul
del /f /q "✅商業級UI設計完成.md" 2>nul
del /f /q "✅問題修正完成-測試指南.md" 2>nul
del /f /q "✅新功能完成總結.md" 2>nul
del /f /q "✅UI修正完成-v3.md" 2>nul
del /f /q "方案總結-待確認.md" 2>nul
del /f /q "正確的測評表分析.md" 2>nul
del /f /q "如何使用聊天界面.md" 2>nul
del /f /q "快速啟動指南.md" 2>nul
del /f /q "快速測試新功能.md" 2>nul
del /f /q "系統更新總結-2025-11-16.md" 2>nul
del /f /q "使用說明-圖解.txt" 2>nul
del /f /q "使用說明.txt" 2>nul
del /f /q "前後端整合說明.md" 2>nul
del /f /q "問題修正說明-2025-11-16-v2.md" 2>nul
del /f /q "問題修正總結-2025-11-16.md" 2>nul
del /f /q "問題診斷-下一步.md" 2>nul
del /f /q "問題診斷指南.md" 2>nul
del /f /q "啟動測試說明.md" 2>nul
del /f /q "啟動腳本說明.txt" 2>nul
del /f /q "測試智能搜索.md" 2>nul
del /f /q "測試API.ps1" 2>nul
del /f /q "無外鍵處理方案-總結.md" 2>nul
del /f /q "無外鍵資料庫處理指南.md" 2>nul
del /f /q "新功能說明-面試問題生成.md" 2>nul
del /f /q "資料庫逆向工程方案.md" 2>nul
del /f /q "資料庫探索結果分析.md" 2>nul
del /f /q "API_v2修正說明.md" 2>nul
del /f /q "README-快速開始.md" 2>nul
del /f /q "README-資料庫逆向工程.md" 2>nul
del /f /q "Test測評表完整說明.md" 2>nul
del /f /q "UI更新說明.md" 2>nul
del /f /q "升級完成說明.md" 2>nul
del /f /q "database_schema_report.json" 2>nul
del /f /q "database_schema_report.md" 2>nul
del /f /q "connections.xml" 2>nul
del /f /q "LLMHost.txt" 2>nul
echo ✓ Old documentation removed

:: BackEnd directory - Test and debug files
echo [4/5] Cleaning BackEnd test files...
del /f /q "BackEnd\check_db.bat" 2>nul
del /f /q "BackEnd\check_trait_mapping.py" 2>nul
del /f /q "BackEnd\debug_trait_results.py" 2>nul
del /f /q "BackEnd\diagnose_database.py" 2>nul
del /f /q "BackEnd\explore_database_schema.py" 2>nul
del /f /q "BackEnd\query_traits.py" 2>nul
del /f /q "BackEnd\setup_and_run.bat" 2>nul
del /f /q "BackEnd\start_api.bat" 2>nul
del /f /q "BackEnd\start_fixed_api.py" 2>nul
del /f /q "BackEnd\talent_search_api_fixed.py" 2>nul
del /f /q "BackEnd\talent_search_api.py" 2>nul
del /f /q "BackEnd\talent_search_engine_fixed.py" 2>nul
del /f /q "BackEnd\test_enrich.py" 2>nul
del /f /q "BackEnd\test_full_flow.py" 2>nul
del /f /q "BackEnd\test_hybrid.bat" 2>nul
del /f /q "BackEnd\test_ssh_connection.py" 2>nul
del /f /q "BackEnd\conversation_enhanced_search.py" 2>nul
del /f /q "BackEnd\conversation_manager.py" 2>nul
del /f /q "BackEnd\convert_ppk_to_openssh.py" 2>nul
del /f /q "BackEnd\database_schema.json" 2>nul
del /f /q "BackEnd\intent_definitions.example.json" 2>nul
del /f /q "BackEnd\intent_definitions.json" 2>nul
del /f /q "BackEnd\requirements_api.txt" 2>nul
echo ✓ BackEnd test files removed

:: Tests directory
echo [5/5] Cleaning tests directory...
if exist "tests" (
    del /f /q "tests\test_jsonb_queries.py" 2>nul
    del /f /q "tests\test_fixed_search.py" 2>nul
)
echo ✓ Test files removed

:: Old assets directory (if using new frontend)
echo.
echo [Optional] Cleaning old assets directory...
set /p cleanup_assets="Remove old assets directory? (Y/N): "
if /i "%cleanup_assets%"=="Y" (
    rmdir /s /q "assets" 2>nul
    echo ✓ Old assets directory removed
) else (
    echo ⊘ Kept assets directory
)

:: Old frontend files
echo.
echo [Optional] Cleaning old frontend files...
set /p cleanup_old_frontend="Remove old frontend HTML file? (Y/N): "
if /i "%cleanup_old_frontend%"=="Y" (
    del /f /q "talent-chat-frontend.html" 2>nul
    echo ✓ Old frontend HTML removed
) else (
    echo ⊘ Kept old frontend HTML
)

echo.
echo ========================================
echo   ✓ Cleanup Complete!
echo ========================================
echo.
echo Remaining important files:
echo   ✓ start-all.bat
echo   ✓ stop-all.bat
echo   ✓ setup-first-time.bat
echo   ✓ README-QUICKSTART.md
echo   ✓ BackEnd/talent_search_api_v2.py
echo   ✓ BackEnd/interview_api.py
echo   ✓ frontend/ (Vue 3 + Vite)
echo.
pause

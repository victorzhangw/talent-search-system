@echo off
chcp 65001 >nul
title List Old Files to be Cleaned

echo ========================================
echo   Files Marked for Cleanup
echo ========================================
echo.

cd /d "%~dp0"

echo [ROOT DIRECTORY - Old BAT Files]
echo.
if exist "重啟API服務.bat" echo   ✓ 重啟API服務.bat
if exist "停止所有服務.bat" echo   ✓ 停止所有服務.bat
if exist "停止服務.bat" echo   ✓ 停止服務.bat
if exist "探索資料庫結構.bat" echo   ✓ 探索資料庫結構.bat
if exist "啟動人才搜索服務.bat" echo   ✓ 啟動人才搜索服務.bat
if exist "啟動完整系統-Vite版.bat" echo   ✓ 啟動完整系統-Vite版.bat
if exist "啟動完整系統.bat" echo   ✓ 啟動完整系統.bat
if exist "啟動並測試.bat" echo   ✓ 啟動並測試.bat
if exist "啟動新版API.bat" echo   ✓ 啟動新版API.bat
if exist "診斷資料庫.bat" echo   ✓ 診斷資料庫.bat
if exist "GStart.bat" echo   ✓ GStart.bat
if exist "start_all.bat" echo   ✓ start_all.bat
if exist "stop_all.bat" echo   ✓ stop_all.bat
echo.

echo [ROOT DIRECTORY - Old HTML/Test Files]
echo.
if exist "talent-chat-frontend-backup.html" echo   ✓ talent-chat-frontend-backup.html
if exist "test_api.html" echo   ✓ test_api.html
if exist "測試修正-tooltip.html" echo   ✓ 測試修正-tooltip.html
if exist "index.html" echo   ✓ index.html (old version)
echo.

echo [ROOT DIRECTORY - Old Documentation]
echo.
if exist "✅中文特質名稱修正完成.md" echo   ✓ ✅中文特質名稱修正完成.md
if exist "✅完成-立即使用.md" echo   ✓ ✅完成-立即使用.md
if exist "✅商業級UI設計完成.md" echo   ✓ ✅商業級UI設計完成.md
if exist "✅問題修正完成-測試指南.md" echo   ✓ ✅問題修正完成-測試指南.md
if exist "✅新功能完成總結.md" echo   ✓ ✅新功能完成總結.md
if exist "✅UI修正完成-v3.md" echo   ✓ ✅UI修正完成-v3.md
if exist "升級完成說明.md" echo   ✓ 升級完成說明.md
if exist "快速啟動指南.md" echo   ✓ 快速啟動指南.md
if exist "測試智能搜索.md" echo   ✓ 測試智能搜索.md
if exist "測試API.ps1" echo   ✓ 測試API.ps1
echo   ... and more old documentation files
echo.

echo [BACKEND DIRECTORY - Test/Debug Files]
echo.
if exist "BackEnd\check_db.bat" echo   ✓ BackEnd\check_db.bat
if exist "BackEnd\check_trait_mapping.py" echo   ✓ BackEnd\check_trait_mapping.py
if exist "BackEnd\debug_trait_results.py" echo   ✓ BackEnd\debug_trait_results.py
if exist "BackEnd\test_enrich.py" echo   ✓ BackEnd\test_enrich.py
if exist "BackEnd\test_full_flow.py" echo   ✓ BackEnd\test_full_flow.py
if exist "BackEnd\test_hybrid.bat" echo   ✓ BackEnd\test_hybrid.bat
echo.

echo [BACKEND DIRECTORY - Old API Versions]
echo.
if exist "BackEnd\talent_search_api.py" echo   ✓ BackEnd\talent_search_api.py (old)
if exist "BackEnd\talent_search_api_fixed.py" echo   ✓ BackEnd\talent_search_api_fixed.py (old)
if exist "BackEnd\start_fixed_api.py" echo   ✓ BackEnd\start_fixed_api.py (old)
echo.

echo [TESTS DIRECTORY]
echo.
if exist "tests\test_jsonb_queries.py" echo   ✓ tests\test_jsonb_queries.py
if exist "tests\test_fixed_search.py" echo   ✓ tests\test_fixed_search.py
echo.

echo ========================================
echo   Files to KEEP (Important)
echo ========================================
echo.
echo [Root Directory]
echo   ✓ start-all.bat (NEW - Start everything)
echo   ✓ stop-all.bat (NEW - Stop everything)
echo   ✓ setup-first-time.bat (NEW - First time setup)
echo   ✓ README-QUICKSTART.md (NEW - Quick start guide)
echo   ✓ README.md (Main documentation)
echo   ✓ PROJECT_STRUCTURE.md
echo.
echo [BackEnd Directory]
echo   ✓ BackEnd\talent_search_api_v2.py (CURRENT VERSION)
echo   ✓ BackEnd\interview_api.py (CURRENT VERSION)
echo   ✓ BackEnd\requirements.txt
echo.
echo [Frontend Directory]
echo   ✓ frontend\ (Vue 3 + Vite - NEW)
echo.
echo [Docs Directory]
echo   ✓ docs\ (Keep all documentation)
echo.

echo ========================================
echo.
echo To clean up these files, run:
echo   cleanup-old-files.bat
echo.
pause

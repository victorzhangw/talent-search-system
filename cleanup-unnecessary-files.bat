@echo off
chcp 65001 >nul
echo ========================================
echo 清理不必要的文件和測試代碼
echo ========================================
echo.

echo 這個腳本將刪除以下類型的文件：
echo 1. 重複的部署文檔（保留最新的）
echo 2. 測試和診斷文件
echo 3. 舊版本的 API 文件
echo 4. 臨時文件和備份
echo.
echo 按任意鍵繼續，或 Ctrl+C 取消...
pause >nul
echo.

echo [1/6] 刪除重複的部署文檔...
del /q "RENDER-FINAL-STEPS.md" 2>nul
del /q "RENDER-ENV-CHECK-REPORT.md" 2>nul
del /q "RENDER-ENV-VARS-SETUP.md" 2>nul
del /q "RENDER-RUNTIME-TXT-FIX.md" 2>nul
del /q "RENDER-PYTHON-VERSION-FIX.md" 2>nul
del /q "RENDER-PYDANTIC-FIX.md" 2>nul
del /q "RENDER-FINAL-SOLUTION.md" 2>nul
del /q "RENDER-EMERGENCY-FIX.md" 2>nul
del /q "RENDER-FIX-V2.md" 2>nul
del /q "RENDER-QUICK-FIX.md" 2>nul
del /q "RENDER-DEPLOYMENT-CHECKLIST.md" 2>nul
del /q "RENDER-FRONTEND-FIX.md" 2>nul
del /q "RENDER-前後端完整部署.md" 2>nul
del /q "RENDER-FRONTEND-DEPLOYMENT.md" 2>nul
del /q "RENDER-DEPLOYMENT-STEPS.md" 2>nul
del /q "DEPLOYMENT-SUCCESS.md" 2>nul
del /q "NEXT-STEPS.md" 2>nul
del /q "START-DEPLOYMENT.md" 2>nul
del /q "DEPLOYMENT-GUIDE.md" 2>nul
del /q "FRONTEND-DEPLOYMENT-GUIDE.md" 2>nul
del /q "DEPLOY-TO-RENDER.md" 2>nul
del /q "DEPLOYMENT-QUICKSTART.md" 2>nul
del /q "README-DEPLOYMENT.md" 2>nul
del /q "FREE-HOSTING-OPTIONS.md" 2>nul
del /q "FLYIO-DEPLOYMENT.md" 2>nul
del /q "SETUP-SSH-KEY.md" 2>nul
del /q "GIT-REPOSITORIES.md" 2>nul
del /q "BITBUCKET-SETUP.md" 2>nul
del /q "GITHUB-SETUP.md" 2>nul
del /q "診斷Render服務.md" 2>nul
del /q "前端API-URL修正說明.md" 2>nul
del /q "雲端API修正總結.md" 2>nul
del /q "雲端API問題排查指南.md" 2>nul
del /q "修正完成-2024-11-18.md" 2>nul
del /q "DEPLOYMENT-FIX-2024-11-18.md" 2>nul
del /q "快速驗證指南.md" 2>nul
del /q "API-CONFIG.md" 2>nul
del /q "統一API設定指南.md" 2>nul
echo ✅ 已刪除重複的部署文檔

echo.
echo [2/6] 刪除測試和診斷文件...
del /q "diagnose-cloud-api.html" 2>nul
del /q "check-deployment.html" 2>nul
del /q "test-frontend-changes.html" 2>nul
del /q "check-render-deployment.bat" 2>nul
del /q "fix-cloud-api.bat" 2>nul
del /q "fix-frontend-api-url.bat" 2>nul
del /q "push-to-bitbucket.bat" 2>nul
del /q "test_api.html" 2>nul
del /q "測試修正-tooltip.html" 2>nul
del /q "測試API.ps1" 2>nul
del /q "talent-chat-frontend-backup.html" 2>nul
echo ✅ 已刪除測試和診斷文件

echo.
echo [3/6] 刪除舊版本的 API 文件...
del /q "BackEnd\start_fixed_api.py" 2>nul
del /q "BackEnd\talent_search_api_v2.py" 2>nul
del /q "BackEnd\app.py" 2>nul
echo ✅ 已刪除舊版本的 API 文件

echo.
echo [4/6] 刪除測試腳本...
del /q "BackEnd\test_full_flow.py" 2>nul
del /q "BackEnd\test_enrich.py" 2>nul
del /q "BackEnd\check_trait_mapping.py" 2>nul
del /q "BackEnd\debug_trait_results.py" 2>nul
del /q "BackEnd\test_ssh_connection.py" 2>nul
del /q "BackEnd\diagnose_database.py" 2>nul
del /q "BackEnd\explore_database_schema.py" 2>nul
del /q "BackEnd\query_traits.py" 2>nul
del /q "BackEnd\query_stella_data.py" 2>nul
del /q "BackEnd\analyze_stella_report.py" 2>nul
del /q "BackEnd\generate_test_report.py" 2>nul
del /q "tests\test_jsonb_queries.py" 2>nul
del /q "tests\test_fixed_search.py" 2>nul
echo ✅ 已刪除測試腳本

echo.
echo [5/6] 刪除舊的啟動腳本和說明...
del /q "setup-bitbucket.bat" 2>nul
del /q "setup-github.bat" 2>nul
del /q "setup-first-time.bat" 2>nul
del /q "prepare-deployment.bat" 2>nul
del /q "deploy-fix-now.bat" 2>nul
del /q "setup-flyio-secrets.bat" 2>nul
del /q "show-ssh-key.bat" 2>nul
del /q "list-old-files.bat" 2>nul
del /q "cleanup-old-files.bat" 2>nul
del /q "START-HERE.md" 2>nul
del /q "HOW-TO-START.md" 2>nul
del /q "CLEANUP-GUIDE.md" 2>nul
del /q "README-QUICKSTART.md" 2>nul
del /q "FIXED-VENV-ISSUE.md" 2>nul
del /q "SSH連接問題說明.md" 2>nul
del /q "問題診斷-下一步.md" 2>nul
del /q "使用說明.txt" 2>nul
del /q "使用說明-圖解.txt" 2>nul
del /q "啟動腳本說明.txt" 2>nul
echo ✅ 已刪除舊的啟動腳本和說明

echo.
echo [6/6] 刪除其他不必要的文件...
del /q "BackEnd\README-UNIFIED-API.md" 2>nul
del /q "BackEnd\config.py" 2>nul
del /q "index.html" 2>nul
del /q "logo.svg" 2>nul
del /q "LLMHost.txt" 2>nul
del /q "connections.xml" 2>nul
del /q "database_schema_report.json" 2>nul
del /q "database_schema_report.md" 2>nul
del /q "fly.toml" 2>nul
echo ✅ 已刪除其他不必要的文件

echo.
echo ========================================
echo 清理完成！
echo ========================================
echo.
echo 保留的重要文件：
echo ✅ 最終部署說明-2024-11-18.md （最新部署指南）
echo ✅ 啟動說明.md （本地啟動說明）
echo ✅ README.md （項目說明）
echo ✅ PROJECT_STRUCTURE.md （項目結構）
echo ✅ talent-chat-frontend.html （獨立前端）
echo ✅ BackEnd/talent_search_api.py （完整版 API）
echo ✅ BackEnd/talent_search_engine_fixed.py （搜索引擎）
echo ✅ BackEnd/interview_api.py （面試 API）
echo ✅ BackEnd/conversation_*.py （對話管理）
echo ✅ frontend/ （Vue 前端項目）
echo ✅ docs/ （文檔目錄）
echo.
echo 下一步：
echo 1. 檢查刪除的文件是否正確
echo 2. 如果確認無誤，提交到 Git
echo 3. git add -A
echo 4. git commit -m "清理不必要的文件和測試代碼"
echo 5. git push bitbucket main
echo.
pause

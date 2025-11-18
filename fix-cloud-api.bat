@echo off
chcp 65001 >nul
echo ========================================
echo 修正雲端 API 問題
echo ========================================
echo.

echo [1/5] 檢查 Git 狀態...
git status
echo.

echo [2/5] 添加修改的文件...
git add BackEnd/start_fixed_api.py
git add BackEnd/app.py
git add 雲端API問題排查指南.md
git add diagnose-cloud-api.html
echo ✅ 文件已添加
echo.

echo [3/5] 提交修改...
git commit -m "修正雲端 API 端點問題 - 改善 CORS 和錯誤處理"
echo ✅ 修改已提交
echo.

echo [4/5] 推送到遠端...
git push origin main
if %errorlevel% neq 0 (
    echo ❌ 推送失敗，請檢查網絡連接
    pause
    exit /b 1
)
echo ✅ 推送成功
echo.

echo [5/5] 下一步操作...
echo.
echo 請在 Render Dashboard 中執行以下操作：
echo 1. 訪問 https://dashboard.render.com
echo 2. 找到 talent-search-api 服務
echo 3. 點擊 "Manual Deploy"
echo 4. 選擇 "Deploy latest commit"
echo 5. 等待部署完成（約 3-5 分鐘）
echo 6. 查看日誌確認沒有錯誤
echo.
echo 部署完成後，使用以下工具測試：
echo - diagnose-cloud-api.html （診斷工具）
echo - check-deployment.html （部署檢查）
echo.
echo ========================================
echo 修正腳本執行完成
echo ========================================
pause

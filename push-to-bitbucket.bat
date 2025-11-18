@echo off
chcp 65001 >nul
echo ========================================
echo 推送修正到 Bitbucket 並觸發 Render 部署
echo ========================================
echo.

echo [1/6] 檢查 Git 狀態...
git status
echo.

echo [2/6] 添加所有修改的文件...
git add talent-chat-frontend.html
git add BackEnd/start_fixed_api.py
git add BackEnd/app.py
git add 雲端API問題排查指南.md
git add 雲端API修正總結.md
git add diagnose-cloud-api.html
git add check-deployment.html
git add fix-cloud-api.bat
git add push-to-bitbucket.bat
git add API-CONFIG.md
git add DEPLOYMENT-FIX-2024-11-18.md
git add 快速驗證指南.md
git add 修正完成-2024-11-18.md
git add test-frontend-changes.html
echo ✅ 文件已添加
echo.

echo [3/6] 提交修改...
git commit -m "修正雲端API問題和新增重新開始按鈕

- 新增重新開始按鈕功能
- 修正 start_fixed_api.py 的 CORS 配置
- 改善 /api/traits 端點錯誤處理
- 添加環境自動檢測
- 創建診斷工具和文檔"

if %errorlevel% neq 0 (
    echo ⚠️ 沒有新的修改需要提交，或提交失敗
    echo.
)
echo.

echo [4/6] 推送到 Bitbucket...
echo 正在推送到 Bitbucket 遠端倉庫...
git push bitbucket main
if %errorlevel% neq 0 (
    echo ❌ 推送到 Bitbucket 失敗
    echo.
    echo 可能的原因：
    echo 1. Bitbucket 遠端未配置
    echo 2. 網絡連接問題
    echo 3. 認證失敗
    echo.
    echo 請檢查 Bitbucket 配置：
    echo git remote -v
    echo.
    pause
    exit /b 1
)
echo ✅ 成功推送到 Bitbucket
echo.

echo [5/6] 檢查遠端倉庫...
git remote -v
echo.

echo [6/6] Render 自動部署...
echo.
echo ✅ 代碼已推送到 Bitbucket！
echo.
echo Render 將自動檢測到更新並開始部署：
echo.
echo 📋 接下來的步驟：
echo.
echo 1. 訪問 Render Dashboard
echo    https://dashboard.render.com
echo.
echo 2. 找到 talent-search-api 服務
echo.
echo 3. 查看部署狀態
echo    - 如果 Render 已連接到 Bitbucket，會自動部署
echo    - 如果沒有自動部署，點擊 "Manual Deploy"
echo.
echo 4. 等待部署完成（約 3-5 分鐘）
echo    - 查看 "Logs" 標籤確認沒有錯誤
echo    - 確認看到 "Application startup complete"
echo.
echo 5. 測試 API 端點
echo    curl https://talent-search-api.onrender.com/health
echo    curl https://talent-search-api.onrender.com/api/traits
echo.
echo 6. 使用診斷工具驗證
echo    在瀏覽器打開 diagnose-cloud-api.html
echo.
echo ========================================
echo 推送完成！等待 Render 部署...
echo ========================================
echo.
echo 💡 提示：
echo - Render 通常需要 3-5 分鐘完成部署
echo - 可以在 Dashboard 查看實時日誌
echo - 部署完成後會自動重啟服務
echo.
pause

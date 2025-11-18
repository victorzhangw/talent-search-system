@echo off
echo ========================================
echo Render 部署緊急修復
echo ========================================
echo.

echo 步驟 1: 檢查 Git 狀態
git status
echo.

echo 步驟 2: 添加更新的文件
git add requirements.txt render.yaml RENDER-EMERGENCY-FIX.md
echo.

echo 步驟 3: 提交更改
git commit -m "Emergency Fix: Direct list all dependencies and force rebuild"
echo.

echo 步驟 4: 推送到遠端
git push origin main
echo.

echo ========================================
echo ✅ Git 推送完成！
echo ========================================
echo.
echo 接下來請在 Render Dashboard 執行：
echo 1. 進入你的服務
echo 2. Settings ^> Build ^& Deploy
echo 3. 點擊 "Clear build cache"
echo 4. 然後 Manual Deploy ^> "Clear build cache ^& deploy"
echo.
echo 這會強制 Render 重新安裝所有依賴！
echo.
pause

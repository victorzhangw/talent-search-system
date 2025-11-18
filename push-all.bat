@echo off
chcp 65001 >nul
echo ========================================
echo 推送到所有遠端
echo ========================================
echo.

echo [1/2] 推送到 GitHub...
git push origin main
if errorlevel 1 (
    echo ❌ GitHub 推送失敗
    pause
    exit /b 1
)
echo ✅ GitHub 推送成功
echo.

echo [2/2] 推送到 Bitbucket...
git push bitbucket main
if errorlevel 1 (
    echo ❌ Bitbucket 推送失敗
    echo.
    echo 提示: 如果尚未設置 Bitbucket，請運行 setup-bitbucket.bat
    pause
    exit /b 1
)
echo ✅ Bitbucket 推送成功
echo.

echo ========================================
echo ✅ 所有推送完成！
echo ========================================
echo.
echo 📍 GitHub: https://github.com/victorzhangw/talent-search-system
echo 📍 Bitbucket: 已更新
echo.
pause

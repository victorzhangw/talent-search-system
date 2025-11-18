@echo off
chcp 65001 >nul
echo ========================================
echo Bitbucket 設置助手
echo ========================================
echo.

echo 📋 當前遠端設置:
git remote -v
echo.

echo ========================================
echo 步驟 1: 創建 Bitbucket Repository
echo ========================================
echo.
echo 請先在 Bitbucket 創建一個新的 repository：
echo 1. 訪問 https://bitbucket.org/repo/create
echo 2. Repository name: talent-search-system
echo 3. 選擇 Private (推薦)
echo 4. 不要勾選 "Include a README"
echo 5. 點擊 "Create repository"
echo.
echo 創建後，複製 repository URL
echo 格式: https://bitbucket.org/你的用戶名/talent-search-system.git
echo.

set /p BITBUCKET_URL="請輸入 Bitbucket Repository URL: "

if "%BITBUCKET_URL%"=="" (
    echo ❌ URL 不能為空
    pause
    exit /b 1
)

echo.
echo ========================================
echo 步驟 2: 添加 Bitbucket 遠端
echo ========================================
echo.

echo 正在添加 Bitbucket 遠端...
git remote add bitbucket %BITBUCKET_URL% 2>nul
if errorlevel 1 (
    echo ⚠️  遠端 bitbucket 已存在，正在更新...
    git remote set-url bitbucket %BITBUCKET_URL%
)

echo ✅ 已添加 Bitbucket 遠端
echo.

echo 當前遠端設置:
git remote -v
echo.

echo ========================================
echo 步驟 3: 推送到 Bitbucket
echo ========================================
echo.
echo 即將推送代碼到 Bitbucket...
echo.
echo ⚠️  重要提醒：
echo 推送時需要輸入 Bitbucket 認證：
echo   • 用戶名: 你的 Bitbucket 用戶名
echo   • 密碼: App Password (不是帳號密碼)
echo.
echo 如何獲取 App Password:
echo 1. 訪問 https://bitbucket.org/account/settings/app-passwords/
echo 2. 點擊 "Create app password"
echo 3. 勾選 "Repositories: Read" 和 "Repositories: Write"
echo 4. 複製生成的 password
echo.
pause

echo 正在推送...
git push -u bitbucket main

if errorlevel 1 (
    echo.
    echo ❌ 推送失敗
    echo.
    echo 可能的原因：
    echo 1. 認證失敗 - 請確認使用 App Password
    echo 2. 網絡問題 - 請檢查網絡連接
    echo 3. Repository URL 錯誤 - 請檢查 URL 是否正確
    echo.
    echo 手動推送命令:
    echo git push -u bitbucket main
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ 成功！
echo ========================================
echo.
echo 你的代碼已經推送到 Bitbucket！
echo.
echo 📍 GitHub: https://github.com/victorzhangw/talent-search-system
echo 📍 Bitbucket: %BITBUCKET_URL%
echo.
echo 下次更新代碼時：
echo   git add .
echo   git commit -m "你的更改說明"
echo   git push origin main        (推送到 GitHub)
echo   git push bitbucket main     (推送到 Bitbucket)
echo.
echo 或使用 push-all.bat 一次推送到兩個平台
echo.
pause

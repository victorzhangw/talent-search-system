@echo off
title Talent Search V2 - Chat Widget
echo ===========================================
echo Starting Talent Search V2 Frontend (Chat Widget)
echo ===========================================
cd frontend\chat-widget
echo Installing dependencies if needed...
if not exist "node_modules" (
    call npm install
)

echo Starting Vite Dev Server...
call npm run dev

pause

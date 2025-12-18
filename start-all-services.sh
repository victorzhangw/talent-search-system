#!/bin/bash

echo "================================================================"
echo "  🚀 人才管理系統 - 一鍵啟動所有服務"
echo "================================================================"
echo ""

# 檢查是否在正確的目錄
if [ ! -d "BackEnd" ]; then
    echo "❌ 錯誤：未找到 BackEnd 目錄"
    echo "請在項目根目錄執行此腳本"
    exit 1
fi

if [ ! -d "frontend" ]; then
    echo "❌ 錯誤：未找到 frontend 目錄"
    echo "請在項目根目錄執行此腳本"
    exit 1
fi

echo "✅ 目錄檢查通過"
echo ""

# 啟動後端 API（後台運行）
echo "📡 正在啟動後端 API (Port 8000)..."
cd BackEnd
nohup python main_api.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "   ✅ 後端 API 已啟動 (PID: $BACKEND_PID)"
cd ..
echo ""

# 等待後端啟動
echo "⏳ 等待後端服務啟動... (3 秒)"
sleep 3
echo ""

# 啟動前端（後台運行）
echo "🎨 正在啟動前端服務 (Port 5173)..."
cd frontend
nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   ✅ 前端服務已啟動 (PID: $FRONTEND_PID)"
cd ..
echo ""

# 等待前端啟動
echo "⏳ 等待前端服務啟動... (5 秒)"
sleep 5
echo ""

echo "================================================================"
echo "  🎉 所有服務已啟動！"
echo "================================================================"
echo ""
echo "📋 服務清單："
echo "   • 後端 API:  http://localhost:8000 (PID: $BACKEND_PID)"
echo "   • API 文檔:  http://localhost:8000/docs"
echo "   • 前端應用:  http://localhost:5173 (PID: $FRONTEND_PID)"
echo ""
echo "📚 功能模組："
echo "   • 人才搜索:  http://localhost:8000/api/talent"
echo "   • HR 諮詢:   http://localhost:8000/api/hr-consult"
echo ""
echo "📝 日誌文件："
echo "   • 後端日誌:  logs/backend.log"
echo "   • 前端日誌:  logs/frontend.log"
echo ""
echo "🛑 停止服務："
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo "   或執行: ./stop-all-services.sh"
echo ""
echo "================================================================"

# 保存 PID 到文件
mkdir -p logs
echo $BACKEND_PID > logs/backend.pid
echo $FRONTEND_PID > logs/frontend.pid

# 打開瀏覽器（根據系統）
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open http://localhost:5173
    open http://localhost:8000/docs
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open http://localhost:5173 2>/dev/null
    xdg-open http://localhost:8000/docs 2>/dev/null
fi

echo "✅ 瀏覽器已打開（如果支援）！"
echo ""

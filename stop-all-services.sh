#!/bin/bash

echo "================================================================"
echo "  🛑 停止所有服務"
echo "================================================================"
echo ""

echo "🔍 正在查找運行中的服務..."
echo ""

# 從 PID 文件停止服務
if [ -f "logs/backend.pid" ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    echo "🛑 停止後端 API (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null && echo "   ✅ 後端服務已停止" || echo "   ℹ️  後端服務未運行"
    rm logs/backend.pid
else
    echo "ℹ️  未找到後端 PID 文件"
fi
echo ""

if [ -f "logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    echo "🛑 停止前端服務 (PID: $FRONTEND_PID)..."
    kill $FRONTEND_PID 2>/dev/null && echo "   ✅ 前端服務已停止" || echo "   ℹ️  前端服務未運行"
    rm logs/frontend.pid
else
    echo "ℹ️  未找到前端 PID 文件"
fi
echo ""

# 檢查並停止佔用 port 的進程
echo "🛑 檢查 Port 8000..."
PORT_8000_PID=$(lsof -ti:8000)
if [ ! -z "$PORT_8000_PID" ]; then
    kill $PORT_8000_PID 2>/dev/null
    echo "   ✅ Port 8000 已釋放"
else
    echo "   ℹ️  Port 8000 未被佔用"
fi
echo ""

echo "🛑 檢查 Port 5173..."
PORT_5173_PID=$(lsof -ti:5173)
if [ ! -z "$PORT_5173_PID" ]; then
    kill $PORT_5173_PID 2>/dev/null
    echo "   ✅ Port 5173 已釋放"
else
    echo "   ℹ️  Port 5173 未被佔用"
fi
echo ""

echo "================================================================"
echo "  ✅ 所有服務已停止"
echo "================================================================"
echo ""

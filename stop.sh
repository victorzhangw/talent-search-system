#!/bin/bash

# 人才管理系統 - 停止服務 (Linux/Mac)

echo ""
echo "========================================"
echo "  人才管理系統 - 停止服務"
echo "========================================"
echo ""

echo "[1/3] 正在停止後端服務..."

# 停止後端進程
if [ -f "backend.pid" ]; then
    BACKEND_PID=$(cat backend.pid)
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        kill $BACKEND_PID
        echo "[成功] 已停止後端服務 (PID: $BACKEND_PID)"
    else
        echo "[提示] 後端進程不存在"
    fi
    rm backend.pid
else
    echo "[提示] 未找到後端 PID 文件"
    # 嘗試通過端口查找並終止
    BACKEND_PID=$(lsof -ti:8000)
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID
        echo "[成功] 已停止後端服務 (PID: $BACKEND_PID)"
    fi
fi

echo ""
echo "[2/3] 正在停止前端服務..."

# 停止前端進程
if [ -f "frontend.pid" ]; then
    FRONTEND_PID=$(cat frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        kill $FRONTEND_PID
        echo "[成功] 已停止前端服務 (PID: $FRONTEND_PID)"
    else
        echo "[提示] 前端進程不存在"
    fi
    rm frontend.pid
else
    echo "[提示] 未找到前端 PID 文件"
    # 嘗試通過端口查找並終止
    FRONTEND_PID=$(lsof -ti:5173)
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID
        echo "[成功] 已停止前端服務 (PID: $FRONTEND_PID)"
    fi
fi

echo ""
echo "[3/3] 清理完成"

echo ""
echo "========================================"
echo "  所有服務已停止"
echo "========================================"
echo ""

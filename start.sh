#!/bin/bash

# 人才管理系統 - 統一啟動腳本 (Linux/Mac)

echo ""
echo "========================================"
echo "  人才管理系統 - 統一啟動腳本"
echo "========================================"
echo ""

# 檢查 Python
if ! command -v python3 &> /dev/null; then
    echo "[錯誤] 未找到 Python，請先安裝 Python 3.10+"
    exit 1
fi

# 檢查 Node.js
if ! command -v node &> /dev/null; then
    echo "[錯誤] 未找到 Node.js，請先安裝 Node.js 16+"
    exit 1
fi

echo "[1/4] 檢查環境..."
echo ""

# 檢查後端環境變數文件
if [ ! -f "BackEnd/.env.local" ]; then
    echo "[警告] 未找到 BackEnd/.env.local 文件"
    echo "[提示] 請複製 BackEnd/.env.example 為 BackEnd/.env.local 並配置"
    exit 1
fi

# 檢查後端依賴
if [ ! -d "BackEnd/venv" ]; then
    echo "[提示] 未找到虛擬環境，正在創建..."
    cd BackEnd
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
    echo "[完成] 虛擬環境創建完成"
    echo ""
fi

# 檢查前端依賴
if [ ! -d "frontend/node_modules" ]; then
    echo "[提示] 未找到前端依賴，正在安裝..."
    cd frontend
    npm install
    cd ..
    echo "[完成] 前端依賴安裝完成"
    echo ""
fi

echo "[2/4] 啟動後端服務..."
echo ""

# 啟動後端 API
cd BackEnd
source venv/bin/activate
nohup python main_api.py > ../backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../backend.pid
cd ..

echo "[等待] 等待後端服務啟動..."
sleep 5

# 檢查後端是否啟動成功
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "[成功] 後端服務已啟動 (PID: $BACKEND_PID)"
else
    echo "[警告] 後端服務可能未成功啟動，請檢查 backend.log"
fi
echo ""

echo "[3/4] 啟動前端服務..."
echo ""

# 啟動前端開發服務器
cd frontend
nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../frontend.pid
cd ..

echo "[等待] 等待前端服務啟動..."
sleep 5

echo ""
echo "[4/4] 啟動完成！"
echo ""
echo "========================================"
echo "  服務已啟動"
echo "========================================"
echo ""
echo "後端 API:"
echo "  - API 文檔: http://localhost:8000/docs"
echo "  - 健康檢查: http://localhost:8000/health"
echo "  - 人才搜索: http://localhost:8000/api/talent"
echo "  - HR 諮詢: http://localhost:8000/api/hr-consult"
echo ""
echo "前端界面:"
echo "  - 主界面: http://localhost:5173"
echo ""
echo "進程 ID:"
echo "  - 後端 PID: $BACKEND_PID"
echo "  - 前端 PID: $FRONTEND_PID"
echo ""
echo "日誌文件:"
echo "  - 後端日誌: backend.log"
echo "  - 前端日誌: frontend.log"
echo ""
echo "========================================"
echo ""
echo "[提示] 要停止服務，請運行: ./stop.sh"
echo ""

# 在 Mac 上自動打開瀏覽器
if [[ "$OSTYPE" == "darwin"* ]]; then
    sleep 2
    open http://localhost:5173
fi

# Fly.io Dockerfile - Python FastAPI 應用

FROM python:3.10-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements
COPY BackEnd/requirements.txt /app/requirements.txt

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用代碼
COPY BackEnd /app/BackEnd

# 設置工作目錄到 BackEnd
WORKDIR /app/BackEnd

# 暴露端口
EXPOSE 8000

# 啟動命令
CMD ["python", "start_fixed_api.py"]

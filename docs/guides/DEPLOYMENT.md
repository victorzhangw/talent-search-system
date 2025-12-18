# 部署指南

## 概述

本指南說明如何將人才管理系統部署到生產環境。

## 部署選項

### 選項 1: Docker 部署（推薦）

#### 1.1 準備 Docker 環境

確保已安裝：

- Docker
- Docker Compose

#### 1.2 配置環境變數

創建 `.env.production` 文件：

```bash
# 生產環境配置
ENVIRONMENT=production

# 資料庫配置
DB_SSH_HOST=production_ssh_host
DB_SSH_PORT=22
DB_SSH_USERNAME=production_user
DB_SSH_PRIVATE_KEY_FILE=private-key-openssh.pem
DB_HOST=localhost
DB_PORT=5432
DB_NAME=production_db
DB_USER=production_user
DB_PASSWORD=secure_password

# LLM API 配置
LLM_API_KEY=production_api_key
LLM_API_HOST=https://api.siliconflow.cn
LLM_MODEL=deepseek-ai/DeepSeek-V3
LLM_MAX_RESPONSE_LENGTH=150
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500

# 應用配置
HOST=0.0.0.0
PORT=8000
DEBUG=False
```

#### 1.3 構建 Docker 映像

```bash
docker build -t talent-management-system .
```

#### 1.4 運行容器

```bash
docker run -d \
  --name talent-system \
  -p 8000:8000 \
  --env-file .env.production \
  talent-management-system
```

### 選項 2: Render 部署

#### 2.1 準備 Render 配置

專案已包含 `render.yaml` 配置文件。

#### 2.2 連接 GitHub

1. 登入 Render
2. 連接 GitHub 倉庫
3. Render 將自動檢測 `render.yaml`

#### 2.3 配置環境變數

在 Render Dashboard 中設置環境變數：

- `LLM_API_KEY`
- `DB_SSH_HOST`
- `DB_SSH_USERNAME`
- 等等...

#### 2.4 部署

Render 將自動構建和部署應用。

### 選項 3: 傳統伺服器部署

#### 3.1 準備伺服器

- Ubuntu 20.04+ 或 CentOS 8+
- Python 3.10+
- Node.js 16+
- Nginx（作為反向代理）

#### 3.2 安裝依賴

```bash
# 安裝 Python 依賴
cd BackEnd
pip install -r requirements.txt

# 安裝 Node.js 依賴
cd ../frontend
npm install
npm run build
```

#### 3.3 配置 Nginx

創建 Nginx 配置文件 `/etc/nginx/sites-available/talent-system`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端靜態文件
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 後端 API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # API 文檔
    location /docs {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
    }
}
```

啟用配置：

```bash
sudo ln -s /etc/nginx/sites-available/talent-system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 3.4 使用 Systemd 管理後端服務

創建服務文件 `/etc/systemd/system/talent-backend.service`：

```ini
[Unit]
Description=Talent Management System Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/BackEnd
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python main_api.py
Restart=always

[Install]
WantedBy=multi-user.target
```

啟動服務：

```bash
sudo systemctl daemon-reload
sudo systemctl enable talent-backend
sudo systemctl start talent-backend
```

## 安全性配置

### 1. HTTPS 配置

使用 Let's Encrypt 獲取免費 SSL 證書：

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 2. 環境變數安全

- 不要將 `.env.production` 提交到 Git
- 使用密鑰管理服務（如 AWS Secrets Manager）
- 定期輪換 API Key

### 3. 資料庫安全

- 使用強密碼
- 限制資料庫訪問 IP
- 啟用 SSL 連接
- 定期備份

### 4. API 安全

- 啟用 CORS 限制
- 實施速率限制
- 添加身份驗證和授權
- 記錄所有 API 請求

## 監控和日誌

### 1. 應用日誌

後端日誌位置：`/var/log/talent-backend/`

配置日誌輪轉：

```bash
# /etc/logrotate.d/talent-backend
/var/log/talent-backend/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
}
```

### 2. 性能監控

推薦使用：

- Prometheus + Grafana
- New Relic
- Datadog

### 3. 錯誤追蹤

推薦使用：

- Sentry
- Rollbar

## 備份策略

### 1. 資料庫備份

每日自動備份：

```bash
#!/bin/bash
# backup-db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/database"
DB_NAME="production_db"

pg_dump $DB_NAME | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# 保留最近 30 天的備份
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
```

設置 cron 任務：

```bash
0 2 * * * /path/to/backup-db.sh
```

### 2. 配置文件備份

定期備份：

- `.env.production`
- `prompts/hr_consultation_prompts.json`
- Nginx 配置文件

## 擴展和優化

### 1. 水平擴展

使用負載均衡器（如 Nginx、HAProxy）分發請求到多個後端實例。

### 2. 快取策略

- 使用 Redis 快取頻繁查詢的數據
- 實施 CDN 加速靜態資源

### 3. 資料庫優化

- 添加適當的索引
- 使用連接池
- 實施讀寫分離

## 故障恢復

### 1. 備份恢復

```bash
# 恢復資料庫
gunzip < backup_20251217.sql.gz | psql production_db
```

### 2. 回滾部署

```bash
# Docker
docker stop talent-system
docker run -d --name talent-system <previous-image>

# Git
git revert <commit-hash>
git push
```

## 檢查清單

部署前檢查：

- [ ] 環境變數已正確配置
- [ ] 資料庫連接測試通過
- [ ] LLM API 測試通過
- [ ] SSL 證書已配置
- [ ] 防火牆規則已設置
- [ ] 備份策略已實施
- [ ] 監控已配置
- [ ] 日誌輪轉已設置
- [ ] 錯誤追蹤已啟用
- [ ] 性能測試已完成

## 相關資源

- [快速開始指南](GETTING_STARTED.md)
- [環境變數配置](../configuration/README_ENV.md)
- [故障排除指南](TROUBLESHOOTING.md)

## 獲取支援

如有部署問題，請聯繫開發團隊。

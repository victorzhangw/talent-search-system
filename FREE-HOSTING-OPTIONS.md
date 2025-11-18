# 🆓 免費部署平台比較

## 完整方案比較

| 平台                        | 前端 | 後端 | 數據庫     | 優點             | 缺點            | 推薦度     |
| --------------------------- | ---- | ---- | ---------- | ---------------- | --------------- | ---------- |
| **Render**                  | ✅   | ✅   | ✅ (90 天) | 一站式、自動部署 | 會休眠          | ⭐⭐⭐⭐⭐ |
| **Railway**                 | ✅   | ✅   | ✅         | 簡單易用         | $5/月額度       | ⭐⭐⭐⭐   |
| **Vercel + PythonAnywhere** | ✅   | ✅   | ❌         | 前端快速         | 需分開管理      | ⭐⭐⭐⭐   |
| **Fly.io**                  | ✅   | ✅   | ✅         | 全球 CDN         | 需信用卡        | ⭐⭐⭐⭐   |
| **Netlify + Heroku**        | ✅   | ❌   | ❌         | 前端優秀         | Heroku 不再免費 | ⭐⭐⭐     |

---

## 1. Render (最推薦) ⭐⭐⭐⭐⭐

### 優點

- ✅ 一個平台搞定前後端和數據庫
- ✅ 自動從 GitHub 部署
- ✅ 支援 Python + Node.js
- ✅ 免費 PostgreSQL (90 天)
- ✅ 免費 SSL 證書
- ✅ 設定簡單

### 缺點

- ⚠️ 閒置 15 分鐘後休眠
- ⚠️ 首次喚醒需 30-60 秒
- ⚠️ 數據庫 90 天後需付費或遷移

### 免費額度

- **Web Service**: 750 小時/月
- **Static Site**: 無限制
- **PostgreSQL**: 90 天免費試用

### 適合場景

- 快速原型展示
- 個人項目
- 小型應用

### 部署指南

查看 [DEPLOY-TO-RENDER.md](./DEPLOY-TO-RENDER.md)

---

## 2. Railway ⭐⭐⭐⭐

### 優點

- ✅ 介面友善
- ✅ 支援 PostgreSQL
- ✅ 自動部署
- ✅ 不會休眠

### 缺點

- ⚠️ 每月只有 $5 免費額度
- ⚠️ 額度用完需付費

### 免費額度

- **計算**: $5/月
- **數據庫**: 包含在 $5 內
- **流量**: 100GB/月

### 部署步驟

1. **註冊 Railway**

   - 訪問 https://railway.app
   - 使用 GitHub 登入

2. **創建新項目**

   - 點擊 "New Project"
   - 選擇 "Deploy from GitHub repo"

3. **添加服務**

   - 添加 PostgreSQL 數據庫
   - 添加 Python 服務（後端）
   - 添加 Node.js 服務（前端）

4. **配置環境變數**

   - 設定數據庫連接
   - 設定 LLM API 密鑰

5. **部署**
   - Railway 會自動建置和部署

---

## 3. Vercel (前端) + PythonAnywhere (後端) ⭐⭐⭐⭐

### 優點

- ✅ Vercel 前端速度極快
- ✅ PythonAnywhere 後端穩定
- ✅ 兩者都有永久免費方案

### 缺點

- ⚠️ 需要分開管理兩個平台
- ⚠️ 需要另外找數據庫

### 免費額度

**Vercel**:

- 無限制靜態網站
- 100GB 流量/月
- 自動 SSL

**PythonAnywhere**:

- 1 個 Web 應用
- 512MB 存儲
- 每天重啟一次

### 部署步驟

#### 前端 (Vercel)

1. 訪問 https://vercel.com
2. 連接 GitHub repository
3. 配置：
   - Framework: Vite
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`
4. 添加環境變數：
   - `VITE_API_URL`: PythonAnywhere 的 URL

#### 後端 (PythonAnywhere)

1. 訪問 https://www.pythonanywhere.com
2. 註冊免費帳號
3. 上傳代碼：
   ```bash
   git clone https://github.com/你的用戶名/你的repo.git
   ```
4. 創建虛擬環境：
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r BackEnd/requirements.txt
   ```
5. 配置 Web 應用：
   - Python 版本: 3.10
   - WSGI 文件: 指向你的 FastAPI 應用
   - 靜態文件: 配置路徑

---

## 4. Fly.io ⭐⭐⭐⭐

### 優點

- ✅ 支援 Docker
- ✅ 全球 CDN
- ✅ 免費 PostgreSQL
- ✅ 不會休眠

### 缺點

- ⚠️ 需要信用卡驗證
- ⚠️ 配置較複雜

### 免費額度

- **計算**: 3 個小型應用
- **數據庫**: 3GB 存儲
- **流量**: 160GB/月

### 部署步驟

1. **安裝 Fly CLI**

   ```bash
   # Windows (PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. **登入**

   ```bash
   fly auth login
   ```

3. **初始化應用**

   ```bash
   fly launch
   ```

4. **配置 fly.toml**

   ```toml
   app = "talent-search"

   [build]
     builder = "paketobuildpacks/builder:base"

   [[services]]
     internal_port = 8000
     protocol = "tcp"
   ```

5. **部署**
   ```bash
   fly deploy
   ```

---

## 5. Supabase (數據庫) + Netlify (前端) + Render (後端) ⭐⭐⭐⭐

### 優點

- ✅ 各取所長
- ✅ Supabase 數據庫永久免費
- ✅ Netlify 前端速度快

### 缺點

- ⚠️ 需要管理三個平台
- ⚠️ 配置較複雜

### 免費額度

**Supabase**:

- 500MB 數據庫
- 無限 API 請求
- 永久免費

**Netlify**:

- 100GB 流量/月
- 自動部署
- 永久免費

**Render**:

- 750 小時/月
- 會休眠

### 部署步驟

#### 1. Supabase (數據庫)

1. 訪問 https://supabase.com
2. 創建新項目
3. 獲取數據庫連接字符串
4. 遷移數據：
   ```bash
   pg_dump 原數據庫 | psql Supabase連接字符串
   ```

#### 2. Netlify (前端)

1. 訪問 https://netlify.com
2. 連接 GitHub repository
3. 配置：
   - Base directory: `frontend`
   - Build command: `npm run build`
   - Publish directory: `frontend/dist`
4. 添加環境變數：
   - `VITE_API_URL`: Render 後端 URL

#### 3. Render (後端)

按照 [DEPLOY-TO-RENDER.md](./DEPLOY-TO-RENDER.md) 部署後端

---

## 🎯 推薦方案

### 快速原型 / 展示

**Render (全包)**

- 最簡單
- 5 分鐘部署
- 一個平台管理

### 長期運行 / 生產環境

**Supabase + Netlify + Render**

- 數據庫永久免費
- 前端速度快
- 後端穩定

### 預算有限

**Vercel + PythonAnywhere + Supabase**

- 全部永久免費
- 需要手動管理

---

## 💡 優化建議

### 1. 避免休眠

使用 **UptimeRobot** 免費監控：

- 註冊 https://uptimerobot.com
- 添加監控（每 5 分鐘 ping 一次）
- 服務就不會休眠

### 2. 數據庫遷移

如果 Render 數據庫 90 天到期：

1. 遷移到 Supabase（永久免費）
2. 或遷移到 ElephantSQL（20MB 免費）
3. 或升級 Render 付費方案（$7/月）

### 3. 自定義域名

大部分平台都支持免費自定義域名：

- 在 Cloudflare 註冊免費域名
- 配置 DNS 指向部署平台
- 自動獲得 SSL 證書

---

## 📊 成本預估

### 完全免費方案

- **前端**: Netlify / Vercel (免費)
- **後端**: Render / PythonAnywhere (免費)
- **數據庫**: Supabase (免費)
- **監控**: UptimeRobot (免費)
- **總成本**: $0/月

### 升級方案

- **前端**: Netlify Pro ($19/月)
- **後端**: Render Standard ($7/月)
- **數據庫**: Render PostgreSQL ($7/月)
- **總成本**: $33/月

---

## 🆘 需要幫助？

1. 查看各平台官方文檔
2. 加入社群討論
3. 創建 GitHub Issue

---

**選擇最適合你的方案，開始部署吧！** 🚀

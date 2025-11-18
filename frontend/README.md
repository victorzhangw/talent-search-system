# AI 人才搜索系統 - 前端

基於 Vue 3 + Vite 構建的現代化前端應用。

## 🚀 快速開始

### 安裝依賴

```bash
cd frontend
npm install
```

### 開發模式

```bash
npm run dev
```

應用將在 `http://localhost:3000` 啟動

### 生產構建

```bash
npm run build
```

構建產物將輸出到 `dist/` 目錄

### 預覽生產構建

```bash
npm run preview
```

## 📁 項目結構

```
frontend/
├── src/
│   ├── api/              # API 調用
│   │   └── talent.js
│   ├── assets/           # 靜態資源
│   │   └── css/
│   ├── components/       # Vue 組件
│   │   ├── AppHeader.vue
│   │   ├── ChatArea.vue
│   │   ├── ResultsArea.vue
│   │   ├── CandidateCard.vue
│   │   └── InterviewDialog.vue
│   ├── config/           # 配置文件
│   │   └── index.js
│   ├── router/           # 路由配置
│   │   └── index.js
│   ├── stores/           # Pinia 狀態管理
│   │   ├── talent.js
│   │   └── interview.js
│   ├── views/            # 頁面視圖
│   │   └── Home.vue
│   ├── App.vue           # 根組件
│   └── main.js           # 入口文件
├── index.html            # HTML 模板
├── vite.config.js        # Vite 配置
└── package.json          # 依賴配置
```

## 🛠️ 技術棧

- **Vue 3** - 漸進式 JavaScript 框架
- **Vite** - 下一代前端構建工具
- **Pinia** - Vue 官方狀態管理庫
- **Vue Router** - 官方路由管理器
- **Axios** - HTTP 客戶端

## 🔧 環境變量

創建 `.env` 文件配置環境變量：

```env
# 開發環境
VITE_API_BASE_URL=http://localhost:8000

# 生產環境
# VITE_API_BASE_URL=https://api.yourdomain.com
```

## 📝 開發指南

### 添加新組件

1. 在 `src/components/` 創建 `.vue` 文件
2. 使用 `<script setup>` 語法
3. 導入並使用 Pinia store

### 添加新頁面

1. 在 `src/views/` 創建 `.vue` 文件
2. 在 `src/router/index.js` 添加路由配置

### API 調用

使用 `src/api/talent.js` 中的方法：

```javascript
import { talentAPI } from "@/api/talent";

// 搜索人才
const result = await talentAPI.searchTalents(query);
```

### 狀態管理

使用 Pinia store：

```javascript
import { useTalentStore } from "@/stores/talent";

const talentStore = useTalentStore();
talentStore.sendMessage("搜索條件");
```

## 🎨 樣式指南

- 使用全局 CSS 變量（在 `style.css` 中定義）
- 組件樣式使用 `scoped`
- 遵循 BEM 命名規範

## 🔒 安全性

- 所有 API 請求通過 axios 攔截器處理
- 環境變量不包含敏感信息
- 生產構建自動啟用代碼混淆

## 📦 部署

### 部署到 Nginx

```bash
npm run build
# 將 dist/ 目錄內容複製到 Nginx 服務器
```

### 部署到 Vercel/Netlify

直接連接 Git 倉庫，自動部署

## 🐛 常見問題

### API 連接失敗

檢查後端服務是否啟動：

```bash
# 後端應該在 http://localhost:8000 運行
```

### 熱更新不工作

清除緩存並重啟：

```bash
rm -rf node_modules/.vite
npm run dev
```

## 📄 License

MIT

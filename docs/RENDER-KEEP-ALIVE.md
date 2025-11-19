# Render 免費版保持在線方案

## 問題說明

Render 免費版有以下限制：

- **閒置 15 分鐘後自動休眠**
- 休眠後首次訪問需要 30-60 秒冷啟動
- 每月 750 小時免費運行時間（約 31 天）

## 解決方案

### 方案 1：UptimeRobot 監控（推薦）⭐

**優點：**

- 完全免費
- 設定簡單
- 提供監控報告和告警
- 不消耗你的資源

**設定步驟：**

1. 註冊 UptimeRobot

   - 網址：https://uptimerobot.com
   - 免費方案：50 個監控，5 分鐘間隔

2. 添加監控

   ```
   Monitor Type: HTTP(s)
   Friendly Name: Talent Search API
   URL: https://talent-search-system.onrender.com/health
   Monitoring Interval: 5 minutes
   ```

3. 完成！服務會每 5 分鐘自動 ping 一次

### 方案 2：GitHub Actions 定時任務

**優點：**

- 完全免費
- 與代碼庫整合
- 可自定義間隔

**已配置：**

- 文件位置：`.github/workflows/keep-alive.yml`
- 執行間隔：每 10 分鐘
- 自動執行，無需額外設定

**手動觸發：**

```bash
# 在 GitHub repo 頁面
Actions → Keep Render Service Alive → Run workflow
```

### 方案 3：前端心跳檢測

**優點：**

- 用戶訪問時自動保持連線
- 無需外部服務

**已實現：**

- 文件位置：`frontend/src/utils/keepAlive.js`
- 只在生產環境啟用
- 每 10 分鐘自動 ping 後端

**工作原理：**

```javascript
// 在 main.js 中自動啟動
if (import.meta.env.PROD) {
  keepAliveService.start();
}
```

### 方案 4：其他免費監控服務

#### Cron-job.org

- 網址：https://cron-job.org
- 免費：無限監控，1 分鐘間隔
- 設定：
  ```
  URL: https://talent-search-system.onrender.com/health
  Interval: Every 5 minutes
  ```

#### Better Uptime

- 網址：https://betteruptime.com
- 免費：10 個監控，3 分鐘間隔

#### Pingdom

- 網址：https://www.pingdom.com
- 免費試用：1 個監控

## 推薦配置

**最佳實踐：**

1. ✅ 使用 **UptimeRobot**（主要方案）
2. ✅ 啟用 **GitHub Actions**（備用方案）
3. ✅ 前端心跳檢測（用戶訪問時）

這樣可以確保：

- 即使沒有用戶訪問，服務也保持在線
- 多重保障，更可靠
- 完全免費

## 監控效果

設定完成後，你的服務將：

- ✅ 永不休眠（只要在免費時數內）
- ✅ 首次訪問無需等待冷啟動
- ✅ 提供更好的用戶體驗

## 注意事項

1. **免費時數限制**

   - Render 免費版每月 750 小時
   - 保持在線會用完所有時數
   - 如果超過，服務會停止直到下個月

2. **多個服務**

   - 如果你有多個 Render 服務
   - 750 小時是所有服務共享的
   - 需要合理分配

3. **升級選項**
   - 如果需要 24/7 運行且無時數限制
   - 考慮升級到 Render 付費方案（$7/月起）

## 健康檢查端點

後端已實現健康檢查端點：

```
GET https://talent-search-system.onrender.com/health
```

**返回示例：**

```json
{
  "status": "healthy",
  "timestamp": "2024-11-19T10:30:00",
  "environment": "production",
  "checks": {
    "api": "ok",
    "database": "connected",
    "ssh_tunnel": "active"
  }
}
```

## 故障排除

### 服務仍然休眠？

1. 檢查 UptimeRobot 是否正常運行
2. 確認 GitHub Actions 是否執行成功
3. 查看 Render 日誌是否有錯誤
4. 確認 `/health` 端點返回 200 狀態碼

### GitHub Actions 未執行？

1. 檢查 repo 的 Actions 是否啟用
2. 確認 workflow 文件語法正確
3. 查看 Actions 頁面的執行記錄

---

**更新日期：** 2024-11-19  
**狀態：** ✅ 已實現所有方案

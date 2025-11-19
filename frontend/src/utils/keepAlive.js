/**
 * Keep Alive 服務
 * 定期 ping 後端 API，防止 Render 免費版休眠
 */

import { talentAPI } from "@/api/talent";

class KeepAliveService {
  constructor() {
    this.intervalId = null;
    this.pingInterval = 10 * 60 * 1000; // 10 分鐘
    this.isRunning = false;
  }

  /**
   * 開始心跳檢測
   */
  start() {
    if (this.isRunning) {
      console.log("⏰ Keep-alive service is already running");
      return;
    }

    console.log("🚀 Starting keep-alive service...");
    this.isRunning = true;

    // 立即執行一次
    this.ping();

    // 設定定時器
    this.intervalId = setInterval(() => {
      this.ping();
    }, this.pingInterval);

    console.log(
      `✅ Keep-alive service started (interval: ${this.pingInterval / 1000}s)`
    );
  }

  /**
   * 停止心跳檢測
   */
  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
      this.isRunning = false;
      console.log("⏹️ Keep-alive service stopped");
    }
  }

  /**
   * 執行 ping
   */
  async ping() {
    try {
      const startTime = Date.now();
      await talentAPI.healthCheck();
      const duration = Date.now() - startTime;
      console.log(`💓 Backend health check OK (${duration}ms)`);
    } catch (error) {
      console.warn("⚠️ Backend health check failed:", error.message);
      // 不拋出錯誤，靜默失敗
    }
  }

  /**
   * 檢查服務是否運行中
   */
  isActive() {
    return this.isRunning;
  }
}

// 創建單例
const keepAliveService = new KeepAliveService();

export default keepAliveService;

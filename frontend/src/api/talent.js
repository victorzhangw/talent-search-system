import axios from "axios";
import config from "@/config";

// 創建 axios 實例
const apiClient = axios.create({
  baseURL: config.apiBaseUrl,
  timeout: config.timeout,
  headers: {
    "Content-Type": "application/json",
  },
});

// 請求攔截器
apiClient.interceptors.request.use(
  (config) => {
    // 記錄請求開始時間
    config.metadata = { startTime: new Date() };
    console.log(
      `📤 API Request: ${config.method?.toUpperCase()} ${config.url}`
    );
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 響應攔截器
apiClient.interceptors.response.use(
  (response) => {
    // 計算請求耗時
    const duration = new Date() - response.config.metadata.startTime;
    console.log(`✅ API Response: ${response.config.url} (${duration}ms)`);
    return response.data;
  },
  async (error) => {
    const duration = error.config?.metadata
      ? new Date() - error.config.metadata.startTime
      : 0;

    // 處理不同類型的錯誤
    if (error.code === "ECONNABORTED") {
      console.error(
        `⏱️ API Timeout: ${error.config?.url} (${duration}ms) - 服務可能正在冷啟動`
      );
      error.userMessage =
        "請求超時，服務可能正在啟動中，請稍後再試（約 30-60 秒）";
    } else if (error.response) {
      // 服務器返回錯誤狀態碼
      console.error(
        `❌ API Error: ${error.config?.url} - Status ${error.response.status}`
      );
      error.userMessage =
        error.response.data?.detail ||
        error.response.data?.message ||
        `服務器錯誤 (${error.response.status})`;
    } else if (error.request) {
      // 請求已發送但沒有收到響應
      console.error(
        `🔌 Network Error: ${error.config?.url} - 無法連接到服務器`
      );
      error.userMessage = "無法連接到服務器，請檢查網絡連接";
    } else {
      console.error(`❌ Unknown Error:`, error.message);
      error.userMessage = "發生未知錯誤，請稍後再試";
    }

    return Promise.reject(error);
  }
);

// 重試輔助函數
async function retryRequest(requestFn, maxRetries = 2, retryDelay = 2000) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await requestFn();
    } catch (error) {
      // 如果是超時錯誤且還有重試機會
      if (error.code === "ECONNABORTED" && attempt < maxRetries) {
        console.log(
          `🔄 重試請求 (${attempt}/${maxRetries})，等待 ${
            retryDelay / 1000
          } 秒...`
        );
        await new Promise((resolve) => setTimeout(resolve, retryDelay));
        // 增加下次重試的延遲時間
        retryDelay *= 1.5;
      } else {
        throw error;
      }
    }
  }
}

// API 方法
export const talentAPI = {
  // 搜索人才（支援會話 ID）- 帶重試機制
  async searchTalents(query, sessionId = null, filters = null) {
    return retryRequest(() =>
      apiClient.post("/api/search", {
        query,
        session_id: sessionId,
        filters,
      })
    );
  },

  // 生成面試問題
  generateInterviewQuestions(candidates, conversationHistory = []) {
    return apiClient.post("/api/generate-interview-questions", {
      candidates,
      conversation_history: conversationHistory,
    });
  },

  // 獲取特質定義
  getTraits() {
    return apiClient.get("/api/traits");
  },

  // 健康檢查
  healthCheck() {
    return apiClient.get("/health");
  },

  // 獲取候選人列表
  getCandidates(limit = 20) {
    return apiClient.get("/api/candidates", { params: { limit } });
  },
};

export default apiClient;

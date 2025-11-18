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
    // 可以在這裡添加 token 等
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 響應攔截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    console.error("API Error:", error);
    return Promise.reject(error);
  }
);

// API 方法
export const talentAPI = {
  // 搜索人才（支援會話 ID）
  searchTalents(query, sessionId = null, filters = null) {
    return apiClient.post("/api/search", {
      query,
      session_id: sessionId,
      filters,
    });
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

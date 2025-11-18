// API 調用封裝
import config from "./config.js";

class TalentAPI {
  constructor() {
    this.baseUrl = config.apiBaseUrl;
    this.timeout = config.timeout;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const defaultOptions = {
      timeout: this.timeout,
      headers: {
        "Content-Type": "application/json",
      },
    };

    try {
      const response = await axios({
        url,
        ...defaultOptions,
        ...options,
      });
      return response.data;
    } catch (error) {
      console.error(`API Error: ${endpoint}`, error);
      throw error;
    }
  }

  // 搜索人才
  async searchTalents(query, filters = null) {
    return this.request("/api/search", {
      method: "POST",
      data: { query, filters },
    });
  }

  // 生成面試問題
  async generateInterviewQuestions(candidates, conversationHistory = []) {
    return this.request("/api/generate-interview-questions", {
      method: "POST",
      data: {
        candidates,
        conversation_history: conversationHistory,
      },
    });
  }

  // 獲取特質定義
  async getTraits() {
    return this.request("/api/traits", {
      method: "GET",
    });
  }

  // 健康檢查
  async healthCheck() {
    return this.request("/health", {
      method: "GET",
    });
  }
}

export default new TalentAPI();

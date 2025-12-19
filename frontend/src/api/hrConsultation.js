/**
 * HR 諮詢 API 客戶端
 */

import axios from "axios";

// 創建 HR 諮詢專用的 axios 實例
const hrApiClient = axios.create({
  baseURL: import.meta.env.VITE_HR_API_BASE_URL || "http://localhost:8000",
  timeout: 90000, // 增加到 90 秒以支持長回應生成（LLM 響應時間約 54 秒）
  headers: {
    "Content-Type": "application/json",
  },
});

// 請求攔截器
hrApiClient.interceptors.request.use(
  (config) => {
    console.log(`[HR API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error("[HR API] 請求錯誤:", error);
    return Promise.reject(error);
  }
);

// 響應攔截器
hrApiClient.interceptors.response.use(
  (response) => {
    console.log(`[HR API] 響應成功:`, response.data);
    return response;
  },
  (error) => {
    console.error("[HR API] 響應錯誤:", error.response?.data || error.message);
    return Promise.reject(error);
  }
);

/**
 * HR 諮詢主 API
 * @param {string} query - 諮詢問題
 * @param {number|null} candidateId - 候選人 ID（可選）
 * @param {string|null} candidateName - 候選人姓名（可選）
 * @param {string|null} sessionId - 會話 ID（可選）
 * @returns {Promise<Object>} 諮詢結果
 */
export const hrConsult = async (
  query,
  candidateId = null,
  candidateName = null,
  sessionId = null
) => {
  try {
    const requestData = {
      query,
      candidate_id: candidateId,
      candidate_name: candidateName,
      session_id: sessionId,
    };

    // 調試日誌
    console.log("[HR API] 發送諮詢請求:", requestData);

    const response = await hrApiClient.post(
      "/api/hr-consult/chat",
      requestData
    );

    console.log("[HR API] 收到響應:", response.data);

    return response.data;
  } catch (error) {
    console.error("[HR API] 請求失敗:", error);
    throw handleApiError(error);
  }
};

/**
 * 獲取候選人列表
 * @param {Object} params - 查詢參數
 * @returns {Promise<Object>} 候選人列表
 */
export const getCandidates = async (params = {}) => {
  try {
    const response = await hrApiClient.get("/api/hr-consult/candidates", {
      params: {
        search: params.search || undefined,
        has_test_data:
          params.hasTestData !== undefined ? params.hasTestData : undefined,
        sort_by: params.sortBy || "last_test_date",
        sort_order: params.sortOrder || "desc",
        limit: params.limit || 20,
        offset: params.offset || 0,
      },
    });
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
};

/**
 * 獲取候選人詳情
 * @param {number} candidateId - 候選人 ID
 * @returns {Promise<Object>} 候選人詳細資訊
 */
export const getCandidateDetail = async (candidateId) => {
  try {
    const response = await hrApiClient.get(
      `/api/hr-consult/candidate/${candidateId}`
    );
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
};

/**
 * 獲取諮詢歷史
 * @param {Object} params - 查詢參數
 * @returns {Promise<Object>} 歷史記錄
 */
export const getConsultationHistory = async (params = {}) => {
  try {
    const response = await hrApiClient.get("/api/hr-consult/history", {
      params: {
        session_id: params.sessionId || null,
        candidate_id: params.candidateId || null,
        limit: params.limit || 10,
      },
    });
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
};

/**
 * 清除會話歷史
 * @param {string} sessionId - 會話 ID
 * @returns {Promise<Object>} 刪除結果
 */
export const clearSessionHistory = async (sessionId) => {
  try {
    const response = await hrApiClient.delete(
      `/api/hr-consult/history/${sessionId}`
    );
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
};

/**
 * 獲取統計資訊
 * @returns {Promise<Object>} 統計數據
 */
export const getStatistics = async () => {
  try {
    const response = await hrApiClient.get("/api/hr-consult/statistics");
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
};

/**
 * 健康檢查
 * @returns {Promise<Object>} 服務狀態
 */
export const healthCheck = async () => {
  try {
    const response = await hrApiClient.get("/health");
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
};

/**
 * 處理 API 錯誤
 * @param {Error} error - 錯誤對象
 * @returns {Error} 格式化的錯誤
 */
function handleApiError(error) {
  if (error.response) {
    // 服務器返回錯誤響應
    const status = error.response.status;
    const detail =
      error.response.data?.detail || error.response.data?.error || "未知錯誤";

    const errorMessage =
      {
        400: "請求參數錯誤",
        404: "資源不存在",
        500: "服務器內部錯誤",
        503: "服務暫時不可用",
      }[status] || `請求失敗 (${status})`;

    const err = new Error(`${errorMessage}: ${detail}`);
    err.status = status;
    err.detail = detail;
    return err;
  } else if (error.request) {
    // 請求已發送但沒有收到響應
    return new Error("無法連接到 HR 諮詢服務，請檢查網絡連接");
  } else {
    // 其他錯誤
    return new Error(`請求失敗: ${error.message}`);
  }
}

export default {
  hrConsult,
  getCandidates,
  getCandidateDetail,
  getConsultationHistory,
  clearSessionHistory,
  getStatistics,
  healthCheck,
};

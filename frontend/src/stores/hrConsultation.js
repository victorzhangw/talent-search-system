/**
 * HR 諮詢 Pinia Store
 */

import { defineStore } from "pinia";
import {
  hrConsult,
  getCandidates,
  getCandidateDetail,
  getConsultationHistory,
  clearSessionHistory,
} from "@/api/hrConsultation";

export const useHRConsultationStore = defineStore("hrConsultation", {
  state: () => ({
    // 當前選中的候選人
    selectedCandidate: null,

    // 候選人列表
    candidates: [],
    candidatesTotal: 0,
    candidatesLoading: false,

    // 候選人列表分頁和排序
    candidatesPage: 1,
    candidatesPageSize: 10,
    candidatesSortBy: "last_test_date", // last_test_date, name, created_at
    candidatesSortOrder: "desc", // asc, desc
    candidatesSearchQuery: "",

    // 諮詢相關
    consultationLoading: false,
    currentConsultation: null,
    consultationError: null,

    // 諮詢歷史
    consultationHistory: [],
    historyLoading: false,

    // 會話 ID
    sessionId: null,

    // UI 狀態
    showCandidateSelector: false,
    showHistoryPanel: false,
  }),

  getters: {
    /**
     * 是否已選擇候選人
     */
    hasSelectedCandidate(state) {
      return state.selectedCandidate !== null;
    },

    /**
     * 當前候選人姓名
     */
    selectedCandidateName(state) {
      return state.selectedCandidate?.name || "";
    },

    /**
     * 有測評數據的候選人
     */
    candidatesWithTestData(state) {
      return state.candidates.filter((c) => c.has_test_data);
    },

    /**
     * 是否正在加載
     */
    isLoading(state) {
      return (
        state.consultationLoading ||
        state.candidatesLoading ||
        state.historyLoading
      );
    },

    /**
     * 總頁數
     */
    candidatesTotalPages(state) {
      return Math.ceil(state.candidatesTotal / state.candidatesPageSize);
    },

    /**
     * 是否有上一頁
     */
    candidatesHasPrevPage(state) {
      return state.candidatesPage > 1;
    },

    /**
     * 是否有下一頁
     */
    candidatesHasNextPage(state) {
      return (
        state.candidatesPage <
        Math.ceil(state.candidatesTotal / state.candidatesPageSize)
      );
    },
  },

  actions: {
    /**
     * 初始化會話
     */
    initSession() {
      if (!this.sessionId) {
        this.sessionId = `hr_session_${Date.now()}_${Math.random()
          .toString(36)
          .substr(2, 9)}`;
        console.log("[HR Store] 會話已初始化:", this.sessionId);
      }
    },

    /**
     * 執行 HR 諮詢
     */
    async consult(query) {
      this.consultationLoading = true;
      this.consultationError = null;

      try {
        this.initSession();

        // 保存當前候選人信息，確保多輪對話中保持一致
        const candidateId = this.selectedCandidate?.id || null;
        const candidateName = this.selectedCandidate?.name || null;

        console.log("[HR Store] 執行諮詢:", {
          query,
          candidateId,
          candidateName,
          sessionId: this.sessionId,
        });

        const result = await hrConsult(
          query,
          candidateId,
          candidateName,
          this.sessionId
        );

        if (result.success) {
          this.currentConsultation = result;

          // 如果自動識別了候選人，更新選中狀態（只在第一次時）
          if (result.candidate && !this.selectedCandidate) {
            this.selectedCandidate = {
              id: result.candidate.id,
              name: result.candidate.name,
              email: result.candidate.email,
            };
            console.log(
              "[HR Store] 自動識別候選人:",
              this.selectedCandidate.name
            );
          }

          // 重新加載歷史
          await this.loadHistory();

          return result;
        } else {
          throw new Error(result.error || "諮詢失敗");
        }
      } catch (error) {
        console.error("[HR Store] 諮詢失敗:", error);
        this.consultationError = error.message;
        throw error;
      } finally {
        this.consultationLoading = false;
      }
    },

    /**
     * 加載候選人列表
     */
    async loadCandidates(params = {}) {
      this.candidatesLoading = true;

      try {
        // 更新搜索查詢
        if (params.search !== undefined) {
          this.candidatesSearchQuery = params.search;
        }

        // 更新分頁
        if (params.page !== undefined) {
          this.candidatesPage = params.page;
        }

        // 更新排序
        if (params.sortBy !== undefined) {
          this.candidatesSortBy = params.sortBy;
        }
        if (params.sortOrder !== undefined) {
          this.candidatesSortOrder = params.sortOrder;
        }

        const offset = (this.candidatesPage - 1) * this.candidatesPageSize;

        const result = await getCandidates({
          search: this.candidatesSearchQuery,
          hasTestData:
            params.hasTestData !== undefined ? params.hasTestData : true,
          limit: this.candidatesPageSize,
          offset: offset,
          sortBy: this.candidatesSortBy,
          sortOrder: this.candidatesSortOrder,
        });

        if (result.success) {
          this.candidates = result.candidates;
          this.candidatesTotal = result.total;
          return result;
        } else {
          throw new Error("加載候選人列表失敗");
        }
      } catch (error) {
        console.error("[HR Store] 加載候選人失敗:", error);
        throw error;
      } finally {
        this.candidatesLoading = false;
      }
    },

    /**
     * 設置候選人頁碼
     */
    setCandidatesPage(page) {
      this.candidatesPage = page;
      return this.loadCandidates();
    },

    /**
     * 上一頁
     */
    candidatesPrevPage() {
      if (this.candidatesHasPrevPage) {
        return this.setCandidatesPage(this.candidatesPage - 1);
      }
    },

    /**
     * 下一頁
     */
    candidatesNextPage() {
      if (this.candidatesHasNextPage) {
        return this.setCandidatesPage(this.candidatesPage + 1);
      }
    },

    /**
     * 設置排序
     */
    setCandidatesSort(sortBy, sortOrder = "desc") {
      this.candidatesSortBy = sortBy;
      this.candidatesSortOrder = sortOrder;
      this.candidatesPage = 1; // 重置到第一頁
      return this.loadCandidates();
    },

    /**
     * 搜索候選人
     */
    searchCandidates(query) {
      this.candidatesSearchQuery = query;
      this.candidatesPage = 1; // 重置到第一頁
      return this.loadCandidates();
    },

    /**
     * 重置候選人列表狀態
     */
    resetCandidatesState() {
      this.candidatesPage = 1;
      this.candidatesSearchQuery = "";
      this.candidatesSortBy = "last_test_date";
      this.candidatesSortOrder = "desc";
    },

    /**
     * 選擇候選人
     */
    async selectCandidate(candidate) {
      try {
        // 如果提供的是 ID，則加載詳細資訊
        if (typeof candidate === "number") {
          const result = await getCandidateDetail(candidate);
          if (result.success) {
            this.selectedCandidate = result.candidate;
          }
        } else {
          this.selectedCandidate = candidate;
        }

        console.log("[HR Store] 已選擇候選人:", this.selectedCandidate.name);
        return this.selectedCandidate;
      } catch (error) {
        console.error("[HR Store] 選擇候選人失敗:", error);
        throw error;
      }
    },

    /**
     * 取消選擇候選人
     */
    clearSelectedCandidate() {
      this.selectedCandidate = null;
      console.log("[HR Store] 已清除候選人選擇");
    },

    /**
     * 加載諮詢歷史
     */
    async loadHistory(candidateId = null) {
      this.historyLoading = true;

      try {
        const result = await getConsultationHistory({
          sessionId: this.sessionId,
          candidateId: candidateId || this.selectedCandidate?.id,
          limit: 20,
        });

        if (result.success) {
          this.consultationHistory = result.history;
          return result;
        } else {
          throw new Error("加載歷史失敗");
        }
      } catch (error) {
        console.error("[HR Store] 加載歷史失敗:", error);
        throw error;
      } finally {
        this.historyLoading = false;
      }
    },

    /**
     * 清除會話歷史
     */
    async clearHistory() {
      if (!this.sessionId) return;

      try {
        await clearSessionHistory(this.sessionId);
        this.consultationHistory = [];
        console.log("[HR Store] 歷史已清除");
      } catch (error) {
        console.error("[HR Store] 清除歷史失敗:", error);
        throw error;
      }
    },

    /**
     * 重置所有狀態
     */
    reset() {
      this.selectedCandidate = null;
      this.currentConsultation = null;
      this.consultationError = null;
      this.consultationHistory = [];
      this.sessionId = null;
      this.resetCandidatesState();
      console.log("[HR Store] 狀態已重置");
    },

    /**
     * 切換候選人選擇器
     */
    toggleCandidateSelector() {
      this.showCandidateSelector = !this.showCandidateSelector;
      // 打開時重置狀態並加載
      if (this.showCandidateSelector) {
        this.resetCandidatesState();
        this.loadCandidates({ hasTestData: true });
      }
    },

    /**
     * 切換歷史面板
     */
    toggleHistoryPanel() {
      this.showHistoryPanel = !this.showHistoryPanel;
    },
  },
});

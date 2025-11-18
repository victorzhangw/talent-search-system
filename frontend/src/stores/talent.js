import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { talentAPI } from "@/api/talent";

export const useTalentStore = defineStore("talent", () => {
  // State
  const sessionId = ref(generateSessionId());
  const messages = ref([
    {
      id: 1,
      type: "system",
      content:
        '👋 歡迎使用 AI 人才搜索系統！\n\n您可以用自然語言描述您需要的人才，例如：\n• "列出所有候選人"\n• "找一個溝通能力強的銷售人員"\n• "搜索具有領導力的管理人才"\n\n💡 支援漸進式篩選：\n• "從這些人中找出內向型的"\n• "再篩選出有領導力的"\n• "重新搜索"（清空篩選）\n\n我會為您找到最匹配的候選人！',
    },
  ]);
  const candidates = ref([]);
  const selectedCandidates = ref([]);
  const filterHistory = ref([]); // 篩選歷史
  const suggestions = ref([
    "善於溝通的銷售人員",
    "有創造力的設計師",
    "分析能力強的數據分析師",
  ]);
  const connectionStatus = ref("已連線");
  const isTyping = ref(false);
  const traitDefinitions = ref({});

  // 生成會話 ID
  function generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Getters
  const selectedCount = computed(() => selectedCandidates.value.length);
  const candidatesCount = computed(() => candidates.value.length);

  // Actions
  async function sendMessage(userInput) {
    if (!userInput.trim() || isTyping.value) return;

    const userMessage = {
      id: Date.now(),
      type: "user",
      content: userInput,
    };

    messages.value.push(userMessage);
    isTyping.value = true;

    try {
      // 傳遞會話 ID
      const response = await talentAPI.searchTalents(
        userInput,
        sessionId.value
      );

      const systemMessage = {
        id: Date.now() + 1,
        type: "system",
        content: `${response.query_understanding}`,
      };

      messages.value.push(systemMessage);
      candidates.value = response.candidates;

      if (response.suggestions) {
        suggestions.value = response.suggestions;
      }
    } catch (error) {
      console.error("搜索錯誤:", error);

      const errorMessage = {
        id: Date.now() + 1,
        type: "system",
        content: "抱歉，搜索時發生錯誤。請確認 API 服務是否正在運行。",
      };
      messages.value.push(errorMessage);
      connectionStatus.value = "連接失敗";
    } finally {
      isTyping.value = false;
    }
  }

  function resetSession() {
    sessionId.value = generateSessionId();
    messages.value = [
      {
        id: 1,
        type: "system",
        content: "👋 新的對話已開始！\n\n您可以用自然語言描述您需要的人才。",
      },
    ];
    candidates.value = [];
    selectedCandidates.value = [];
    filterHistory.value = [];
    suggestions.value = [
      "善於溝通的銷售人員",
      "有創造力的設計師",
      "分析能力強的數據分析師",
    ];
  }

  function addFilterStep(query, count) {
    filterHistory.value.push({
      query,
      count,
      timestamp: Date.now(),
    });
  }

  function clearFilterHistory() {
    filterHistory.value = [];
  }

  async function checkApiConnection() {
    try {
      await talentAPI.healthCheck();
      connectionStatus.value = "已連線";
    } catch (error) {
      connectionStatus.value = "未連線";
    }
  }

  async function loadTraitDefinitions() {
    try {
      const response = await talentAPI.getTraits();
      const traits = response.traits;
      traitDefinitions.value = {};
      traits.forEach((trait) => {
        traitDefinitions.value[trait.chinese_name] = trait.description;
      });
    } catch (error) {
      console.error("載入特質定義失敗:", error);
    }
  }

  function toggleSelection(candidate) {
    const index = selectedCandidates.value.findIndex(
      (c) => c.id === candidate.id
    );
    if (index > -1) {
      selectedCandidates.value.splice(index, 1);
    } else {
      selectedCandidates.value.push(candidate);
    }
  }

  function isSelected(candidateId) {
    return selectedCandidates.value.some((c) => c.id === candidateId);
  }

  function clearSelection() {
    selectedCandidates.value = [];
  }

  return {
    // State
    sessionId,
    messages,
    candidates,
    selectedCandidates,
    filterHistory,
    suggestions,
    connectionStatus,
    isTyping,
    traitDefinitions,
    // Getters
    selectedCount,
    candidatesCount,
    // Actions
    sendMessage,
    checkApiConnection,
    loadTraitDefinitions,
    toggleSelection,
    isSelected,
    clearSelection,
    resetSession,
    addFilterStep,
    clearFilterHistory,
  };
});

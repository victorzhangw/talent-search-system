import { defineStore } from "pinia";
import { ref } from "vue";
import { talentAPI } from "@/api/talent";

export const useInterviewStore = defineStore("interview", () => {
  // State
  const showDialog = ref(false);
  const messages = ref([]);
  const isGenerating = ref(false);
  const selectedCandidates = ref([]);

  // Actions
  async function generateQuestions(candidates) {
    if (!candidates || candidates.length === 0) {
      alert("請先選擇至少一位候選人");
      return;
    }

    selectedCandidates.value = candidates;
    showDialog.value = true;
    messages.value = [];
    isGenerating.value = true;

    try {
      const response = await talentAPI.generateInterviewQuestions(
        candidates,
        []
      );

      messages.value.push({
        role: "assistant",
        content: response.questions,
      });
    } catch (error) {
      console.error("生成面試問題失敗:", error);
      messages.value.push({
        role: "assistant",
        content: "抱歉，生成面試問題時發生錯誤。請稍後再試。",
      });
    } finally {
      isGenerating.value = false;
    }
  }

  async function sendMessage(userInput) {
    if (!userInput.trim() || isGenerating.value) return;

    const userMessage = {
      role: "user",
      content: userInput,
    };

    messages.value.push(userMessage);
    isGenerating.value = true;

    try {
      const response = await talentAPI.generateInterviewQuestions(
        selectedCandidates.value,
        messages.value
      );

      messages.value.push({
        role: "assistant",
        content: response.questions,
      });
    } catch (error) {
      console.error("發送消息失敗:", error);
      messages.value.push({
        role: "assistant",
        content: "抱歉，處理您的請求時發生錯誤。請稍後再試。",
      });
    } finally {
      isGenerating.value = false;
    }
  }

  function closeDialog() {
    showDialog.value = false;
    messages.value = [];
    selectedCandidates.value = [];
  }

  function downloadAsCSV() {
    if (messages.value.length === 0) {
      alert("沒有可下載的內容");
      return;
    }

    let csvContent = "\uFEFF";
    csvContent += "面試問題建議\n\n";

    csvContent += "候選人信息\n";
    selectedCandidates.value.forEach((candidate, index) => {
      csvContent += `${index + 1},${candidate.name},${
        candidate.email
      },匹配度: ${Math.round(candidate.match_score * 100)}%\n`;
    });
    csvContent += "\n";

    csvContent += "面試問題\n";
    messages.value.forEach((message) => {
      if (message.role === "assistant") {
        const plainText = message.content
          .replace(/<[^>]*>/g, "")
          .replace(/\n\n+/g, "\n")
          .trim();
        csvContent += `\n${plainText}\n`;
      }
    });

    const blob = new Blob([csvContent], {
      type: "text/csv;charset=utf-8;",
    });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);

    link.setAttribute("href", url);
    link.setAttribute(
      "download",
      `面試問題_${new Date().toISOString().slice(0, 10)}.csv`
    );
    link.style.visibility = "hidden";

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  return {
    // State
    showDialog,
    messages,
    isGenerating,
    selectedCandidates,
    // Actions
    generateQuestions,
    sendMessage,
    closeDialog,
    downloadAsCSV,
  };
});

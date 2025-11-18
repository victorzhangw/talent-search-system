const { createApp } = Vue;

createApp({
  data() {
    return {
      messages: [
        {
          id: 1,
          type: "system",
          content:
            '👋 歡迎使用 AI 人才搜索系統！\n\n您可以用自然語言描述您需要的人才，例如：\n• "列出所有候選人"\n• "找一個溝通能力強的銷售人員"\n• "搜索具有領導力的管理人才"\n\n我會為您找到最匹配的候選人！',
        },
      ],
      userInput: "",
      isTyping: false,
      candidates: [],
      selectedCandidates: [],
      suggestions: [
        "善於溝通的銷售人員",
        "有創造力的設計師",
        "分析能力強的數據分析師",
      ],
      connectionStatus: "已連線",
      apiBaseUrl: "http://localhost:8000",
      showInterviewDialog: false,
      interviewMessages: [],
      interviewInput: "",
      isGeneratingQuestions: false,
      traitDefinitions: {},
    };
  },
  methods: {
    async sendMessage() {
      if (!this.userInput.trim() || this.isTyping) return;

      const userMessage = {
        id: Date.now(),
        type: "user",
        content: this.userInput,
      };

      this.messages.push(userMessage);
      const query = this.userInput;
      this.userInput = "";
      this.isTyping = true;

      this.scrollToBottom();

      try {
        const response = await axios.post(`${this.apiBaseUrl}/api/search`, {
          query: query,
          filters: null,
        });

        this.isTyping = false;

        const systemMessage = {
          id: Date.now() + 1,
          type: "system",
          content: `${response.data.query_understanding}。找到 ${response.data.total} 位候選人，以下是最匹配的結果。`,
        };

        this.messages.push(systemMessage);
        this.candidates = response.data.candidates;

        if (response.data.suggestions) {
          this.suggestions = response.data.suggestions;
        }

        this.scrollToBottom();
      } catch (error) {
        this.isTyping = false;
        console.error("搜索錯誤:", error);

        const errorMessage = {
          id: Date.now() + 1,
          type: "system",
          content: "抱歉，搜索時發生錯誤。請確認 API 服務是否正在運行。",
        };
        this.messages.push(errorMessage);
        this.connectionStatus = "連接失敗";
      }
    },

    useSuggestion(suggestion) {
      this.userInput = suggestion;
    },

    viewCandidate(candidate) {
      alert(
        `查看候選人詳情：\n\n姓名：${candidate.name}\nEmail：${
          candidate.email
        }\n匹配度：${Math.round(candidate.match_score * 100)}%\n\n${
          candidate.match_reason
        }`
      );
    },

    getInitials(name) {
      return name.substring(0, 2).toUpperCase();
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer;
        container.scrollTop = container.scrollHeight;
      });
    },

    async checkApiConnection() {
      try {
        await axios.get(`${this.apiBaseUrl}/health`);
        this.connectionStatus = "已連線";
      } catch (error) {
        this.connectionStatus = "未連線";
      }
    },

    async loadTraitDefinitions() {
      try {
        const response = await axios.get(`${this.apiBaseUrl}/api/traits`);
        const traits = response.data.traits;
        this.traitDefinitions = {};
        traits.forEach((trait) => {
          this.traitDefinitions[trait.chinese_name] = trait.description;
        });
      } catch (error) {
        console.error("載入特質定義失敗:", error);
      }
    },

    toggleSelection(candidate) {
      const index = this.selectedCandidates.findIndex(
        (c) => c.id === candidate.id
      );
      if (index > -1) {
        this.selectedCandidates.splice(index, 1);
      } else {
        this.selectedCandidates.push(candidate);
      }
    },

    isSelected(candidateId) {
      return this.selectedCandidates.some((c) => c.id === candidateId);
    },

    formatMatchReason(reason) {
      let formatted = reason;
      const traitPattern = /([^(]+)\((\d+)分\)/g;
      formatted = formatted.replace(traitPattern, (match, traitName, score) => {
        const description = this.traitDefinitions[traitName] || "暫無描述";
        return `<span class="trait-tooltip" @mouseenter="positionTooltip($event)">${traitName}(${score}分)<span class="tooltip-text"><strong>${traitName}</strong><br/>${description}<br/><br/>分數: ${score}/100</span></span>`;
      });
      return formatted;
    },

    positionTooltip(event) {
      const tooltip = event.target.querySelector(".tooltip-text");
      if (!tooltip) return;

      const rect = event.target.getBoundingClientRect();
      const tooltipWidth = 350;
      const tooltipHeight = 140;
      const margin = 10;

      let top = rect.top - tooltipHeight - margin;
      let left = rect.left;

      if (top < margin) {
        top = rect.bottom + margin;
        tooltip.classList.remove("tooltip-bottom");
        tooltip.classList.add("tooltip-top");
      } else {
        tooltip.classList.remove("tooltip-top");
        tooltip.classList.add("tooltip-bottom");
      }

      if (left + tooltipWidth > window.innerWidth - margin) {
        left = window.innerWidth - tooltipWidth - margin;
      }

      if (left < margin) {
        left = margin;
      }

      tooltip.style.top = top + "px";
      tooltip.style.left = left + "px";
    },

    async generateInterviewQuestions() {
      if (this.selectedCandidates.length === 0) {
        alert("請先選擇至少一位候選人");
        return;
      }

      this.showInterviewDialog = true;
      this.interviewMessages = [];
      this.isGeneratingQuestions = true;

      try {
        const response = await axios.post(
          `${this.apiBaseUrl}/api/generate-interview-questions`,
          {
            candidates: this.selectedCandidates,
            conversation_history: [],
          }
        );

        this.interviewMessages.push({
          role: "assistant",
          content: response.data.questions,
        });
      } catch (error) {
        console.error("生成面試問題失敗:", error);
        this.interviewMessages.push({
          role: "assistant",
          content: "抱歉，生成面試問題時發生錯誤。請稍後再試。",
        });
      } finally {
        this.isGeneratingQuestions = false;
      }
    },

    async sendInterviewMessage() {
      if (!this.interviewInput.trim() || this.isGeneratingQuestions) return;

      const userMessage = {
        role: "user",
        content: this.interviewInput,
      };

      this.interviewMessages.push(userMessage);
      this.interviewInput = "";
      this.isGeneratingQuestions = true;

      try {
        const response = await axios.post(
          `${this.apiBaseUrl}/api/generate-interview-questions`,
          {
            candidates: this.selectedCandidates,
            conversation_history: this.interviewMessages,
          }
        );

        this.interviewMessages.push({
          role: "assistant",
          content: response.data.questions,
        });
      } catch (error) {
        console.error("發送消息失敗:", error);
        this.interviewMessages.push({
          role: "assistant",
          content: "抱歉，處理您的請求時發生錯誤。請稍後再試。",
        });
      } finally {
        this.isGeneratingQuestions = false;
      }
    },

    closeInterviewDialog() {
      this.showInterviewDialog = false;
      this.interviewMessages = [];
      this.interviewInput = "";
    },

    formatInterviewMessage(content) {
      let formatted = content;
      const lines = formatted.split("\n");
      let inList = false;
      let result = [];

      for (let line of lines) {
        if (
          line.match(
            /^(#+\s*)?(.*(問題|建議|評估|技能|能力|特質|候選人|面試).*)$/
          )
        ) {
          if (inList) {
            result.push("</ul>");
            inList = false;
          }
          const title = line.replace(/^#+\s*/, "");
          result.push(
            `<div class="interview-section-title"><i class="fas fa-chevron-right"></i>${title}</div>`
          );
        } else if (line.match(/^\d+\.\s+(.+)$/)) {
          if (!inList) {
            result.push('<ul class="interview-question-list">');
            inList = true;
          }
          const content = line.replace(/^\d+\.\s+/, "");
          result.push(
            `<li class="interview-question-item"><i class="fas fa-circle-question"></i><span>${content}</span></li>`
          );
        } else if (line.match(/^[•\-\*]\s+(.+)$/)) {
          if (!inList) {
            result.push('<ul class="interview-question-list">');
            inList = true;
          }
          const content = line.replace(/^[•\-\*]\s+/, "");
          result.push(
            `<li class="interview-question-item"><i class="fas fa-check-circle"></i><span>${content}</span></li>`
          );
        } else if (line.trim()) {
          if (inList) {
            result.push("</ul>");
            inList = false;
          }
          result.push(line);
        } else {
          if (inList) {
            result.push("</ul>");
            inList = false;
          }
          result.push("<br/>");
        }
      }

      if (inList) {
        result.push("</ul>");
      }

      return result.join("\n");
    },

    downloadAsExcel() {
      if (this.interviewMessages.length === 0) {
        alert("沒有可下載的內容");
        return;
      }

      let csvContent = "\uFEFF";
      csvContent += "面試問題建議\n\n";

      csvContent += "候選人信息\n";
      this.selectedCandidates.forEach((candidate, index) => {
        csvContent += `${index + 1},${candidate.name},${
          candidate.email
        },匹配度: ${Math.round(candidate.match_score * 100)}%\n`;
      });
      csvContent += "\n";

      csvContent += "面試問題\n";
      this.interviewMessages.forEach((message) => {
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
    },
  },

  mounted() {
    this.checkApiConnection();
    this.loadTraitDefinitions();
  },
}).mount("#app");

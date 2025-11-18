# 設計文檔

## 概述

人才聊天搜索功能是一個基於自然語言處理的智能人才匹配系統，整合到現有的人才性質分析平台中。系統採用現代化的聊天介面，結合 AI 驅動的語義理解和搜索算法，為用戶提供直觀且高效的人才發現體驗。

## 架構

### 系統架構圖

<svg width="800" height="600" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#4F46E5;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#7C3AED;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="grad2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#059669;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0D9488;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="grad3" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#DC2626;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#EA580C;stop-opacity:1" />
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="2" dy="2" stdDeviation="3" flood-color="#00000030"/>
    </filter>
  </defs>
  
  <!-- 用戶介面層 -->
  <rect x="320" y="20" width="160" height="50" rx="10" fill="url(#grad1)" filter="url(#shadow)"/>
  <text x="400" y="35" text-anchor="middle" fill="white" font-family="Arial" font-size="12" font-weight="bold">Vue.js 前端</text>
  <text x="400" y="50" text-anchor="middle" fill="white" font-family="Arial" font-size="10">用戶介面層</text>
  
  <!-- API 閘道 -->
  <rect x="320" y="100" width="160" height="40" rx="8" fill="url(#grad2)" filter="url(#shadow)"/>
  <text x="400" y="125" text-anchor="middle" fill="white" font-family="Arial" font-size="12" font-weight="bold">API 閘道</text>
  
  <!-- 核心服務層 -->
  <rect x="50" y="180" width="120" height="40" rx="8" fill="url(#grad3)" filter="url(#shadow)"/>
  <text x="110" y="205" text-anchor="middle" fill="white" font-family="Arial" font-size="11" font-weight="bold">聊天服務</text>
  
  <rect x="200" y="180" width="120" height="40" rx="8" fill="url(#grad3)" filter="url(#shadow)"/>
  <text x="260" y="205" text-anchor="middle" fill="white" font-family="Arial" font-size="11" font-weight="bold">搜索服務</text>
  
  <rect x="350" y="180" width="120" height="40" rx="8" fill="url(#grad3)" filter="url(#shadow)"/>
  <text x="410" y="205" text-anchor="middle" fill="white" font-family="Arial" font-size="11" font-weight="bold">LLM 增強引擎</text>
  
  <rect x="500" y="180" width="120" height="40" rx="8" fill="url(#grad3)" filter="url(#shadow)"/>
  <text x="560" y="205" text-anchor="middle" fill="white" font-family="Arial" font-size="11" font-weight="bold">用戶管理服務</text>
  
  <!-- AI 處理層 -->
  <rect x="50" y="260" width="100" height="35" rx="6" fill="#8B5CF6" filter="url(#shadow)"/>
  <text x="100" y="282" text-anchor="middle" fill="white" font-family="Arial" font-size="10">NLP 處理引擎</text>
  
  <rect x="170" y="260" width="100" height="35" rx="6" fill="#8B5CF6" filter="url(#shadow)"/>
  <text x="220" y="282" text-anchor="middle" fill="white" font-family="Arial" font-size="10">對話管理器</text>
  
  <rect x="290" y="260" width="100" height="35" rx="6" fill="#8B5CF6" filter="url(#shadow)"/>
  <text x="340" y="282" text-anchor="middle" fill="white" font-family="Arial" font-size="10">搜索引擎</text>
  
  <rect x="410" y="260" width="100" height="35" rx="6" fill="#8B5CF6" filter="url(#shadow)"/>
  <text x="460" y="282" text-anchor="middle" fill="white" font-family="Arial" font-size="10">開源 LLM</text>
  
  <rect x="530" y="260" width="100" height="35" rx="6" fill="#8B5CF6" filter="url(#shadow)"/>
  <text x="580" y="282" text-anchor="middle" fill="white" font-family="Arial" font-size="10">向量資料庫</text>
  
  <!-- 資料層 -->
  <rect x="150" y="340" width="120" height="35" rx="6" fill="#059669" filter="url(#shadow)"/>
  <text x="210" y="362" text-anchor="middle" fill="white" font-family="Arial" font-size="10">人才資料庫</text>
  
  <rect x="300" y="340" width="120" height="35" rx="6" fill="#059669" filter="url(#shadow)"/>
  <text x="360" y="362" text-anchor="middle" fill="white" font-family="Arial" font-size="10">用戶資料庫</text>
  
  <rect x="450" y="340" width="120" height="35" rx="6" fill="#059669" filter="url(#shadow)"/>
  <text x="510" y="362" text-anchor="middle" fill="white" font-family="Arial" font-size="10">Redis 快取</text>
  
  <!-- 連接線 -->
  <line x1="400" y1="70" x2="400" y2="100" stroke="#374151" stroke-width="2" marker-end="url(#arrowhead)"/>
  <line x1="400" y1="140" x2="110" y2="180" stroke="#374151" stroke-width="2" marker-end="url(#arrowhead)"/>
  <line x1="400" y1="140" x2="260" y2="180" stroke="#374151" stroke-width="2" marker-end="url(#arrowhead)"/>
  <line x1="400" y1="140" x2="410" y2="180" stroke="#374151" stroke-width="2" marker-end="url(#arrowhead)"/>
  <line x1="400" y1="140" x2="560" y2="180" stroke="#374151" stroke-width="2" marker-end="url(#arrowhead)"/>
  
  <line x1="110" y1="220" x2="100" y2="260" stroke="#6B7280" stroke-width="1.5"/>
  <line x1="110" y1="220" x2="220" y2="260" stroke="#6B7280" stroke-width="1.5"/>
  <line x1="260" y1="220" x2="340" y2="260" stroke="#6B7280" stroke-width="1.5"/>
  <line x1="410" y1="220" x2="460" y2="260" stroke="#6B7280" stroke-width="1.5"/>
  <line x1="410" y1="220" x2="580" y2="260" stroke="#6B7280" stroke-width="1.5"/>
  
  <line x1="340" y1="295" x2="210" y2="340" stroke="#6B7280" stroke-width="1.5"/>
  <line x1="560" y1="220" x2="360" y2="340" stroke="#6B7280" stroke-width="1.5"/>
  <line x1="220" y1="295" x2="510" y2="340" stroke="#6B7280" stroke-width="1.5"/>
  
  <!-- 箭頭標記 -->
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#374151"/>
    </marker>
  </defs>
  
  <!-- 圖例 -->
  <rect x="20" y="420" width="760" height="160" rx="10" fill="#F9FAFB" stroke="#E5E7EB" stroke-width="1"/>
  <text x="30" y="440" fill="#374151" font-family="Arial" font-size="14" font-weight="bold">系統架構說明</text>
  
  <text x="30" y="460" fill="#6B7280" font-family="Arial" font-size="11">• Vue.js 前端提供響應式聊天介面，支援即時通訊和結果展示</text>
  <text x="30" y="480" fill="#6B7280" font-family="Arial" font-size="11">• API 閘道負責路由、認證和負載均衡</text>
  <text x="30" y="500" fill="#6B7280" font-family="Arial" font-size="11">• LLM 增強引擎整合開源大語言模型，提供智能搜索和結果解釋</text>
  <text x="30" y="520" fill="#6B7280" font-family="Arial" font-size="11">• 向量資料庫支援語義搜索和 RAG 架構</text>
  <text x="30" y="540" fill="#6B7280" font-family="Arial" font-size="11">• Redis 快取提升系統響應速度和用戶體驗</text>
  <text x="30" y="560" fill="#6B7280" font-family="Arial" font-size="11">• 微服務架構確保系統可擴展性和維護性</text>
</svg>

### 技術棧

**前端：**

- Vue.js 3 + Composition API
- WebSocket 用於即時通訊
- Tailwind CSS 用於樣式設計
- Chart.js 用於特質雷達圖顯示
- Pinia 用於狀態管理

**後端：**

- Node.js/Express 或 Python/FastAPI
- WebSocket 服務（Socket.io 或原生 WebSocket）
- Redis 用於會話管理和快取
- PostgreSQL 或現有資料庫系統

**AI/NLP：**

- 開源大語言模型（如 Qwen-2.5、ChatGLM4、Baichuan2）
- 模型推理服務（Ollama、vLLM 或 TensorRT-LLM）
- 中文 NLP 模型（如 BERT-Chinese 作為輔助）
- 向量搜索引擎（Elasticsearch 或 Pinecone）
- 語義相似度計算和 RAG 架構

## 組件與介面

### 1. 聊天介面組件 (ChatInterface)

**職責：**

- 渲染聊天對話介面
- 處理用戶輸入和訊息發送
- 顯示搜索結果和候選人卡片

**主要方法：**

```typescript
interface ChatInterface {
  sendMessage(message: string): Promise<void>;
  displayResults(candidates: Candidate[]): void;
  showTypingIndicator(): void;
  hideTypingIndicator(): void;
  clearChat(): void;
}
```

### 2. NLP 處理引擎 (NLPEngine)

**職責：**

- 解析用戶自然語言輸入
- 識別搜索意圖和關鍵實體
- 轉換為結構化搜索參數

**主要方法：**

```typescript
interface NLPEngine {
  parseQuery(userInput: string): Promise<ParsedQuery>;
  extractTraits(text: string): Promise<TraitEntity[]>;
  identifyIntent(text: string): Promise<SearchIntent>;
  generateClarificationQuestions(ambiguousQuery: ParsedQuery): string[];
}
```

### 3. 搜索引擎 (SearchEngine)

**職責：**

- 執行人才搜索查詢
- 計算候選人匹配分數
- 排序和過濾結果

**主要方法：**

```typescript
interface SearchEngine {
  searchCandidates(query: SearchQuery): Promise<SearchResult[]>;
  calculateMatchScore(candidate: Candidate, requirements: Requirements): number;
  rankResults(results: SearchResult[]): SearchResult[];
  applyFilters(results: SearchResult[], filters: SearchFilters): SearchResult[];
}
```

### 4. 對話管理器 (ConversationManager)

**職責：**

- 管理對話狀態和上下文
- 處理多輪對話邏輯
- 維護搜索歷史

**主要方法：**

```typescript
interface ConversationManager {
  initializeSession(userId: string): Promise<ConversationSession>;
  updateContext(sessionId: string, message: Message): Promise<void>;
  getConversationHistory(sessionId: string): Promise<Message[]>;
  saveSearchQuery(sessionId: string, query: SearchQuery): Promise<void>;
}
```

## 資料模型

### 1. 候選人模型 (Candidate)

```typescript
interface Candidate {
  id: string;
  name: string;
  email: string;
  assessmentResults: AssessmentResult[];
  traits: TraitScore[];
  lastAssessmentDate: Date;
  privacyLevel: PrivacyLevel;
}

interface TraitScore {
  traitName: string;
  score: number;
  category: string;
  description: string;
}
```

### 2. 搜索查詢模型 (SearchQuery)

```typescript
interface SearchQuery {
  originalText: string;
  parsedTraits: RequiredTrait[];
  jobRole?: string;
  experienceLevel?: ExperienceLevel;
  priorities: TraitPriority[];
  filters: SearchFilters;
}

interface RequiredTrait {
  name: string;
  minScore?: number;
  weight: number;
  isRequired: boolean;
}
```

### 3. 對話會話模型 (ConversationSession)

```typescript
interface ConversationSession {
  sessionId: string;
  userId: string;
  messages: Message[];
  currentContext: SearchContext;
  searchHistory: SearchQuery[];
  createdAt: Date;
  lastActivity: Date;
}

interface Message {
  id: string;
  type: "user" | "system" | "result";
  content: string;
  timestamp: Date;
  metadata?: MessageMetadata;
}
```

## 錯誤處理

### 1. NLP 處理錯誤

**策略：**

- 當無法理解用戶輸入時，提供範例查詢
- 對於模糊查詢，生成澄清問題
- 實施降級機制，使用關鍵字搜索作為備選

**實作：**

```typescript
class NLPErrorHandler {
  handleParsingError(error: NLPError, userInput: string): ErrorResponse {
    if (error.type === "AMBIGUOUS_QUERY") {
      return {
        type: "clarification",
        message: "您的需求有些模糊，請問您是指：",
        suggestions: this.generateSuggestions(userInput),
      };
    }
    // 其他錯誤處理...
  }
}
```

### 2. 搜索錯誤

**策略：**

- 資料庫連接失敗時顯示友好錯誤訊息
- 搜索超時時提供簡化搜索選項
- 無結果時建議調整搜索條件

### 3. 系統錯誤

**策略：**

- 實施斷路器模式防止級聯失敗
- 提供離線模式或快取結果
- 記錄詳細錯誤日誌用於監控

## 測試策略

### 1. 單元測試

**覆蓋範圍：**

- NLP 引擎的語言理解準確性
- 搜索算法的匹配邏輯
- 資料模型的驗證規則
- API 端點的輸入輸出

**測試工具：**

- Jest 或 Vitest 用於 JavaScript/TypeScript
- pytest 用於 Python 組件

### 2. 整合測試

**測試場景：**

- 端到端的搜索流程
- WebSocket 連接和訊息傳遞
- 資料庫查詢和結果返回
- 權限驗證和資料過濾

### 3. 用戶體驗測試

**測試重點：**

- 聊天介面的響應性和流暢度
- 搜索結果的相關性和準確性
- 多輪對話的上下文保持
- 不同裝置和瀏覽器的兼容性

### 4. 效能測試

**測試指標：**

- NLP 處理延遲（目標 < 1 秒）
- 搜索查詢響應時間（目標 < 2 秒）
- 並發用戶支援能力
- 記憶體和 CPU 使用率

## 安全考量

### 1. 資料隱私

**措施：**

- 實施基於角色的存取控制 (RBAC)
- 敏感資料脫敏處理
- 搜索日誌的定期清理
- 符合 GDPR 或相關隱私法規

### 2. API 安全

**措施：**

- JWT 令牌驗證
- API 速率限制
- 輸入驗證和清理
- HTTPS 強制加密

### 3. 會話安全

**措施：**

- 會話超時機制
- 安全的 WebSocket 連接 (WSS)
- 跨站請求偽造 (CSRF) 防護
- XSS 攻擊防護

## 部署架構

### 1. 微服務部署

**服務分離：**

- 聊天服務 (Chat Service)
- NLP 服務 (NLP Service)
- 搜索服務 (Search Service)
- LLM 推理服務 (LLM Inference Service)
- 用戶管理服務 (User Service)

### 2. 容器化

**Docker 配置：**

- 每個服務獨立的 Docker 容器
- Docker Compose 用於本地開發
- Kubernetes 用於生產環境

### 3. 監控與日誌

**監控工具：**

- Prometheus + Grafana 用於指標監控
- ELK Stack 用於日誌分析
- 健康檢查端點
- 錯誤追蹤和警報系統

### 5. LLM 增強搜索引擎 (LLMEnhancedSearchEngine)

**職責：**

- 利用大語言模型提升搜索理解能力
- 生成智能的搜索結果解釋
- 提供個性化的候選人推薦理由
- 處理複雜的多條件查詢

**主要方法：**

```typescript
interface LLMEnhancedSearchEngine {
  enhanceQuery(
    userQuery: string,
    context: ConversationContext
  ): Promise<EnhancedQuery>;
  generateExplanation(
    candidate: Candidate,
    query: SearchQuery
  ): Promise<string>;
  suggestRefinements(
    results: SearchResult[],
    originalQuery: string
  ): Promise<string[]>;
  analyzeSearchIntent(
    query: string,
    history: SearchHistory
  ): Promise<SearchIntent>;
  generatePersonalizedRecommendations(
    userId: string,
    preferences: UserPreferences
  ): Promise<Recommendation[]>;
}

interface EnhancedQuery {
  originalQuery: string;
  refinedQuery: string;
  extractedCriteria: SearchCriteria[];
  confidenceScore: number;
  suggestedFilters: SearchFilter[];
}
```

**LLM 增強功能的優勢：**

1. **更準確的意圖理解**

   - 理解複雜的中文表達和語境
   - 處理模糊或不完整的查詢
   - 識別隱含的需求和偏好

2. **智能結果解釋**

   - 為每個推薦候選人生成個性化的匹配理由
   - 解釋為什麼某個候選人符合特定要求
   - 提供改進搜索的建議

3. **上下文感知搜索**

   - 基於對話歷史優化搜索結果
   - 學習用戶的搜索模式和偏好
   - 提供更相關的後續問題和建議

4. **多輪對話優化**
   - 維護長期對話上下文
   - 處理複雜的多步驟查詢
   - 提供自然的對話體驗

### 4. LLM 服務部署考量

**硬體需求：**

- GPU 支援（推薦 NVIDIA A100 或 RTX 4090）
- 大記憶體配置（32GB+ RAM）
- 高速 SSD 儲存用於模型載入

**模型選擇建議：**

- **Qwen-2.5-7B/14B** - 阿里巴巴開源，中文能力強
- **ChatGLM4-9B** - 清華大學開源，對話能力佳
- **Baichuan2-7B/13B** - 百川智能開源，商用友好

**推理服務選項：**

- **Ollama** - 簡單易用，適合開發和小規模部署
- **vLLM** - 高效能推理，適合生產環境
- **TensorRT-LLM** - NVIDIA 優化，最佳 GPU 效能

**擴展策略：**

- 模型量化（INT8/INT4）降低記憶體需求
- 模型並行處理高並發請求
- 快取機制減少重複推理
- 負載均衡分散推理壓力

## RAG (Retrieval-Augmented Generation) 架構

### RAG 架構概述

RAG 架構結合了檢索系統和生成式 AI，為人才搜索提供更準確和相關的結果。系統首先從人才資料庫中檢索相關候選人資訊，然後利用大語言模型生成個性化的搜索結果和解釋。

### RAG 架構流程圖

<svg width="900" height="500" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="ragGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#3B82F6;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#1D4ED8;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="ragGrad2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#10B981;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#059669;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="ragGrad3" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#F59E0B;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#D97706;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="ragGrad4" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#EF4444;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#DC2626;stop-opacity:1" />
    </linearGradient>
    <filter id="ragShadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="3" dy="3" stdDeviation="4" flood-color="#00000040"/>
    </filter>
  </defs>
  
  <!-- 步驟 1: 用戶查詢 -->
  <rect x="50" y="50" width="140" height="60" rx="12" fill="url(#ragGrad1)" filter="url(#ragShadow)"/>
  <text x="120" y="70" text-anchor="middle" fill="white" font-family="Arial" font-size="12" font-weight="bold">1. 用戶查詢</text>
  <text x="120" y="85" text-anchor="middle" fill="white" font-family="Arial" font-size="10">"需要善於溝通的</text>
  <text x="120" y="98" text-anchor="middle" fill="white" font-family="Arial" font-size="10">銷售人員"</text>
  
  <!-- 步驟 2: 查詢向量化 -->
  <rect x="250" y="50" width="140" height="60" rx="12" fill="url(#ragGrad2)" filter="url(#ragShadow)"/>
  <text x="320" y="70" text-anchor="middle" fill="white" font-family="Arial" font-size="12" font-weight="bold">2. 查詢向量化</text>
  <text x="320" y="85" text-anchor="middle" fill="white" font-family="Arial" font-size="10">Embedding 模型</text>
  <text x="320" y="98" text-anchor="middle" fill="white" font-family="Arial" font-size="10">轉換為向量</text>
  
  <!-- 步驟 3: 向量搜索 -->
  <rect x="450" y="50" width="140" height="60" rx="12" fill="url(#ragGrad3)" filter="url(#ragShadow)"/>
  <text x="520" y="70" text-anchor="middle" fill="white" font-family="Arial" font-size="12" font-weight="bold">3. 向量搜索</text>
  <text x="520" y="85" text-anchor="middle" fill="white" font-family="Arial" font-size="10">相似度計算</text>
  <text x="520" y="98" text-anchor="middle" fill="white" font-family="Arial" font-size="10">檢索候選人</text>
  
  <!-- 步驟 4: 結果生成 -->
  <rect x="650" y="50" width="140" height="60" rx="12" fill="url(#ragGrad4)" filter="url(#ragShadow)"/>
  <text x="720" y="70" text-anchor="middle" fill="white" font-family="Arial" font-size="12" font-weight="bold">4. 結果生成</text>
  <text x="720" y="85" text-anchor="middle" fill="white" font-family="Arial" font-size="10">LLM 生成解釋</text>
  <text x="720" y="98" text-anchor="middle" fill="white" font-family="Arial" font-size="10">和推薦理由</text>
  
  <!-- 資料庫層 -->
  <rect x="150" y="180" width="120" height="50" rx="10" fill="#6366F1" filter="url(#ragShadow)"/>
  <text x="210" y="200" text-anchor="middle" fill="white" font-family="Arial" font-size="11" font-weight="bold">人才資料庫</text>
  <text x="210" y="215" text-anchor="middle" fill="white" font-family="Arial" font-size="9">結構化資料</text>
  
  <rect x="320" y="180" width="120" height="50" rx="10" fill="#8B5CF6" filter="url(#ragShadow)"/>
  <text x="380" y="200" text-anchor="middle" fill="white" font-family="Arial" font-size="11" font-weight="bold">向量資料庫</text>
  <text x="380" y="215" text-anchor="middle" fill="white" font-family="Arial" font-size="9">Embedding 向量</text>
  
  <rect x="490" y="180" width="120" height="50" rx="10" fill="#A855F7" filter="url(#ragShadow)"/>
  <text x="550" y="200" text-anchor="middle" fill="white" font-family="Arial" font-size="11" font-weight="bold">知識庫</text>
  <text x="550" y="215" text-anchor="middle" fill="white" font-family="Arial" font-size="9">職位描述、技能</text>
  
  <!-- 連接線和箭頭 -->
  <defs>
    <marker id="ragArrow" markerWidth="12" markerHeight="8" refX="10" refY="4" orient="auto">
      <polygon points="0 0, 12 4, 0 8" fill="#374151"/>
    </marker>
  </defs>
  
  <line x1="190" y1="80" x2="250" y2="80" stroke="#374151" stroke-width="3" marker-end="url(#ragArrow)"/>
  <line x1="390" y1="80" x2="450" y2="80" stroke="#374151" stroke-width="3" marker-end="url(#ragArrow)"/>
  <line x1="590" y1="80" x2="650" y2="80" stroke="#374151" stroke-width="3" marker-end="url(#ragArrow)"/>
  
  <line x1="320" y1="110" x2="210" y2="180" stroke="#6B7280" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="520" y1="110" x2="380" y2="180" stroke="#6B7280" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="720" y1="110" x2="550" y2="180" stroke="#6B7280" stroke-width="2" stroke-dasharray="5,5"/>
  
  <!-- RAG 流程說明 -->
  <rect x="50" y="280" width="800" height="180" rx="15" fill="#F8FAFC" stroke="#E2E8F0" stroke-width="2"/>
  <text x="70" y="305" fill="#1E293B" font-family="Arial" font-size="16" font-weight="bold">RAG 架構優勢與實作細節</text>
  
  <circle cx="80" cy="330" r="4" fill="#3B82F6"/>
  <text x="95" y="335" fill="#475569" font-family="Arial" font-size="12" font-weight="bold">檢索增強 (Retrieval)：</text>
  <text x="95" y="350" fill="#64748B" font-family="Arial" font-size="11">• 使用向量搜索快速找到相關候選人資料</text>
  <text x="95" y="365" fill="#64748B" font-family="Arial" font-size="11">• 支援語義搜索，理解查詢意圖而非僅關鍵字匹配</text>
  
  <circle cx="450" cy="330" r="4" fill="#10B981"/>
  <text x="465" y="335" fill="#475569" font-family="Arial" font-size="12" font-weight="bold">生成增強 (Generation)：</text>
  <text x="465" y="350" fill="#64748B" font-family="Arial" font-size="11">• LLM 基於檢索結果生成個性化解釋</text>
  <text x="465" y="365" fill="#64748B" font-family="Arial" font-size="11">• 提供匹配理由和改進建議</text>
  
  <circle cx="80" cy="385" r="4" fill="#F59E0B"/>
  <text x="95" y="390" fill="#475569" font-family="Arial" font-size="12" font-weight="bold">技術實作：</text>
  <text x="95" y="405" fill="#64748B" font-family="Arial" font-size="11">• 使用 BGE-M3 或 Text2Vec 進行中文向量化</text>
  <text x="95" y="420" fill="#64748B" font-family="Arial" font-size="11">• Pinecone 或 Qdrant 作為向量資料庫</text>
  <text x="95" y="435" fill="#64748B" font-family="Arial" font-size="11">• 實時更新候選人向量索引</text>
  
  <circle cx="450" cy="385" r="4" fill="#EF4444"/>
  <text x="465" y="390" fill="#475569" font-family="Arial" font-size="12" font-weight="bold">效能優化：</text>
  <text x="465" y="405" fill="#64748B" font-family="Arial" font-size="11">• 向量快取減少重複計算</text>
  <text x="465" y="420" fill="#64748B" font-family="Arial" font-size="11">• 分層搜索策略提升響應速度</text>
  <text x="465" y="435" fill="#64748B" font-family="Arial" font-size="11">• 批次處理優化 LLM 推理效率</text>
</svg>

### RAG 實作策略

#### 1. 向量化處理

**Embedding 模型選擇：**

- **BGE-M3** - 支援多語言，中文效果優秀
- **Text2Vec-Chinese** - 專門針對中文優化
- **M3E-Base** - 輕量級中文向量模型

**向量化內容：**

- 候選人技能描述和評估結果
- 職位需求和角色描述
- 用戶查詢和歷史搜索

#### 2. 檢索策略

**多階段檢索：**

1. **粗排階段** - 向量相似度快速篩選
2. **精排階段** - 結合業務規則和權重
3. **重排階段** - LLM 評估最終相關性

**檢索優化：**

- 混合搜索（向量 + 關鍵字）
- 動態權重調整
- 個性化搜索偏好

#### 3. 生成策略

**Prompt 工程：**

```
你是一個專業的人才匹配顧問。基於以下候選人資料和用戶需求，
請生成個性化的推薦理由和匹配分析。

用戶需求：{user_query}
候選人資料：{candidate_data}
匹配分數：{match_score}

請提供：
1. 匹配理由（為什麼推薦這個候選人）
2. 優勢分析（候選人的突出特質）
3. 潛在考量（需要注意的方面）
4. 建議問題（面試時可以詢問的問題）
```

**生成控制：**

- 溫度參數調整創造性
- 長度限制確保簡潔
- 格式化輸出便於展示

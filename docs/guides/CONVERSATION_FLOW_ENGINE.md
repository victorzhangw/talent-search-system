# 智能對話流程管理系統（可視化 / 可配置 / 可指定模型）可行性方案

> 目標：以「流程（Workflow/State Machine）」取代目前散落在程式碼中的 hard coding，讓對話能做：意圖識別與歸納、上下文/狀態管理、多輪引導、內容審核與安全終止，並且每個節點可指定 LLM model（甚至不同供應商）。

---

## 0. 現況盤點（對齊你們目前程式）

目前後端已具備部分能力，但存在「規則硬編碼、模組分散、缺少審核」等問題：

- **上下文管理雛形**：`BackEnd/conversation_manager.py`
  - `ConversationContext` 保存 `messages/current_candidate/current_candidates/last_intent`（目前是**記憶體 in-memory** sessions）。
  - `analyze_context_intent()` 用關鍵字規則判斷 follow-up（describe/interview/compare/filter...）。
- **意圖定義檔**：`BackEnd/intent_definitions.json`
  - 已有 intents/entities/settings，但目前後端主要流程並未完整以它驅動（仍以 if/else + 關鍵字為主）。
- **Prompt 配置**：
  - HR 諮詢已用 `BackEnd/prompt_manager.py` + `BackEnd/prompts/hr_consultation_prompts.json`（但仍偏「單一模組」用法）。
  - 人才搜尋/面試等仍存在不少 prompt 組字與 LLM 設定分散（例如 `BackEnd/interview_api.py` 內硬放 LLM_CONFIG）。
- **內容審核缺口**：`BackEnd/security/input_validator.py` 幾乎空白，目前缺少：
  - 使用者輸入前置審核
  - LLM 回覆的後置審核
  - 以及「違規後終止/降級」策略

因此：需要一個「對話流程引擎（Conversation Orchestrator）」把意圖、狀態、審核、LLM 節點與工具（DB/搜尋/分析）串在一起。

---

## 1. 整體架構（建議）

### 1.1 核心元件

1. **Conversation Orchestrator（流程引擎）**
   - 讀取 workflow 定義（JSON/YAML/DB）
   - 依照狀態、意圖、審核結果執行下一個節點
   - 產出可視化（Mermaid/JSON graph）

2. **Intent Router（意圖識別與歸納）**
   - 規則 + LLM 分類（雙層）：
     - 快速規則：關鍵字/正則/slot hints（便宜且可控）
     - LLM intent classification：輸出 `intent + confidence + entities`
   - 以 `intent_definitions.json` 驅動（或升級為 intents 資料表）

3. **Context/State Store（上下文與狀態）**
   - 取代 in-memory：Redis/PostgreSQL（建議先 Redis）
   - 存：messages（最近 N 輪）、candidate scope、對話狀態(state)、tool outputs（可選）

4. **Policy & Moderation（內容審核與安全策略）**
   - Input moderation、Output moderation
   - 需要「可配置」：哪些類別直接終止、哪些需要改寫/拒答

5. **LLM Node Runner（LLM 節點執行器）**
   - 每個節點可指定 `provider/model/temperature/max_tokens/tools`
   - 支援 fallback（例如主模型失敗 -> 次模型）

6. **Tool Nodes（資料與業務工具節點）**
   - Talent search / HR consult / interview generator / DB lookup
   - 每個工具節點產出結構化結果，供下一個節點 prompt 注入

---

## 2. 典型流程（你描述的流程）

你目前的需求流程：
- 前端按「開始對話」-> API 傳多個 candidateIds
- 後端自動回覆問候語
- 等使用者輸入
- 後端做意圖判斷 -> 選 prompt 類型
- 需要記憶狀態，多輪引導
- 流程需要可視化
- 各節點調用 LLM 可指定 model

### 2.1 Mermaid：高階流程圖（入口/路由/審核/終止）

```mermaid
flowchart TD
  A[StartConversation API\n(candidates[])] --> B[Init Session + Store Candidates]
  B --> C[LLM Node: Greeting]\n(model=greeting_model)
  C --> D[Wait User Message]

  D --> E[Moderation: Input]
  E -->|blocked| Z1[End: Refuse + Close Session]
  E -->|ok| F[Intent Router\n(rule -> LLM classify)]

  F --> G{State + Intent\nDecide Next Node}

  G -->|search / filter| T1[Tool Node: TalentSearch]
  G -->|compare| T2[Tool Node: CompareCandidates]
  G -->|interview| T3[Tool Node: InterviewGuide]
  G -->|hr_consult| T4[Tool Node: HRConsultation]
  G -->|unknown| H[LLM Node: Clarify Question]

  T1 --> R[LLM Node: Compose Answer]\n(model=answer_model)
  T2 --> R
  T3 --> R
  T4 --> R
  H --> R

  R --> O[Moderation: Output]
  O -->|blocked| Z2[End: Safe Completion\n(Refuse/De-escalate)]
  O -->|ok| S[Persist State + Return Response]
  S --> D
```

---

## 3. Workflow / State Machine 設計（可視化 + 可配置）

### 3.1 建議用「圖（Graph）」而非純 if/else

- 每個節點是 Node（LLM/Tool/Policy/Router）
- 邊（Edge）以條件表達式控制（intent、state、moderation_result、slots）
- 允許：
  - 分支/合流
  - fallback
  - 子流程（sub-workflow）

你們可以：
- **輕量自研**：讀 JSON/YAML，執行節點（最可控，最快落地）
- 或採用框架：例如 LangGraph（Python）、Temporal（偏工作流）、或其他 state machine lib

本方案以「自研 JSON/YAML Workflow + 可輸出 Mermaid」為主（避免框架綁定）。

### 3.2 Workflow 定義（範例：YAML）

> 實務上建議：
> - 開發初期 YAML/JSON 放 repo（好 review）
> - 穩定後搬到 DB（加版本/回溯/灰度）

```yaml
id: talent_chat_v1
version: 1
entry: init
nodes:
  init:
    type: state_init
    set:
      state: "WAIT_USER"
    next: greet

  greet:
    type: llm
    model:
      provider: openai_compatible
      name: deepseek-ai/DeepSeek-V3
      temperature: 0.2
      max_tokens: 200
    prompt:
      system: "你是專業的人才顧問。用簡短禮貌的方式打招呼，並詢問使用者想了解哪些候選人的哪些面向。"
      user: "候選人數量：{{ candidates_count }}"
    next: wait_user

  wait_user:
    type: wait_user
    next: input_moderation

  input_moderation:
    type: moderation
    policy_ref: default_policy
    input: "{{ user_message }}"
    next:
      blocked: end_refuse
      ok: intent_router

  intent_router:
    type: intent_router
    intent_definitions_ref: intents_v1
    model:
      provider: openai_compatible
      name: deepseek-ai/DeepSeek-V3.1
      temperature: 0
    next: decide

  decide:
    type: switch
    cases:
      - when: "{{ intent }} == 'search'"
        next: tool_search
      - when: "{{ intent }} == 'compare'"
        next: tool_compare
      - when: "{{ intent }} == 'interview'"
        next: tool_interview
      - when: "{{ intent }} == 'hr_consult'"
        next: tool_hr_consult
    default_next: clarify

  tool_search:
    type: tool
    tool_name: talent_search
    input:
      query: "{{ user_message }}"
      scope: "{{ session.scope }}"
    next: compose

  tool_compare:
    type: tool
    tool_name: compare_candidates
    input:
      candidate_ids: "{{ session.candidate_ids }}"
      query: "{{ user_message }}"
    next: compose

  tool_interview:
    type: tool
    tool_name: generate_interview
    input:
      candidate_ids: "{{ session.candidate_ids }}"
      query: "{{ user_message }}"
    next: compose

  tool_hr_consult:
    type: tool
    tool_name: hr_consult
    input:
      candidate_ids: "{{ session.candidate_ids }}"
      query: "{{ user_message }}"
    next: compose

  clarify:
    type: llm
    model:
      provider: openai_compatible
      name: deepseek-ai/DeepSeek-V3
      temperature: 0.3
      max_tokens: 250
    prompt:
      system: "你需要先澄清需求。"
      user: "使用者問題：{{ user_message }}\n請用 1-2 個問題釐清他想做：搜尋/比較/面試/候選人解讀。"
    next: output_moderation

  compose:
    type: llm
    model:
      provider: openai_compatible
      name: deepseek-ai/DeepSeek-V3.1
      temperature: 0.4
      max_tokens: 600
    prompt:
      system_ref: prompts.answer_composer.system
      user_ref: prompts.answer_composer.user
    next: output_moderation

  output_moderation:
    type: moderation
    policy_ref: default_policy
    input: "{{ assistant_message }}"
    next:
      blocked: end_safe
      ok: persist

  persist:
    type: persist
    save:
      messages: true
      state: true
      slots: true
    next: wait_user

  end_refuse:
    type: end
    message: "抱歉，我無法協助這類內容。如果你願意，可以改問與人才選擇/面試相關的問題。"

  end_safe:
    type: end
    message: "我無法提供該內容。不過我可以協助你以合規方式討論人才評估或面試準備。"
```

---

## 4. 意圖識別與歸納（Intent Router）

### 4.1 意圖定義：從 `intent_definitions.json` 升級成「可被路由器直接使用」

你們已經有 `BackEnd/intent_definitions.json`，建議調整為：
- intents 附帶：`route_to`（預設節點/子流程）、`required_slots`、`clarify_questions`
- 允許同義詞/多語

範例（概念）：

```json
{
  "intents": {
    "search": {
      "name": "搜尋人才",
      "route_to": "tool_search",
      "required_slots": ["traits"],
      "clarify_questions": ["你想找什麼職位？", "最重視哪些特質？"],
      "enabled": true
    }
  }
}
```

### 4.2 雙層分類（推薦）

1. **Rule-first**：若命中高置信規則（例如「比較」「排除」「從這些人中」），直接給 intent
2. **LLM classify**：其餘走分類 prompt，輸出：

```json
{
  "intent": "compare",
  "confidence": 0.81,
  "entities": {"candidate_names": ["A", "B"]},
  "needs_clarification": false,
  "suggested_next_question": ""
}
```

> 這樣才能用 `min_confidence` 做 fallback：confidence 太低 -> 走 `clarify`。

---

## 5. 上下文/狀態管理（Context Management）

### 5.1 狀態欄位建議

- `session_id`
- `state`：WAIT_USER / IN_TOOL / IN_CLARIFY / END
- `candidate_ids`（前端傳入的候選人集合）
- `focus_candidate_id`（目前鎖定的候選人）
- `scope`：current / all
- `slots`：traits / role / seniority / constraints...
- `history`：最近 N 輪（或做摘要）

### 5.2 儲存層建議

- PoC：Redis（TTL 24h），快速
- 正式：PostgreSQL + Redis（Redis 做熱資料、PG 做稽核/回放）

---

## 6. 內容審核與終止策略（Moderation/Policy）

### 6.1 審核位置

1. **Input moderation**：使用者輸入進入流程前
2. **Tool-call guard**：工具節點前（避免把敏感內容送到 DB 或外部服務）
3. **Output moderation**：LLM 回覆送回前端前

### 6.2 策略（可配置）

- 類別：暴力、性、仇恨、騷擾、自殘、違法、個資（PII）等
- 動作：
  - `block_end`：直接拒答並結束
  - `block_continue`：拒答但允許繼續問（看產品設計）
  - `rewrite`：請模型改寫成合規版本

範例 policy（概念）：

```yaml
id: default_policy
rules:
  - category: sexual
    action: block_end
  - category: violence
    action: block_end
  - category: pii
    action: block_continue
```

> 你們的 `BackEnd/security/input_validator.py` 建議改成：
> - 基礎 regex/keyword
> - + 可選 LLM moderation（或第三方 moderation API）

---

## 7. LLM 節點可指定 model（Model Policy）

### 7.1 為什麼要「節點級」model 指定

- Greeting 用小模型/低 token
- Intent classify 用 temperature=0、要求 JSON schema
- Compose answer 用大模型
- Safety rewrite 用安全對齊更強的模型

### 7.2 建議配置結構

- workflow node 內可 inline model
- 或引用 `model_policies`：集中管理、可灰度

```yaml
model_policies:
  greeting_model:
    provider: openai_compatible
    name: deepseek-ai/DeepSeek-V3
    temperature: 0.2
  classifier_model:
    provider: openai_compatible
    name: deepseek-ai/DeepSeek-V3.1
    temperature: 0
  answer_model:
    provider: openai_compatible
    name: deepseek-ai/DeepSeek-V3.1
    temperature: 0.4
```

---

## 8. 可視化（Workflow Designer）

### 8.1 最小可行：Mermaid 自動輸出

- Workflow JSON/YAML -> 轉 Mermaid flowchart/state diagram
- 前端管理台直接渲染 Mermaid（或用 `react-flow` / `vue-flow`）

### 8.2 進階：可視化編輯器

- UI 以「節點」為單位：LLM Node / Tool Node / Router / Moderation / Persist / End
- Node 表單可選 model policy、prompt template、輸入輸出映射
- Deploy：存成 workflow version，後端熱更新

---

## 9. API 契約建議（取代硬編碼的核心）

### 9.1 建議新增：統一對話 API

1) `POST /api/chat/start`
- body：`candidate_ids[]`, `user_id`, `metadata`
- response：`session_id`, `assistant_message`（問候語）

2) `POST /api/chat/message`
- body：`session_id`, `message`
- response：`assistant_message`, `state`, `intent`, `debug`（可選）

3) `GET /api/chat/workflows/{id}`
- 回 workflow JSON + Mermaid（供管理台顯示）

---

## 10. 導入路線圖（最小風險替換 hard coding）

### Phase 1（1-2 週）：先把流程抽成「workflow 配置」
- 只做：start/greet/intent_router/compose/persist
- context store 改成 Redis
- moderation 先做 rule-based（regex/keyword）

### Phase 2（2-4 週）：把現有模組變成 Tool Nodes
- talent_search / compare / interview / hr_consult 變成工具節點
- 把 prompt 統一走 Prompt Registry（template + variables）

### Phase 3（4-8 週）：可視化管理台 + 版本化 + 灰度
- workflow 版本管理
- A/B model policy
- 觀測：每節點 latency/token/cost

---

## 11. 與現有程式的對應（落地切入點）

- `ConversationContext/ConversationManager`：可改造成 context store 的 domain model（但 sessions 要搬到 Redis/DB）。
- `intent_definitions.json`：升級為 Intent Registry（增加 route_to/required_slots）。
- `prompt_manager.py`：擴展成 Prompt Registry（不只 HR consult）。
- `security/input_validator.py`：實作成 Moderation service（input/output/tool-call）。
- `interview_api.py` / `talent_search_api.py`：把 LLM 調用集中到 LLM Node Runner，避免每個模組各自組 config。

---

## 12. 你們下一步我建議先確認的決策

1. Context store 先用 **Redis** 還是直接用 **PostgreSQL**？（我建議 Redis 起步）
2. Workflow 定義要先放 repo（YAML/JSON），還是要直接進 DB 做版本？
3. Moderation 先 rule-based，還是要一開始就接 LLM moderation？


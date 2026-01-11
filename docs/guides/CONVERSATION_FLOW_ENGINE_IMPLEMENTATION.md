# 智能對話流程引擎：實踐步驟（方案 1：新增新 API，不影響既有代碼）

> 本文件是「未來逐步落實」的唯一依據（Single Source of Truth）。
> 
> 原則：**先旁路新增（parallel run），後逐步導流（gradual cutover），最後再淘汰舊流程（deprecate）**。

相關設計方案請先閱讀：`docs/guides/CONVERSATION_FLOW_ENGINE.md`。

---

## 0. 目標與非目標

### 0.1 目標

1. 意圖識別與歸納：把使用者提問分類到固定 Prompt/工具子流程（Intent Router）。
2. 上下文管理：保存 session state、候選人範圍、最近對話、slots，支援多輪引導。
3. 內容審核：Input/Output/Tool-call 三段式審核，違規可拒答並（視 policy）結束對話。
4. 取代硬編碼：用 Workflow/Graph 定義取代 if/else、prompt 拼字與分散的 LLM 設定。
5. 可視化：Workflow 定義可輸出 Mermaid，提供管理台渲染基礎。
6. LLM 節點可指定 model：每個節點可指定 provider/model/temperature/max_tokens，並支援 fallback。

### 0.2 非目標（第一期不做）

- 不重構/替換既有 `/api/talent/*`、`/api/hr-consult/*` 行為。
- 不在第一期就做完整拖拉式流程編輯器（只做 Mermaid 輸出 + 配置檔）。
- 不一次把所有 prompts 全部收斂（先覆蓋「聊天流程」所需的最小集合）。

---

## 1. 導入策略（保證不影響既有功能）

- **新增**一套新 API：
  - `POST /api/chat/start`
  - `POST /api/chat/message`
  - `GET /api/chat/workflows/{id}`（可選）
- 新 API 使用「Workflow Runner」處理，不依賴舊的 `ConversationManager`。
- 舊 API（人才搜尋、HR 諮詢、面試等）維持原狀。
- 新流程中對資料/能力的依賴以「Tool Node」形式包裝：
  - 先做 minimal wrappers（直接呼叫既有 service/function），不要重寫邏輯。

---

## 2. 工作拆解（Milestones）

> 建議每個 milestone 都要產出可驗收的 API 行為與最小測試。

### Milestone 1：建立新聊天 API + Session Store（不接 LLM 也能跑通） ✅（已完成）

**目標**：可以 start -> 取得 session_id；message -> 能把訊息寫入 session store 並回固定回覆。

**新增/調整檔案（建議路徑）**

- `BackEnd/chat/`（新增資料夾）
  - `router.py`：新 API 路由
  - `schemas.py`：Pydantic models
  - `session_store.py`：SessionStore interface + Redis/Memory 實作
  - `types.py`：共用型別（SessionState、NodeIO 等）
- `BackEnd/main_api.py`
  - 掛載 `app.include_router(chat_router, prefix="/api/chat")`

**Session data schema（最小必需）**

- `session_id`
- `created_at`/`updated_at`
- `candidate_ids: list[str|int]`
- `state: str`（例如 WAIT_USER）
- `messages: list[{role, content, ts}]`（先只存最近 N 輪）
- `slots: dict`（先留空）

**驗收標準**

- `POST /api/chat/start` 回 `session_id` + `assistant_message`（先用固定 greeting）。
- `POST /api/chat/message` 回 `assistant_message`（先 echo/固定），並可 `GET /api/chat/session/{id}`（可選 debug）查到狀態。

---

### Milestone 2：Workflow Runner v0（Node 執行 + Mermaid 輸出） ✅（已完成）

**目標**：把 greeting/wait/persist 這類流程從程式 if/else 抽到 workflow YAML/JSON。

**新增檔案（建議）**

- `BackEnd/chat/workflows/`
  - `talent_chat_v1.yaml`（workflow 定義）
- `BackEnd/chat/workflow_loader.py`
  - 讀取 YAML/JSON、做 schema validation
- `BackEnd/chat/workflow_runner.py`
  - `run(session, user_message?) -> assistant_message + debug`
- `BackEnd/chat/mermaid_exporter.py`
  - `workflow -> mermaid flowchart`（先支援 node + next 邊即可）

**驗收標準**

- start 時透過 workflow 的 `greet` node 生成 greeting（先不用 LLM 也可：template node）。
- `GET /api/chat/workflows/{id}` 可回傳 workflow JSON 與 Mermaid 字串。

---

### Milestone 3：Moderation v0（rule-based） ✅（已完成：input moderation + output moderation + 終止對話）

**目標**：補齊「輸入/輸出」審核節點，可配置政策並能終止對話。

**新增/調整檔案**

- `BackEnd/chat/moderation/`
  - `policy_loader.py`（載入 YAML/JSON policy）
  - `moderator.py`（rule-based：keyword/regex + category mapping）
- （可選）擴寫既有：`BackEnd/security/input_validator.py` 轉為可重用 module

**驗收標準**

- 有 `policy_ref: default_policy` 的 moderation node。
- 違規輸入會走 `end_refuse`，並標記 session `state=END`。

---

### Milestone 4：Intent Router v1（rule-first + LLM classify） ✅（已完成 rule-first；LLM fallback 為可選）

**目標**：意圖識別可回：intent/confidence/entities，並依 confidence 決定 clarify。

**新增/調整檔案**

- `BackEnd/chat/intent/`
  - `intent_registry.py`：讀取 `BackEnd/intent_definitions.json`（或複製一份到 chat 模組）
  - `rule_router.py`：高置信規則
  - `llm_classifier.py`：LLM JSON schema 分類器
  - `router.py`：整合 rule-first + LLM fallback

**LLM classify 輸出 schema（必須嚴格）**

```json
{"intent":"search","confidence":0.76,"entities":{},"needs_clarification":false,"suggested_next_question":""}
```

**驗收標準**

- 針對 10+ 條測試語句能穩定分到 search/compare/interview/hr_consult/unknown。
- confidence < 閾值時會走 clarify node。

---

### Milestone 5：LLM Node Runner（節點級 model 指定 + fallback） ✅（已完成最小版）

**目標**：把 LLM 呼叫集中成一個 client，node 可以指定 model policy。

**新增檔案**

- `BackEnd/chat/llm/`
  - `client.py`：OpenAI-compatible client（你們現有多個模組都用 `/v1/chat/completions`）
  - `model_policy.py`：model policies（provider/name/params/fallbacks）

**驗收標準**

- greeting/classify/compose 使用不同 model/temperature。
- 任一模型失敗可 fallback（例如 5xx/timeout）。

---

### Milestone 6：Tool Nodes（串接既有能力，不重寫） ✅（已接入第 1 個 tool：talent_search，DB 直連版）

> 注意：目前 `talent_search` tool 使用 **DB 直連**（需要 `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD`）。
> 若你們的 DB 必須透過 SSH tunnel，請在後續里程碑新增 tunnel 支援或改用 app.state 共享連線（但要避免 import `talent_search_api.py` 造成副作用）。

**目標**：把人才搜尋、HR 諮詢、面試問題生成等能力用「工具節點」接入 workflow。

**策略**

- **只包裝，不重寫**：Tool Node 內部直接呼叫既有函式/服務（或 HTTP call）。
- Tool Node 產出結構化 `tool_result`，交給 compose node 生成自然語言輸出。

**候選 Tool Nodes**

- `talent_search`：呼叫你們現有 talent search 引擎
- `compare_candidates`
- `generate_interview`
- `hr_consult`

**驗收標準**

- workflow 中能依 intent 走到正確工具節點。
- 回覆由 compose node 統一生成（避免各模組各自拼 prompt）。

---

### Milestone 7：觀測與灰度（可選但建議）

**目標**：每個節點有 trace，能看延遲、token、錯誤、命中 intent。

- 每次 `run()` 產出 `trace_id`
- 節點級 log：開始/結束時間、model、token、moderation result

---

## 3. API 契約（新 API，與舊 API 完全獨立）

### 3.1 `POST /api/chat/start`

Request:

```json
{
  "user_id": "u123",
  "workflow_id": "talent_chat_v1",
  "candidate_ids": [1,2,3],
  "metadata": {"locale":"zh-TW"}
}
```

Response:

```json
{
  "success": true,
  "session_id": "sess_xxx",
  "assistant_message": "...greeting...",
  "state": "WAIT_USER"
}
```

### 3.2 `POST /api/chat/message`

Request:

```json
{
  "session_id": "sess_xxx",
  "message": "我想比較 1 號跟 2 號候選人"
}
```

Response:

```json
{
  "success": true,
  "assistant_message": "...",
  "state": "WAIT_USER",
  "intent": "compare",
  "debug": {"trace_id":"..."}
}
```

---

## 4. 配置檔與版本化規範（必須遵守）

### 4.1 Workflow

- 位置（初期）：`BackEnd/chat/workflows/*.yaml`
- 版本欄位必填：`id`, `version`, `entry`
- Node 需具備：`type`, `next`（或 next map）

### 4.2 Intent registry

- 初期沿用：`BackEnd/intent_definitions.json`
- 逐步擴充欄位：`route_to`, `required_slots`, `clarify_questions`

### 4.3 Prompt registry ✅（已完成最小版）

- Chat 引擎 prompts 位置：`BackEnd/chat/prompts/prompts_zh_tw.json`
- Workflow 中**禁止**硬寫大量文字模板：請改用 `prompt_ref: <prompt_id>`（end 節點用 `message_ref`）。
- 後續若要支援多語系：新增 `prompts_en_us.json`，並依 session metadata/locale 決定載入檔案。

### 4.4 Moderation policy

- `BackEnd/chat/policies/moderation_default.yaml`

### 4.5 Model policy

- `BackEnd/chat/policies/models.yaml`
- 同一個 node 必須只引用 policy key，不要在 node 裡散落寫死（方便集中調參）。

---

## 5. 測試與驗收（每個 milestone 都要做）

### 5.1 必做的自動化測試

- 單元測試：
  - workflow loader schema validation
  - intent router（rule + LLM mock）
  - moderation rules
- API 測試：
  - start/message happy path
  - blocked path（輸入違規）
  - intent low confidence -> clarify

### 5.2 手動驗收腳本（建議保留）

- `curl`/Postman collection：start/message/workflow mermaid

---

## 6. 灰度與切換規則（未來落實必須照做）

1. 新 API 先只給內部使用（或特定前端頁面）
2. 加入 feature flag：
   - 前端可切：legacy / workflow
3. 指標達標後（錯誤率、回覆品質、審核命中）才允許提高流量
4. 舊 API 淘汰流程：
   - 標記 deprecated
   - 通知前端改呼叫新 API
   - 最後移除舊路由/舊 hard code

---

## 7. 當前狀態（與既有代碼的界線）

- 本計畫 **不修改**：
  - `BackEnd/talent_search_routes.py`
  - `BackEnd/hr_consultation_routes.py`
  - `BackEnd/interview_api.py`

- 本計畫 **新增**：
  - `BackEnd/chat/*` 及其配置檔
  - `docs/guides/CONVERSATION_FLOW_ENGINE*.md`

---

## 8. 變更流程（文件治理）

- 本文件如需更新：
  1) 先提出變更理由（影響哪些 milestone）
  2) 再更新文件內容
  3) 最後才修改代碼

---

## 9. 下一步（請選）

A. 我直接開始建立 `BackEnd/chat/` 的骨架 + `POST /api/chat/start`、`POST /api/chat/message`（Milestone 1）

B. 先把 workflow YAML schema + loader + Mermaid exporter 做出來（Milestone 2）

C. 你想先定義第一版 workflow：只做 greeting + intent router + clarify + compose（不接工具）還是要一開始就接 talent_search？

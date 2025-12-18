# 前端搜索與後端處理流程分析

## 1. 概述
當用戶在前端搜索並選擇候選人後，輸入文字進行諮詢時，系統會通過 HR 諮詢模組處理請求。該流程涉及前端 API 調用、後端路由分發、服務層邏輯處理、資料庫查詢以及 LLM 整合。

## 2. 前端處理 (Frontend)

### 2.1 用戶交互
*   **組件**: `frontend/src/components/ChatArea.vue` (或 `HRConsultationPanel.vue`)
*   **動作**: 用戶在搜索模式下選擇候選人，並在輸入框輸入問題。
*   **狀態**: 前端維護 `selectedCandidate` (ID, Name) 和 `userInput`。

### 2.2 API 調用
*   **文件**: `frontend/src/api/hrConsultation.js`
*   **函數**: `hrConsult(query, candidateId, candidateName, sessionId)`
*   **請求**:
    *   **Method**: `POST`
    *   **URL**: `/api/hr-consult`
    *   **Payload**:
        ```json
        {
          "query": "用戶輸入的問題",
          "candidate_id": 123,
          "candidate_name": "候選人姓名",
          "session_id": "可選的會話ID"
        }
        ```

## 3. 後端處理 (Backend)

### 3.1 路由分發 (Routing)
*   **入口**: `BackEnd/main_api.py`
    *   掛載路由: `app.include_router(hr_router, prefix="/api/hr-consult", ...)`
*   **路由定義**: `BackEnd/hr_consultation_routes.py`
    *   **Endpoint**: `@router.post("")` (對應 `/api/hr-consult`)
    *   **處理**: 接收 `ConsultationRequest`，初始化 `HRConsultationService`，調用 `consult` 方法。

### 3.2 服務層邏輯 (Service Layer)
*   **核心類**: `HRConsultationService` (位於 `BackEnd/hr_consultation_service.py`)
*   **主要方法**: `consult(...)`

#### 處理步驟：

1.  **識別候選人 (`_resolve_candidate`)**:
    *   優先級：`candidate_id` > `candidate_name` > 從 `query` 中提取姓名。
    *   查詢表：`test_invitee`。
    *   驗證企業權限 (`enterprise_id`)。

2.  **獲取測評數據 (`_get_latest_test_data`)**:
    *   查詢表：`test_project_result` 關聯 `test_invitation`。
    *   條件：取最新且狀態為 `completed` 的測驗結果。
    *   內容：包含特質分數 (`trait_results`)、總分、預測結果等。

3.  **獲取特質配置 (`_get_trait_configs`)**:
    *   查詢表：`test_project_trait`。
    *   內容：獲取特質的權重 (`weight`)、優先級 (`is_primary`) 和顯示順序。

4.  **生成諮詢建議 (`_generate_consultation`)**:
    *   **分析優劣勢**: 根據分數篩選優勢 (>=80) 和劣勢 (<60)。
    *   **構建 System Prompt**: 
        *   整合候選人基本資料 (職位、狀態)。
        *   整合測驗歷史數據 (完成率、最後測驗日期)。
        *   詳細列出主要特質和所有特質的分數、權重。
        *   設定 HR 專家角色與回答限制 (150字)。
    *   **調用 LLM**: 使用 `httpx` 調用 SiliconFlow API (DeepSeek-V3)。
    *   **後處理**: 截斷過長的回答，提取回答中提到的特質。

5.  **保存歷史 (`_save_consultation_history`)**:
    *   將問答記錄寫入 `hr_consultation_history` 表。

### 3.3 數據結構關係
*   **候選人**: `test_invitee`
*   **測驗邀請**: `test_invitation`
*   **測驗結果**: `test_project_result` (存儲 JSONB 格式的特質分數)
*   **特質定義**: `test_project_trait` (定義權重與優先級)

## 4. 總結
後端通過整合結構化的測評數據（分數、權重、特質定義）與非結構化的候選人資料，構建豐富的 Context 提供給 LLM，從而生成基於數據的專業 HR 建議。

# 13. `expected_sections` 拆分為 single／multi（資料格式擴充）

**類型**：資料格式變更（資料＋程式雙邊）｜**優先度**：P2｜**依賴**：10（完整性檢查）

## 目標

把 `question_injection_table_v9.json` 每題目前單一份的 `expected_sections`，拆成 `expected_sections_single` 與 `expected_sections_multi` 兩份，並讓事項 10 的完整性檢查依 `audience`／實際受測人數選用正確的一份。

## 為什麼需要（逐字引用問題描述，`_ LOG 實作補充說明 for victor.txt` 第 74–98 行）

> 目前每題只有一份 `expected_sections`，但許多題目的單人版與多人版使用不同段落標題。例如「工作中的主要優勢與潛力」：
>
> 單人版預期段落為：自然優勢行為／潛在發展方向／優勢發揮的情境條件／主管使用提醒
>
> 多人版指令要求的內容卻是：對象間差異比對／協同與互補優勢／合作挑戰與拉扯／發展與配置策略
>
> 若多人回答完全遵照多人版指令，使用單人版 `expected_sections` 檢查仍會被判定缺少四個段落。因此**目前的資料不能直接作為多人版驗收契約**。

這是一個**明確的資料缺陷**（會讓 both 題型的多人回答被誤判失敗），不是打包程式邏輯的問題，但打包程式端要配合改讀取欄位。

## 建議資料格式（逐字引用）

```json
{
  "expected_sections_single": [
    "自然優勢行為",
    "潛在發展方向",
    "優勢發揮的情境條件",
    "主管使用提醒"
  ],
  "expected_sections_multi": [
    "工作優勢與潛力差異比對",
    "協同與互補優勢",
    "合作挑戰與拉扯",
    "發展與配置策略"
  ]
}
```

執行時：一位受測者→用 `expected_sections_single`；多位受測者→用 `expected_sections_multi`；**不得在 runtime 從指令文字自行猜測段落**。題庫指令也必須要求 LLM 使用與上述欄位完全相同的標題（這部分需要內容方同步修訂 c 檔的指令文字，確保指令要求的標題與 JSON 的 expected_sections 用詞一致）。

## 這是誰的工作

- **JSON 資料本身的拆分**（把現有 `expected_sections` 依單人/多人指令內容手動拆成兩份）——這需要**逐題核對** `instruction_single`／`instruction_multi` 實際要求的段落標題，是需要讀懂題意的語意工作，理論上應由內容方（Traitty 團隊）做，因為打包程式「零語意邏輯」的職責邊界明確排除「自行解析指令文字抽段落」。
- **打包程式讀取邏輯的修改**（依 audience 選對應欄位）——這是我方可獨立完成的技術工作，即事項本身。

**建議**：把「JSON 資料拆分」列為要回問／委託內容方的項目（見事項 15），本事項聚焦在打包程式端準備好支援新欄位的讀取邏輯，並在資料到位前保持向下相容（欄位不存在時退回舊的單一 `expected_sections`，並在 audit log 記一筆「此題尚未拆分 single/multi」）。

## 驗收標準

- [ ] `question_injection_table` schema 支援新增 `expected_sections_single` / `expected_sections_multi` 兩個欄位。
- [ ] 完整性檢查（事項 10）依當次請求人數自動選用正確欄位：1 人 → single，>1 人 → multi。
- [ ] 舊資料（尚未拆分、只有 `expected_sections`）仍可運作，不因欄位缺失而報錯，並在 log 中標註「未拆分」供追蹤哪些題目還沒補齊。
- [ ] 至少對「工作中的主要優勢與潛力」這一題構造單人/多人兩種測試，驗證各自套用正確的段落清單。

## 補充核對（2026-07-31 複查）：既有模組 prompt 檔案本來就是單人/多人分開存放，可能是現成的拆分素材

`BackEnd/api_v2/prompts/modules/` 目錄下 40 個既有檔案，本來就是 `{module}_single.txt` / `{module}_multi.txt` 成對存在（單人限定題只有 `_single`，如 `mgmt_manual_mgr_single.txt`；多人限定題只有 `_multi`，如 `team_meeting_multi.txt`）——這代表**現有系統本來就各自維護了單人版與多人版不同的輸出段落結構**，跟本事項要解決的問題（單人/多人指令要求不同段落標題）性質上是同一件事，只是現有系統目前把這個差異寫在 prompt 檔案的自然語言指示裡，沒有抽成結構化的 `expected_sections_single`／`expected_sections_multi` 欄位。

這對本事項是好消息：**內容方要拆分 `expected_sections_single`／`expected_sections_multi` 時，不必從頭猜每題的段落標題，可以直接對照這 40 個既有 prompt 檔案裡各自寫的段落架構**（例如 `mgmt_pressure_single.txt` 第 4–24 行「第一部分…第二部分…第三部分…第四部分…」的結構）作為草稿基礎，加速拆分作業。但要提醒一點：**這 40 個既有檔案是各自獨立撰寫的，用詞不保證與客戶最新的 `c_快速提問重構版_v9_20260728.xlsx`／`question_injection_table_v9.json` 完全一致**（兩者可能是不同時間點、不同人分別維護），拆分時仍需要內容方逐題核對兩邊用詞是否一致，不能直接假設既有 prompt 檔案的段落標題就是正確答案，只能當作起草參考。

## 出處對照

- `_ LOG 實作補充說明 for victor.txt` 第 74–127 行
- `b_打包規則_v2_20260727.md` §8
- `00_外包交接說明.md` 常見誤區（expected_sections 段落來源只能是 expected_sections 條）
- 既有程式碼：`BackEnd/api_v2/prompts/modules/`（40 個既有單人/多人分開的模組 prompt 檔案）

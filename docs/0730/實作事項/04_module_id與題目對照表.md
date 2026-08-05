# 04. `module_id` ↔ 題庫題目對照表建置

**類型**：整合缺口｜**優先度**：P0（阻斷自動選題）｜**依賴**：需內容方（Traitty 團隊）**覆核**既有隱性對應（見下方 2026-07-31 複查），不是從零決策

## 目標

建立 API `GET /api/v2/modules/` 回傳的英文 `module.id`，與我方題庫（`question_injection_table_v9.json`／`c_快速提問重構版_v9_20260728.xlsx`）以 `idx`（整數）＋中文 `title` 識別的題目之間的對照表，讓「使用者在前端選了哪個模組」能自動轉成「打包程式要用題庫表哪一題」。

## 背景（這是客戶交付文件明確列出的已知缺口，不是分析過程中發現的）

`README_最終交付.md`「交付前未結項」第 2 條：
> **`module_id ↔ 題目` 對照表未建**——API 用英文碼，題庫用 `idx`／中文 title | 內容方＋API 方 | 未補前選題無法自動對接（03 §3）

`03_API對接說明_TalentChatV2.md` §3：
> ⚠ **整合缺口（需補一張對應表）**：API 的 `module.id` 是英文碼，我方 `question_injection_table` 目前以中文 `title`／`idx` 為鍵，**兩者沒有共用 id**。需要 `module_id ↔ 我方題目` 對應表——建議由我方在題庫表加一欄 `module_id`，或另出對照 JSON。**此表未定案前，選題無法自動對接。**

`b_打包規則_v2_20260727.md` §1.1 也重申：「`question_id` 值域：題庫表每題以 `idx`（整數）＋中文 `title` 識別，**沒有獨立 id 欄**。請以 `idx` 為 `question_id`（title 僅供人閱）。與 API `module.id` 的對照表尚未建立。」

## 為什麼列為獨立事項而不是併入其他項

這張表**不是打包程式的內部邏輯**，而是連接既有 `modules.py`（本 repo 已實作，回傳 `data.categories = {分類名稱: [ModuleItem{id,label,mode}]}`）與新打包器之間的橋樑資料，且**需要內容方共同決定**要用哪一種形式補（題庫表加 `module_id` 欄，或另建 JSON 對照檔）。技術上簡單，但決策權不完全在實作方，值得單獨列出以便你決定由誰、何時處理。

## 補充核對（2026-07-31 複查）：這張表幾乎已經隱含存在，不是從零開始

實際比對 `BackEnd/api_v2/config/quick_modules.json`（22 個既有模組）與 `question_injection_table_v9.json`（22 題）後發現：**兩份清單依 `idx` 順序逐一比對，分類分組完全一致（招募4／管理8／團隊合作3／留才2／培育發展3／深度分析2），且每一題的 `audience` 與對應模組的 `candidate_mode` 100% 相符，0 筆衝突**（例如 idx 1「快速面試提問指南」↔ `recruit_interview`，`single_only`↔`single_only`；idx 15「打造高效會議團隊」↔ `team_meeting`，`multi_only`↔`multi_only`）。

這代表 `quick_modules.json` 很可能就是照這份題庫表的順序建的，只是**目前這個對應關係只存在於兩份檔案「剛好同順序排列」這個隱性巧合裡，沒有任何一處用顯式欄位寫下來**——題庫表沒有 `module_id` 欄，`quick_modules.json` 的 key（`recruit_interview` 等）也沒有反向指回 `idx`。這種「靠陣列順序對齊」的隱性依賴很脆弱：只要有一方之後新增/刪除/重排題目，對應關係就會在無聲無息中錯位，且不會有任何報錯提示。

**因此本事項的性質從「內容方需要重新決定怎麼補」下修為「內容方確認這個既有的隱性對應是否正確，然後我方把它顯式化」**——不必等待內容方重新設計，可以先把目前的位置對應關係整理成明確表格送內容方覆核，覆核通過即可直接落地，不是空白等待。

## 建議做法（供你裁決，非定案）

1. 在 `question_injection_table_v9.json` 每題物件加一個 `module_id` 欄位（英文碼），值直接取自上方核對出的既有 `quick_modules.json` key，與 `BackEnd/api_v2/config/quick_modules.json`（本 repo 既有的模組設定檔，`modules.py` 讀的就是這個檔）的 key 對齊。
2. 或者建一個獨立小 JSON：`{"module_id": "idx"}` 映射表，放在打包器資料目錄，程式啟動時載入。
3. 兩者皆需先盤點 `BackEnd/api_v2/config/quick_modules.json` 現有的 `mode`（`single`/`multi`）是否已經與題庫表的 `audience`（`single_only`/`multi_only`/`both`）一致——`03_API對接說明_TalentChatV2.md` §3 給的對應規則是 `single`↔`single_only`、`multi`↔`multi_only`，我方 `both` 題兩者皆可（本次複查已核對過，0 筆衝突，見上）。

## 驗收標準

- [ ] 對照表（不論哪種形式）能讓前端傳來的 `module_id` 100% 映射到題庫表某一題的 `idx`，無遺漏、無多對一衝突。
- [ ] `quick_modules.json` 的 `mode` 與題庫表 `audience` 交叉驗證一致，不一致的題目列出清單回報內容方。
- [ ] 對照表本身有版本／來源標註，避免日後題庫改版（如題目新增/刪除）忘記同步更新。

## 出處對照

- `README_最終交付.md`「交付前未結項」第 2 條
- `03_API對接說明_TalentChatV2.md` §3
- `b_打包規則_v2_20260727.md` §1.1
- 既有程式碼：`BackEnd/api_v2/routes/modules.py`、`BackEnd/api_v2/config/quick_modules.json`

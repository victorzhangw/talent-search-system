# 03. Talent Chat API v2 對接：受測者評鑑結果（輸入 B）

**類型**：基礎資料層｜**優先度**：P0｜**依賴**：無

## 目標

實作從 Talent Chat API v2 取得人選特質評鑑結果，轉換成打包程式的 `Respondent` 輸入格式；涵蓋單人與多人（batch）兩種情境。

## 背景

這是三類輸入中唯一直接來自本 repo 既有 API 的一類（另兩類是靜態內容正本）。本 repo 已有 `BackEnd/api_v2/routes/candidates.py`、`reports.py` 與 `BackEnd/api_v2/utils/traitty_api.py`，`reports.py` 目前的 `POST /api/v2/reports/batch`（`get_batch_reports()`）已經在做「抓 assessment → 整理 traits → 回傳」，可作為本事項的既有基礎，但**目前輸出格式（`trait_id/name/score/band`）與打包程式需要的 `Respondent{name,id,tests,scores}` 不是同一種形狀**，需要一層轉換 adapter。

> 附帶提醒（與本任務無關但發現於閱讀 `reports.py` 時）：該檔案目前有大量 `print(..., flush=True)` 除錯輸出殘留在正式路徑中，且專案 `CLAUDE.md` 明確記載過同一支檔案曾因 `print` 含 emoji 在 Windows 主控台以 cp950 編碼崩潰過（已修）。若本事項要在 `reports.py` 或同層新增程式碼，記得延續該檔案已有的「無 emoji」慣例；是否要順手清掉這些除錯 print，由你決定是否併入本事項或另開任務。

## 範圍邊界

- **A（特質敘事內容）不來自這支 API**，只有 **B（分數→band）** 與 **C 的「選哪一題」的模組清單**來自 API（C 的實際指令文字仍來自我方題庫表）。
- 打包程式只用 `band`，不用原始 `score`（`03_API對接說明_TalentChatV2.md` 明載：`score` 欄「不需」）。

## 輸入輸出契約（逐字對照 API 欄位）

`GET /api/v2/candidates/{candidate_id}/report` 回傳 `data`：
```json
{ "candidate_name": "王智弘", "assessment_date": "2026-07-20",
  "traits": [ { "trait_id": "CIA_16", "name": "目標路徑清晰", "score": 82, "band": "A" }, ... ] }
```

欄位對接表（`03_API對接說明_TalentChatV2.md` §2）：

| API 欄位 | → 打包程式 | 備註 |
|---|---|---|
| `traits[].trait_id` | `scores` 的 key | join 我方敘事的鍵 |
| `traits[].band` | `scores` 的 value | 伺服器已算好，直接用（**值域未實測，見事項 15**） |
| `traits[].score` | 不需 | |
| `data.candidate_name` | `respondent.name` | |
| `candidate_id`（path 參數） | `respondent.id` | |
| （已測測驗清單） | `respondent.tests` | API 未直接給，由 `trait_id` 前綴（ANI/CIA/SPA/CSR）去重推導 |

參考 adapter（`03_API對接說明_TalentChatV2.md` §2 / `02_參考程式碼_打包器骨架.py` 第 110–120 行，兩份文件內容一致）：
```python
r = api_get(f"/api/v2/candidates/{cid}/report")["data"]
scores = {t["trait_id"]: t["band"] for t in r["traits"]}
tests  = sorted({t["trait_id"].split("_")[0] for t in r["traits"]})
resp = Respondent(name=r["candidate_name"], id=cid, tests=tests, scores=scores)
```

**多人（batch）**：`POST /api/v2/reports/batch`，body `{ "assessment_ids": [62,63,64] }` → `data.reports[]`（`AssessmentReport{assessment_id, assessment_date, project_name_abbreviation, traits[]}`），逐份轉一個 `Respondent`。
⚠ **batch 的 report 不含 `candidate_name`**（只有 `project_name_abbreviation`），姓名需先用 `GET /api/v2/candidates/` 列表的 `latest_assessment.assessment_id` ↔ candidate 對應取回，本事項須實作這個回查。

## 驗收標準

- [ ] 單人情境：輸入 `candidate_id`，輸出正確的 `Respondent{name, id, tests, scores}`。
- [ ] `tests` 正確由 `trait_id` 前綴推導且去重（例如同時有 CIA/SPA 特質時 `tests=["CIA","SPA"]`）。
- [ ] 多人 batch 情境：輸入多個 `assessment_id`，每份正確轉出一個 `Respondent`，且姓名透過 candidate 回查補齊（不是 `project_name_abbreviation`）。
- [ ] band 值若非 `"A"/"B"/"C"` 時能明確報錯或轉換（暫時先報錯即可，實際轉換規則待事項 15 的外部回覆）。

## 補充核對（2026-07-31 複查）：既有程式碼其實不信任 API 給的 `band`，是自己重算的

`BackEnd/api_v2/services/context_builder.py` 第 175–192 行，目前拿到 `score` 後，是拿分數去查 DB 的 `TraitBand`（`min_score <= score <= max_score`）自己算出 band，**完全沒有讀取 API／前端傳來的 `trait.band` 欄位**——即使 `reports.py` 的 `get_batch_reports()` 有把 API 的 `band` 欄位透傳出去（第 150 行 `'band': t.get('band', '')`），下游的 `context_builder.py` 也沒有用它，是自己用 `score` 重新查表決定 band。

這跟客戶規格的假設**正好相反**：`03_API對接說明_TalentChatV2.md` §2 寫的是「`band` 已由伺服器算好，直接用」，`02_參考程式碼_打包器骨架.py` 的 adapter 也是直接拿 API 的 `band` 當 `scores` 的值，不重算。

這是一個**需要你或內容方裁定的架構分歧**，不是誰對誰錯：
- **沿用現有做法（自己用 score 重算 band）**：優點是不依賴 API 的 band 定義是否與我方一致（見事項 15 第 1 條，band 值域本來就未經實測）；缺點是等於整個 `03_API對接說明` 描述的「B 直接來自 API」設計要改寫成「B 來自 API 的 score，band 由我方 DB 表算」。
- **改用客戶規格（直接信任 API 的 band）**：跟交付文件行為一致，但前提是事項 15 第 1 條（band 值域）必須先實測確認 A/B/C 三碼與我方定義的切點完全相同，否則會用錯 band 對錯內容。

本事項需要把這個分歧交由你裁定，再決定 adapter 要怎麼寫。

## 出處對照

- `00_外包交接說明.md` 第 12–24 行
- `03_API對接說明_TalentChatV2.md`（全篇，特別是 §2、§4）
- `02_參考程式碼_打包器骨架.py` 第 109–120 行
- 既有程式碼：`BackEnd/api_v2/routes/reports.py`、`BackEnd/api_v2/routes/candidates.py`、`BackEnd/api_v2/utils/traitty_api.py`、`BackEnd/api_v2/services/context_builder.py` 第 175–192 行（既有 score→band 重算邏輯）

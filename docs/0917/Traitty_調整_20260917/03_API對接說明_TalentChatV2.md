# 03. API 對接說明 — Talent Chat API v2

> 文件站：`https://devzoneapi1.aurocore.com/api/docs/`（spec：`/api/docs/openapi.json`）
> 正式服務：`https://traittyservice.aurocore.com`（本地開發 `http://localhost:5000`）
> 讀者：打包程式外包團隊。本文講**打包程式的三類輸入從這支 API 怎麼拿**。

---

## 0. 一句話

**輸入 B（特質評鑑結果）＋輸入 C 的「選哪一題」＝這支 API 提供；輸入 A（特質敘事內容）不來自 API，是我方 spec 正本。** 程式用 `trait_id` 把 API 回傳的分數 join 到我方敘事。

| 打包程式輸入 | 來源 | API 端點 |
|---|---|---|
| A 特質敘事內容（四欄／交互） | 我方 spec 正本（靜態） | ❌ 不在 API |
| **B 特質評鑑結果（分數→band）** | **本 API** | `GET /api/v2/candidates/{id}/report` |
| C 選哪一題（模組） | 本 API 選題 ＋ 我方題庫表內容 | `GET /api/v2/modules/` |

---

## 1. 認證

所有 `/api/v2/*` 與 `/chat/*` 皆需 **Bearer token**（`security: bearerAuth`）。
先 `POST /auth/login`（或 `/auth/init`）取得 token → 後續請求帶 `Authorization: Bearer <token>`。

---

## 2. 人選 + 分數（輸入 B 主來源）

### `GET /api/v2/candidates/{candidate_id}/report`
回傳 `data`：
```json
{ "candidate_name": "王智弘", "assessment_date": "2026-07-20",
  "traits": [ { "trait_id": "CIA_16", "name": "目標路徑清晰", "score": 82, "band": "A" }, ... ] }
```

**欄位對接（`Trait` → 打包程式 `Respondent`）：**

| API 欄位 | 型別 | → 打包程式 | 備註 |
|---|---|---|---|
| `traits[].trait_id` | string | `scores` 的 key | 例 `CIA_16`；join 我方敘事的鍵 |
| `traits[].band` | string | `scores` 的 value | **伺服器已算好**，程式直接用（值域見 §5 待確認 1） |
| `traits[].score` | number | 不需 | 原始分數，打包只用 band |
| `traits[].name` | string | 備援顯示 | 我方 `traits_113` 也有中文名 |
| `data.candidate_name` | string | `respondent.name` | |
| `candidate_id`（path 參數） | string | `respondent.id` | |
| （已測測驗清單） | — | `respondent.tests` | ⚠ API 未直接給；由 traits 內 `trait_id` 前綴（ANI/CIA/SPA/CSR）去重推導 |

**adapter（對應 `02_參考程式碼` 的輸入 B）：**
```python
r = api_get(f"/api/v2/candidates/{cid}/report")["data"]
scores = {t["trait_id"]: t["band"] for t in r["traits"]}
tests  = sorted({t["trait_id"].split("_")[0] for t in r["traits"]})
resp = Respondent(name=r["candidate_name"], id=cid, tests=tests, scores=scores)
```

### 列人選：`GET /api/v2/candidates/`
分頁 `limit`(≤100)/`offset`；MOCK 模式帶 `enterprise_code`。
回傳 `data[]`＝`Candidate{candidate_id, name, latest_assessment{assessment_id, completion_time}}`。

### 多人：`POST /api/v2/reports/batch`
Body `{ "assessment_ids": [62,63,64] }` → `data.reports[]`＝`AssessmentReport{assessment_id, assessment_date, project_name_abbreviation, traits[]}`。
逐份轉一個 `Respondent`（trait 映射同上）。
⚠ batch 的 report **不含 candidate_name**（只有 `project_name_abbreviation`）；姓名需先用 `candidates` 列表的 `latest_assessment.assessment_id` ↔ candidate 對應取回。

---

## 3. 題目（輸入 C 的選題）

### `GET /api/v2/modules/`
`data.categories`＝`{ 分類名稱: [ ModuleItem{id, label, mode:"single"|"multi"} ] }`
例：`{"招募":[{"id":"recruit_interview","label":"面試問題推薦","mode":"single"}]}`

- `module.id`（英文碼）＝使用者要回答的題目。
- `mode` → 我方 `audience`：`single`↔`single_only`、`multi`↔`multi_only`（我方 `both` 題兩者皆可）。

⚠ **整合缺口（需補一張對應表）**：API 的 `module.id` 是英文碼，我方 `question_injection_table` 目前以中文 `title`／`idx` 為鍵，**兩者沒有共用 id**。需要 `module_id ↔ 我方題目` 對應表——建議由我方在題庫表加一欄 `module_id`，或另出對照 JSON。**此表未定案前，選題無法自動對接。**

---

## 4. 端到端串接流程

```
1. POST /auth/login                         → 取 Bearer token
2. 前端選 人選 + 模組(題目)
3. GET /candidates/{id}/report              → traits → 組 Respondent（輸入 B）
4. module_id → 我方題目（需 §3 對應表）      → 取匡列/指令（輸入 C）
5. 讀我方 spec 正本                          → 特質敘事/交互（輸入 A）
6. 跑 02 打包器 → 產出 LOG payload
7. 送 LLM 生成                               （本 API /chat/ 為現行對話端點，SSE 串流）
```

---

## 5. 交付前必驗（team 用一次 MOCK 呼叫確認）

1. **band 值域**：schema 只標 `string`。我方全系統用 `"A"/"B"/"C"`——需實測確認 API 回的是否同碼；若為數字或其他碼，adapter 要加轉換（分數→band 的切點以我方定義為準）。
2. **trait_id 格式**：確認與我方一致（`CIA_16` 這種 `XXX_nn`）；若有大小寫/補零差異需正規化。
3. **module_id ↔ 我方題目對應表**：由誰提供、何時補（§3 缺口，未補前選題不能自動化）。
4. **batch 人名來源**：確認以 `assessment_id → candidate` 回查姓名的作法可行。

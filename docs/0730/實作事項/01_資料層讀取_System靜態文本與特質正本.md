# 01. 資料層讀取：System 靜態文本 + 特質正本（02 分頁）讀取 adapter

**類型**：基礎資料層｜**優先度**：P0｜**依賴**：無

## 目標

實作兩個 loader，供後續所有組裝邏輯使用：
1. `load_system_prompt()` — 讀入 `[SYSTEM PROMPT]` 靜態全文，一字不改地當常數提供。
2. `load_trait_columns()` — 從內容正本 `0722 02_08 V6.2 spec_.xlsx` 的「02」分頁讀出每個 `trait_id` 的四欄原文，回傳 `{trait_id: {行為面向, 管理重點, 可用於, 禁止}}`。

## 背景

參考程式碼骨架（`02_參考程式碼_打包器骨架.py` 第 93–100 行）把這兩個函式標為 `TODO(外包)`，僅留介面：

```python
def load_system_prompt(pkg) -> str:
    """TODO(外包): 讀 a_LOG完成版模板_v2_*.md 的『第一部分：System 靜態規範』全文，原樣回傳。"""

def load_trait_columns(pkg) -> dict:
    """TODO(外包): 從 spec xlsx『02』分頁讀每個 trait_id 的四欄，回傳 {trait_id: TraitCols}。
    四欄＝行為面向／管理重點／可用於／禁止（欄名以正本實際表頭為準）。"""
```

`traits_113_v6_2.json` 已提供 113 個特質的 `trait_id` / 中文名 / band 標籤（供 §05 分流時查標籤用），但**不含**四欄敘事原文本身——敘事原文只在 xlsx 的 02 分頁，這是本事項要接的部分。

## 範圍邊界

- **只搬運，不改寫**：K/L/ai_do/ai_dont 欄原文一字不動地讀出。
- **不做語意判斷**：欄名前綴正規化（見下）是純字串比對，不是語意動作。
- System 文本**必須逐字**取自 `a_LOG完成版模板_v2_20260727.md` **第 9–52 行**「第一部分：System 靜態規範」整段（第 9 行為該段標題、第 53 行是 `---` 分隔線與第二部分的起點；含【系統角色與判讀引導】6 條與【全域輸出規範】20 條），不得摘要、不得重排條號、不得漏字。建議直接把該段落存成獨立常數檔（例如 `system_prompt.txt`），避免每次從 md 文件解析時誤動格式。

## 輸入輸出契約

**輸入**：`0722 02_08 V6.2 spec_.xlsx` 的「02」分頁；表頭實際欄名需開表確認（文件中提到的正規名稱是 `semantic_description`＝行為面向、`management_focus`＝管理重點、`ai_do`＝可用於、`ai_dont`＝禁止）。

**輸出**：
```python
{
  "CIA_18": {
    "行為面向": "遇到壓力、衝突或失敗後能快速回到可工作狀態，並把打擊轉成修正與補救行動。",
    "管理重點": "適合高壓前線、轉型推進、責任變更頻繁角色；可作為續航與穩定支點。",
    "可用於": "①…②…③…",
    "禁止": "①…②…③…"
  }, ...
}
```

## 關鍵細節：欄名正規化（必做，容易漏）

`b_打包規則_v2_20260727.md` §2：
> 02 正本的 `ai_do`／`ai_dont` 儲存格**部分已自帶**「可用於：」「禁止：」前綴（實測：ANI 69/69、CIA 108/108、CSR 108/108 自帶；**SPA 僅 1/54**）。程式須「**缺則補、有則不重複加**」，否則 CIA/ANI/CSR 會輸出「可用於：可用於：…」，而 SPA 會缺欄名。

參考骨架已給出寫法（`02_參考程式碼_打包器骨架.py` 第 183–188 行 `_prefix()`），可直接沿用：
```python
def _prefix(text, name):
    t = (text or "").strip()
    return t if t.startswith(name) else f"{name}：{t}"
```

> 注意：這是讀取層的輸出還是渲染層的職責，兩種架構都可以，但**必須在某一層做，且只做一次**——若讀取層已補齊前綴，渲染層（事項 07）不可再補一次。

## 驗收標準

- [ ] `load_system_prompt()` 回傳字串與 `a_LOG完成版模板_v2_20260727.md` 第一部分（第 9–52 行）逐字比對零差異（可寫一個 diff 測試）。
- [ ] `load_trait_columns()` 對 113 個特質全數有回傳（與 `traits_113_v6_2.json` 的 `trait_id` 集合做交集比對，無缺漏）。
- [ ] SPA 特質的「可用於」「禁止」欄輸出時前面有補上前綴（抽樣至少 5 個 SPA 特質檢查）。
- [ ] CIA/ANI/CSR 特質的「可用於」「禁止」欄沒有出現「可用於：可用於：」重複前綴（抽樣檢查）。

## 補充核對（2026-07-31 複查）：這個 repo 不是「當場讀 xlsx」，而是已有 DB 內容管線

參考骨架假設打包程式每次組裝時直接開 xlsx 讀取；但本 repo 早就把 02/08 分頁**匯入 PostgreSQL**（`BackEnd/scripts/migrate_traits_from_excel.py`、`BackEnd/api_v2/admin/trait_importer.py`），對應 `trait_definitions`／`trait_bands`／`trait_interactions` 三張表。`TraitBand` 表的欄位剛好就是四欄原文的落地：`description`＝行為面向、`management_focus`＝管理重點、`ai_guidance`（JSON，`{do:[...], dont:[...]}`）＝可用於／禁止。**所以本事項不是新寫一個 xlsx reader，而是確認／延伸既有匯入管線能讀到 V6.2 版本正本，讀取層應該查 DB 而不是每次請求開 xlsx。**

這裡有一個**既有程式碼裡的真實 bug**，剛好命中本事項要處理的欄名正規化問題：`BackEnd/api_v2/services/context_builder.py` 第 219、221 行目前是：
```python
if guidance.get('do'):
    components["base_analysis"] += f"    - MUST DO: {guidance['do']}\n"
if guidance.get('dont'):
    components["base_analysis"] += f"    - DONT: {guidance['dont']}\n"
```
`guidance['do']` 若在 DB 裡是 Python list（`ai_guidance` 欄位型別是 `JSON`），直接印出來就會變成 `MUST DO: ['①…', '②…']` 這種帶方括號、單引號、英文鍵的格式——這正是 `a_LOG完成版模板` 甲類第 4 條明文禁止的「資料結構痕跡」，也是 `01_設計總說明與決策定案_v2_20260728.md` §2.1 特別點名要刪除的「`MUST DO: ['…']` 英文鍵與 Python list 包裝」。**這個 bug 目前活在正式程式碼路徑上，不分做不做新規格都該修**，且修法正好和本事項的 `_prefix()` 正規化邏輯是同一件事：要把 `ai_guidance.do`（list）轉成「可用於：①…②…③…」這種單一字串，而不是直接印 list。

另外需要向內容方確認一件事：客戶文件假設 xlsx 儲存格的「可用於」欄本身就是**已經帶 ①②③ 編號的完整字串**；但現有 DB 的 `ai_guidance` 存的是**清單（list of items）**。兩者資料形狀不同，讀取/渲染層要對齊成同一種——這點看要在匯入階段轉成字串，還是在渲染階段把 list 組回「①…②…③…」，屬於本事項要決定的實作細節，不影響外部契約。

**這個 bug 由客戶自己的資料檔佐證**（2026-07-31 第二次複查發現）：`regex_pack_v6_2.json` 第 4 條規則就是專門為它而存在的——
```json
{
  "id": "strip_python_list_wrapper",
  "purpose": "去除 MUST DO 欄位的 Python list 字串包裝（D4）",
  "pattern": "^\\[?'?|'?\\]?$",
  "note": "建議改為直接讀原欄位文字而非 repr；此 regex 僅為救急。"
}
```
客戶顯然在自己的資料裡也遇過同樣的 `MUST DO: ['…']` 問題，並明確表示**正解是從讀取層直接讀原欄位文字、不要用 repr，那條正則只是救急**。這正好支持本事項的做法：在讀取/渲染層把 `ai_guidance` 的 list 正確組成「可用於：①…②…③…」字串，而不是先印壞再用正則補救。

## 出處對照

- `00_外包交接說明.md` 第 65–76 行（閱讀順序表，第 4、6 項）
- `01_設計總說明與決策定案_v2_20260728.md` §2.1
- `b_打包規則_v2_20260727.md` §0（T4）、§2
- `02_參考程式碼_打包器骨架.py` 第 93–100、183–188 行
- 既有程式碼：`BackEnd/scripts/migrate_traits_from_excel.py`、`BackEnd/api_v2/admin/trait_importer.py`、`BackEnd/api_v2/database/models.py`（`TraitBand`）、`BackEnd/api_v2/services/context_builder.py` 第 199–221 行（含 MUST DO/DONT 洩漏 bug）

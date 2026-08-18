# 對話歷史（記憶）如何帶入模型，以及 prompts.log 的改造規格

日期：2026-08-18
對應客戶提問：「對話歷史是怎麼帶的？log 裡沒有歷史區塊，但 header 標了 HISTORY_TURNS: 2 / 4」
文件用途：**本文件第六節之後為開發依據與後續稽核是否達標的驗收基準。**

---

## 一、結論先講

客戶的猜測 **第 1 種是對的**：歷史確實有帶，走的是 API 的 `messages` 陣列，
夾在 system 訊息與當輪 user 訊息之間。`prompts.log` 目前**刻意只印 LOG 本體**
（`[SYSTEM PROMPT]` / `【輸入數據】` / `[任務指令]`），歷史只留下 header 上的一個數字。

所以「驗收時看不到 AI 實際讀到什麼」這個問題是成立的，而且不只影響歷史——
第五節列出目前 log 還缺的另外兩塊。

---

## 二、實際送給模型的 messages 長什麼樣

打包器路徑（`USE_LOG_PACKER` 開啟時）組出來的陣列，
定義在 `BackEnd/api_v2/services/log_assembler.py:111-114`：

```python
def to_messages(self, history=None):
    return [{'role': 'system',    'content': self.body},        # System prompt + 【輸入數據】
            *(history or []),                                   # 歷史，oldest first
            {'role': 'user',      'content': self.instruction}] # 當輪 [任務指令]
```

呼叫點在 `BackEnd/api_v2/services/log_pipeline.py:111`，
history 由 `packed_chat.try_packed_stream()` 從 `rag_service.load_history(session_id)` 取得
（`BackEnd/api_v2/services/packed_chat.py:141`）。

舊路徑（未走打包器）結構相同，見 `BackEnd/api_v2/services/rag_engine.py:535-539`：

```python
messages = [
    {"role": "system", "content": sys_prompt.strip()},
    *history_messages,
    {"role": "user",   "content": query},
]
```

也就是說 **兩條路徑的歷史處理方式完全一致**，共用同一個 `load_history()`。

---

## 三、逐題回覆

### Q1. 帶幾輪？印象中之前是講三輪？

**目前是 6 輪**，不是 3 輪。經本次確認後**維持 6 輪不變**（決策見第六節 D-3）。

| 位置 | 值 |
|---|---|
| `BackEnd/api_v2/config/settings.py:77` | `MAX_HISTORY_TURNS = int(os.getenv('MAX_HISTORY_TURNS', 6))` |
| `BackEnd/api_v2/.env:30`（本機實際值） | `MAX_HISTORY_TURNS=6` |
| `BackEnd/api_v2/.env.example:32` | `MAX_HISTORY_TURNS=6` |

這裡的「1 輪」= 使用者一則 + AI 一則 = 2 則訊息，
所以 6 輪 = **最多 12 則歷史訊息**（`rag_engine.py:519`：`conv = conv[-(max_turns * 2):]`）。

### Q2. HISTORY_TURNS 是實際帶入的輪數，還是累計輪數？

**是「實際帶入的」，但單位不是輪，是「訊息則數」——這是一個命名錯誤。**

`BackEnd/api_v2/services/packed_chat.py:55`：

```python
f"HISTORY_TURNS: {max(0, len(pipeline.messages) - 2)}"
```

`pipeline.messages` = 1 則 system + N 則歷史 + 1 則當輪 user，
減 2 之後得到的是**歷史訊息則數**，不是輪數。

對照客戶看到的數字：

| log 顯示 | 實際意義 | 換算 |
|---|---|---|
| `HISTORY_TURNS: 0` | 0 則歷史 | 第 1 輪對話（本輪之前沒有紀錄） |
| `HISTORY_TURNS: 2` | 2 則歷史 | 前面有 **1 輪** 完整問答 |
| `HISTORY_TURNS: 4` | 4 則歷史 | 前面有 **2 輪** 完整問答 |

上限會是 `12`（6 輪 x 2），而不是 `6`。所以如果在 log 上看到 `HISTORY_TURNS: 12`，
那代表已經吃滿上限、正在丟舊訊息，不是「跑了 12 輪還全帶著」。

> 這個欄位名字要修（見第七節 A 項）。目前名稱會讓驗收人員把「則數」當「輪數」讀，
> 剛好差兩倍。

### Q3. 超過上限怎麼截？丟最舊的嗎？

**是，丟最舊的，硬截斷，沒有摘要、沒有壓縮。**

`BackEnd/api_v2/services/rag_engine.py:502-525`：

```python
db_msgs = SqlSessionStore().get_messages(session_id)           # 整個 session 全撈，時間升冪
conv = [m for m in db_msgs if m.role in ('user', 'assistant')] # 只留 user / assistant
if conv and conv[-1].role == 'user':                           # 當輪 query 已先寫入 DB，先剔掉
    conv = conv[:-1]
conv = conv[-(max_turns * 2):]                                 # 取「最後 12 則」＝丟最舊的
history = [{"role": m.role, "content": m.content} for m in conv]
```

三個細節值得註記：

1. **截斷是以「則」為單位、不是以「輪」為單位。** 如果某輪因為串流中斷只存到 user 沒存到
   assistant，切出來的視窗第一則有可能是孤兒 assistant 或孤兒 user。目前不會報錯，模型也能讀，
   但驗收時看到不成對的歷史屬正常現象。
2. **`system` 角色的訊息會被濾掉。** 背景產生標題時會寫一筆 `role='system'` 的
   `[System] 產生標題: xxx`（`routes/chat.py:91-95`），它不會進歷史，不佔輪數。
3. **`session_id` 為空或 `"unknown"` 時直接回傳 `[]`**（`rag_engine.py:509-510`），
   歷史完全不帶。前端沒帶 session_id 的請求就是無記憶的一次性問答。

### Q4. 帶的是「使用者提問 + AI 回覆」兩邊，還是只有提問？

**兩邊都帶。** 見上面 `role in ('user', 'assistant')` 的過濾條件。

AI 回覆存的是 `full_assistant_content`（`routes/chat.py:504, 518, 553-561`），
也就是**實際串流給前端、經過出口掃描器與分段閘門放行的最終文字**，
包含補生成（completion pass）補上的段落。被閘門攔下沒放行的內容不會進 DB，
所以也不會進歷史——歷史看到的和使用者螢幕上看到的是同一份文字。

### Q5. 帶的是原文還是摘要？

**原文，逐字。** 程式碼裡沒有任何摘要、截字或壓縮邏輯：
`load_history()` 直接把 `m.content` 原封不動放進 `content` 欄位。

### Q6. 一個驗收時會撞到、但不是 bug 的地方

打包器路徑送給模型的**當輪 user 訊息是 LOG 的 `[任務指令]`**（模組題目的正式指令），
但**寫進 DB 當作下一輪歷史的，是前端送來的原始 query 字串**（`routes/chat.py:461`）。

例：使用者點選快問模組，模型當輪讀到的是題庫展開後的完整任務指令，
而下一輪歷史裡看到的只有「這兩位有比較合適的職位嗎」這種短句。

這是刻意的（歷史裡塞完整任務指令會把 context 撐爆，而且模組指令對後續追問沒有資訊量），
但驗收時如果拿 log 的 `[任務指令]` 去對下一輪的歷史區塊，兩者不會逐字相同，**這不是 bug**。

---

## 四、現況總表

| 客戶問題 | 現況 | 位置 |
|---|---|---|
| 歷史有帶嗎 | 有，走 `messages` 陣列 | `log_assembler.py:111-114`、`rag_engine.py:535-539` |
| 幾輪 | 6 輪（12 則），維持不變 | `settings.py:77`、`.env:30` |
| `HISTORY_TURNS` 意義 | 實際帶入的**則數**（名稱誤導） | `packed_chat.py:55` |
| 截斷方式 | 保留最後 N 則，丟最舊 | `rag_engine.py:519` |
| 帶提問還是連回覆 | 兩邊都帶 | `rag_engine.py:515` |
| 原文還是摘要 | 原文逐字，無摘要 | `rag_engine.py:520` |
| **歷史有印進 log 嗎** | **沒有，只印則數** | `packed_chat.py:34-64` |

---

## 五、現有功能無法達成的部分

### 缺口 1：`prompts.log` 沒有歷史內容（客戶本次主要訴求）

**無法達成，需要改程式。**

不是疏漏，是當初的取捨。`packed_chat.log_payload()` 的註解（`packed_chat.py:41-44`）寫明：

> 記的是 `to_log_text()` 而非 `to_messages()`：前者就是客戶驗收用的三段式 LOG 格式
> （[SYSTEM PROMPT] / 【輸入數據】 / [任務指令]），與 DoD 第 1 條拿去和三份 v7 範例
> 逐行比對的是同一個字串。歷史訊息只記筆數，因為它夾在 system 與 user 之間、不屬於
> LOG 本體，記進去會讓檔案與範例格式對不上。

當初是為了讓 log 能跟三份 v7 範例逐行 diff，才把歷史排除在外。
現在客戶要用同一份 log 驗收追問品質，這個取捨就站不住了——
兩個需求（格式可 diff／內容可稽核）必須拆開處理。

### 缺口 2：舊路徑的 log 同樣沒有歷史，而且原因更根本

`rag_engine._log_prompt()` 在 `_call_llm()` 的**第一行**就被呼叫（`rag_engine.py:529`），
但 `load_history()` 在**第四行**才執行（`rag_engine.py:533`）。
寫 log 的當下歷史根本還沒載入，就算想印也印不到。

### 缺口 3：三份 log 之間沒有可對照的鍵

`prompts.log`、`conversations.log`、`log_packer_audit.log` 目前只有 `SESSION` 與時間戳可對。
同一個 session 連續三輪的 header 長得一模一樣，並行請求還會在檔案裡交錯，
要把「這一筆 prompt」對到「這一筆回覆」與「這一筆閘門稽核」只能靠秒級時間戳去猜。

### 缺口 4：改寫／補生成的 follow-up 呼叫完全沒有 log

`LogPipeline._rewrite()`（`log_pipeline.py:118-123`）與 `_complete()`（`log_pipeline.py:125-131`）
會各自對模型發起額外呼叫，帶的是 `self.messages + [assistant 草稿] + 指令`。
這兩次呼叫的 prompt **沒有進 `prompts.log` 的任何地方**，只有結果統計進 `log_packer_audit.log`。

如果驗收時發現「某段回覆讀起來很怪」，那段有可能根本不是模型原生輸出、而是被 `_rewrite()`
換過的，目前無從追查。本次**不做**（決策見 D-4），列此存查。

---

## 六、決策紀錄

供後續稽核回溯用。以下為 2026-08-18 討論後定案。

### D-1：不採用 `prompts-m.log` / `prompts-d.log` 依內容拆檔

曾評估把「送出的完整 messages」與「LOG 本體資料」拆成兩個檔案，**否決**，三個理由：

1. **把最需要並排看的兩樣東西拆開。** 客戶目的是「判斷追問的回覆品質問題出在資料還是歷史」，
   這要求資料與歷史同框對照。拆檔後每看一筆都要跨檔案配對，而目前**沒有可配對的鍵**
   （見缺口 3），等於要先補 request id，成本比不拆更高。
2. **拆檔想解的問題已經過去了。** 分檔動機是保住 v7 逐行 diff，那是 DoD 第 1 條的一次性驗收，
   已完成；歷史對照則是 UAT 期間每天要用。何況本方案把歷史放在 `====` 分隔線**之前**，
   從 `[SYSTEM PROMPT]` 往下取就與現況逐字相同，diff 本來就不受影響。
3. **兩次寫入、兩種失敗模式。** `log_payload()` 現在整段包在 try/except 裡靜默吞例外
   （`packed_chat.py:60-64`），拆兩檔就可能只成功一半，留下對不到另一半的孤兒記錄。

### D-2：改採「按 session 拆檔」＋「補 REQ id」

實測 `docs/0816/prompts.log`：3 筆記錄、238 KB，單筆 **20,315 / 28,319 / 38,693 字元**，
每筆 350–600 行，其中受測者特質區塊每人約 180–200 行，是絕對主體；`[任務指令]` 只有十幾行。

由此得到兩個結論：

- **真正傷可讀性的不是「歷史和資料混在一起」**，是單筆 20–39K 字元、多個 session 在同一天的
  檔案裡交錯。所以要拆就拆 session，不拆內容。
- **歷史逐字入 log 的膨脹是可接受的。** 單則回覆約 1–2K 字元，吃滿 6 輪上限約 12–15K，
  對一筆 20–39K 的記錄估約 +40%，而且有 `MAX_HISTORY_TURNS` 當天花板、不是無上限成長。
  **因此逐字印，不做摘要或截斷。**（此點修正 8/18 稍早口頭評估中「檔案會快速膨脹」的說法，
  該說法高估了歷史相對於 payload 本體的佔比。）

  **上線後實測，這個 +40% 的估計本身也偏高。** 取 `logs/2026-08-18/prompts.log` 的四筆
  真實請求（同一 session 連續四輪）：

  | REQ | 歷史則數 | 歷史區塊 | LOG 本體 | 佔比 |
  |---|---|---|---|---|
  | `1bfc9b18` | 0 | 60 字元 | 49,675 字元 | +0.1% |
  | `bc4eefcd` | 2 | 3,272 字元 | 42,793 字元 | +7.6% |
  | `40888dba` | 4 | 4,843 字元 | 42,798 字元 | +11.3% |
  | `1bd1e35d` | 6 | 6,362 字元 | 42,713 字元 | +14.9% |

  真實請求的受測者資料比 0816 那批更大（本體 42–49K 而非 20–39K），而歷史是固定成本，
  所以佔比被稀釋。依此線性外推，吃滿 12 則約落在 +25%。結論不變，決策不需重審。

### D-3：`MAX_HISTORY_TURNS` 維持 6 輪

客戶印象中的「3 輪」與現況不符，經確認後**維持 6 輪（12 則）不變**，本次不調整。
若日後要改為 3 輪，改 `.env` 即可、不需動程式碼，但建議先用同一組對話做 3 與 6 的 A/B 比較。

### D-4：follow-up 呼叫的 log（缺口 4）本次不做

超出客戶本次提問範圍，且是唯一需要把 `session_id` 一路傳進 `LogPipeline` 建構子的介面改動，
需要自成一個驗證單元。列為後續項目，不納入本次 DoD。

---

## 七、開發規格

三個工作單元，依序完成，**前一個 Check 綠燈才動下一個**。

### A. 修正 `HISTORY_TURNS` 的語意

**問題**：欄位算的是則數卻叫 turns，驗收人員照字面讀會差兩倍。

**改動**：`BackEnd/api_v2/services/packed_chat.py:49-55`

```python
cap_turns = current_app.config.get('MAX_HISTORY_TURNS', 6)
history_msgs = max(0, len(pipeline.messages) - 2)
...
f"HISTORY_MSGS: {history_msgs} ({history_msgs // 2} turns, "
f"cap={cap_turns} turns/{cap_turns * 2} msgs)"
```

**輸出**：`HISTORY_MSGS: 4 (2 turns, cap=6 turns/12 msgs)`

**連帶**：`BackEnd/scripts/demo_prompt_log.py:237-238` 有一條斷言直接讀 `HISTORY_TURNS`
欄位名並檢查其遞增，必須同步改成 `HISTORY_MSGS`，否則該腳本會失敗。

**舊欄位名不保留。** 兩個名字並存比直接換掉更容易誤讀；改名寫進交付說明即可。

---

### B. 歷史入 log、按 session 拆檔、補 REQ id

三件事同屬一個單元，因為它們改的是同一個寫入路徑。

#### B-1　REQ id

每個 chat 請求產生一個 8 碼 id，寫進三個 log，作為跨檔對照鍵。

**產生點**：`routes/chat.py`，在 `session_store.add_message(session_id, 'user', query)`
（第 461 行）**之前**：

```python
req_id = uuid.uuid4().hex[:8]
```

**寫入點（共四處）**：

| 檔案 | 位置 | 改法 |
|---|---|---|
| `conversations.log` | `routes/chat.py:462` `[USER]` 行 | header 加 `REQ: {req_id}` |
| `conversations.log` | `routes/chat.py:568-574` `[AI]` 行 | 同上 |
| `prompts.log` | `packed_chat.log_payload()` header | 置於 `SESSION` **之前**，成為每筆首欄 |
| `log_packer_audit.log` | `packed_chat.PackedStream.finish()` | `audit['req_id'] = req_id`，需在 `packed_chat.py:109` 的 `json.dumps` 之前設定 |

**傳遞方式：顯式參數，不用 contextvars。**
Flask 的串流 generator 在請求情境邊界上的執行時機不保證，contextvars 在此不可靠；
而顯式傳遞的觸點很少，改動可視。簽章調整：

- `try_packed_stream(rag_service, module_id, query, mode, trait_reports, candidates_info, session_id, req_id)`
  → 往下傳給 `log_payload()` 與 `PackedStream()`
- 舊路徑：`generate_response(..., req_id=None)`（`rag_engine.py:161-163`）
  → `_call_llm(sys_prompt, query, uc_id, session_id, req_id)`（呼叫點 `rag_engine.py:390` 與 `435`）
  → `_log_prompt(session_id, uc_id, sys_prompt, user_query, history, req_id)`

一律給預設值 `None`，既有呼叫端不會因為漏傳而炸掉；`None` 時輸出 `REQ: -`。

#### B-2　歷史區塊

放在 header 之後、`====` 分隔線與 LOG 本體**之前**。這樣從 `[SYSTEM PROMPT]` 往下取的字串
與改造前逐字相同，v7 逐行 diff 不受影響——這是 B-2 的硬約束，由 D-4 驗證項守住。

新增於 `packed_chat.py`：

```python
# 逐字寫入，不截斷。截斷會讓「追問回覆品質是資料問題還是歷史問題」變得無法判斷，
# 而那正是這個區塊存在的理由。膨脹幅度已量測（見文件 D-2），有 MAX_HISTORY_TURNS 當天花板。
def history_text(history):
    if not history:
        return '[CONVERSATION HISTORY]\n(none -- first turn of this session)\n'
    lines = [f'[CONVERSATION HISTORY] oldest first, verbatim, {len(history)} messages']
    for i, m in enumerate(history, 1):
        lines.append(f'--- #{i} {m["role"].upper()} ---')
        lines.append(m['content'])
    return '\n'.join(lines) + '\n'
```

`LogPipeline` 目前只把 history 併進 `self.messages`，`log_payload()` 拿不到，
故 `log_pipeline.py:111` 前多存一份：

```python
self.history = list(history or [])
self.messages = self.log.to_messages(history)
```

**舊路徑（缺口 2）一併修**：把 `_log_prompt()` 從 `_call_llm()` 第一行
（`rag_engine.py:529`）移到 `history_messages = self.load_history(session_id)`
（第 533 行）**之後**，多傳 `history` 參數，沿用同一個 `history_text()`。
兩條路徑的 log 格式就一致了。

#### B-3　按 session 拆檔

**路徑**：`logs/<YYYY-MM-DD>/prompts/<session_id>.log`
**彙總檔 `logs/<YYYY-MM-DD>/prompts.log` 照舊保留**，供「今天總共跑了哪些請求」的掃視需求。

**開關**：`.env` 新增 `PROMPT_LOG_PER_SESSION=false`（預設關），
於 `settings.py` 讀取；UAT 期間設 `true`。上線前需搭配清理策略再開啟——
一個 session 一個檔，檔數無上限。

**實作方式：不走 logging handler。**
`utils/logger.py:76-85` 的註解已經記載過 handler 以 name 快取所造成的 formatter 靜默覆蓋問題；
動態檔名路由要在 handler 層做會更糾結。改為在 `utils/logger.py` 新增一個集中寫入函式：

```python
_SAFE_SESSION_RE = re.compile(r'^[A-Za-z0-9_-]{1,64}$')

def write_prompt_record(session_id, text):
    """寫入 prompts.log；PROMPT_LOG_PER_SESSION 開啟時另寫一份 per-session 檔。

    彙總檔先寫。per-session 的失敗被單獨吞掉，不會連累已經落地的彙總記錄——
    這正是本方案不採 D-1 雙檔拆法的理由之一：只有一個失敗邊界會遺失記錄。
    """
    get_prompt_logger().info(text)
    if not current_app.config.get('PROMPT_LOG_PER_SESSION'):
        return
    try:
        # session_id 直接進路徑，未經檢核的值可以做出目錄跳脫。
        safe = session_id if _SAFE_SESSION_RE.match(str(session_id or '')) else 'unknown'
        ...  # open(path, 'a', encoding='utf-8') 追加同一段 text 與時間戳封裝
    except Exception as e:
        rag_logger.warning(f"[PromptLog] per-session write failed for {session_id}: {e}")
```

`packed_chat.log_payload()` 與 `rag_engine._log_prompt()` 都改呼叫這支，
每個請求只寫一次、只有一個 try/except 邊界。

#### B-4　產出範例

```
REQ: 3f9a7c21 | SESSION: af4d3e45 | USE_CASE: log_packer | MODULE: M03 | QUESTION: 12 |
TYPE: quick | AUDIENCE: multi | RESPONDENTS: 2 | HISTORY_MSGS: 4 (2 turns, cap=6 turns/12 msgs)
[CONVERSATION HISTORY] oldest first, verbatim, 4 messages
--- #1 USER ---
幫我比較這兩位的抗壓性
--- #2 ASSISTANT ---
（AI 上一輪的完整回覆原文，逐字）
--- #3 USER ---
那溝通風格呢
--- #4 ASSISTANT ---
（AI 上一輪的完整回覆原文，逐字）
============================================================
[SYSTEM PROMPT]
...
```

---

### D. 驗證

比照現有 `BackEnd/scripts/verify_*.py` 的做法，新增
`BackEnd/scripts/verify_prompt_log_history.py`，用假的 `stream_fn` 離線跑，不需網路與真實模型。

| # | 驗證項 | 判定 |
|---|---|---|
| V-1 | 第 1 輪 log 出現 `(none -- first turn of this session)` | 字串比對 |
| V-2 | 第 2 輪出現 2 則、第 3 輪出現 4 則，且**逐字等於**前幾輪的 user query 與 assistant 回覆 | 逐字比對 |
| V-3 | `HISTORY_MSGS` 的數字與區塊內實際列出的則數一致 | 數字比對 |
| V-4 | **從 `[SYSTEM PROMPT]` 起算到檔尾的字串，與改造前的輸出完全相同** | 逐字 diff（保證 v7 比對不受影響） |
| V-5 | `MAX_HISTORY_TURNS` 設為 2 時跑第 5 輪，只剩最後 4 則且丟掉的是最舊的 | 逐字比對 |
| V-6 | 同一請求的 `REQ` 值在 `prompts.log`、`conversations.log`、`log_packer_audit.log` 三處相同 | 前兩者讀檔比對；`conversations.log` 見下方註 |
| V-7 | `PROMPT_LOG_PER_SESSION=true` 時 per-session 檔內容與彙總檔中該筆逐字相同 | 逐字比對 |
| V-8 | `PROMPT_LOG_PER_SESSION=false` 時不產生 `prompts/` 目錄 | 路徑不存在 |
| V-9 | session_id 帶 `../` 等字元時落到 `unknown.log`，不寫出目錄之外 | 路徑檢查 |
| V-10 | per-session 寫入失敗時彙總檔該筆仍完整落地，**且失敗確實發生** | 注入失敗後檢查兩件事 |
| V-11 | `demo_prompt_log.py` 全綠 | 以子行程執行既有腳本 |

實作時與上表有兩處出入，記錄如下：

- **V-6 的 `conversations.log` 無法離線驗證。** 那兩行是由 `routes/chat.py` 的串流產生器寫出的，
  要跑到它得有一個活的 request 與資料庫連線，與「離線、不呼叫模型」的前提衝突。
  改為在原始碼層面斷言 `REQ: {req_id}` 至少出現在三個呼叫點（`[USER]`／`[AI]`／`[LLM ERROR]`），
  這擋得住日後有人把欄位改掉；真正的三檔對照留在第八節第 6 條的人工複核。
- **V-10 多了一條前置斷言。** 原本只檢查「彙總檔仍完整」，但彙總檔本來就寫得成——
  注入失效時這條會空過、證明不了任何事。現在先確認 per-session 目錄確實沒被建出來，
  才去看彙總檔。失敗注入的手法是把目錄位置換成一個同名檔案，讓 `os.makedirs` 真的拋例外，
  走的是產品程式碼自己的 except 分支，而不是測試替身模擬出來的分支。

---

## 八、驗收基準（DoD）

以下全數成立才算達標。第 1–3、8 條為自動化，可在本機重跑；第 4–7 條需要真實後端，
留給 UAT 人工複核。

1. [完成] 第七節 A、B 兩單元的程式改動完成，且**分屬兩個可獨立回溯的提交**
   （A：`614b09a`；B：`c6cc0d5`）。
2. [完成] `verify_prompt_log_history.py` 的 V-1 至 V-11 全數通過，輸出可貼進驗收報告。
   連續執行兩次結果相同（截斷測試會改動 app config，重跑不受前次殘留影響）。
3. [完成] `demo_prompt_log.py` 通過（V-11），其中 `HISTORY_TURNS` 斷言已更新為 `HISTORY_MSGS`，
   並補了兩條檢查表頭換算自洽的斷言。
4. [完成] 以真實後端跑一段 **至少 7 輪** 的對話（超過 6 輪上限），取 `prompts.log` 檢查：
   第 7 輪的歷史區塊為 12 則、第 1 輪的問答已被丟棄、`HISTORY_MSGS: 12 (6 turns, cap=6 turns/12 msgs)`。
   8/18 實測 session `1a87194f` 跑滿 8 輪，見第九節。
5. [完成] 同一段對話取 `PROMPT_LOG_PER_SESSION=1` 產生的 per-session 檔，
   確認 8 輪依序落在同一個檔內、無其他 session 交錯。8/18 實測通過。
6. [完成] 取任一筆記錄的 `REQ` 值，能在三份 log 中各找到對應記錄。
   8/18 實測 12/12 通過，見第九節。
7. [部分完成] 拿改造後任一筆記錄的 `[SYSTEM PROMPT]` 以下部分，與 v7 範例逐行 diff，
   結果與改造前一致。（V-4 已在離線層級證明這段等於 `to_log_text()` 逐位元組相同；
   8/18 實測 12 筆記錄的 `====` 之後結構完整，但與客戶三份 v7 範例的逐行 diff 尚未執行。）
8. [完成] `.env.example` 補上 `PROMPT_LOG_PER_SESSION=0` 並註明用途；
   `.env` 於 8/18 設為 `1` 供 UAT 使用。

**不在本次範圍**：缺口 4（follow-up 呼叫的 log），依第六節 D-4 決策順延。

---

## 九、上線後實測紀錄（2026-08-18）

資料來源：`BackEnd/api_v2/logs/2026-08-18/`，共 12 筆真實請求，分屬兩個 session：

- `87a6fe0e-…`：4 輪，歷史則數 0 → 2 → 4 → 6（`PROMPT_LOG_PER_SESSION` 開啟前）
- `1a87194f-…`：8 輪，歷史則數 0 → 2 → 4 → 6 → 8 → 10 → 12 → **12**（開啟後）

| 驗證項 | 結果 |
|---|---|
| 每筆記錄都有 `[CONVERSATION HISTORY]` 區塊，位於表頭之後、`====` 之前 | 12/12 通過 |
| `HISTORY_MSGS` 數字與區塊實際列出的 `--- #n ---` 則數相符 | 12/12 通過 |
| role 序列為 `USER`／`ASSISTANT` 嚴格交替（提問與回覆都帶） | 12/12 通過 |
| 歷史內容與 `conversations.log` 的實際回覆**逐字相同** | 10/10 通過 |
| `REQ` 值在 `prompts.log`、`conversations.log` 的 `[USER]` 與 `[AI]`、`log_packer_audit.log` 四處齊備 | 12/12 通過 |
| `====` 之後緊接 `[SYSTEM PROMPT]`，且 `[任務指令]` 俱在 | 12/12 通過 |

### DoD 第 4 條：上限與截斷（session `1a87194f`）

第 7 輪達到 12 則後，第 8 輪**停在 12 則不再成長**，且視窗整體往前滑一輪：

```
第 7 輪視窗：團隊合作的互補與摩擦 / 各別適合的工作類型 / 這兩位會不會與同事起衝突 /
             誰比較適合從事市場行銷規劃 / 誰比較合適當財務 / 列出這兩位具體合適的工作
第 8 輪視窗：各別適合的工作類型 / 這兩位會不會與同事起衝突 / 誰比較適合從事市場行銷規劃 /
             誰比較合適當財務 / 列出這兩位具體合適的工作 / 公司要推出海鮮販售直播服務
```

第 1 輪的提問「團隊合作的互補與摩擦」確認已不在第 8 輪的視窗內——丟的是最舊的，
與 `rag_engine.py:519` 的 `conv[-(max_turns * 2):]` 行為一致。

### DoD 第 5 條：per-session 檔

`logs/2026-08-18/prompts/1a87194f-….log` 內含該 session 全部 8 筆記錄，
順序與 `prompts.log` 一致，且檔內只出現這一個 session id，
另一個 session `87a6fe0e-…` 完全不在此檔中。

### 膨脹實測（更新第六節 D-2）

吃滿 12 則時：歷史 11,737 字元 / LOG 本體 46,741 字元 = **+25.1%**，
與第六節依 6 則資料外推的「約 +25%」一致。

**客戶原提問對應到的結論**：歷史確實帶入且可在 log 上直接讀到；提問與回覆兩邊都帶；
內容為原文逐字，無摘要或截斷；超過 6 輪上限時丟最舊的。四點皆有真實資料佐證。

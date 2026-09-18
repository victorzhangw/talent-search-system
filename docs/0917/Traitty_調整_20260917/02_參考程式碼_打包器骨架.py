# -*- coding: utf-8 -*-
"""
Traitty LOG 打包器 —— 參考實作骨架（reference skeleton）
=====================================================
給外包實作團隊的「可讀、可對照 b_打包規則 的起點程式」。

【本檔已完整實作（確定性邏輯，可直接用）】
    - b §2 特質分流（全塊區／索引區）
    - b §3 交互選列（匡列型兩步／全人型三步，無題意上限）
    - b §5 組裝順序
    - b §6 交付前單元檢查
    - b §7 出口掃描器建置（per-request 動態縮小 + 9 類硬樣式 + everyday 白名單）
    - b §8 輸出完整性檢查

【你要接的 I/O，程式中標 `TODO(外包)`】
    - 從 `0722 02_08 V6.2 spec_.xlsx` 讀 02 四欄（load_trait_columns）與 08 交互（load_interactions）
    - 實際呼叫 LLM（call_llm）
    - 出口不過時的重生成迴圈（run_with_exit_guard）

實作以 `b_打包規則` 為準；本檔是骨架、不是唯一寫法。設計緣由見 `01_設計總說明`，邊界與驗收見 `00_外包交接說明`。
環境：Python 3.9+；讀 xlsx 建議 openpyxl。
"""
from __future__ import annotations
import json, re, os
from dataclasses import dataclass, field
from typing import Optional

PKG = os.path.dirname(os.path.abspath(__file__))     # 交付包目錄
INSTRUMENTS = ("ANI", "CIA", "SPA", "CSR")


# ══════════════════════════════════════════════════════════════════
# 資料模型
# ══════════════════════════════════════════════════════════════════
@dataclass
class Respondent:
    name: str
    id: str
    tests: list           # ["ANI","CIA",...]  已完成的測驗
    scores: dict          # {trait_id: "A"/"B"/"C"}  只含已測特質

@dataclass(frozen=True)
class TraitCols:          # 從 spec 02 分頁讀（TODO 外包）
    行為面向: str
    管理重點: str
    可用於: str           # 已含「①…②…③…」前綴的原文
    禁止: str

@dataclass
class Interaction:        # 從 spec 08 分頁讀（TODO 外包）
    a_id: str; a_band: str
    b_id: str; b_band: str
    text: str             # 敘事本文；載入時已跑 regex_pack 剝除開頭配對句與殘留代號
    row: int              # 08 原始列序（供鏡像去重與選列排序）
    def ends(self):  return [(self.a_id, self.a_band), (self.b_id, self.b_band)]
    def ids(self):   return {self.a_id, self.b_id}


# ══════════════════════════════════════════════════════════════════
# 資料載入（JSON 直讀；xlsx 兩個 adapter 待外包接）
# ══════════════════════════════════════════════════════════════════
class DataStore:
    def __init__(self, pkg=PKG):
        qi = json.load(open(os.path.join(pkg, "question_injection_table_v9.json"), encoding="utf-8"))
        self.questions      = {q["title"]: q for q in qi["questions"]}
        self.calibration    = set(qi["calibration_traits"])                       # {CIA_33,ANI_23,SPA_12}
        self.risk_endpoints = {(t, b) for t, b in qi["risk_endpoints"]["adopted"]}# 71 對 (id,band)
        self.free_contract  = qi["free_form_input_contract"]

        tr = json.load(open(os.path.join(pkg, "traits_113_v6_2.json"), encoding="utf-8"))
        self.trait_name  = {t["trait_id"]: t["name_zh"] for t in tr["traits"]}
        self.trait_label = {(t["trait_id"], b): lbl
                            for t in tr["traits"] for b, lbl in t["bands"].items()}

        rp = json.load(open(os.path.join(pkg, "regex_pack_v6_2.json"), encoding="utf-8"))
        self.strip_rules = [(re.compile(r["pattern"]), r["replace"]) for r in rp["rules"]]

        self.scanner_cfg = json.load(open(os.path.join(pkg, "exit_scanner_wordlist_v6_2.json"), encoding="utf-8"))

        # a 文件第一部分（System 靜態全文）；外包從 a_LOG完成版模板 抽第一部分為常數
        self.system_prompt = load_system_prompt(pkg)                              # TODO(外包)

        # 內容正本（spec xlsx）→ 兩個 adapter
        self.trait_cols   = load_trait_columns(pkg)                               # TODO(外包): {trait_id: TraitCols}
        self.interactions = load_interactions(pkg, self.strip_rules)             # TODO(外包): list[Interaction]

    def strip(self, text: str) -> str:
        for rx, rep in self.strip_rules:
            text = rx.sub(rep, text)
        return text


def load_system_prompt(pkg) -> str:
    """TODO(外包): 讀 a_LOG完成版模板_v2_*.md 的『第一部分：System 靜態規範』全文，原樣回傳。"""
    raise NotImplementedError("接 a 文件 System 全文")

def load_trait_columns(pkg) -> dict:
    """TODO(外包): 從 spec xlsx『02』分頁讀每個 trait_id 的四欄，回傳 {trait_id: TraitCols}。
    四欄＝行為面向／管理重點／可用於／禁止（欄名以正本實際表頭為準）。"""
    raise NotImplementedError("接 spec 02 四欄")

def load_interactions(pkg, strip_rules) -> list:
    """TODO(外包): 從 spec xlsx『08』分頁讀每一列交互，回傳 list[Interaction]。
    每列需解析出兩端 (id, band) 與敘事本文；載入時對本文套 strip_rules（regex_pack）剝除開頭配對句與殘留代號。
    row＝該列在 08 的原始序（0 起算，供去重與選列排序）。"""
    raise NotImplementedError("接 spec 08 交互列")


# ── 輸入 B：從 Talent Chat API v2 取人選評鑑結果（見 03_API對接說明）──────
def build_respondent_from_api_report(candidate_id: str, report_data: dict) -> "Respondent":
    """report_data ＝ GET /api/v2/candidates/{id}/report 的 data 欄。
    API 的 Trait{trait_id,name,score,band} 直接對應本程式輸入 B：
        - band 已由伺服器算好，直接當 scores 的值（值域待確認 A/B/C，見 03 §5）
        - tests 由 trait_id 前綴（ANI/CIA/SPA/CSR）推導（API 未直接給）
    多人情境改用 POST /api/v2/reports/batch，逐份 AssessmentReport 走相同映射。"""
    traits = report_data["traits"]
    scores = {t["trait_id"]: t["band"] for t in traits}
    tests  = sorted({t["trait_id"].split("_")[0] for t in traits})
    return Respondent(name=report_data.get("candidate_name", candidate_id),
                      id=candidate_id, tests=tests, scores=scores)


# ══════════════════════════════════════════════════════════════════
# b §2  特質分流
# ══════════════════════════════════════════════════════════════════
def split_traits(resp: Respondent, question: Optional[dict], store: DataStore):
    """回傳 (P, S, R, full_ids, index_ids, band_of)。
    P=受測者已測特質(id,band)；S=匡列集合；R=命中風險端點的 id；full=全塊；index=索引。"""
    band_of = dict(resp.scores)                                  # {id: band}，只含已測
    P = {(tid, band_of[tid]) for tid in band_of}

    if question is None or question["type"] == "whole_person":   # 自由提問或全人型 → S=全部
        S = set(band_of)
    else:                                                        # 匡列型：只取受測測驗欄位
        S = set()
        for inst in resp.tests:
            S |= set(question["scoped_traits"].get(inst, []))
        S &= set(band_of)                                       # 只保留受測者實際有的特質

    R = {tid for (tid, band) in P if (tid, band) in store.risk_endpoints}
    full  = {tid for tid in band_of if tid in S}                 # 註：風險/校準特質不因此升全塊（b §2 註）
    index = {tid for tid in band_of if tid not in S}
    return P, S, R, full, index, band_of


# ══════════════════════════════════════════════════════════════════
# b §3  交互選列
# ══════════════════════════════════════════════════════════════════
def candidate_interactions(P, store: DataStore):
    """兩端 (id,band) 都 ∈ P 的列；鏡像去重（同一無序配對取列序在前者）；依列序回傳。"""
    Pset = set(P)
    cands = [it for it in store.interactions
             if (it.a_id, it.a_band) in Pset and (it.b_id, it.b_band) in Pset]
    seen = {}
    for it in sorted(cands, key=lambda x: x.row):
        key = frozenset(it.ends())
        seen.setdefault(key, it)
    return sorted(seen.values(), key=lambda x: x.row)

def select_scoped(cands, S, R, store: DataStore):
    """匡列型兩步 → (本題相關, 作答校準與風險提示)。"""
    trigger = S | store.calibration | R                          # 一端 id ∈ 此集合才入選
    picked  = [it for it in cands if it.ids() & trigger]
    related    = [it for it in picked if it.ids() & S]           # 本題相關：至少一端 ∈ S
    calib_risk = [it for it in picked if not (it.ids() & S)]     # 僅因校準/風險入選
    return related, calib_risk

def select_whole(cands, R, store: DataStore):
    """全人型：無題意過濾、無上限，候選**全注入**，僅分兩個子區塊 → (作答校準與風險提示, 其他參考)。
    ① 保證：觸及 (校準 ∪ R) 的列 → 「作答校準與風險提示」（排前，讀的顯著性高）
    ② 其餘：全部 → 「其他參考」（子區塊內按列序）
    設計（2026-07-28 用戶裁定）：與匡列型同一原則「相關的全注入、不做任意砍量」，只差匡列型多一道題意過濾。
    全注入自然覆蓋每個有候選的特質，故不需覆蓋步驟；不設 fill、不設 hardcap——依 System S2§15 由 LLM 自濾。"""
    trigger = store.calibration | R
    guaranteed = [it for it in cands if it.ids() & trigger]
    other      = [it for it in cands if not (it.ids() & trigger)]
    return guaranteed, other


# ══════════════════════════════════════════════════════════════════
# b §5  組裝（render + assemble）
# ══════════════════════════════════════════════════════════════════
def _prefix(text: str, name: str) -> str:
    """欄名正規化：02 正本的 ai_do/ai_dont 儲存格**有些已自帶**「可用於：」「禁止：」前綴
    （ANI 69/69、CIA 108/108、CSR 108/108 自帶；SPA 僅 1/54），直接再加一次會輸出
    「可用於：可用於：…」。故只在缺前綴時補上。（資料面根治＝正本補齊 SPA 53 列前綴）"""
    t = (text or "").strip()
    return t if t.startswith(name) else f"{name}：{t}"

def render_full_block(tid, band, store: DataStore):
    c = store.trait_cols[tid]; lbl = store.trait_label[(tid, band)]
    return (f"[特質 | {tid}_{band} | {lbl}]\n"
            f"{_prefix(c.行為面向, '行為面向')}\n{_prefix(c.管理重點, '管理重點')}\n"
            f"{_prefix(c.可用於, '可用於')}\n{_prefix(c.禁止, '禁止')}")

def render_index_line(tid, band, store: DataStore):
    c = store.trait_cols[tid]; lbl = store.trait_label[(tid, band)]
    return f"- {tid}_{band}｜{store.trait_name[tid]}｜{lbl}：{c.行為面向}"

def render_interaction(it: Interaction, store: DataStore):
    la = store.trait_label[(it.a_id, it.a_band)]; lb = store.trait_label[(it.b_id, it.b_band)]
    return (f"[交互 | {it.a_id}_{it.a_band} × {it.b_id}_{it.b_band} | {la} × {lb}]\n{it.text}")

def build_respondent_block(resp, question, store: DataStore):
    """組一位受測者的『### 區塊』（不含 SYSTEM / 任務指令）。回傳 (文字, 稽核用 dict)。"""
    P, S, R, full, index, band_of = split_traits(resp, question, store)
    whole = question is None or question["type"] == "whole_person"
    parts = [f"### [受測者 | {resp.name} | {resp.id}]"]

    # 全塊區
    hdr = "#### 判讀主體特質（全人型＝全部特質）" if whole else "#### 判讀主體特質"
    parts.append(hdr)
    parts += [render_full_block(t, band_of[t], store) for t in sorted(full)]

    # 索引區（全人型無索引）；索引行彼此連續，故併成單一區塊
    if index and not whole:
        parts.append("#### 其他特質索引（僅供關聯參考，非本題判讀主體）")
        parts.append("\n".join(render_index_line(t, band_of[t], store) for t in sorted(index)))

    # 交互選列
    cands = candidate_interactions(P, store)
    if whole:
        guaranteed, other = select_whole(cands, R, store)     # 全注入，無未注入、無截斷
        if guaranteed:
            parts.append("#### 交互作用——作答校準與風險提示")
            parts += [render_interaction(it, store) for it in guaranteed]
        if other:
            parts.append("#### 交互作用——其他參考")
            parts += [render_interaction(it, store) for it in other]
    else:
        related, calib_risk = select_scoped(cands, S, R, store)
        if related:
            parts.append("#### 交互作用——本題相關")
            parts += [render_interaction(it, store) for it in related]
        if calib_risk:
            parts.append("#### 交互作用——作答校準與風險提示")
            parts += [render_interaction(it, store) for it in calib_risk]
        if 0 < len(related) < 5:
            parts.append("（本題相關交互較少，判讀以特質區塊為主）")

    injected = (guaranteed + other) if whole else (related + calib_risk)
    audit = dict(P=P, S=S, R=R, full=full, index=index, interactions=injected,
                 related=(None if whole else related))
    return "\n\n".join(parts), audit

def check_audience(respondents, question):
    """b §1.1 前置驗證：人數與該題 audience 必須相符，不符即拒絕請求（不組裝）。
    否則 single_only 題碰到多人請求會把佔位字串「僅適用單人」當任務指令送出。"""
    if question is None: return                      # 自由提問無此限制
    multi = len(respondents) > 1
    aud = question["audience"]
    if multi and aud == "single_only":
        raise ValueError(f"「{question['title']}」僅支援單人，收到 {len(respondents)} 位受測者")
    if not multi and aud == "multi_only":
        raise ValueError(f"「{question['title']}」僅支援多人，收到 1 位受測者")

def assemble_log(respondents, question, store: DataStore):
    """b §5 完整組裝。respondents=list[Respondent]（單人給 1 個）。"""
    check_audience(respondents, question)
    multi = len(respondents) > 1
    blocks, audits = [], []
    for r in respondents:
        blk, au = build_respondent_block(r, question, store); blocks.append(blk); audits.append(au)

    if question is None:            # 自由提問：任務指令＝user_query 原文（由呼叫端帶入）
        task = "[任務指令]\n{user_query}"
    else:
        task = "[任務指令]\n" + (question["instruction_multi"] if multi else question["instruction_single"])

    log = ("[SYSTEM PROMPT]\n" + store.system_prompt + "\n\n---\n\n"
           "## 【輸入數據】\n\n" + "\n\n".join(blocks) + "\n\n---\n\n" + task)
    return log, audits


# ══════════════════════════════════════════════════════════════════
# b §6  交付前單元檢查（每次組裝跑；回傳問題清單，空＝過）
# ══════════════════════════════════════════════════════════════════
def unit_check(log_text, respondents, question, store: DataStore, audits):
    """b §6 四項全做。回傳問題清單，空＝過。"""
    problems = []
    for resp, au in zip(respondents, audits):
        # 1 全塊數 ＝ |S∩P|；索引行數 ＝ |P| - 全塊數
        if len(au["full"]) != len(au["S"] & {t for t, _ in au["P"]}):
            problems.append(f"{resp.name}: 全塊數 != |S∩P|")
        if len(au["index"]) != len(au["P"]) - len(au["full"]):
            problems.append(f"{resp.name}: 索引行數 != |P| - 全塊數")
        # 2 每個交互標頭的兩端 ID 都出現在全塊區或索引區
        present = au["full"] | au["index"]
        for it in au.get("interactions", []):
            missing = it.ids() - present
            if missing:
                problems.append(f"{resp.name}: 交互兩端未出現於特質區塊：{sorted(missing)}")
        # 4 子區塊歸屬（匡列型「本題相關」至少一端 ∈ S）
        if au["related"] is not None:
            for it in au["related"]:
                if not (it.ids() & au["S"]):
                    problems.append(f"{resp.name}: 本題相關列兩端皆不屬 S：{it.ids()}")
    # 3 無結構殘留。註：strip_rules 只適用『敘事本文』——標頭的 XXX_nn ID 是合法內部標記
    #   且必須保留（00 DoD 5），故本項僅檢查字面符號，不對全文套 strip_rules。
    for bad in ("['", "()", "（）"):
        if bad in log_text:
            problems.append(f"殘留結構符號：{bad}")
    return problems


# ══════════════════════════════════════════════════════════════════
# b §7  出口掃描器（per-request 動態縮小 + 9 硬樣式 + everyday 白名單）
# ══════════════════════════════════════════════════════════════════
def build_exit_scanner(store: DataStore, injected_names, injected_labels):
    """回傳 scan(answer)->list[hit]。只掃本次實際注入的名稱/標籤 + 靜態硬樣式。"""
    hard = [(h["id"], re.compile(h["pattern"])) for h in store.scanner_cfg["hard_patterns"]]
    everyday = load_everyday_whitelist(store.scanner_cfg)          # 只擋構念式用法的白名單詞
    # 名稱/標籤：everyday 詞需後接程度/分數判定才算洩漏；其餘直接擋
    guard = r"(?=[偏程度分高低強弱]|傾向|指標|區間)"
    name_pats, label_pats = [], []
    for w in set(injected_names):
        pat = re.escape(w) + (guard if w in everyday else "")
        name_pats.append((w, re.compile(pat)))
    for w in set(injected_labels):
        pat = re.escape(w) + (guard if w in everyday else "")
        label_pats.append((w, re.compile(pat)))

    def scan(answer: str):
        hits = []
        for hid, rx in hard:
            if rx.search(answer): hits.append(("hard:" + hid, rx.pattern))
        for w, rx in name_pats:
            if rx.search(answer): hits.append(("name", w))
        for w, rx in label_pats:
            if rx.search(answer): hits.append(("label", w))
        return hits
    return scan

def load_everyday_whitelist(cfg) -> set:
    """取 everyday_words / everyday_labels（只擋構念式用法的日常詞）。
    ⚠ 這兩個鍵是**巢狀**的，不在頂層：
        trait_names_blocklist.everyday_words  （20 詞，如「信任」「同理心」）
        band_labels_blocklist.everyday_labels （4 詞）
    取錯路徑會得到空集合 → 84 個特質名與 266 個標籤全部硬攔 →「展現韌性」這類
    日常語用被判洩漏、每次重生落人工。"""
    out = set()
    for parent, child in (("trait_names_blocklist", "everyday_words"),
                          ("band_labels_blocklist", "everyday_labels")):
        node = cfg.get(parent) or {}
        v = node.get(child) if isinstance(node, dict) else None
        if isinstance(v, list): out |= set(v)
        v2 = cfg.get(child)                      # 容錯：若日後改放頂層也能取到
        if isinstance(v2, list): out |= set(v2)
    if not out:
        raise ValueError("everyday 白名單為空——詞表結構可能已變更，請檢查路徑（見本函式註解）")
    return out


# ══════════════════════════════════════════════════════════════════
# b §8  輸出完整性檢查（出口掃描器旁掛）
# ══════════════════════════════════════════════════════════════════
CALIB_EVIDENCE_WORDS = ("佐證", "行為事例", "工作樣本", "不以單次")

def log_skip(msg: str):
    """略過某項檢查時的記錄（b §8「不可靜默跳過」）。外包改接自家 logger。"""
    print("[completeness:SKIP]", msg)

def completeness_check(answer, respondents, question, store: DataStore):
    problems = []
    if question is None:                               # 自由提問：≤1000 字
        if len(answer) > 1000:
            problems.append(f"自由提問回答 {len(answer)} 字 > 1000")
    else:                                              # 題庫題：期望段落子集寬鬆判定
        expected = question.get("expected_sections") or []
        if not expected:
            # 空值＝該題指令未定義固定段落標題（b §8）。略過但必須 log，不可靜默通過。
            log_skip(f"「{question['title']}」未做段落齊全檢查"
                     f"（原因：{question.get('expected_sections_note', '指令未定義固定段落標題')}）")
        for sec in expected:
            if sec not in answer:
                problems.append(f"缺段落：{sec}")
        if len(respondents) > 1:                       # 多人題：每位姓名各成段
            for r in respondents:
                if r.name not in answer:
                    problems.append(f"多人題缺受測者段落：{r.name}")
    # 共同：受測者含社會期望反應 A 段 → 回答須含佐證措辭
    has_calib_A = any(r.scores.get(t) == "A" for r in respondents for t in store.calibration)
    if has_calib_A and not any(w in answer for w in CALIB_EVIDENCE_WORDS):
        problems.append("含社會期望反應 A 段但回答缺佐證類措辭")
    return problems


# ══════════════════════════════════════════════════════════════════
# 出口守衛：呼叫 LLM → 掃描 → 不過帶原因重生一次（上限 1）
# ══════════════════════════════════════════════════════════════════
def call_llm(log_text: str) -> str:
    """TODO(外包): 把 log_text 送給 runtime LLM，回傳其回答文字。"""
    raise NotImplementedError("接 LLM 呼叫")

def run_with_exit_guard(log_text, scan, respondents, question, store):
    answer = call_llm(log_text)
    hits = scan(answer); miss = completeness_check(answer, respondents, question, store)
    if hits or miss:                                   # 帶『缺了什麼』重生一次
        reason = f"（重生原因：洩漏={hits}；缺漏={miss}）"
        answer = call_llm(log_text + "\n\n[重生要求] " + reason)
        hits = scan(answer); miss = completeness_check(answer, respondents, question, store)
        if hits or miss:
            return answer, {"status": "manual_review", "hits": hits, "miss": miss}
    return answer, {"status": "ok"}


# ══════════════════════════════════════════════════════════════════
# 端到端範例（把上面串起來）
# ══════════════════════════════════════════════════════════════════
def run(request: dict, store: DataStore):
    """request schema 見 b §1.1。回傳最終 answer 與稽核資訊。"""
    resp_dicts = request.get("respondents") or [request["respondent"]]
    respondents = [Respondent(**r) for r in resp_dicts]
    if request["mode"] == "free":
        question = None
    else:
        title = request["question_id"]                 # 這裡以題目標題當 id；外包可改用真正 id 欄
        question = store.questions[title]

    log_text, audits = assemble_log(respondents, question, store)
    if question is None:                               # 自由提問把 user_query 代進任務指令
        log_text = log_text.replace("{user_query}", request["user_query"])

    problems = unit_check(log_text, respondents, question, store, audits)
    if problems:
        raise RuntimeError(f"單元檢查未過（b §6）：{problems}")

    # per-request 動態掃描器：蒐集本次注入的名稱與標籤
    names  = {store.trait_name[t] for au in audits for t, _ in au["P"]}
    labels = {store.trait_label[(t, b)] for au in audits for t, b in au["P"]}
    scan = build_exit_scanner(store, names, labels)

    answer, status = run_with_exit_guard(log_text, scan, respondents, question, store)
    return {"log": log_text, "answer": answer, "status": status}


if __name__ == "__main__":
    # 示意：實跑需先補三個 TODO(外包) adapter
    store = DataStore()
    demo = {
        "respondent": {"name": "王智弘", "id": "RESP_R2",
                       "tests": ["CIA"], "scores": {"CIA_16": "A", "CIA_18": "A", "CIA_05": "B"}},
        "mode": "quick",
        "question_id": "如何面對困難、壓力、挑戰",
    }
    print(run(demo, store)["log"])

"""Adapter that lets the chat route drive the LOG packer without changing its stream loop.

The route's streaming loop reads OpenAI-shaped chunks (`chunk.choices[0].delta.content`),
so this wraps the packer's cleared segments in that shape. One gated segment arrives as
one chunk -- the typewriter effect becomes a client-side replay of verified text, which is
the point of the segment gate: nothing reaches the browser until it has been scanned.

`packed_stream()` 服務不了的請求會拋 `PackerRefused`，不再回 None。

這是 U7（決策 D2）之後的語意改變。以前回 None 是「切換到舊路徑」的訊號：呼叫端會安靜地
落到模組 prompt 那條路，而那條路沒有分段閘門、沒有出口掃描、沒有齊全檢查。舊路徑移除後
沒有地方可以退，所以「打不了包」就是終局——必須讓使用者看到明確的錯誤，而不是拿到一份
看起來正常、實際上沒有經過任何稽核的回答。

拒絕的四種情形，各有自己的錯誤碼（見 `PackerRefused`）：
  * 沒有可解析的受測者（含完全沒帶 trait_reports 的請求）
  * `module_id` 不在題庫（`module_map` 在 import 時就驗過 22 個模組全部對得上，
    所以這只會是客戶端送了未知的 id）
  * 題目的 audience 與受測者人數不符——spec b §1.1 要求拒絕。舊路徑是安靜地改用另一份
    prompt，這正是 D2 要終結的那種降級。
  * 特質名稱對不上題庫、或 payload 組不出來
"""

import json
from typing import Optional

from ..utils.logger import get_daily_logger, history_text_block, write_prompt_record
from .log_assembler import AudienceMismatch, UnknownTrait
from .log_pipeline import LogPipeline
from .module_map import module_map
from .respondent_adapter import from_trait_reports
from .focus_detect import detect_focus
from .repeat_detect import measure as measure_repeat

packer_logger = get_daily_logger('LogPacker', 'log_packer_audit.log')


class PackerRefused(Exception):
    """打包器無法服務這個請求。

    `code` 給前端分辨用，`message` 是要顯示給使用者的中文說明。訊息刻意講清楚「為什麼」
    而不只是「失敗了」——這些情形全部需要使用者做點什麼（重選人、換題目、聯繫管理員），
    一句「系統錯誤」會讓他們只是重試。
    """

    def __init__(self, code: str, message: str):
        super().__init__(f'{code}: {message}')
        self.code = code
        self.message = message

# settings.py 的同名預設值。這裡只在讀不到 app config 時當退路，見 _history_cap_turns()。
DEFAULT_HISTORY_CAP_TURNS = 6


def _history_cap_turns():
    """MAX_HISTORY_TURNS，取不到就用預設值。

    刻意吞掉所有例外：這個數字只是 header 上的一個註記，為了它讓整筆 prompt 記錄寫不出來
    是很糟的交換。沒有 app context 時（離線腳本）也走這條退路。
    """
    try:
        from flask import current_app
        return int(current_app.config.get('MAX_HISTORY_TURNS', DEFAULT_HISTORY_CAP_TURNS))
    except Exception:
        return DEFAULT_HISTORY_CAP_TURNS


def _per_session_enabled():
    try:
        from flask import current_app
        return bool(current_app.config.get('PROMPT_LOG_PER_SESSION'))
    except Exception:
        return False


def log_payload(pipeline: LogPipeline, session_id, module_id, question, req_id=None,
                dropped=None):
    """Write the assembled LOG verbatim to prompts.log before anything is sent.

    事項 07 §3: 舊路徑的 `_log_prompt()` 只掛在 `rag_engine._call_llm()` 上，打包器不經過
    那裡，所以在補上這裡之前 prompts.log 對打包器的請求是完全空白的——log 裡看不到特質
    屬性、交互敘事與分段內容，只有 log_packer_audit.log 的統計數字。

    記的是 `to_log_text()` 而非 `to_messages()`：前者就是客戶驗收用的三段式 LOG 格式
    （[SYSTEM PROMPT] / 【輸入數據】 / [任務指令]），與 DoD 第 1 條拿去和三份 v7 範例
    逐行比對的是同一個字串。

    歷史區塊放在 header 與 `====` 分隔線「之間」，也就是 LOG 本體之外。這個位置是硬性的：
    從 `[SYSTEM PROMPT]` 往下取到檔尾，字串必須與沒有歷史區塊時逐字相同，v7 逐行比對才不
    會受影響。原本歷史只記筆數就是為了守住這件事，但那讓驗收看不到模型實際讀到什麼——
    改放在本體之外，兩個需求就不必互相犧牲。
    """
    log = pipeline.log
    audit = log.audit
    try:
        # 這個欄位一路到 8/18 都叫 HISTORY_TURNS，算的卻是 `len(messages) - 2`，也就是
        # 「則數」而不是「輪數」——1 輪 = 使用者一則 + AI 一則。客戶讀 log 時把 2 當成
        # 兩輪、實際只有一輪，剛好差兩倍。改名並把換算與上限一起印出來，讓驗收人員不必
        # 回頭查 .env 才知道 12 是吃滿了還是還早。
        cap_turns = _history_cap_turns()
        history_msgs = max(0, len(pipeline.messages) - 2)
        header = (f"REQ: {req_id or '-'} | "
                  f"SESSION: {session_id} | USE_CASE: log_packer | "
                  f"MODULE: {module_id or '(free-form)'} | "
                  f"QUESTION: {audit.get('question_id')} | "
                  f"TYPE: {audit.get('question_type')} | "
                  f"AUDIENCE: {audit.get('audience')} | "
                  f"RESPONDENTS: {len(audit.get('respondents') or [])} | "
                  f"HISTORY_MSGS: {history_msgs} ({history_msgs // 2} turns, "
                  f"cap={cap_turns} turns/{cap_turns * 2} msgs) | "
                  # 讀 log 的人第一眼就要知道這份 payload 是不是完整的。註記放在 header
                  # 與 ==== 分隔線之間，也就是 LOG 本體之外——本體從 [SYSTEM PROMPT] 起
                  # 必須與 v7 範例逐字相同，加一行進去會讓 DoD 1 的比對失效。
                  f"DROPPED_TRAITS: {len(dropped or ())}")
        write_prompt_record(
            session_id,
            f"{header}\n"
            f"{history_text_block(pipeline.history)}"
            f"============================================================\n"
            f"{log.to_log_text()}",
            per_session=_per_session_enabled())
    except Exception as e:
        # Never let an audit-trail failure take down a request that would otherwise
        # succeed; the packer audit log records that the payload went unlogged.
        packer_logger.error(f"session={session_id} failed to write the payload to "
                            f"prompts.log: {e}")


def dropped_audit(skips, respondents):
    """Per-respondent drop counts plus the raw list, for the audit record (事項 12).

    A trait the adapter could not place is skipped and the answer is written from what is
    left, with nothing in the record to say so: 2026-08-31 dropped 235 traits across 21
    requests -- one report lost 61 of its 79 -- and the reader saw an analysis that looked
    complete. `traits_total` alone cannot show this, because it counts what arrived, not
    what was sent.

    Returns (respondents with the two counts added, summary). The respondent dicts are
    rebuilt rather than mutated: `PipelineResult.audit` copies the outer dict only, so the
    entries are still the assembler's own.
    """
    by_id = {}
    for reason, ctx in (skips or ()):
        by_id.setdefault(str(ctx.get('candidate_id')), []).append({
            'reason': reason,
            'api_trait_id': ctx.get('api_trait_id'),
            'display_name': ctx.get('display_name'),
        })
    augmented = []
    for r in (respondents or ()):
        n = len(by_id.get(str(r.get('respondent_id')), ()))
        augmented.append({**r, 'traits_dropped': n,
                          'traits_sent': (r.get('traits_total') or 0) + n})
    return augmented, {'total': sum(len(v) for v in by_id.values()),
                       'by_respondent': by_id}


def apply_roster(trait_reports, candidate_ids, candidates_info, session_id):
    """本輪名單以 `candidate_ids` 為準；`trait_reports` 只是資料來源。

    打包器原本直接拿 `trait_reports.keys()` 當名單，而那是前端整包 sessionStorage 快取，
    不是這次請求選了誰。前端送來的 `candidate_ids` 才是本輪名單，而它一直沒有被用到。
    少了這道過濾，前端任何一條清快取的路徑漏掉一次，被移除的人就繼續留在 payload 裡。

    順帶記一件 `chat.py` 的守門看不到的事：那裡的檢查是 `candidates_info ⊆ trait_reports`，
    單向，所以 `candidates_info` 被截短永遠不會被擋。而 `sendMessage` 的 `candidates_info`
    是拿分頁清單（20 筆）過濾出來的，鎖定的人只要不在當前頁就會掉——掉了姓名就退化成
    `Candidate-<id>`。全語料還沒出現過，但這裡是唯一能在伺服器端看到它的地方。

    回傳 (要用的 reports, 稽核用的 roster 記錄)。
    """
    reports = trait_reports or {}
    # `candidate_ids` 沒送來時維持原行為：順序就是 trait_reports 的插入序，而且說出來。
    audit = {'source': 'trait_reports', 'requested': None, 'used': len(reports),
             'dropped': [], 'ordered_by': 'trait_reports_insertion'}
    if candidate_ids:
        wanted = {str(c) for c in candidate_ids}
        # 依 `candidate_ids` 的順序重建，不是依 `trait_reports` 的 dict 插入順序。
        # 位置代號 RESP_nn 是照這個順序指派的（log_assembler.log_label_for），而
        # `trait_reports` 的順序取決於前端怎麼組那個物件——同一份名單換一條建構路徑
        # 就可能整組換位，離線重放同一筆請求會拿到不同的代號。綁在前端送來的名單
        # 順序上之後，「名單尾端加人 -> 既有號碼不變、新人拿下一個號」自然成立。
        #
        # key 先正規化成字串再取：原本的寫法用 `str(k) in wanted` 比對，正是因為
        # `reports` 的 key 不保證已經是字串，所以這裡不能直接 `reports[str(c)]`。
        by_id = {str(k): v for k, v in reports.items()}
        seen, kept = set(), {}
        for cid in (str(c) for c in candidate_ids):
            if cid in by_id and cid not in seen:      # candidate_ids 可能有重複
                seen.add(cid)
                kept[cid] = by_id[cid]
        dropped = sorted(str(k) for k in reports if str(k) not in wanted)
        audit = {'source': 'candidate_ids', 'requested': len(wanted),
                 'used': len(kept), 'dropped': dropped, 'ordered_by': 'candidate_ids'}
        if dropped:
            packer_logger.warning(
                f"session={session_id} dropped {len(dropped)} stale trait report(s) not in "
                f"this turn's candidate_ids: {dropped}")
        reports = kept
        if candidates_info is not None and len(candidates_info) < len(wanted):
            audit['candidates_info_short_by'] = len(wanted) - len(candidates_info)
            packer_logger.warning(
                f"session={session_id} candidates_info carries {len(candidates_info)} of "
                f"{len(wanted)} candidate_ids -- the frontend truncated the roster, so the "
                f"missing respondents will be named Candidate-<id> in the payload")
    return reports, audit


class _Chunk:
    """Minimal stand-in for an OpenAI streaming chunk."""

    def __init__(self, content):
        self.usage = None
        self.choices = [type('C', (), {'delta': type('D', (), {'content': content})()})()]


class PackedStream:
    def __init__(self, pipeline: LogPipeline, stream_fn, session_id, question, req_id=None,
                 dropped=None, roster=None, focus=None):
        self._pipeline = pipeline
        self._stream_fn = stream_fn
        self._session_id = session_id
        self._question = question
        self._req_id = req_id
        self._dropped = list(dropped or ())
        self._roster = roster or {}
        self._focus = focus or {}
        self.finished = False
        self.audit: dict = {}

    def __iter__(self):
        for segment in self._pipeline.stream(self._stream_fn):
            yield _Chunk(segment)
        self.finish()

    @property
    def status(self) -> str:
        result = self._pipeline.result
        return result.status if result else 'incomplete'

    def finish(self) -> dict:
        """Write the structured audit record b §8 asks for.

        Idempotent, and repeat calls return the same audit rather than an empty dict:
        iterating the stream finishes it, and the route calls this again afterwards to
        decide whether to notify the user. Returning {} the second time meant the notice
        never fired -- found on the first live run.
        """
        if self.finished:
            return self.audit
        self.finished = True
        result = self._pipeline.result
        audit = result.audit if result else {'status': 'incomplete'}
        respondents, dropped = dropped_audit(self._dropped, audit.get('respondents'))
        if respondents:
            audit['respondents'] = respondents
        audit['dropped_traits'] = dropped
        # 名單從哪裡來、丟掉了誰。讀 log 的人第一眼就要能分辨「模型漏寫」與
        # 「這個人根本沒進 payload」。
        audit['roster'] = self._roster
        # 「使用者這輪在問誰」。**只記錄，不參與判定**——missing_respondents 仍以整個
        # 名單為期待值。放在這裡是為了累積可標註的樣本，見 focus_detect.py。
        audit['focus'] = self._focus
        # 「這一輪有多少是把上一輪重寫一遍」。同樣**只記錄**——它要量的是 [前輪脈絡]
        # 區塊有沒有用，而那個區塊還沒加時就得先有基線。見 repeat_detect.py（E-16）。
        try:
            audit['repeat'] = measure_repeat(self._pipeline.checker.text,
                                             self._pipeline.history)
        except Exception as e:
            audit['repeat'] = {}
            packer_logger.warning(f"session={self._session_id} repeat measure failed: {e}")
        audit['session_id'] = self._session_id
        # 這一輪的 prompt 記在 prompts.log、回覆記在 conversations.log、閘門結果記在這裡。
        # 三個檔以前只有 session_id 可對，而同一個 session 連續幾輪的 header 長得一模一樣，
        # 並行請求還會交錯，實務上只能靠秒級時間戳去猜。req_id 就是那個缺掉的鍵。
        audit['req_id'] = self._req_id or '-'
        self.audit = audit
        packer_logger.info(json.dumps(audit, ensure_ascii=False, default=str))
        if audit.get('status') != 'ok' or dropped['total']:
            packer_logger.warning(
                f"req={audit['req_id']} session={self._session_id} "
                f"status={audit.get('status')} "
                f"leakage_hits={audit.get('leakage_hits')} "
                f"missing_sections={audit.get('missing_sections')} "
                f"dropped_traits={dropped['total']}")
        for line in (audit.get('log') or []):
            packer_logger.info(f"req={audit['req_id']} | session={self._session_id} | {line}")
        return audit


def packed_stream(rag_service, module_id: Optional[str], query: str,
                  trait_reports: dict, candidates_info, session_id, req_id=None,
                  candidate_ids=None) -> PackedStream:
    """A PackedStream, or `PackerRefused` if this request cannot be packed."""
    try:
        question = module_map.question_for(module_id) if module_id else None
        if module_id and question is None:
            packer_logger.warning(f"session={session_id} module_id={module_id!r} has no question")
            raise PackerRefused(
                'UNKNOWN_MODULE',
                '這個提問模組已不存在或尚未設定，請改用其他快速提問或直接輸入問題。')

        dropped = []

        def _skip(reason, ctx):
            dropped.append((reason, ctx))
            packer_logger.warning(f"session={session_id} skipped trait: "
                                  f"reason={reason} | {ctx}")

        reports, roster = apply_roster(trait_reports, candidate_ids, candidates_info,
                                       session_id)
        respondents = from_trait_reports(reports, candidates_info, on_skip=_skip)
        if not respondents:
            packer_logger.warning(f"session={session_id} no resolvable respondents")
            raise PackerRefused(
                'NO_RESPONDENTS',
                '請先選擇至少一位有評測資料的受測者，再提出問題。')

        history = rag_service.load_history(session_id)

        # 「使用者這一輪在問誰」。本來就在串流開始前算完，只是結果只寫進稽核；現在提前到
        # 建 pipeline 之前，好讓覆蓋率檢查拿它當分母（見 CompletenessChecker.focus_names）。
        # 它只吃 user_query / 名單 / history / respondents，完全不碰回答，所以前移沒有
        # 任何阻礙。題庫題的「提問」是模組指令不是使用者的話，判「問誰」沒有意義，所以
        # 只在自由提問算。
        focus = {}
        if question is None:
            try:
                focus = detect_focus(query, [r.name for r in respondents],
                                     history=history, respondents=respondents)
            except Exception as e:                   # 稽核欄位不該弄掉一個請求
                packer_logger.warning(f"session={session_id} focus detection failed: {e}")

        # 只有「明確點名且沒有衝突」才換分母。排除語與追問繼承維持用整份名單——
        # 前者的語義是「名單減 X」而不是「只有 X」，後者比點名脆弱得多。
        focus_names = (focus.get('names') or []) if (
            focus.get('source') == 'named' and not focus.get('conflict')) else None

        pipeline = LogPipeline(respondents, question,
                               user_query=query if question is None else None,
                               history=history,
                               followup_fn=rag_service.packer_followup,
                               focus_names=focus_names)
    except AudienceMismatch as e:
        # spec b §1.1 要求拒絕。舊路徑是安靜地改用另一份 prompt——那正是 D2 要終結的降級。
        packer_logger.warning(f"session={session_id} audience mismatch: {e}")
        raise PackerRefused(
            'AUDIENCE_MISMATCH',
            '這個提問只適用於目前選定的受測者人數以外的情況，請調整選取的人數或改用其他提問。')
    except (UnknownTrait, ValueError) as e:
        packer_logger.warning(f"session={session_id} cannot pack: {e}")
        raise PackerRefused(
            'CANNOT_PACK',
            '特質資料無法組裝成分析依據，請重新載入頁面後再試；若持續發生請聯繫管理員。')

    log_payload(pipeline, session_id, module_id, question, req_id, dropped)
    return PackedStream(pipeline, rag_service.packer_stream, session_id, question, req_id,
                        dropped=dropped, roster=roster, focus=focus)

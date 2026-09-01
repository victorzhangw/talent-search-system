"""Adapter that lets the chat route drive the LOG packer without changing its stream loop.

The route's streaming loop reads OpenAI-shaped chunks (`chunk.choices[0].delta.content`),
so this wraps the packer's cleared segments in that shape. One gated segment arrives as
one chunk -- the typewriter effect becomes a client-side replay of verified text, which is
the point of the segment gate: nothing reaches the browser until it has been scanned.

`try_packed_stream` returns None whenever the packer cannot serve the request. That is the
switch between the two paths: the caller falls through to the legacy module-prompt route
untouched, so a request is never served by both.

Not served here, deliberately:
  * requests without frontend trait reports -- the upstream-fetch merge still lives inside
    `generate_response`, and duplicating it to serve a flagged-off path would be two
    copies of the same resolution.
  * module ids with no question mapping, and quick-question requests whose respondent
    count contradicts the question's audience (b §1.1 says reject; the legacy route's
    fallback quietly uses the other prompt instead, so falling through preserves today's
    behaviour rather than changing it behind a flag).
"""

import json
from typing import Optional

from ..utils.logger import get_daily_logger, history_text_block, write_prompt_record
from .log_assembler import AudienceMismatch, UnknownTrait
from .log_pipeline import LogPipeline
from .module_map import module_map
from .respondent_adapter import from_trait_reports

packer_logger = get_daily_logger('LogPacker', 'log_packer_audit.log')

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


class _Chunk:
    """Minimal stand-in for an OpenAI streaming chunk."""

    def __init__(self, content):
        self.usage = None
        self.choices = [type('C', (), {'delta': type('D', (), {'content': content})()})()]


class PackedStream:
    def __init__(self, pipeline: LogPipeline, stream_fn, session_id, question, req_id=None,
                 dropped=None):
        self._pipeline = pipeline
        self._stream_fn = stream_fn
        self._session_id = session_id
        self._question = question
        self._req_id = req_id
        self._dropped = list(dropped or ())
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


def try_packed_stream(rag_service, module_id: Optional[str], query: str, mode: str,
                      trait_reports: dict, candidates_info, session_id, req_id=None
                      ) -> Optional[PackedStream]:
    """A PackedStream, or None to let the caller use the legacy path."""
    try:
        question = module_map.question_for(module_id) if module_id else None
        if module_id and question is None:
            packer_logger.info(f"session={session_id} module_id={module_id!r} has no question; "
                               f"falling back to the legacy path")
            return None

        dropped = []

        def _skip(reason, ctx):
            dropped.append((reason, ctx))
            packer_logger.warning(f"session={session_id} skipped trait: "
                                  f"reason={reason} | {ctx}")

        respondents = from_trait_reports(trait_reports, candidates_info, on_skip=_skip)
        if not respondents:
            packer_logger.info(f"session={session_id} no resolvable respondents; legacy path")
            return None

        pipeline = LogPipeline(respondents, question,
                               user_query=query if question is None else None,
                               history=rag_service.load_history(session_id),
                               followup_fn=rag_service.packer_followup)
    except AudienceMismatch as e:
        # b §1.1 wants this rejected. The legacy route instead falls back to the other
        # prompt; changing that is a product decision, not something to slip in behind a
        # flag, so the legacy behaviour stands until the packer becomes the only path.
        packer_logger.warning(f"session={session_id} audience mismatch: {e}; legacy path")
        return None
    except (UnknownTrait, ValueError) as e:
        packer_logger.warning(f"session={session_id} cannot pack: {e}; legacy path")
        return None

    log_payload(pipeline, session_id, module_id, question, req_id, dropped)
    return PackedStream(pipeline, rag_service.packer_stream, session_id, question, req_id,
                        dropped=dropped)

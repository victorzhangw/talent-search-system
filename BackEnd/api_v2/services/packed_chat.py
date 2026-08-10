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

from ..utils.logger import get_daily_logger, get_prompt_logger
from .log_assembler import AudienceMismatch, UnknownTrait
from .log_pipeline import LogPipeline
from .module_map import module_map
from .respondent_adapter import from_trait_reports

packer_logger = get_daily_logger('LogPacker', 'log_packer_audit.log')


def log_payload(pipeline: LogPipeline, session_id, module_id, question):
    """Write the assembled LOG verbatim to prompts.log before anything is sent.

    事項 07 §3: 舊路徑的 `_log_prompt()` 只掛在 `rag_engine._call_llm()` 上，打包器不經過
    那裡，所以在補上這裡之前 prompts.log 對打包器的請求是完全空白的——log 裡看不到特質
    屬性、交互敘事與分段內容，只有 log_packer_audit.log 的統計數字。

    記的是 `to_log_text()` 而非 `to_messages()`：前者就是客戶驗收用的三段式 LOG 格式
    （[SYSTEM PROMPT] / 【輸入數據】 / [任務指令]），與 DoD 第 1 條拿去和三份 v7 範例
    逐行比對的是同一個字串。歷史訊息只記筆數，因為它夾在 system 與 user 之間、不屬於
    LOG 本體，記進去會讓檔案與範例格式對不上。
    """
    log = pipeline.log
    audit = log.audit
    try:
        header = (f"SESSION: {session_id} | USE_CASE: log_packer | "
                  f"MODULE: {module_id or '(free-form)'} | "
                  f"QUESTION: {audit.get('question_id')} | "
                  f"TYPE: {audit.get('question_type')} | "
                  f"AUDIENCE: {audit.get('audience')} | "
                  f"RESPONDENTS: {len(audit.get('respondents') or [])} | "
                  f"HISTORY_TURNS: {max(0, len(pipeline.messages) - 2)}")
        get_prompt_logger().info(
            f"{header}\n"
            f"============================================================\n"
            f"{log.to_log_text()}")
    except Exception as e:
        # Never let an audit-trail failure take down a request that would otherwise
        # succeed; the packer audit log records that the payload went unlogged.
        packer_logger.error(f"session={session_id} failed to write the payload to "
                            f"prompts.log: {e}")


class _Chunk:
    """Minimal stand-in for an OpenAI streaming chunk."""

    def __init__(self, content):
        self.usage = None
        self.choices = [type('C', (), {'delta': type('D', (), {'content': content})()})()]


class PackedStream:
    def __init__(self, pipeline: LogPipeline, stream_fn, session_id, question):
        self._pipeline = pipeline
        self._stream_fn = stream_fn
        self._session_id = session_id
        self._question = question
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
        audit['session_id'] = self._session_id
        self.audit = audit
        packer_logger.info(json.dumps(audit, ensure_ascii=False, default=str))
        if audit.get('status') != 'ok':
            packer_logger.warning(
                f"session={self._session_id} status={audit.get('status')} "
                f"leakage_hits={audit.get('leakage_hits')} "
                f"missing_sections={audit.get('missing_sections')}")
        for line in (audit.get('log') or []):
            packer_logger.info(f"session={self._session_id} | {line}")
        return audit


def try_packed_stream(rag_service, module_id: Optional[str], query: str, mode: str,
                      trait_reports: dict, candidates_info, session_id
                      ) -> Optional[PackedStream]:
    """A PackedStream, or None to let the caller use the legacy path."""
    try:
        question = module_map.question_for(module_id) if module_id else None
        if module_id and question is None:
            packer_logger.info(f"session={session_id} module_id={module_id!r} has no question; "
                               f"falling back to the legacy path")
            return None

        respondents = from_trait_reports(
            trait_reports, candidates_info,
            on_skip=lambda reason, ctx: packer_logger.warning(
                f"session={session_id} skipped trait: reason={reason} | {ctx}"))
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

    log_payload(pipeline, session_id, module_id, question)
    return PackedStream(pipeline, rag_service.packer_stream, session_id, question)

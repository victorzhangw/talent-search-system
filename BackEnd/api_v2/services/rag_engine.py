"""LLM 客戶端與對話歷史，供 LOG 打包器使用。

這個檔案曾經是整條舊生成管線：意圖路由（use_cases.json）、模組路由
（quick_modules.json + prompts/modules/*.txt）、ContextBuilder 組裝、prompt 模板套用、
上游資料抓取與合併。U7 依決策 D2 把那條路徑整段移除——打包器已經是唯一路徑，而舊路徑
沒有分段閘門、沒有出口掃描、沒有齊全檢查，留著它等於留一條「安靜降級成未稽核輸出」的退路。

移除前的證據：2026-09-05 至 09-09 的 conversations.log 裡，唯一的真實使用者
（a080697@gmail.com，89 次請求）全部走打包器；所有觸發舊路徑的請求都是
candidates: []，且 SessionID 為 GATE_TEST / IDENTITY_TEST，來自驗證腳本。
rag_service.log 的 "Module route" 自 2026-08-10 起是 0。

現在這裡只剩三件事：持有 LLM 客戶端、讀對話歷史、把打包器組好的 messages 送出去。
"""

import time
import openai
import logging
from flask import current_app
from ..utils.logger import get_daily_logger

def get_rag_logger():
    return get_daily_logger("RAG_Logger", "rag_service.log", level=logging.DEBUG)

rag_logger = get_rag_logger()

class RAGService:
    def __init__(self):
        api_key = current_app.config.get('LLM_API_KEY')
        api_base = current_app.config.get('LLM_API_BASE')
        self.model_name = current_app.config.get('LLM_MODEL') or 'deepseek-v4-flash'

        # Fallback: Retry loading .env if key is missing (Hotfix for loading issue)
        if not api_key:
             rag_logger.warning("LLM_API_KEY is None. Attempting to reload .env manually...")
             try:
                 import os
                 from dotenv import load_dotenv
                 env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
                 load_dotenv(env_path, override=True)
                 api_key = os.getenv('LLM_API_KEY')
             except Exception as e:
                 rag_logger.error(f".env reload failed: {e}", exc_info=True)

        # Final Safety Check: Use dummy key to prevent crash, let the packer surface the
        # authentication error rather than failing at startup.
        if not api_key:
             rag_logger.error("CRITICAL: Still no API KEY. Using dummy key to prevent startup crash.", exc_info=False)
             api_key = "sk-dummy-key-for-init"

        # Read here rather than at call time: the SSE generator runs after the request
        # has been handed to the WSGI server, and this object is a module-level singleton
        # built inside before_request, where the app context is guaranteed.
        self.disable_thinking = current_app.config.get('LLM_DISABLE_THINKING', True)

        rag_logger.info(f"Init LLM - Base: {api_base}, Key: {api_key[:5]}..., "
                        f"thinking={'disabled' if self.disable_thinking else 'enabled'}")

        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=api_base
        )

    def load_history(self, session_id):
        """Prior turns for this session, oldest first, capped at MAX_HISTORY_TURNS.

        這段以前寫死在舊路徑的 `_call_llm()` 裡，打包器不經過那裡，於是每一個請求都是在
        沒有任何歷史的情況下送出去的——「那他呢？」這種追問到了模型手上，沒有東西可以
        解析「他」。抽出來之後兩條路徑共用；現在只剩打包器一條。
        """
        if not session_id or session_id == "unknown":
            return []
        try:
            from .session_store import SqlSessionStore
            max_turns = current_app.config.get('MAX_HISTORY_TURNS', 6)
            db_msgs = SqlSessionStore().get_messages(session_id)
            conv = [m for m in db_msgs if m.role in ('user', 'assistant')]
            # 排除最後一條：chat.py 在呼叫本函式前已將當前 query 存入 DB
            if conv and conv[-1].role == 'user':
                conv = conv[:-1]
            conv = conv[-(max_turns * 2):]
            history = [{"role": m.role, "content": m.content} for m in conv]
            rag_logger.info(f"[History] Loaded {len(history)} msgs for session {session_id}")
            return history
        except Exception as e:
            rag_logger.warning(f"[History] Failed to load history: {e}")
            return []

    # --- LOG packer adapters (事項 16) -------------------------------------------------
    # The packer builds its own messages and needs plain text back, so these bypass the
    # prompt-template path entirely and just drive the client. Injected into LogPipeline
    # rather than imported by it, which is what lets the whole pipeline be tested offline.

    def _thinking_kwargs(self):
        """extra_body that switches the model's reasoning off, when configured.

        Passed through `extra_body` because it is not an OpenAI-schema parameter; the
        client forwards it verbatim to DeepSeek.
        """
        if not self.disable_thinking:
            return {}
        return {'extra_body': {'thinking': {'type': 'disabled'}}}

    def packer_stream(self, messages):
        """Token strings for a packer-assembled request.

        Only `content` is yielded. When reasoning is enabled the model streams
        `reasoning_content` first -- thousands of chunks that are dropped here -- and the
        user sees nothing at all until it finishes. That is logged rather than left
        invisible: it was the entire cause of a 330s "hang" on UAT, and from the packer's
        side it is indistinguishable from a stalled connection.
        """
        rag_logger.info(f"[Packer] streaming with model '{self.model_name}', "
                        f"{len(messages)} messages, "
                        f"thinking={'disabled' if self.disable_thinking else 'enabled'}")
        started = time.perf_counter()
        reasoning_chunks = reasoning_chars = 0
        first_content_at = None
        # Readable by callers that want to report where the time went (run_packer_live
        # prints it); the warning below is what production leaves behind in the log.
        self.last_stream_stats = stats = {'thinking': not self.disable_thinking,
                                          'reasoning_chunks': 0, 'reasoning_chars': 0,
                                          'first_content_at': None}
        stream = self.client.chat.completions.create(
            model=self.model_name, messages=messages, stream=True,
            **self._thinking_kwargs())
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta:
                delta = chunk.choices[0].delta
                reasoning = getattr(delta, 'reasoning_content', None)
                if reasoning:
                    reasoning_chunks += 1
                    reasoning_chars += len(reasoning)
                    stats['reasoning_chunks'] = reasoning_chunks
                    stats['reasoning_chars'] = reasoning_chars
                content = delta.content
                if content:
                    if first_content_at is None:
                        first_content_at = time.perf_counter() - started
                        stats['first_content_at'] = first_content_at
                        if reasoning_chunks:
                            rag_logger.warning(
                                f"[Packer] first answer token at {first_content_at:.1f}s "
                                f"after {reasoning_chunks} reasoning chunks "
                                f"({reasoning_chars} chars) -- the user saw nothing for "
                                f"that whole time")
                        else:
                            rag_logger.info(f"[Packer] first answer token at "
                                            f"{first_content_at:.2f}s")
                    yield content

    def packer_followup(self, messages, instruction):
        """One non-streamed turn: segment rewrite or missing-section completion. Returns
        empty on failure so the gate falls back to blocked/manual_review rather than
        releasing unverified text."""
        try:
            resp = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages + [{'role': 'user', 'content': instruction}],
                stream=False, **self._thinking_kwargs())
            return (resp.choices[0].message.content or '') if resp.choices else ''
        except Exception as e:
            rag_logger.error(f"[Packer] follow-up call failed: {e}", exc_info=True)
            return ''

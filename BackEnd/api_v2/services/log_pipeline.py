"""One request, end to end: assemble -> call the model -> gate every segment -> audit.

This is the seam between the deterministic packer (事項 01-08) and the output guard
(事項 09/10/12/16). The model is injected rather than imported so the whole path can be
exercised without network access; `rag_engine` supplies the real one.

The rewrite instruction matters more than it looks. A rewriter that merely deletes the
banned terms produces text that passes the scanner while reading as broken Chinese --
observed directly while testing, where 「他的 CIA_05 衝動管理偏高，在 B 段表現尚可」 came back
as 「他的　偏高，在 表現尚可」: clean and useless. So it asks for the same meaning restated in
workplace-behaviour language and names the forbidden terms only as a constraint.
"""

from typing import Callable, Iterable, Iterator, List, Optional

from .completeness_check import CompletenessChecker
from .exit_scanner import ExitScanner
from .log_assembler import AssembledLog, Respondent, assemble
from .question_table import table
from .segment_gate import SegmentGate

# Sent as follow-up turns, so the model still has the payload and its own draft in view.
REWRITE_INSTRUCTION = (
    '上一段輸出使用了不得出現的字詞：{terms}。\n'
    '請「重寫」該段，保留原本要表達的判讀與建議，改用主管與 HR 能理解的職場行為語言表述。\n'
    '不是刪除這些字詞——刪掉會讓句子不完整；請換一種說法把同樣的意思講清楚。\n'
    '只輸出改寫後的該段內容，不要加說明、不要重複其他段落。\n\n'
    '原段落：\n{segment}'
)

COMPLETION_INSTRUCTION = (
    '你的回答還缺少以下內容：{reason}。\n'
    '請「只補上」缺少的部分，沿用先前的段落標題格式；不要重寫或重複已經輸出過的段落。'
)

# stream_fn(messages) -> iterable of token strings
StreamFn = Callable[[List[dict]], Iterable[str]]
# followup_fn(messages, instruction) -> one complete reply
FollowupFn = Callable[[List[dict], str], str]


class PipelineResult:
    __slots__ = ('log', 'gate', 'answer')

    def __init__(self, log: AssembledLog, gate: SegmentGate, answer: str):
        self.log = log
        self.gate = gate
        self.answer = answer

    @property
    def status(self) -> str:
        return self.gate.result.status

    @property
    def audit(self) -> dict:
        """The structured record b §8 asks for and that 事項 12 keys its follow-up off."""
        merged = dict(self.log.audit)
        merged.update(self.gate.result.as_audit())
        return merged


class LogPipeline:
    def __init__(self, respondents: List[Respondent], question: Optional[dict],
                 user_query: Optional[str] = None, history: Optional[List[dict]] = None,
                 followup_fn: Optional[FollowupFn] = None):
        # assemble() runs the b §6 unit checks and raises before anything is sent.
        self.log = assemble(respondents, question, user_query=user_query)
        self.messages = self.log.to_messages(history)
        self.checker = CompletenessChecker(respondents, question, table.calibration_traits)
        self.followup_fn = followup_fn
        self.gate = SegmentGate(ExitScanner.for_log(self.log), checker=self.checker,
                                rewriter=self._rewrite, completer=self._complete)
        self.result: Optional[PipelineResult] = None

    def _rewrite(self, segment: str, banned: List[str]) -> str:
        if self.followup_fn is None:
            return segment
        return self.followup_fn(
            self.messages + [{'role': 'assistant', 'content': segment}],
            REWRITE_INSTRUCTION.format(terms='、'.join(banned), segment=segment))

    def _complete(self, reason: str) -> str:
        if self.followup_fn is None:
            return ''
        return self.followup_fn(
            self.messages + [{'role': 'assistant', 'content': self.checker.text}],
            COMPLETION_INSTRUCTION.format(reason=reason))

    def stream(self, stream_fn: StreamFn) -> Iterator[str]:
        """Yields display-ready segments. `self.result` is set once iteration ends."""
        released = []
        for segment in self.gate.run(stream_fn(self.messages)):
            released.append(segment)
            yield segment
        self.result = PipelineResult(self.log, self.gate, ''.join(released))

    def run(self, stream_fn: StreamFn) -> PipelineResult:
        """Non-streaming convenience: drain the stream and hand back the result."""
        for _ in self.stream(stream_fn):
            pass
        return self.result

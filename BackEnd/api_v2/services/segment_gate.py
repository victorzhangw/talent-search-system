"""Segment-gated output: scan before each segment is shown (事項 16 + 12).

The client's ruling of 2026-08-05 moved the checkpoint from "after the whole answer" to
"before each segment is displayed". The model still streams; the backend buffers up to a
segment boundary, scans it (the scan itself is negligible -- building the scanner is the
cost, and that happens once per request), and only then releases it. A segment that trips
the scanner is sent back to the model for a rewrite of that segment alone, together with
the terms it may not use, and is re-scanned before release.

    tokens ──▶ Segmenter ──▶ scan ──clean──▶ emit (typewriter replay)
                                │
                                └─dirty──▶ rewrite (≤2) ──▶ re-scan
                                                │
                                                └─still dirty──▶ stop, status=blocked

What this design can and cannot promise, stated plainly because the original spec wording
promised more: a segment that never comes clean is never shown, and neither is anything
after it -- but segments already released cannot be recalled. 「不得把該回覆回傳前端」 becomes
「未通過的段落不會顯示」. Confirmed with the client (丙-3).

Completeness (b §8) is whole-answer scoped and cannot be judged per segment, so headings
are accumulated as segments clear and the verdict comes at the end. If something is
missing, the model is asked once for the missing part only, which is then gated like any
other segment and appended -- the earlier segments stay on screen (丙-2).

Leakage retries and the completeness retry are counted separately (b §7), so a stubborn
segment cannot exhaust the budget that the completeness pass needs.
"""

import re
from typing import Callable, Iterable, Iterator, List, Optional

from .completeness_check import CompletenessChecker
from .exit_scanner import ExitScanner

SEGMENT_MAX_CHARS = 400          # 丁-1: keeps the buffering wait at 1-2s, not 5s
OVERLAP_CHARS = 16               # 丁-2: catches a marker split across a boundary
MAX_SEGMENT_REWRITES = 2         # 丁-3
MAX_COMPLETION_ATTEMPTS = 1      # b §8: 補生成一次

_SENTENCE_END_RE = re.compile(r'[。！？!?；;]')
_BLANK_LINE_RE = re.compile(r'\n[ \t]*\n')

STATUS_OK = 'ok'
STATUS_MANUAL_REVIEW = 'manual_review'
STATUS_BLOCKED = 'blocked'


class Segmenter:
    """Cuts a token stream at blank lines, or earlier if a paragraph runs long.

    Emitted segments include their trailing separator, so concatenating everything the
    gate released reproduces exactly what the user saw.
    """

    def __init__(self, max_chars: int = SEGMENT_MAX_CHARS):
        self.max_chars = max_chars
        self._buf = ''

    def feed(self, token: str) -> List[str]:
        self._buf += token or ''
        out = []
        while True:
            piece = self._take()
            if piece is None:
                break
            out.append(piece)
        return out

    def flush(self) -> List[str]:
        out = []
        while True:
            piece = self._take()
            if piece is None:
                break
            out.append(piece)
        if self._buf.strip():
            out.append(self._buf)
        self._buf = ''
        return out

    def _take(self) -> Optional[str]:
        m = _BLANK_LINE_RE.search(self._buf)
        if m:
            piece, self._buf = self._buf[:m.end()], self._buf[m.end():]
            return piece
        if len(self._buf) > self.max_chars:
            window = self._buf[:self.max_chars]
            ends = list(_SENTENCE_END_RE.finditer(window))
            cut = ends[-1].end() if ends else self.max_chars
            piece, self._buf = self._buf[:cut], self._buf[cut:]
            return piece
        return None


class SegmentRecord:
    __slots__ = ('index', 'released', 'rewrites', 'hits', 'final_hits')

    def __init__(self, index):
        self.index = index
        self.released = False
        self.rewrites = 0
        self.hits: List[str] = []        # terms seen on the first scan
        self.final_hits: List[str] = []  # terms still present when we gave up

    def as_audit(self):
        return {'index': self.index, 'released': self.released, 'rewrites': self.rewrites,
                'hits': self.hits, 'final_hits': self.final_hits}


class GateResult:
    def __init__(self):
        self.status = STATUS_OK
        self.segments: List[SegmentRecord] = []
        self.completeness = None
        self.completion_attempts = 0

    @property
    def retry_count(self):
        # b §7: the two budgets are tracked apart.
        return {'leakage': sum(s.rewrites for s in self.segments),
                'completeness': self.completion_attempts}

    def as_audit(self):
        audit = {'status': self.status,
                 'retry_count': self.retry_count,
                 'segments': [s.as_audit() for s in self.segments],
                 'leakage_hits': [h for s in self.segments for h in s.final_hits]}
        if self.completeness is not None:
            audit.update(self.completeness.as_audit())
        return audit


class SegmentGate:
    """rewriter(segment, banned_terms) -> rewritten segment.
    completer(reason) -> extra text supplying what the completeness check found missing."""

    def __init__(self, scanner: ExitScanner, checker: Optional[CompletenessChecker] = None,
                 rewriter: Optional[Callable[[str, List[str]], str]] = None,
                 completer: Optional[Callable[[str], str]] = None,
                 max_rewrites: int = MAX_SEGMENT_REWRITES,
                 max_chars: int = SEGMENT_MAX_CHARS,
                 overlap: int = OVERLAP_CHARS):
        self.scanner = scanner
        self.checker = checker
        self.rewriter = rewriter
        self.completer = completer
        self.max_rewrites = max_rewrites
        self.segmenter = Segmenter(max_chars)
        self.overlap = overlap
        self.result = GateResult()
        self._tail = ''

    def _scan(self, segment: str):
        """Scan with the tail of the previous released segment prepended, keeping only
        hits that reach into the new text -- anything wholly inside the tail was already
        cleared when that segment went out."""
        tail = self._tail[-self.overlap:] if self.overlap else ''
        hits = self.scanner.scan(tail + segment)
        return [h for h in hits if h.start + len(h.text) > len(tail)]

    def _clear(self, segment: str, record: SegmentRecord) -> Optional[str]:
        """Return a releasable segment, or None if it could not be cleaned."""
        hits = self._scan(segment)
        if not hits:
            return segment
        record.hits = self.scanner.banned_terms(hits)

        while record.rewrites < self.max_rewrites and self.rewriter is not None:
            record.rewrites += 1
            try:
                segment = self.rewriter(segment, self.scanner.banned_terms(hits))
            except Exception:
                break
            hits = self._scan(segment)
            if not hits:
                return segment

        record.final_hits = self.scanner.banned_terms(hits)
        return None

    def _release(self, segment: str, record: SegmentRecord) -> str:
        record.released = True
        self._tail = segment
        if self.checker is not None:
            self.checker.observe(segment)
        return segment

    def _gate(self, segment: str) -> Optional[str]:
        record = SegmentRecord(len(self.result.segments))
        self.result.segments.append(record)
        cleaned = self._clear(segment, record)
        return None if cleaned is None else self._release(cleaned, record)

    def run(self, tokens: Iterable[str]) -> Iterator[str]:
        """Yields display-ready segments. Stops early if one cannot be cleaned.

        Each segment is gated and released the moment its boundary arrives, while the
        model is still producing the rest. Draining the whole token stream first would
        make the wait the length of the entire answer instead of one segment -- which is
        the difference between this design and the whole-answer buffering it replaced.
        """
        blocked = False
        for token in tokens:
            for segment in self.segmenter.feed(token):
                released = self._gate(segment)
                if released is None:
                    blocked = True
                    break
                yield released
            if blocked:
                break

        if not blocked:
            for segment in self.segmenter.flush():
                released = self._gate(segment)
                if released is None:
                    blocked = True
                    break
                yield released

        if blocked:
            self.result.status = STATUS_BLOCKED
            return

        if self.checker is None:
            return
        outcome = self.checker.finalize()
        self.result.completeness = outcome
        if outcome.status != 'failed':
            return

        # 丙-2: ask for the missing part only; what is already on screen stays.
        #
        # Only run it for a failure appending can actually fix. A calibration-evidence or
        # over-length failure asked the model to do something an appendix cannot do, and
        # it responded by re-emitting the whole answer -- which, since released segments
        # are never recalled, the user read twice. See `appendable_reason`.
        reason = outcome.appendable_reason()
        if self.completer is None or not reason:
            self.result.status = STATUS_MANUAL_REVIEW
            return
        for _ in range(MAX_COMPLETION_ATTEMPTS):
            self.result.completion_attempts += 1
            try:
                extra = self.completer(reason)
            except Exception:
                break
            if not (extra or '').strip():
                break
            released = self._gate(extra)
            if released is None:
                self.result.status = STATUS_BLOCKED
                return
            yield released
            outcome = self.checker.finalize()
            self.result.completeness = outcome
            if outcome.status != 'failed':
                return
            reason = outcome.appendable_reason()
            if not reason:
                break
        self.result.status = STATUS_MANUAL_REVIEW

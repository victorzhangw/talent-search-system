"""Split a respondent's traits into full blocks and index lines (事項 05, b §2).

    全塊區 = S ∩ P   四欄原文 + 標頭 [特質 | ID_band | 標籤]
    索引區 = P − S   一行摘要 - ID_band｜中文名｜標籤：行為面向全文

where P is everything the respondent was measured on and S is the question's scoped
set. Whole-person questions and free-form asks set S = P, so there is no index region
at all and the subject header carries a different suffix.

The rule that is easiest to get wrong, and that 00_外包交接說明 calls out by name:
**risk and calibration traits are not promoted to full blocks**. Hitting a risk endpoint
changes which interactions are guaranteed (事項 06), never which region a trait lands in.
An unscoped calibration trait stays in the index, where its 行為面向 already carries the
credibility sentence.

Ordering is by trait_id, matching the client's v7 examples in both regions.
"""

from typing import Dict, List, Optional, Tuple

from .question_table import QuestionTable

# Verbatim from a 文件 第二部分 / b §5. The suffix on the subject header is the only
# structural tell of whole-person mode inside the payload.
SUBJECT_HEADER = '#### 判讀主體特質'
SUBJECT_HEADER_WHOLE = '#### 判讀主體特質（全人型＝全部特質）'
INDEX_HEADER = '#### 其他特質索引（僅供關聯參考，非本題判讀主體）'


class SplitResult:
    __slots__ = ('full', 'index', 'whole_person', 'scoped_ids')

    def __init__(self, full, index, whole_person, scoped_ids):
        self.full: List[Tuple[str, str]] = full
        self.index: List[Tuple[str, str]] = index
        self.whole_person: bool = whole_person
        self.scoped_ids: set = scoped_ids

    @property
    def subject_header(self) -> str:
        return SUBJECT_HEADER_WHOLE if self.whole_person else SUBJECT_HEADER

    @property
    def has_index_region(self) -> bool:
        """Whole-person emits no index region at all -- not even an empty header."""
        return not self.whole_person and bool(self.index)

    def __repr__(self):
        return (f'<SplitResult full={len(self.full)} index={len(self.index)} '
                f'whole_person={self.whole_person}>')


def split_traits(scores: Dict[str, str], question: Optional[dict],
                 tests=None) -> SplitResult:
    """scores: the respondent's {trait_id: band} (P). question: the table row, or None
    for free-form. tests: which assessments they took; defaults to the prefixes present
    in `scores`, which is the same thing."""
    if tests is None:
        tests = sorted({t.split('_')[0] for t in scores})

    whole = QuestionTable.is_whole_person(question)
    scoped = QuestionTable.scoped_ids(question, tests)

    ordered = sorted(scores.items())
    if whole:
        return SplitResult(ordered, [], True, set(scores))

    full = [(t, b) for t, b in ordered if t in scoped]
    index = [(t, b) for t, b in ordered if t not in scoped]
    return SplitResult(full, index, False, scoped)

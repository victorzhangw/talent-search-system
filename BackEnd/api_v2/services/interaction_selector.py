"""Pick and group the interaction rows for one respondent (事項 06, b §3).

The governing principle is 「相關的全注入、不做任意砍量、無條數上限」. Older drafts
described a 覆蓋輪 / 補充 10 / >90 截斷 scheme; b §3 revoked it explicitly ("若你在任何
舊版文件或口頭需求中看到 25/40 條上限、覆蓋輪、補充輪等字眼，那些已被推翻，不要實作"),
and the candidate pool is bounded anyway -- there are no cross-assessment interactions.

    candidates   rows whose BOTH ends (trait_id, band) are in P
    dedup        the 08 sheet stores 226 pairs in both directions; keep the earlier row
    scoped       step 1 drops pairs touching neither S nor 校準 nor R, step 2 groups the
                 rest into 本題相關 / 作答校準與風險提示
    whole-person no step 1; everything is grouped into 作答校準與風險提示 / 其他參考

Grouping is not decided here: an interaction's sub-block comes from endpoint_registry,
which resolves it from the endpoint types the two ends hit and the blocks' priority.
That keeps "which endpoint type shows up where" a data question.
"""

from typing import Dict, List, Optional

from sqlalchemy import text

from ..database import db_session
from .endpoint_registry import registry
from .narrative_cleaner import cleaner
from .trait_blocks import TraitBlockRenderer

# b §3 註記. Emitted only for the scoped 本題相關 sub-block, only at 1-4 items.
SPARSE_FOOTNOTE = '本題相關交互較少，判讀以特質區塊為主'
SPARSE_FOOTNOTE_MAX = 4

_CANDIDATE_SQL = text("""
    SELECT id, primary_trait_id, split_part(primary_band, '(', 1) AS pband,
           trigger_trait_id, trigger_band, narrative
    FROM trait_interactions
    WHERE trigger_trait_id IS NOT NULL AND narrative IS NOT NULL
    ORDER BY id
""")


class Interaction:
    __slots__ = ('row_id', 'a_id', 'a_band', 'b_id', 'b_band', 'narrative')

    def __init__(self, row_id, a_id, a_band, b_id, b_band, narrative):
        self.row_id = row_id
        self.a_id, self.a_band = a_id, a_band
        self.b_id, self.b_band = b_id, b_band
        self.narrative = narrative

    @property
    def ends(self):
        return (self.a_id, self.b_id)

    @property
    def key(self):
        """Unordered identity, for mirror dedup."""
        return frozenset({(self.a_id, self.a_band), (self.b_id, self.b_band)})

    def render(self, renderer: TraitBlockRenderer) -> str:
        la = renderer.semantic_label(self.a_id, self.a_band)
        lb = renderer.semantic_label(self.b_id, self.b_band)
        header = f'[交互 | {self.a_id}_{self.a_band} × {self.b_id}_{self.b_band} | {la} × {lb}]'
        return f'{header}\n{cleaner.clean(self.narrative)}'

    def __repr__(self):
        return f'<Interaction {self.a_id}_{self.a_band}x{self.b_id}_{self.b_band}>'


class SelectedBlock:
    __slots__ = ('block_key', 'header', 'items', 'footnote')

    def __init__(self, block_key, header, items, footnote=None):
        self.block_key = block_key
        self.header = header
        self.items: List[Interaction] = items
        self.footnote: Optional[str] = footnote

    def __repr__(self):
        return f'<SelectedBlock {self.block_key} n={len(self.items)}>'


_cache = None


def _all_rows():
    """08 rows are static reference data; load once per process."""
    global _cache
    if _cache is None:
        _cache = [Interaction(r[0], r[1], (r[2] or '').strip(), r[3], r[4], r[5])
                  for r in db_session.execute(_CANDIDATE_SQL)]
    return _cache


def reset_cache():
    global _cache
    _cache = None


def candidates(scores: Dict[str, str]) -> List[Interaction]:
    """Rows with both ends in P, mirrors collapsed to the earlier row, in row order."""
    seen = set()
    out = []
    for it in _all_rows():
        if scores.get(it.a_id) != it.a_band or scores.get(it.b_id) != it.b_band:
            continue
        if it.key in seen:
            continue
        seen.add(it.key)
        out.append(it)
    return out


def select_interactions(scores: Dict[str, str], question: Optional[dict],
                        scoped_ids: Optional[set]) -> List[SelectedBlock]:
    """Grouped, ordered sub-blocks. Empty sub-blocks are dropped entirely -- b §3 says a
    0-item 本題相關 emits neither header nor footnote."""
    whole = question is None or question.get('type') == 'whole_person'
    question_type = 'whole_person' if whole else 'scoped'
    S = set() if whole else (scoped_ids or set())

    grouped: Dict[str, List[Interaction]] = {}
    for it in candidates(scores):
        block_key = registry.block_for_interaction(it.ends, scores, S or None, question_type)
        if block_key is None:
            continue                      # scoped step 1: touches neither S nor 校準 nor R
        grouped.setdefault(block_key, []).append(it)

    blocks = []
    for block in registry.ordered_blocks(question_type):
        items = grouped.get(block.block_key)
        if not items:
            continue
        footnote = None
        if (not whole and block.block_key == 'related'
                and 1 <= len(items) <= SPARSE_FOOTNOTE_MAX):
            footnote = SPARSE_FOOTNOTE
        blocks.append(SelectedBlock(block.block_key, block.header_text, items, footnote))
    return blocks

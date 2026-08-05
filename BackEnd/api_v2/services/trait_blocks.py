"""Render one respondent trait as either a full block or an index line.

Formats are fixed by `a_LOG完成版模板_v2_20260727.md` §2.1 and `b_打包規則` §2 and must
match the client's v7 LOG examples character for character -- see
scripts/verify_trait_blocks.py.

    full block            index line
    ----------            ----------
    [特質 | CIA_05_B | 情境波動]        - CIA_01_A｜盡責｜高度自律：做事有一致的自我要求…
    行為面向：…
    管理重點：…
    可用於：①…②…③…
    禁止：①…②…③…

Which traits get which form is decided upstream (事項 05): the question's scoped set
becomes full blocks, everything else the respondent has becomes index lines. Risk and
calibration traits are NOT promoted to full blocks by virtue of being hit.

The four columns are injected verbatim. Two data quirks are handled here:

  * `ai_do` / `ai_dont` carry their own 「可用於：」/「禁止：」 prefix in the ANI, CIA and
    CSR rows but not in 53 of the 54 SPA rows. b §2 requires "缺則補、有則不重複加",
    otherwise CIA rows render 「可用於：可用於：…」 and SPA rows lose the column name.
  * The text comes from `ai_guidance.do_raw` / `dont_raw`, not the split lists -- the
    lists lose newlines on the 24 bullet-style rows.
"""

from typing import Optional

from ..database import db_session, TraitBand, TraitDefinition

DO_PREFIX = '可用於：'
DONT_PREFIX = '禁止：'


def _prefixed(text: str, prefix: str) -> str:
    """Add the column name only if the cell doesn't already start with it."""
    text = (text or '').strip()
    if not text:
        return ''
    return text if text.startswith(prefix.rstrip('：')) else prefix + text


def _guidance(band_row) -> tuple:
    g = band_row.ai_guidance or {}
    if isinstance(g, str):
        import json
        g = json.loads(g)
    return g.get('do_raw') or '', g.get('dont_raw') or ''


class TraitBlockRenderer:
    """Loads trait rows once per respondent set and renders the two block forms."""

    def __init__(self):
        self._bands = {}
        self._names = {}

    def _band_row(self, trait_id: str, band: str):
        key = (trait_id, band)
        if key not in self._bands:
            self._bands[key] = (db_session.query(TraitBand)
                                .filter(TraitBand.trait_id == trait_id,
                                        TraitBand.band == band)
                                .first())
        return self._bands[key]

    def _name_zh(self, trait_id: str) -> str:
        if trait_id not in self._names:
            row = (db_session.query(TraitDefinition)
                   .filter(TraitDefinition.trait_id == trait_id).first())
            self._names[trait_id] = row.name_zh if row else trait_id
        return self._names[trait_id]

    def semantic_label(self, trait_id: str, band: str) -> str:
        """The short band label, e.g. 情境波動. Used in both the trait block header and
        the two ends of an interaction header."""
        row = self._band_row(trait_id, band)
        return row.semantic_label if row else ''

    def render_full_block(self, trait_id: str, band: str) -> Optional[str]:
        row = self._band_row(trait_id, band)
        if row is None:
            return None
        do, dont = _guidance(row)
        lines = [f'[特質 | {trait_id}_{band} | {row.semantic_label}]',
                 f'行為面向：{(row.description or "").strip()}']
        if (row.management_focus or '').strip():
            lines.append(f'管理重點：{row.management_focus.strip()}')
        if do:
            lines.append(_prefixed(do, DO_PREFIX))
        if dont:
            lines.append(_prefixed(dont, DONT_PREFIX))
        return '\n'.join(lines)

    def render_index_line(self, trait_id: str, band: str) -> Optional[str]:
        row = self._band_row(trait_id, band)
        if row is None:
            return None
        return (f'- {trait_id}_{band}｜{self._name_zh(trait_id)}｜'
                f'{row.semantic_label}：{(row.description or "").strip()}')

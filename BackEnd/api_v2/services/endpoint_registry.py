"""Endpoint registry: the single place that answers "which endpoints does this
respondent hit, and which LOG sub-block does an interaction belong to".

Data source is the DB (`trait_endpoints` / `endpoint_blocks`), which is loaded from
the spec workbook's 09/10 sheets by scripts/migrate_traits_from_excel.py. Nothing
here hard-codes an endpoint, a trait id, or a sub-block header: adding an endpoint
(or a whole new endpoint type) is a data change, not a code change.

Two conventions from the spec that this module encapsulates:

  * `band = '*'` means a trait-level endpoint -- it matches whichever band the
    respondent is in. Risk endpoints are (trait, band) level; answer calibration
    is trait level. Callers never need to know the difference.
  * When one interaction matches several blocks, it is rendered ONCE, in the block
    with the lowest `priority` (decision of 2026-08-05).

`endpoint_level` (core / marginal / property_peak) is deliberately not used for any
branching: the 2026-07-27 ruling adopted all levels, so membership is the only test.
It is carried for auditing only.
"""

from typing import Dict, Iterable, List, Optional, Set

from ..database import db_session, TraitEndpoint, EndpointBlock

ANY_BAND = '*'

# Pseudo-type for "this interaction touches the question's scoped set S". It is not
# an endpoint, but it competes for the same slot, so it takes part in the same
# priority resolution. Its block is whichever block the data marks as scope-driven.
SCOPED_BLOCK_KEY = 'related'
WHOLE_PERSON_FALLBACK_BLOCK_KEY = 'other'


def _normalize_band(value):
    """'A (高)' -> 'A'. Some tables carry a Chinese descriptor suffix, respondents
    never do; normalizing both sides keeps the join honest."""
    if not value:
        return value
    return str(value).split('(')[0].strip()


class Block:
    __slots__ = ('block_key', 'question_type', 'header_text', 'sort_order',
                 'priority', 'footnote_rule')

    def __init__(self, row):
        self.block_key = row.block_key
        self.question_type = row.question_type
        self.header_text = row.header_text
        self.sort_order = row.sort_order
        self.priority = row.priority
        self.footnote_rule = row.footnote_rule

    def applies_to(self, question_type: str) -> bool:
        return self.question_type in ('both', question_type)

    def __repr__(self):
        return f'<Block {self.block_key} p={self.priority}>'


class EndpointRegistry:
    """Loaded once and cached; call refresh() after re-running the spec import."""

    def __init__(self):
        self._blocks: Dict[str, Block] = {}
        # (trait_id, band) -> {endpoint_type: block_key}; band may be ANY_BAND
        self._by_pair: Dict[tuple, Dict[str, str]] = {}
        self._loaded = False

    # -- loading -----------------------------------------------------------
    def refresh(self):
        blocks = db_session.query(EndpointBlock).all()
        endpoints = db_session.query(TraitEndpoint).all()

        self._blocks = {b.block_key: Block(b) for b in blocks}
        self._by_pair = {}
        for e in endpoints:
            key = (e.trait_id, _normalize_band(e.band))
            self._by_pair.setdefault(key, {})[e.endpoint_type] = e.block_key
        self._loaded = True
        return self

    def _ensure(self):
        if not self._loaded:
            self.refresh()

    # -- introspection -----------------------------------------------------
    @property
    def blocks(self) -> Dict[str, Block]:
        self._ensure()
        return self._blocks

    def header(self, block_key: str) -> Optional[str]:
        self._ensure()
        block = self._blocks.get(block_key)
        return block.header_text if block else None

    def ordered_blocks(self, question_type: str) -> List[Block]:
        """Blocks valid for this question type, in output order."""
        self._ensure()
        return sorted((b for b in self._blocks.values() if b.applies_to(question_type)),
                      key=lambda b: b.sort_order)

    def endpoint_types(self) -> Set[str]:
        self._ensure()
        return {t for types in self._by_pair.values() for t in types}

    def pairs_for_type(self, endpoint_type: str) -> Set[tuple]:
        """All (trait_id, band) registered under one type. band may be ANY_BAND.
        Used by audits that diff the DB against the spec's source-of-truth list."""
        self._ensure()
        return {pair for pair, types in self._by_pair.items() if endpoint_type in types}

    # -- hit testing -------------------------------------------------------
    def types_for(self, trait_id: str, band: str) -> Dict[str, str]:
        """{endpoint_type: block_key} this (trait, band) hits. Empty dict if none."""
        self._ensure()
        band = _normalize_band(band)
        hit = dict(self._by_pair.get((trait_id, ANY_BAND), {}))
        hit.update(self._by_pair.get((trait_id, band), {}))
        return hit

    def hits(self, trait_bands: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """Respondent's {trait_id: band} -> {trait_id: {endpoint_type: block_key}},
        only for traits that hit something."""
        result = {}
        for trait_id, band in trait_bands.items():
            types = self.types_for(trait_id, band)
            if types:
                result[trait_id] = types
        return result

    def hit_trait_ids(self, trait_bands: Dict[str, str],
                      endpoint_type: Optional[str] = None) -> Set[str]:
        """Trait ids hitting any endpoint, or a specific type.

        `hit_trait_ids(scores, 'risk')` is R in the packing rules; with no type it is
        the whole trigger set (calibration union R) used by the scoped-question filter.
        """
        hits = self.hits(trait_bands)
        if endpoint_type is None:
            return set(hits)
        return {t for t, types in hits.items() if endpoint_type in types}

    # -- block resolution --------------------------------------------------
    def resolve_block(self, block_keys: Iterable[str], question_type: str) -> Optional[str]:
        """An interaction matched these blocks -> the one it is rendered in.

        Lowest priority number wins; keys not valid for this question type are
        ignored. Returns None when nothing matches (caller decides the fallback).
        """
        self._ensure()
        candidates = [self._blocks[k] for k in set(block_keys)
                      if k in self._blocks and self._blocks[k].applies_to(question_type)]
        if not candidates:
            return None
        return min(candidates, key=lambda b: b.priority).block_key

    def block_for_interaction(self, end_traits: Iterable[str], trait_bands: Dict[str, str],
                              scoped_set: Optional[Set[str]], question_type: str) -> Optional[str]:
        """Decide the sub-block for one interaction.

        end_traits  : the two trait ids of the pair
        trait_bands : respondent's {trait_id: band}
        scoped_set  : S for a scoped question, None for whole-person/free-form
        """
        keys = set()
        if scoped_set and any(t in scoped_set for t in end_traits):
            keys.add(SCOPED_BLOCK_KEY)
        for t in end_traits:
            keys.update(self.types_for(t, trait_bands.get(t)).values())

        resolved = self.resolve_block(keys, question_type)
        if resolved:
            return resolved
        if question_type == 'whole_person':
            return WHOLE_PERSON_FALLBACK_BLOCK_KEY
        return None


registry = EndpointRegistry()

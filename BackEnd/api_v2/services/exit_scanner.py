r"""Scan an LLM answer for internal markers before it reaches the user (事項 09, b §7).

Three layers, from `exit_scanner_wordlist_v6_2.json`:

  hard patterns   9 always-on regexes: trait ids, band codes, 聯動/連動 scaffolding,
                  score leaks, Chinese band-zone wording, HR decisions, labelling
                  verdicts, demographics, integrity verdicts.
  trait names     84 Chinese trait names -- narrowed per request to the ones actually
                  injected, so a name that was never in the payload cannot false-positive.
  band labels     266 semantic labels, narrowed the same way. The wordlist itself records
                  why: 「回答中『快速轉換做法』『自信推進下』撞上 ANI_03/SPA_03 標籤，但該二
                  特質不在當次 payload，屬純詞彙撞名誤報；per-request 縮小後此類誤報歸零」.

Two traps this module exists to avoid:

1. `everyday_words` and `everyday_labels` are NESTED keys, not top level. Reading them
   from the root yields empty sets, which turns 84 names and 266 labels into hard blocks
   -- 「展現韌性」 would be flagged as a leak and every answer would end up in manual
   review. load_wordlist() fails loudly if either comes back empty.

2. The guard that separates everyday usage from construct usage has to tolerate adverbs
   between the word and the degree term. The pack's rule is
       詞 + (?=[偏程度分高低強弱]|傾向|指標|區間)
   which catches 「韌性偏高」 but not 「韌性很高」/「韌性較高」/「情緒反應相對較強」 -- 3 of the
   9 spec cases. Allowing an optional adverb run in the lookahead fixes all of them
   without inventing new blocks: 「這個挑戰很大」 still passes, because 大 is not a degree
   term. The adverbs are never a trigger on their own.
"""

import json
import os
import re
from typing import Iterable, List, Optional, Set

_CONFIG = os.path.join(os.path.dirname(__file__), '..', 'config',
                       'exit_scanner_wordlist_v6_2.json')

# 詞 + optional adverb run + degree term, or one of the explicit suffixes.
DEGREE_GUARD = r'(?=[很較相對更]{0,3}[偏程度分高低強弱]|傾向|指標|區間)'


class Hit:
    __slots__ = ('category', 'rule', 'text', 'start')

    def __init__(self, category, rule, text, start):
        self.category = category      # hard_pattern | trait_name | band_label
        self.rule = rule              # pattern id, or the word itself
        self.text = text
        self.start = start

    def __repr__(self):
        return f'{self.category}:{self.rule}={self.text!r}@{self.start}'

    def __eq__(self, other):
        return (self.category, self.rule, self.text, self.start) == \
               (other.category, other.rule, other.text, other.start)

    def __hash__(self):
        return hash((self.category, self.rule, self.text, self.start))


class Wordlist:
    def __init__(self, config_path=None):
        with open(os.path.abspath(config_path or _CONFIG), encoding='utf-8') as f:
            data = json.load(f)
        self.version = data.get('version')
        self.hard_patterns = [(p['id'], re.compile(p['pattern'])) for p in data['hard_patterns']]

        names = data['trait_names_blocklist']
        labels = data['band_labels_blocklist']
        self.all_names: Set[str] = set(names['all_names'])
        self.all_labels: Set[str] = set(labels['labels'])
        # Nested on purpose -- see the module docstring.
        self.everyday_words: Set[str] = set(names.get('everyday_words') or [])
        self.everyday_labels: Set[str] = set(labels.get('everyday_labels') or [])

        if not self.everyday_words or not self.everyday_labels:
            raise ValueError(
                'everyday whitelist came back empty -- check the nested paths '
                'trait_names_blocklist.everyday_words / band_labels_blocklist.everyday_labels. '
                'An empty whitelist hard-blocks every trait name and label.')


wordlist = Wordlist()


def _compile_group(words: Iterable[str], guarded: Set[str]):
    """One regex for the plain words, one for the everyday ones behind the degree guard."""
    plain = sorted((w for w in words if w and w not in guarded), key=len, reverse=True)
    every = sorted((w for w in words if w and w in guarded), key=len, reverse=True)
    plain_re = re.compile('|'.join(re.escape(w) for w in plain)) if plain else None
    every_re = re.compile('(?:' + '|'.join(re.escape(w) for w in every) + ')' + DEGREE_GUARD) \
        if every else None
    return plain_re, every_re


def _compile_identifiers(opaque_ids, name_bound_ids):
    """Patterns for respondent identifiers that must never reach the reader.

    Two shapes, because the two kinds of identifier carry very different collision risk:

      * `RESP_01` -- a position token this system invents. It cannot occur in natural
        Chinese, so it is banned outright wherever it appears.
      * the raw Traitty candidate_id -- `55`, `63`. Banning a bare two-digit number would
        hit 「1955 年」 and 「55%」, so it is only a hit directly after that respondent's
        name, which is the shape the model actually produced: 「許品優（55）」.

    The second rule guards a payload that no longer contains the id at all (see
    LOG_LABEL_PREFIX); it is here so that putting a raw id back into the LOG cannot
    silently reach the reader again.

    Each entry is (identifier, pattern): the identifier alone is what gets handed to the
    rewriter, because the second pattern's match spans the respondent's name too.
    """
    patterns = []
    for term in sorted(set(opaque_ids or ())):
        patterns.append((term, re.compile(re.escape(term))))
    for name, ident in sorted(set(name_bound_ids or ())):
        if not name or not ident:
            continue
        patterns.append((ident, re.compile(
            re.escape(name) + r'\s*[（(]?\s*' + re.escape(ident) + r'\s*[）)]?(?!\d)')))
    return patterns


class ExitScanner:
    """Built once per request and reused across segments -- the compile is the expensive
    part, the scan itself is negligible."""

    def __init__(self, injected_names: Optional[Iterable[str]] = None,
                 injected_labels: Optional[Iterable[str]] = None,
                 wl: Optional[Wordlist] = None,
                 opaque_ids: Optional[Iterable[str]] = None,
                 name_bound_ids: Optional[Iterable[tuple]] = None):
        self.wl = wl or wordlist
        names = set(injected_names) if injected_names is not None else set(self.wl.all_names)
        labels = set(injected_labels) if injected_labels is not None else set(self.wl.all_labels)
        self.injected_names = names
        self.injected_labels = labels
        self._name_plain, self._name_everyday = _compile_group(names, self.wl.everyday_words)
        self._label_plain, self._label_everyday = _compile_group(labels, self.wl.everyday_labels)
        self._id_patterns = _compile_identifiers(opaque_ids, name_bound_ids)

    @classmethod
    def for_log(cls, log) -> 'ExitScanner':
        return cls(log.injected_names, log.injected_labels,
                   opaque_ids=getattr(log, 'log_labels', None),
                   name_bound_ids=getattr(log, 'name_bound_ids', None))

    def scan(self, answer: str) -> List[Hit]:
        if not answer:
            return []
        hits: List[Hit] = []
        for rule_id, rx in self.wl.hard_patterns:
            for m in rx.finditer(answer):
                hits.append(Hit('hard_pattern', rule_id, m.group(0), m.start()))
        for ident, rx in self._id_patterns:
            for m in rx.finditer(answer):
                hits.append(Hit('identifier', ident, m.group(0), m.start()))
        for category, plain, every in (('trait_name', self._name_plain, self._name_everyday),
                                       ('band_label', self._label_plain, self._label_everyday)):
            for rx in (plain, every):
                if rx is None:
                    continue
                for m in rx.finditer(answer):
                    hits.append(Hit(category, m.group(0), m.group(0), m.start()))
        return sorted(set(hits), key=lambda h: (h.start, h.category, h.rule))

    def is_clean(self, answer: str) -> bool:
        return not self.scan(answer)

    def banned_terms(self, hits: Iterable[Hit]) -> List[str]:
        """The words to hand back to the model when asking it to rewrite a segment.
        Only the concrete terms -- hard-pattern matches are shown as-is.

        An identifier hit spans the respondent's name as well (「許品優（55）」), and handing
        that back would read as an instruction to stop naming the person -- which system
        prompt rule 4 requires. Only the identifier itself is forbidden.
        """
        return sorted({h.rule if h.category == 'identifier' else h.text for h in hits})

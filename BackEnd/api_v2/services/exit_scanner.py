r"""Scan an LLM answer for internal markers before it reaches the user (事項 09, b §7).

Three layers, from `exit_scanner_wordlist_v6_2.json`:

  reminder mask   規範乙-8 的制式提醒句先遮罩再掃，見 ROLE_FIT_REMINDER。
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

# 全域輸出規範乙-8（2026-09-17 客戶更新）要求的制式提醒句。適任／排序類提問出現時，
# 模型必須原句附上這一段。
#
# 為什麼要遮罩：`hr_decision` 攔的是 `適合擔任[^，。；]{0,8}(職|主管|經理|崗位)`，而模型
# 寫這句提醒時幾乎一定會複述題意（「關於是否適合擔任區域主管一職…」）。命中之後
# `banned_terms()` 會把命中的字串丟回去要模型別再寫，模型很可能連提醒句一起拿掉——
# 新規則被既有的攔截機制自己消掉。實測過提醒句本身：九條 hard_patterns 全部 0 命中，
# 危險的是它周圍的複述。
#
# 遮罩字元用 \x00 而不是空白：`band_code` 的樣式是 `[ABC]\s*[段屬]`，拿空白當遮罩等於
# 在答案裡插入 `\s`，有機會讓遮罩前後的字湊成一次假命中。\x00 不出現在任何一條
# hard_patterns、不是 \s、也不在特質名與 band 標籤裡。等長替換，`Hit.start` 不會失真。
ROLE_FIT_REMINDER = ('不可將AI回答用於人選擔任某職務或角色是否適任及排序順位之單一參考，'
                     '需多方驗證後決策')
_REMINDER_MASK = '\x00'
# 模型不會逐字照抄。2026-09-18 的實測輸出寫的是「不可將 AI 回答用於…」，而制式句是
# 「不可將AI回答用於…」——差在英文縮寫兩側各一個空白，逐字比對就此落空，遮罩等於沒開。
# 所以改成允許字元之間出現任意空白（半形、全形都算），遮罩長度仍等於實際命中的長度，
# `Hit.start` 不會失真。
_REMINDER_RE = re.compile(r'\s*'.join(re.escape(ch) for ch in ROLE_FIT_REMINDER))


def mask_reminder(answer: str):
    """把制式提醒句換成等長遮罩，回傳 (遮罩後的字串, [(起, 迄), ...])。

    比對允許字元之間有空白（見 `_REMINDER_RE`），但仍要求逐字同序。模型寫出語意相同
    而措辭不同的版本時不在此列——那種情況由 `completeness_check` 的決策提醒檢查處理，
    不是掃描器的事。
    """
    if not answer:
        return answer, []
    spans = []
    out = []
    i = 0
    for m in _REMINDER_RE.finditer(answer):
        out.append(answer[i:m.start()])
        out.append(_REMINDER_MASK * (m.end() - m.start()))
        spans.append((m.start(), m.end()))
        i = m.end()
    if not spans:
        return answer, []
    out.append(answer[i:])
    return ''.join(out), spans


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
        # 規範乙-8 的制式提醒句不受掃描 -- 見 ROLE_FIT_REMINDER。位移不變，所以
        # `Hit.start` 仍然指向原字串的位置。
        answer, _ = mask_reminder(answer)
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

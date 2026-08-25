"""Traditional-Chinese normalisation for LLM-generated conversation titles.

Why this exists at all: the title prompt asks for 繁體中文（台灣用語）but reasoning models
(deepseek-v4-flash) do not reliably honour it, so a title occasionally comes back in
Simplified Chinese. 972851d added `OpenCC('s2twp').convert(raw_title)` as the safety net.

Why that net had to be replaced: Simplified -> Traditional is one-to-many, so running it
over text that is *already* Traditional does not leave that text alone -- it rewrites it.
Measured against the shipped dictionaries:

    游淑芬 -> 遊淑芬      余明哲 -> 餘明哲      范先生 -> 範先生
    干預   -> 幹預        公布   -> 公佈        台北   -> 臺北
    了解   -> 瞭解        采訪   -> 採訪        布置   -> 佈置

游 / 余 / 范 are common Taiwanese surnames, so any session whose respondent had one got
their name spelled wrong in the history list -- which is exactly what the client reported
on 2026-08-24. The conversion was firing on 100% of titles to protect against the small
fraction that actually came back Simplified.

So the rule here is: convert only when the title genuinely contains Simplified Chinese,
and never let a conversion touch a respondent's name.

A second, unrelated class of damage in the same report -- 「面對」written as 「麵對」-- does
*not* come from OpenCC (no dictionary in the package produces 麵對; the 124 inputs it does
turn into 麵 are all noodle words). That one is the model doing its own bad Simplified ->
Traditional pass, and it is handled by `fix_known_misconversions` below.
"""

import os
from typing import Iterable, Optional

from ..config.settings import Config

# OpenCC config used when the text really is Simplified. `s2twp` -- what 972851d used --
# additionally applies TWPhrases, which is Taiwanese *vocabulary substitution* rather than
# script conversion (公布 -> 公佈, 了解 -> 瞭解, 軟件 -> 軟體). Rewriting a title the model
# already wrote correctly is not this net's job, so the phrase layer is dropped.
OPENCC_CONFIG = 's2tw'

# Off by default; see Config.TITLE_OPENCC_ENABLED for why. Read once at import, like every
# other flag in settings.py -- it is a deploy-time switch, not a per-request one. Module
# level rather than read inside the function so tests can flip it without touching os.environ.
CONVERT_ENABLED = Config.TITLE_OPENCC_ENABLED

_simplified_only = None      # frozenset of characters that cannot be Traditional Chinese
_converter = None
_warned = False


def _dictionary_path(filename):
    import opencc
    return os.path.join(os.path.dirname(opencc.__file__), 'dictionary', filename)


def _load_simplified_only():
    """Characters that exist only in Simplified Chinese, from OpenCC's own dictionary.

    STCharacters.txt maps each Simplified character to its Traditional candidates:

        对	對             <- 对 is never valid Traditional
        游	游 遊          <- 游 IS valid Traditional (it is its own first candidate)
        面	面 麪          <- so is 面

    Taking `keys - values` therefore yields the characters that *cannot* appear in correct
    Traditional text, and leaves every shared character out of the set. That is the whole
    reason this is derived from the dictionary rather than from `s2t(c) != c`: the latter
    flags 游 (it converts to 遊) and would re-introduce the bug this module exists to fix.
    """
    keys, values = set(), set()
    with open(_dictionary_path('STCharacters.txt'), encoding='utf-8') as f:
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 2:
                continue
            keys.add(parts[0])
            for candidate in parts[1].split(' '):
                values.update(candidate)
    return frozenset(keys - values)


def simplified_only_chars():
    """Cached `_load_simplified_only`. Empty set if the dictionary cannot be read.

    Failing to an empty set means `contains_simplified` is always False and no conversion
    ever runs. That is the safe direction: an occasional Simplified title is a cosmetic
    defect, whereas converting text that is already Traditional corrupts respondents'
    names on every session. The warning makes the degraded state visible in the log.
    """
    global _simplified_only, _warned
    if _simplified_only is None:
        try:
            _simplified_only = _load_simplified_only()
        except Exception as e:
            _simplified_only = frozenset()
            if not _warned:
                _warned = True
                print(f"WARNING: [title_zh] OpenCC dictionary unreadable ({e}); "
                      f"Simplified-Chinese detection is disabled for session titles.")
    return _simplified_only


def contains_simplified(text: Optional[str]) -> bool:
    """True only when `text` holds a character that cannot be Traditional Chinese."""
    chars = simplified_only_chars()
    return any(c in chars for c in (text or ''))


def _convert(text):
    global _converter
    if _converter is None:
        from opencc import OpenCC
        _converter = OpenCC(OPENCC_CONFIG)
    return _converter.convert(text)


def restore_names(text: str, candidate_names: Optional[Iterable[str]]) -> str:
    """Put respondents' names back exactly as the database spells them.

    Second line of defence, for the branch where conversion did run: the title was
    genuinely Simplified, we converted the whole string, and a name inside it went through
    the same one-to-many mapping (游淑芬 -> 遊淑芬). The backend already holds the correct
    spelling in `candidate_names`, so the converted form is simply undone.

    Longest name first, so a name that contains another name is not half-replaced.
    """
    for name in sorted({n for n in (candidate_names or []) if n}, key=len, reverse=True):
        converted = _convert(name)
        if converted != name and converted in text:
            text = text.replace(converted, name)
    return text


# Food words are the only place 麵 is correct. A talent-assessment title will not mention
# noodles, so an unguarded 麵 in one is the model's own bad conversion of 面 -- observed as
# 「麵對」in the 2026-08-24 client report, but the same slip produces 麵試 / 方麵 / 全麵 /
# 層麵 too, which is why this is a rule about the character rather than a list of words.
MIAN_FOOD_WORDS = ('麵包', '麵條', '麵粉', '麵店', '麵食', '麵線',
                   '拉麵', '泡麵', '湯麵', '炒麵', '速食麵', '義大利麵')


def fix_known_misconversions(text: str) -> str:
    """Repair Traditional-variant slips the model makes on its own.

    These survive `contains_simplified` by construction: 麵 *is* a Traditional character,
    so the text contains no Simplified at all and nothing above it fires. Kept as an
    explicit, extendable list rather than a general rule because picking the right variant
    of a one-to-many mapping is not decidable from the characters alone.
    """
    if '麵' in text and not any(w in text for w in MIAN_FOOD_WORDS):
        text = text.replace('麵', '面')
    return text


def normalize_title(raw_title: Optional[str],
                    candidate_names: Optional[Iterable[str]] = None) -> str:
    """The safety net `background_generate_title` applies to the model's title.

    With `CONVERT_ENABLED` off (the default) no OpenCC conversion happens at all -- the
    title is the model's own Traditional Chinese, constrained by the prompt, with the
    respondents' names supplied by the backend rather than by the model. `麵 -> 面` still
    runs: it is a fixed substitution for a slip the model makes on its own, not a
    script conversion, so the reason the OpenCC layer is off does not apply to it.

    With it on, Traditional input is still returned byte-identical -- only genuinely
    Simplified input is converted, and names survive either way.
    """
    text = raw_title or ''
    if not text:
        return text
    if CONVERT_ENABLED and contains_simplified(text):
        text = restore_names(_convert(text), candidate_names)
    return fix_known_misconversions(text)

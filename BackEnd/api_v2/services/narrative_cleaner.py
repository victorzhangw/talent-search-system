r"""Deterministic stripping of interaction narratives (事項 02, b §0 T5).

The 08 sheet stores each narrative with its pairing information as a lead-in clause:

    與 CIA_22 (紀律遵循度) A聯動：表現為「…」。他在…
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^ trait_id + 中文名 + band, all three of which the
                                 exit scanner is designed to keep out of the output

The pairing is carried by the interaction block header instead ([交互 | A_band × B_band |
label × label]), so the lead-in is removed here. Rules and their order come from the
client's regex_pack_v6_2.json, loaded as data from config/ so a spec update flows in
without a code change.

Scope: narrative BODY text only. Never run these over a whole assembled LOG -- rule
`strip_trait_id_refs` would eat the ID in every block header, which b §6 requires to
survive (the runtime LLM needs it to disambiguate same-named traits across tests).

Two deliberate deviations from the pack, both measured against all 2,389 rows:

  * `strip_python_list_wrapper` is NOT applied. It targets the MUST DO field, not
    narratives, and its pattern `^\[?'?|'?\]?$` matches the empty string, so it "hits"
    every row while doing nothing -- but it would silently eat a leading '[' if a
    narrative ever had one. The field it was meant to patch is fixed at the source now
    (ai_guidance.do_raw), so the workaround is unnecessary here.
  * The chained lead-in form 「與 CIA_06 (條理性) C 與 CIA_07 (完美主義) A：…」 used to be
    handled by a regex written here, because the pack had no rule for it. It is now
    `strip_chained_opening` in the pack, where b's 「語意都住在引用的資料表裡」 says it
    belongs; nothing is hard-coded here any more. It stays dormant (0 rows in V6.3/V7,
    4 in V6.1) but is kept as a defence: the client's 2026-09-17 V7 fixed those 4 rows,
    and a rule that only exists because the data currently happens to be clean is the
    kind that gets deleted right before the data stops being clean.

  * `rewrite_band_zone_zhong` (added V7-20260918) rewrites the band sense of 「中段」.
    V7 replaced 19 `B 段` and 3 `B 屬` with 「中段」, which the exit scanner's `band_code`
    (`[ABC]\s*段`) and `band_zone_zh` (`[高中低](分區|分組|分群|區間)`) both miss -- so the
    change swapped a wording that would have been caught and rewritten for one that
    reaches the reader untouched. The rule is deliberately narrow (sentence-initial,
    followed by one of five observed continuations): 5 rows use 「中段」 in its everyday
    sense (「在任務中段設確認點」) and a whole-word block would eat them.
"""

import json
import os
import re

_CONFIG = os.path.join(os.path.dirname(__file__), '..', 'config', 'regex_pack_v6_2.json')

# Applied in this order; ids not listed here are not narrative rules.
# `strip_chained_opening` runs immediately after `strip_opening_clause`: the standard
# form is stripped first, and whatever is left that still opens with a trait id is the
# chained form. `rewrite_band_zone_zhong` runs before the id/paren strippers because it
# keys off sentence punctuation those rules do not touch.
NARRATIVE_RULE_IDS = ('strip_opening_clause', 'strip_chained_opening',
                      'rewrite_band_zone_zhong', 'strip_paren_codes',
                      'strip_trait_id_refs', 'strip_empty_parens')


class NarrativeCleaner:
    def __init__(self, config_path=None):
        with open(os.path.abspath(config_path or _CONFIG), encoding='utf-8') as f:
            pack = json.load(f)
        self.version = pack.get('version')
        by_id = {r['id']: r for r in pack['rules']}
        missing = [rid for rid in NARRATIVE_RULE_IDS if rid not in by_id]
        if missing:
            raise ValueError(f'regex_pack is missing expected rules: {missing}')
        self.rules = [(rid, re.compile(by_id[rid]['pattern']), by_id[rid].get('replace', ''))
                      for rid in NARRATIVE_RULE_IDS]

    def clean(self, narrative: str) -> str:
        if not narrative:
            return narrative
        text = narrative
        for _rid, rx, repl in self.rules:
            text = rx.sub(repl, text)
        return text.strip()


cleaner = NarrativeCleaner()

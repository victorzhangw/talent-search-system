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
  * A defensive fallback for the chained lead-in form
    「與 CIA_06 (條理性) C 與 CIA_07 (完美主義) A：…」, which the pack's pattern does not
    match (it requires 「聯動：」). That form appears 4 times in the V6.1 spec and 0 times
    in V6.2/V6.3, so it is dormant -- but if the 08 sheet is ever regenerated with it,
    the pack's rule alone would pass the lead-in straight through into the payload.
"""

import json
import os
import re

_CONFIG = os.path.join(os.path.dirname(__file__), '..', 'config', 'regex_pack_v6_2.json')

# Applied in this order; ids not listed here are not narrative rules.
NARRATIVE_RULE_IDS = ('strip_opening_clause', 'strip_paren_codes',
                      'strip_trait_id_refs', 'strip_empty_parens')

# Requires a trait id before the colon, so it cannot truncate a body that merely
# happens to start with 「與」.
CHAINED_OPENING_RE = re.compile(r'^與\s*[A-Z]{3}_\d+.*?[：:]\s*')


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
        for rid, rx, repl in self.rules:
            text = rx.sub(repl, text)
            if rid == 'strip_opening_clause':
                text = CHAINED_OPENING_RE.sub('', text)
        return text.strip()


cleaner = NarrativeCleaner()

"""Exit scanner acceptance: the spec's case table, the 9 hard patterns, and narrowing.

Usage:
    python scripts/verify_exit_scanner.py

The everyday-word cases come verbatim from the acceptance table in
`_ LOG 實作補充說明 for victor.txt`; three extra false-positive guards are added because
"block more" is only correct if it doesn't also block ordinary Chinese.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

from api_v2.services.exit_scanner import ExitScanner, Wordlist, wordlist  # noqa: E402
from api_v2.services.log_assembler import Respondent, assemble  # noqa: E402
from api_v2.services.question_table import table  # noqa: E402

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


# (sentence, should_block). First 11 are the spec's acceptance table.
EVERYDAY_CASES = [
    ('面對挑戰時展現韌性', False),
    ('韌性偏高', True),
    ('韌性很高', True),
    ('韌性較高', True),
    ('建立團隊信任', False),
    ('信任程度偏低', True),
    ('快速轉換做法', False),
    ('快速轉換傾向明顯', True),
    ('情緒反應可能較明顯', False),
    ('情緒反應分數較高', True),
    ('情緒反應相對較強', True),
    # false-positive guards: everyday words in ordinary sentences
    ('這個挑戰很大', False),
    ('他願意表達感謝', False),
    ('團隊需要承諾', False),
]

HARD_CASES = [
    ('trait_id', '這與 CIA_05 有關'),
    ('band_code', '他落在 B 段'),
    ('linkage', '兩者形成聯動關係'),
    ('score_leak', '此項得分 78 分'),
    ('band_zone_zh', '他屬於高分區'),
    ('hr_decision', '建議錄取'),
    ('label_verdict', '他就是不適任'),
    ('demographic', '他 35 歲'),
    ('integrity_verdict', '此人表裡不一'),
]


def main():
    print(f'\nwordlist {wordlist.version}')

    print('\n[1] Nested whitelist paths (trap 1)')
    check('everyday_words loaded, 20 entries', len(wordlist.everyday_words) == 20,
          len(wordlist.everyday_words))
    check('everyday_labels loaded, 4 entries', len(wordlist.everyday_labels) == 4,
          sorted(wordlist.everyday_labels))
    check('84 trait names / 266 labels',
          len(wordlist.all_names) == 84 and len(wordlist.all_labels) == 266,
          f'{len(wordlist.all_names)} / {len(wordlist.all_labels)}')
    check('an empty whitelist is rejected at load time, not silently accepted',
          _raises_on_empty_whitelist())

    print('\n[2] everyday guard -- the spec acceptance table (trap 2)')
    # Scan with every name and label enabled so the guard, not narrowing, decides.
    full = ExitScanner()
    passed = 0
    for sentence, should_block in EVERYDAY_CASES:
        blocked = bool(full.scan(sentence))
        ok = blocked == should_block
        passed += ok
        if not ok:
            check(f'{sentence} -> expected {"block" if should_block else "pass"}', False,
                  full.scan(sentence)[:2])
    check(f'all {len(EVERYDAY_CASES)} cases behave as specified',
          passed == len(EVERYDAY_CASES), f'{passed}/{len(EVERYDAY_CASES)}')

    print('\n[3] Non-everyday names block on sight, no degree term needed')
    for term in ('心理特權', '社會期望反應', '目標效能感'):
        check(f'{term} blocked bare', bool(full.scan(f'他的{term}值得注意')),
              full.scan(f'他的{term}值得注意')[:1])

    print('\n[4] The 9 hard patterns each fire')
    for rule_id, sentence in HARD_CASES:
        hits = [h for h in full.scan(sentence) if h.category == 'hard_pattern']
        check(f'{rule_id}: {sentence}', any(h.rule == rule_id for h in hits),
              [h.rule for h in hits])
    check('score_leak does not fire on 分鐘 / 分析',
          not [h for h in full.scan('花了 30 分鐘做分析') if h.rule == 'score_leak'])

    print('\n[5] per-request narrowing')
    narrow = ExitScanner(injected_names={'韌性'}, injected_labels=set())
    check('an injected everyday name still needs the degree guard',
          not narrow.scan('展現韌性') and bool(narrow.scan('韌性偏高')))
    check('a label that was NOT injected does not fire',
          not narrow.scan('快速轉換傾向明顯'),
          narrow.scan('快速轉換傾向明顯')[:1])
    check('the same sentence fires when that label IS injected',
          bool(ExitScanner(injected_names=set(),
                           injected_labels={'快速轉換'}).scan('快速轉換傾向明顯')))
    check('hard patterns stay on regardless of narrowing',
          bool(narrow.scan('這與 CIA_05 有關')))

    print('\n[6] Built from a real assembly')
    q = table.get('如何面對困難、壓力、挑戰')
    r = [Respondent('王智弘', 'RESP_R2', {'CIA_05': 'B', 'CIA_01': 'A', 'CIA_33': 'A'})]
    log = assemble(r, q)
    scanner = ExitScanner.for_log(log)
    check('scanner narrows to the payload vocabulary',
          scanner.injected_names and scanner.injected_names <= wordlist.all_names,
          sorted(scanner.injected_names))
    check('labels narrowed too', scanner.injected_labels <= wordlist.all_labels,
          sorted(scanner.injected_labels))
    check('the payload itself would be flagged (it is full of internal markers)',
          bool(scanner.scan(log.to_log_text())))
    clean = '他在高壓情境下通常能維持節奏，建議主管在連續高壓期主動關心狀態。'
    check('a clean business-language answer passes', scanner.is_clean(clean),
          scanner.scan(clean)[:3])

    print('\n[7] banned_terms feeds the rewrite request')
    hits = full.scan('他的韌性偏高，且與 CIA_05 有關')
    terms = full.banned_terms(hits)
    check('returns the concrete offending terms', '韌性' in terms and 'CIA_05' in terms, terms)

    print('\n[8] False-positive exposure (informational -- needs a content-side ruling)')
    # A short trait name that is NOT whitelisted is a hard block: whenever that trait is
    # in the payload, the most natural Chinese word for the behaviour becomes unusable and
    # every answer using it goes to rewrite.
    risky = sorted(n for n in wordlist.all_names
                   if len(n) <= 3 and n not in wordlist.everyday_words)
    print(f'  {len(risky)} trait names are <=3 chars and hard-blocked: {"、".join(risky)}')
    for term in ('盡責', '謙虛', '寬恕'):
        if term in risky:
            s = ExitScanner(injected_names={term}, injected_labels=set())
            sentence = f'他做事{term}，交付品質穩定。'
            print(f'  e.g. 「{sentence}」 -> '
                  f'{"blocked" if s.scan(sentence) else "passes"} when {term} is injected')
    print('  Compare: 審慎 and 誠懇 ARE whitelisted, so 「行事審慎」 passes. The list looks')
    print('  under-inclusive rather than wrong; raised with the content side, not patched here')
    print('  (the wordlist is client data).')

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


def _raises_on_empty_whitelist():
    import json
    import tempfile
    data = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'api_v2', 'config',
                                       'exit_scanner_wordlist_v6_2.json'), encoding='utf-8'))
    data['trait_names_blocklist']['everyday_words'] = []
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
        path = f.name
    try:
        Wordlist(path)
        return False
    except ValueError:
        return True
    finally:
        os.unlink(path)


if __name__ == '__main__':
    sys.exit(main())

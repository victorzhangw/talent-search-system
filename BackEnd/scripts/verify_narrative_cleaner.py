"""Re-clean every interaction narrative in the client's v7 LOG examples and diff.

Usage:
    python scripts/verify_narrative_cleaner.py

Takes each [交互 | …] block the client's pipeline produced, looks the pair up in
trait_interactions, runs our cleaner over the stored narrative, and requires a
character-for-character match. Also asserts the properties the exit scanner depends on
across all 2,389 rows, not just the ones the examples happen to cover.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

from sqlalchemy import text  # noqa: E402
from api_v2.database.connection import get_db_engine  # noqa: E402
from api_v2.services.narrative_cleaner import cleaner  # noqa: E402

PKG = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', '0730',
                   'Traitty_調整_20260728＿final')
EXAMPLES = ['新版LOG範例_匡列型_壓力題_v7.txt',
            '新版LOG範例_全人型_雙測驗_v7.txt',
            '新版LOG範例_多人型_會議團隊_v7.txt']

HEADER_RE = re.compile(r'^\[交互 \| ([A-Z]{3}_\d+)_([ABC]) × ([A-Z]{3}_\d+)_([ABC]) \| (.+)\]$')
TRAIT_ID_RE = re.compile(r'[A-Z]{3}_\d+')

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def main():
    eng = get_db_engine()
    with eng.connect() as c:
        rows = c.execute(text("""SELECT primary_trait_id, split_part(primary_band,'(',1) pb,
                                        trigger_trait_id, trigger_band, narrative
                                 FROM trait_interactions
                                 WHERE narrative IS NOT NULL ORDER BY id""")).fetchall()
    by_pair = {}
    for r in rows:
        by_pair.setdefault((r.primary_trait_id, r.pb.strip(), r.trigger_trait_id, r.trigger_band),
                           r.narrative)
    print(f'\nloaded {len(rows)} narratives, regex_pack {cleaner.version}')

    total = matched = 0
    unmatched_lookup = []
    mismatched = []

    for name in EXAMPLES:
        lines = open(os.path.join(PKG, name), encoding='utf-8').read().split('\n')
        for i, line in enumerate(lines):
            m = HEADER_RE.match(line)
            if not m:
                continue
            a, ab, b, bb, _ = m.groups()
            body = lines[i + 1] if i + 1 < len(lines) else ''
            if not body.strip():          # header with no narrative line in the example
                continue
            total += 1
            stored = by_pair.get((a, ab, b, bb)) or by_pair.get((b, bb, a, ab))
            if stored is None:
                unmatched_lookup.append(f'{a}_{ab} x {b}_{bb}')
                continue
            actual = cleaner.clean(stored)
            if actual == body:
                matched += 1
            else:
                mismatched.append((name, f'{a}_{ab} x {b}_{bb}', body, actual))

    print(f'\n[1] Narratives re-cleaned and compared ({total} interaction blocks in the examples)')
    check('every pair in the examples exists in trait_interactions',
          not unmatched_lookup, unmatched_lookup[:3])
    check('every narrative matches character for character',
          not mismatched, f'{len(mismatched)} mismatched, {matched} matched')
    for name, pair, exp, act in mismatched[:3]:
        print(f'       {name} {pair}')
        print(f'         expected: {exp[:100]}')
        print(f'         actual  : {act[:100]}')

    print('\n[2] Properties across all 2,389 stored narratives')
    cleaned = [cleaner.clean(r.narrative) for r in rows]
    check('no lead-in clause survives',
          not [t for t in cleaned if t.startswith('與')],
          len([t for t in cleaned if t.startswith('與')]))
    check('no trait id survives in any body',
          not [t for t in cleaned if TRAIT_ID_RE.search(t)],
          len([t for t in cleaned if TRAIT_ID_RE.search(t)]))
    check('no 聯動 wording survives', not [t for t in cleaned if '聯動' in t],
          len([t for t in cleaned if '聯動' in t]))
    check('no empty parens', not [t for t in cleaned if re.search(r'[（(]\s*[)）]', t)])
    check('cleaning never empties a narrative', all(t.strip() for t in cleaned))

    print('\n[3] The cleaner is body-only (must never be run over an assembled LOG)')
    header = '[特質 | CIA_05_B | 情境波動]'
    check('a block header would lose its ID if cleaned -- documented, not a bug',
          'CIA_05' not in cleaner.clean(header), repr(cleaner.clean(header)))

    print('\n[4] Defensive rule for the chained lead-in (V6.1 had 4, V6.2/V6.3 have 0)')
    chained = '與 CIA_06 (條理性) C 與 CIA_07 (完美主義) A：表現為「同時要求流程與細節的人」。'
    out = cleaner.clean(chained)
    check('chained form is stripped', out == '表現為「同時要求流程與細節的人」。', repr(out))
    keeps = '與同儕協作時：他偏好先把話講清楚。'
    check('a body that merely starts with 與 is left alone', cleaner.clean(keeps) == keeps,
          repr(cleaner.clean(keeps)))

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

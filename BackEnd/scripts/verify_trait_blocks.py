"""Render every trait block in the client's v7 LOG examples from our DB and diff.

Usage:
    python scripts/verify_trait_blocks.py

This is the DoD 第 1 條 check applied to 事項 05's output only: take the trait blocks
and index lines the client's own pipeline produced, re-render them from trait_bands /
trait_definitions, and require a character-for-character match.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

from api_v2.services.trait_blocks import TraitBlockRenderer, DO_PREFIX, DONT_PREFIX  # noqa: E402

PKG = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', '0730',
                   'Traitty_調整_20260728＿final')
EXAMPLES = ['新版LOG範例_匡列型_壓力題_v7.txt',
            '新版LOG範例_全人型_雙測驗_v7.txt',
            '新版LOG範例_多人型_會議團隊_v7.txt']

HEADER_RE = re.compile(r'^\[特質 \| ([A-Z]{3}_\d+)_([ABC]) \| (.+)\]$')
INDEX_RE = re.compile(r'^- ([A-Z]{3}_\d+)_([ABC])｜')

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def blocks_in(lines):
    """Yield (trait_id, band, [block lines]) for each full trait block."""
    i = 0
    while i < len(lines):
        m = HEADER_RE.match(lines[i])
        if m:
            j = i + 1
            while j < len(lines) and lines[j].strip() and not HEADER_RE.match(lines[j]) \
                    and not lines[j].startswith('#'):
                j += 1
            yield m.group(1), m.group(2), lines[i:j]
            i = j
        else:
            i += 1


def main():
    renderer = TraitBlockRenderer()
    total_blocks = total_index = 0
    mismatched_blocks = []
    mismatched_index = []
    spa_seen = prefixed_ok = 0

    for name in EXAMPLES:
        lines = open(os.path.join(PKG, name), encoding='utf-8').read().split('\n')

        for trait_id, band, expected in blocks_in(lines):
            total_blocks += 1
            actual = (renderer.render_full_block(trait_id, band) or '').split('\n')
            if actual != expected:
                mismatched_blocks.append((name, trait_id, band, expected, actual))
            if trait_id.startswith('SPA'):
                spa_seen += 1
                if any(l.startswith('可用於：') for l in actual):
                    prefixed_ok += 1

        for line in lines:
            m = INDEX_RE.match(line)
            if m:
                total_index += 1
                actual = renderer.render_index_line(m.group(1), m.group(2))
                if actual != line:
                    mismatched_index.append((name, m.group(1), m.group(2), line, actual))

    # b §2 requires the column name be added when the cell lacks it ("缺則補"), and calls
    # the un-prefixed SPA output a defect ("SPA 會缺欄名"; data-side fix is on the client's
    # README backlog). The v7 examples were rendered before that rule was applied, so an
    # SPA block that differs ONLY by the prefix we added is expected, not a regression.
    def prefix_only(expected, actual):
        if len(expected) != len(actual):
            return False
        for e, a in zip(expected, actual):
            if e == a:
                continue
            if not (a.startswith(DO_PREFIX) and a[len(DO_PREFIX):] == e) and \
               not (a.startswith(DONT_PREFIX) and a[len(DONT_PREFIX):] == e):
                return False
        return True

    known = [m for m in mismatched_blocks if prefix_only(m[3], m[4])]
    unknown = [m for m in mismatched_blocks if not prefix_only(m[3], m[4])]

    print(f'\n[1] Full trait blocks re-rendered from DB ({total_blocks} blocks)')
    check('no unexpected difference from the examples', not unknown,
          f'{len(unknown)} unexplained of {len(mismatched_blocks)} mismatched')
    for name, tid, band, exp, act in unknown[:3]:
        print(f'       {name} {tid}_{band}')
        for e, a in zip(exp, act):
            if e != a:
                print(f'         expected: {e[:100]}')
                print(f'         actual  : {a[:100]}')
                break
        if len(exp) != len(act):
            print(f'         line count {len(exp)} vs {len(act)}')
    check('all remaining differences are the b §2 column-name prefix',
          all(t.startswith('SPA') for _, t, _, _, _ in known),
          f'{len(known)} blocks, traits {sorted({t for _, t, _, _, _ in known})}')
    if known:
        print('  [NOTE] deliberate: b §2 「缺則補、有則不重複加」 vs examples rendered before it.')
        print(f'         affects {len(known)} SPA blocks; client README lists the data-side')
        print('         fix (補齊 SPA 53 列前綴) as pending, program-side normalization stands in.')

    print(f'\n[2] Index lines re-rendered from DB ({total_index} lines)')
    check('every index line matches the example character for character',
          not mismatched_index, f'{len(mismatched_index)} mismatched')
    for name, tid, band, exp, act in mismatched_index[:3]:
        print(f'       {name} {tid}_{band}')
        print(f'         expected: {exp[:110]}')
        print(f'         actual  : {act[:110]}')

    print('\n[3] Column-name normalization (b §2 「缺則補、有則不重複加」)')
    check('SPA blocks get the 可用於 prefix added', spa_seen == 0 or prefixed_ok == spa_seen,
          f'{prefixed_ok}/{spa_seen} SPA blocks in the examples')
    doubled = [(n, t, b) for n, t, b, e, a in mismatched_blocks
               if any('可用於：可用於' in l or '禁止：禁止' in l for l in a)]
    check('no doubled column name anywhere', not doubled, doubled[:3])

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

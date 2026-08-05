"""Reproduce the interaction sub-blocks of the client's v7 LOG examples.

Usage:
    python scripts/verify_interaction_selector.py

For each respondent in each example: recover P from the trait region, re-run selection,
and require the sub-block headers, their order, and the interaction blocks inside them
(header line + narrative) to come out character for character identical.

The examples never exercise the sparse-footnote or empty-sub-block rules (b §3 註記), so
those are covered by constructed cases at the end.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

from api_v2.services.question_table import table  # noqa: E402
from api_v2.services.trait_blocks import TraitBlockRenderer  # noqa: E402
from api_v2.services.interaction_selector import (select_interactions, candidates,  # noqa: E402
                                                  SPARSE_FOOTNOTE, _all_rows)

PKG = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', '0730',
                   'Traitty_調整_20260728＿final')
B_DOC = os.path.join(PKG, 'b_打包規則_v2_20260727.md')

CASES = [
    ('新版LOG範例_匡列型_壓力題_v7.txt', '如何面對困難、壓力、挑戰'),
    ('新版LOG範例_全人型_雙測驗_v7.txt', '個人使用說明書(主管)'),
    ('新版LOG範例_多人型_會議團隊_v7.txt', '打造高效會議團隊'),
]

RESPONDENT_RE = re.compile(r'^### \[受測者 \| ')
TRAIT_RE = re.compile(r'^\[特質 \| ([A-Z]{3}_\d+)_([ABC]) \| ')
INDEX_RE = re.compile(r'^- ([A-Z]{3}_\d+)_([ABC])｜')
SUBBLOCK_RE = re.compile(r'^#### 交互作用——')
INTER_RE = re.compile(r'^\[交互 \| ')

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def respondent_sections(lines):
    starts = [i for i, l in enumerate(lines) if RESPONDENT_RE.match(l)]
    for a, b in zip(starts, starts[1:] + [len(lines)]):
        yield lines[a:b]


def expected_blocks(chunk):
    """[(sub-block header, [rendered interaction block, ...]), ...] as the example has it."""
    out = []
    current = None
    i = 0
    while i < len(chunk):
        line = chunk[i]
        if SUBBLOCK_RE.match(line):
            current = (line, [])
            out.append(current)
            i += 1
        elif INTER_RE.match(line) and current is not None:
            body = chunk[i + 1] if i + 1 < len(chunk) else ''
            current[1].append(f'{line}\n{body}')
            i += 2
        else:
            i += 1
    return out


def main():
    renderer = TraitBlockRenderer()
    print(f'\nloaded {len(_all_rows())} interaction rows')

    for filename, title in CASES:
        question = table.get(title)
        lines = open(os.path.join(PKG, filename), encoding='utf-8').read().split('\n')
        print(f'\n[{filename}]  idx={question["idx"]} type={question["type"]}')

        for n, chunk in enumerate(respondent_sections(lines), 1):
            P = dict([(m.group(1), m.group(2)) for l in chunk if (m := TRAIT_RE.match(l))]
                     + [(m.group(1), m.group(2)) for l in chunk if (m := INDEX_RE.match(l))])
            scoped = set()
            for ids in (question.get('scoped_traits') or {}).values():
                scoped.update(ids)

            actual = select_interactions(P, question, scoped)
            expected = expected_blocks(chunk)
            label = f'respondent {n}'

            check(f'{label}: sub-block headers and order',
                  [b.header for b in actual] == [h for h, _ in expected],
                  f'{[b.header[-6:] for b in actual]} vs {[h[-6:] for h, _ in expected]}')

            for blk, (header, exp_items) in zip(actual, expected):
                got = [it.render(renderer) for it in blk.items]
                check(f'{label}: {header[-8:]} item count',
                      len(got) == len(exp_items), f'{len(got)} vs {len(exp_items)}')
                first_diff = next((i for i, (g, e) in enumerate(zip(got, exp_items)) if g != e), None)
                check(f'{label}: {header[-8:]} items match verbatim, in order',
                      first_diff is None, f'first difference at #{first_diff}')
                if first_diff is not None:
                    print(f'         expected: {exp_items[first_diff][:110]}')
                    print(f'         actual  : {got[first_diff][:110]}')

            check(f'{label}: no footnote emitted (examples have none)',
                  all(b.footnote is None for b in actual),
                  [b.footnote for b in actual if b.footnote])

    print('\n[Mirror dedup]')
    P = dict([(m.group(1), m.group(2)) for m in
              (TRAIT_RE.match(l) or INDEX_RE.match(l) for l in
               open(os.path.join(PKG, CASES[0][0]), encoding='utf-8')) if m])
    cands = candidates(P)
    keys = [c.key for c in cands]
    check('no unordered pair appears twice', len(keys) == len(set(keys)),
          f'{len(keys)} candidates, {len(set(keys))} distinct')
    check('candidates stay in row order', [c.row_id for c in cands] == sorted(c.row_id for c in cands))

    print('\n[b §3 註記: sparse footnote / empty sub-block]')
    check('footnote string is verbatim from b §3',
          SPARSE_FOOTNOTE in open(B_DOC, encoding='utf-8').read(), SPARSE_FOOTNOTE)

    q = table.get('如何面對困難、壓力、挑戰')
    scoped5 = set()
    for ids in (q.get('scoped_traits') or {}).values():
        scoped5.update(ids)

    # Find a P that yields a small 本題相關 block by trimming the full example down.
    for size in range(2, 40):
        trimmed = dict(list(P.items())[:size])
        blocks = {b.block_key: b for b in select_interactions(trimmed, q, scoped5)}
        rel = blocks.get('related')
        if rel and 1 <= len(rel.items) <= 4:
            check(f'1-4 items in 本題相關 -> footnote appears (n={len(rel.items)})',
                  rel.footnote == SPARSE_FOOTNOTE, rel.footnote)
            break
    else:
        check('found a case with 1-4 本題相關 items', False)

    # A respondent with no scoped trait at all: 本題相關 must vanish, header and all.
    unscoped = {t: b for t, b in P.items() if t not in scoped5}
    blocks = select_interactions(unscoped, q, scoped5)
    check('0 items in 本題相關 -> sub-block omitted entirely',
          all(b.block_key != 'related' for b in blocks), [b.block_key for b in blocks])
    check('0 items in 本題相關 -> no footnote anywhere',
          all(b.footnote is None for b in blocks))

    print('\n[whole-person: no footnote, no truncation]')
    q15 = table.get('打造高效會議團隊')
    blocks = select_interactions(P, q15, set())
    check('whole-person emits no 本題相關 block',
          all(b.block_key != 'related' for b in blocks), [b.block_key for b in blocks])
    check('whole-person emits no footnote', all(b.footnote is None for b in blocks))
    check('whole-person injects every candidate',
          sum(len(b.items) for b in blocks) == len(candidates(P)),
          f'{sum(len(b.items) for b in blocks)} vs {len(candidates(P))} candidates')

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

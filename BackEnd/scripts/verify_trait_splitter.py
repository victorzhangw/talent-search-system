"""Reproduce the trait split of every respondent in the client's v7 LOG examples.

Usage:
    python scripts/verify_trait_splitter.py

Each example gives us the answer: the trait ids under 判讀主體特質 are the full blocks,
the ones under 其他特質索引 are the index lines, and their union is the respondent's P.
Feed P and the matching question row back through split_traits() and the two regions --
membership AND order -- must come out identical.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api_v2.services.question_table import table  # noqa: E402
from api_v2.services.trait_splitter import (split_traits, SUBJECT_HEADER,  # noqa: E402
                                            SUBJECT_HEADER_WHOLE, INDEX_HEADER)

PKG = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', '0730',
                   'Traitty_調整_20260728＿final')

# example file -> the question it was rendered from
CASES = [
    ('新版LOG範例_匡列型_壓力題_v7.txt', '如何面對困難、壓力、挑戰'),
    ('新版LOG範例_全人型_雙測驗_v7.txt', '個人使用說明書(主管)'),
    ('新版LOG範例_多人型_會議團隊_v7.txt', '打造高效會議團隊'),
]

RESPONDENT_RE = re.compile(r'^### \[受測者 \| ')
FULL_RE = re.compile(r'^\[特質 \| ([A-Z]{3}_\d+)_([ABC]) \| ')
INDEX_RE = re.compile(r'^- ([A-Z]{3}_\d+)_([ABC])｜')

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def respondent_sections(lines):
    """Split a multi-respondent example into one chunk per 受測者."""
    starts = [i for i, l in enumerate(lines) if RESPONDENT_RE.match(l)]
    for a, b in zip(starts, starts[1:] + [len(lines)]):
        yield lines[a:b]


def main():
    print(f'\nquestion table {table.version}, {len(table)} questions')

    for filename, title in CASES:
        question = table.get(title)
        lines = open(os.path.join(PKG, filename), encoding='utf-8').read().split('\n')
        print(f'\n[{filename}]  question idx={question["idx"]} type={question["type"]}')

        for n, chunk in enumerate(respondent_sections(lines), 1):
            expected_full = [(m.group(1), m.group(2)) for l in chunk if (m := FULL_RE.match(l))]
            expected_index = [(m.group(1), m.group(2)) for l in chunk if (m := INDEX_RE.match(l))]
            P = dict(expected_full + expected_index)

            result = split_traits(P, question)
            label = f'respondent {n} (P={len(P)})'

            check(f'{label}: full blocks match, in order', result.full == expected_full,
                  f'{len(result.full)} vs {len(expected_full)} expected')
            check(f'{label}: index lines match, in order', result.index == expected_index,
                  f'{len(result.index)} vs {len(expected_index)} expected')
            check(f'{label}: |full| + |index| == |P|',
                  len(result.full) + len(result.index) == len(P))

            header = SUBJECT_HEADER_WHOLE if result.whole_person else SUBJECT_HEADER
            check(f'{label}: subject header present verbatim', header in chunk, header)
            if result.whole_person:
                check(f'{label}: whole-person emits no index region',
                      not result.index and INDEX_HEADER not in chunk)
            else:
                check(f'{label}: scoped emits the index header', INDEX_HEADER in chunk)

    print('\n[Rules that the examples alone would not catch]')
    q = table.get('如何面對困難、壓力、挑戰')

    # Calibration traits must stay in the index unless the question scopes them.
    P = {'CIA_05': 'B', 'CIA_33': 'A', 'CIA_01': 'A'}
    r = split_traits(P, q)
    check('calibration trait stays out of the full region',
          ('CIA_33', 'A') in r.index and ('CIA_33', 'A') not in r.full)

    # ...and a risk endpoint hit must not promote either. CIA_32_A is a risk endpoint
    # that this question does not scope; picking one it DOES scope (CIA_36 among them)
    # would prove nothing, since scoping alone puts it in the full region.
    P2 = {'CIA_32': 'A', 'CIA_05': 'B'}
    r2 = split_traits(P2, q)
    check('risk endpoint hit does not promote to the full region',
          ('CIA_32', 'A') in r2.index and ('CIA_32', 'A') not in r2.full)
    check('a scoped trait that is also a risk endpoint still goes full',
          ('CIA_05', 'B') in r2.full)

    # injection_set would have promoted the calibration traits; scoped_traits must not.
    offenders = []
    for question in table.all():
        if question['type'] != 'scoped':
            continue
        scoped = set()
        for ids in (question.get('scoped_traits') or {}).values():
            scoped.update(ids)
        if table.calibration_traits & scoped:
            offenders.append(question['idx'])
    check('no scoped question scopes a calibration trait (so none can be promoted)',
          not offenders, offenders)

    # Free-form takes the whole-person path with no question object at all.
    r3 = split_traits({'CIA_01': 'A', 'CIA_33': 'A'}, None)
    check('free-form: S = P, no index region',
          r3.whole_person and len(r3.full) == 2 and not r3.index)
    check('free-form: whole-person subject header',
          r3.subject_header == SUBJECT_HEADER_WHOLE)

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

"""Run the b §6 unit checks over real assemblies, then prove they actually catch faults.

Usage:
    python scripts/verify_unit_check.py

A check that never fires looks identical to a check that passes, so every rule is also
exercised against a deliberately corrupted payload.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

from api_v2.services.question_table import table  # noqa: E402
from api_v2.services.log_assembler import Respondent, assemble  # noqa: E402
from api_v2.services.trait_splitter import split_traits  # noqa: E402
from api_v2.services.unit_check import run_unit_checks  # noqa: E402

PKG = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', '0730',
                   'Traitty_調整_20260728＿final')
CASES = [
    ('新版LOG範例_匡列型_壓力題_v7.txt', '如何面對困難、壓力、挑戰'),
    ('新版LOG範例_全人型_雙測驗_v7.txt', '個人使用說明書(主管)'),
    ('新版LOG範例_多人型_會議團隊_v7.txt', '打造高效會議團隊'),
]

RESPONDENT_RE = re.compile(r'^### \[受測者 \| (.+?) \| (.+?)\]$')
TRAIT_RE = re.compile(r'^\[特質 \| ([A-Z]{3}_\d+)_([ABC]) \| ')
INDEX_RE = re.compile(r'^- ([A-Z]{3}_\d+)_([ABC])｜')

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def parse_respondents(lines):
    starts = [i for i, l in enumerate(lines) if RESPONDENT_RE.match(l)]
    out = []
    for a, b in zip(starts, starts[1:] + [len(lines)]):
        name, rid = RESPONDENT_RE.match(lines[a]).groups()
        chunk = lines[a:b]
        scores = dict([(m.group(1), m.group(2)) for l in chunk if (m := TRAIT_RE.match(l))]
                      + [(m.group(1), m.group(2)) for l in chunk if (m := INDEX_RE.match(l))])
        out.append(Respondent(name, rid, scores))
    return out


def build(filename, title):
    question = table.get(title)
    lines = open(os.path.join(PKG, filename), encoding='utf-8').read().split('\n')
    respondents = parse_respondents(lines)
    log = assemble(respondents, question)
    scoped = {r.respondent_id: split_traits(r.scores, question).scoped_ids for r in respondents}
    return log, respondents, question, scoped


def main():
    print('\n[1] Real assemblies pass all four checks')
    built = []
    for filename, title in CASES:
        log, respondents, question, scoped = build(filename, title)
        built.append((filename, log, respondents, question, scoped))
        problems = run_unit_checks(log.to_log_text(), respondents, question, scoped)
        check(f'{filename[:22]}…: clean', not problems, problems[:3])

    print('\n[2] Each rule fires when the payload is corrupted')
    filename, log, respondents, question, scoped = built[0]
    text = log.to_log_text()

    def codes(mutated, resp=None, q=None, s=None):
        return {p.code for p in run_unit_checks(mutated, resp or respondents,
                                                q if q is not None else question,
                                                s if s is not None else scoped)}

    # 1. counts -- drop one full block header
    dropped = text.replace('[特質 | CIA_05_B | 情境波動]\n', '', 1)
    check('full_count fires when a full block is missing', 'full_count' in codes(dropped))

    # 2. an interaction end that appears in no region
    dangling = text.replace('[交互 | CIA_01_A × CIA_09_A |',
                            '[交互 | ZZZ_99_A × CIA_09_A |', 1)
    check('dangling_interaction_end fires', 'dangling_interaction_end' in codes(dangling))

    # 3. text hygiene
    check("python_list_repr fires on \"['\"",
          'python_list_repr' in codes(text.replace('行為面向：', "行為面向：['", 1)))
    check('empty_parens fires',
          'empty_parens' in codes(text.replace('王智弘 |', '王智弘（） |', 1)))
    check('paren_code fires in a body line',
          'paren_code' in codes(text.replace('行為面向：一般狀態', '行為面向：（31）一般狀態', 1)))
    check('trait_id_in_body fires in a body line',
          'trait_id_in_body' in codes(text.replace('行為面向：一般狀態',
                                                   '行為面向：與 CIA_22 一般狀態', 1)))

    # 4. sub-block membership -- move an unscoped pair into 本題相關
    unscoped_pair = '[交互 | CIA_01_A × CIA_32_A | 高度自律 × 高特權感]'
    if unscoped_pair in text:
        head, tail = text.split('#### 交互作用——作答校準與風險提示', 1)
        moved = (head + unscoped_pair + '\n占位敘事。\n\n'
                 + '#### 交互作用——作答校準與風險提示' + tail)
        check('wrong_subblock fires when an unscoped pair sits in 本題相關',
              'wrong_subblock' in codes(moved))
    else:
        check('found an unscoped pair to relocate', False)

    print('\n[3] The id check must NOT fire on legal ids')
    check('block headers keep their ids without tripping the check',
          'trait_id_in_body' not in codes(text))
    check('index lines keep their ids without tripping the check',
          all('- CIA_01_A｜' not in p.message for p in
              run_unit_checks(text, respondents, question, scoped)))
    # Questions 21/22 spell out ids inside the instruction on purpose.
    q21 = table.get('領導風格與潛能分析')
    r = [Respondent('甲', 'R1', {'ANI_01': 'A', 'ANI_05': 'A'})]
    s21 = {'R1': split_traits(r[0].scores, q21).scoped_ids}
    log21 = assemble(r, q21)
    check('ids inside the task instruction are not flagged',
          'ANI_05' in log21.instruction
          and 'trait_id_in_body' not in {p.code for p in
                                         run_unit_checks(log21.to_log_text(), r, q21, s21)})

    print('\n[4] Wired into assemble() by default (b §6 「每次組裝跑」)')
    clean = assemble(respondents, question)
    check('a clean assembly records unit_check=passed in the audit',
          clean.audit.get('unit_check') == 'passed', clean.audit.get('unit_check'))
    from api_v2.services.log_assembler import UnknownTrait
    try:
        assemble([Respondent('X', 'RX', {'ZZZ_99': 'A'})], question)
        caught = None
    except UnknownTrait as exc:
        caught = str(exc)
    except Exception as exc:  # noqa: BLE001 - we want the type in the message
        caught = f'{type(exc).__name__}: {exc}'
    check('an unknown trait fails with a clear error, not a TypeError',
          caught is not None and 'ZZZ_99' in caught and 'TypeError' not in caught, caught)

    print('\n[5] Whole-person and free-form')
    filename, log, respondents, question, scoped = built[1]
    check('whole-person assembly is clean',
          not run_unit_checks(log.to_log_text(), respondents, question, scoped))
    free = assemble(respondents, None, user_query='他適合帶新人嗎？')
    check('free-form assembly is clean',
          not run_unit_checks(free.to_log_text(), respondents, None, {}))

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

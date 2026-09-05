"""Regenerate the client's v7 LOG examples end to end and diff every line.

Usage:
    python scripts/verify_log_assembler.py

This is DoD 第 1 條 in full: recover each example's respondents from its own trait
regions, assemble the LOG from our data layer, and compare the whole file line by line.
Anything that differs has to be an explained, listed deviation -- otherwise it fails.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

from api_v2.services.question_table import table  # noqa: E402
from api_v2.services.log_assembler import (Respondent, assemble, check_audience,  # noqa: E402
                                           AudienceMismatch, SYSTEM_MARKER,
                                           INSTRUCTION_MARKER, ROSTER_MARKER)

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
POSITION_LABEL_RE = re.compile(r'RESP_\d{2}')

# Known, documented deviations. Anything outside these must match exactly.
SPA_PREFIXES = ('可用於：', '禁止：')

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


def classify(expected: str, actual: str) -> str:
    """'' when identical, otherwise the name of the known deviation, or 'UNEXPECTED'."""
    if expected == actual:
        return ''
    if actual.startswith(SPA_PREFIXES) and any(
            actual == p + expected for p in SPA_PREFIXES):
        return 'b§2 SPA column-name prefix'
    if expected.startswith(SYSTEM_MARKER) and actual == SYSTEM_MARKER:
        return 'example-file annotation after [SYSTEM PROMPT]'
    if expected.startswith('15. 自濾授權') and actual.startswith('15. 自濾授權'):
        return 'a-doc rule 15 clause (examples predate it)'
    e_head, a_head = RESPONDENT_RE.match(expected), RESPONDENT_RE.match(actual)
    if e_head and a_head and e_head.group(1) == a_head.group(1) \
            and POSITION_LABEL_RE.fullmatch(a_head.group(2)):
        # Same format, same name, different ID token. The examples' own tokens are ad-hoc
        # placeholders -- RESP_R2, RESP_TEAM_01, RESP_R3_DUAL, one scheme per file -- so
        # there is nothing here to reproduce. We mint a position token instead, because
        # filling this field with the real candidate_id put 「許品優（55）」 into answers.
        return 'respondent ID token (examples use ad-hoc placeholders)'
    return 'UNEXPECTED'


def main():
    for filename, title in CASES:
        question = table.get(title)
        raw = open(os.path.join(PKG, filename), encoding='utf-8').read()
        expected = raw.split('\n')
        while expected and not expected[-1].strip():
            expected.pop()

        respondents = parse_respondents(expected)
        log = assemble(respondents, question)
        actual = log.to_log_text().split('\n')

        print(f'\n[{filename}]  {len(respondents)} respondent(s), idx={question["idx"]}')
        check('line count matches', len(actual) == len(expected),
              f'{len(actual)} vs {len(expected)}')

        deviations = {}
        unexpected = []
        for i, (e, a) in enumerate(zip(expected, actual)):
            kind = classify(e, a)
            if not kind:
                continue
            deviations[kind] = deviations.get(kind, 0) + 1
            if kind == 'UNEXPECTED':
                unexpected.append((i + 1, e, a))

        check('no unexpected line differences', not unexpected, f'{len(unexpected)} lines')
        for lineno, e, a in unexpected[:4]:
            print(f'       line {lineno}')
            print(f'         expected: {e[:100]}')
            print(f'         actual  : {a[:100]}')
        for kind, n in sorted(deviations.items()):
            if kind != 'UNEXPECTED':
                print(f'  [NOTE] {n} line(s): {kind}')

    print('\n[audience 前置驗證 (b §1.1)]')
    one = [Respondent('甲', 'R1', {'CIA_01': 'A'})]
    two = one + [Respondent('乙', 'R2', {'CIA_01': 'A'})]

    single_only = table.get('快速面試提問指南')
    check('single_only + 2 respondents -> rejected',
          _raises(lambda: check_audience(two, single_only)))
    check('single_only + 1 respondent -> accepted',
          not _raises(lambda: check_audience(one, single_only)))

    multi_only = table.get('打造高效會議團隊')
    check('multi_only + 1 respondent -> rejected',
          _raises(lambda: check_audience(one, multi_only)))
    check('multi_only + 2 respondents -> accepted',
          not _raises(lambda: check_audience(two, multi_only)))

    both = table.get('如何面對困難、壓力、挑戰')
    check('both accepts either count',
          not _raises(lambda: check_audience(one, both))
          and not _raises(lambda: check_audience(two, both)))
    check('assemble() itself refuses a mismatched request',
          _raises(lambda: assemble(two, single_only)))
    check('the placeholder instruction never reaches the payload',
          '僅適用單人' not in assemble(one, single_only).to_log_text())

    print('\n[instruction selection]')
    check('single respondent uses instruction_single',
          assemble(one, both).instruction.endswith(both['instruction_single']))
    check('multiple respondents use instruction_multi',
          assemble(two, both).instruction.endswith(both['instruction_multi']))

    print('\n[free-form (b §1.1 / free_form_input_contract)]')
    check('free-form without user_query is rejected', _raises(lambda: assemble(one, None)))
    q = '我下週要跟他談年度目標，該怎麼開場？'
    free = assemble(one, None, user_query=q)
    # 契約寫的是「[任務指令]＝user_query 原文」。名單宣告是它前面的一個平行區塊，
    # 指令本身一字未改，所以這個子字串必須逐字存在。
    check('task instruction is the user text verbatim, unwrapped',
          free.instruction.endswith(f'{INSTRUCTION_MARKER}\n{q}'), repr(free.instruction))
    check('free-form takes the whole-person path',
          '（全人型＝全部特質）' in free.body and '其他特質索引' not in free.body)

    print('\n[本輪判讀對象 -- 自由提問的名單宣告]')
    check('free-form carries the roster block before the instruction',
          free.instruction.startswith(ROSTER_MARKER), repr(free.instruction[:40]))
    check('single respondent is announced as 共 1 位',
          '共 1 位：甲。' in free.instruction, repr(free.instruction[:60]))
    free_multi = assemble(two, None, user_query=q)
    check('every respondent is named, in payload order',
          '共 2 位：甲、乙。' in free_multi.instruction, repr(free_multi.instruction[:60]))
    check('the roster never carries a RESP_xx token',
          not re.search(r'RESP_\d+', free_multi.instruction.split(INSTRUCTION_MARKER)[0]))
    check('it tells the model to ignore rosters from earlier turns',
          '先前對話' in free.instruction)
    check('題庫題 carries no roster block -- v7 diff must stay at 0 lines',
          ROSTER_MARKER not in assemble(two, both).instruction)

    print('\n[to_messages() vs to_log_text()]')
    log = assemble(one, both)
    msgs = log.to_messages()
    check('two messages, system then user', [m['role'] for m in msgs] == ['system', 'user'])
    check('history is inserted between them',
          [m['role'] for m in log.to_messages([{'role': 'user', 'content': 'x'},
                                               {'role': 'assistant', 'content': 'y'}])]
          == ['system', 'user', 'assistant', 'user'])
    rejoined = msgs[0]['content'] + '\n\n---\n\n' + msgs[1]['content']
    check('rejoining the messages reproduces the canonical LOG byte for byte',
          rejoined == log.to_log_text())
    check('system message ends with the data block, not the instruction',
          INSTRUCTION_MARKER not in msgs[0]['content'])

    print('\n[audit fields for 事項 12]')
    audit = assemble(two, both).audit
    check('carries question_id / audience / per-respondent counts',
          audit['question_id'] == both['idx'] and audit['audience'] == 'multi'
          and len(audit['respondents']) == 2, audit['respondents'][0])

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


def _raises(fn):
    try:
        fn()
        return False
    except (AudienceMismatch, ValueError):
        return True


if __name__ == '__main__':
    sys.exit(main())

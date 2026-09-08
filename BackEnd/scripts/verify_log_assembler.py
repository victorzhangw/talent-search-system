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
                                           INSTRUCTION_MARKER, ROSTER_MARKER,
                                           COVERAGE_CLAUSE, CONTEXT_MARKER,
                                           CONTEXT_BLOCK)

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


def split_roster(actual):
    """把 `[本輪判讀對象]` 區塊從產出的 LOG 裡拿掉，回傳 (其餘行, 區塊行)。

    v7 範例是客戶在名單宣告存在之前寫的，所以那幾行在 expected 裡不可能有對應。逐行比對
    是 DoD 第 1 條，不能因為多了一個區塊就整份放寬——所以在這裡把區塊「取出來」單獨檢查，
    剩下的部分仍然要求 0 未解釋差異。這比在 classify() 裡放行整段安全：只要區塊的形狀跑掉
    （多一行、少一行、位置不對），這裡就切不乾淨，剩下的行照樣會對不齊而爆掉。
    """
    try:
        i = actual.index(ROSTER_MARKER)
    except ValueError:
        return actual, []
    j = actual.index(INSTRUCTION_MARKER, i)
    # 區塊與 [任務指令] 之間有一個空行，一起拿掉。
    return actual[:i] + actual[j:], actual[i:j - 1]


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
        actual, roster = split_roster(log.to_log_text().split('\n'))

        print(f'\n[{filename}]  {len(respondents)} respondent(s), idx={question["idx"]}')
        n = len(respondents)
        check('the roster block is present and well formed',
              len(roster) in (3, 4) and roster[0] == ROSTER_MARKER
              and roster[1].startswith(f'共 {n} 位：'), roster)
        check('every respondent is named in the roster block',
              all(r.name in roster[1] for r in respondents), roster[1] if roster else '')
        wants = n > 1 and bool(question.get('per_person_sections'))
        check('coverage clause appears exactly when the question demands per-person '
              'sections',
              (len(roster) == 4 and roster[-1] == COVERAGE_CLAUSE.format(n=n)) == wants,
              f'per_person={question.get("per_person_sections")} n={n} '
              f'lines={len(roster)}')
        check('line count matches once the roster block is taken out',
              len(actual) == len(expected), f'{len(actual)} vs {len(expected)}')

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
    # 2026-09-08 req e332a385：名單 11 位、11 份特質全送，模型寫「根據您提供的八位成員
    # 特質資料」，逐人分析只寫 7 位。題庫題原本不加名單區塊是為了維持 v7 的 0 差異，
    # 那份範例只有 2 個人——這個取捨在 11 人的規模下不成立。
    pp = table.get('領導風格與潛能分析')          # per_person_sections=True
    quiz_multi = assemble(two, both).instruction    # 如何面對困難…＝False
    check('題庫題 also carries the roster block (req e332a385)',
          quiz_multi.startswith(ROSTER_MARKER), repr(quiz_multi[:30]))
    pp_multi = assemble(two, pp).instruction
    check('per_person 的題目才被要求涵蓋全部 N 位，且不是硬性配額',
          COVERAGE_CLAUSE.format(n=2) in pp_multi and '資料不足以明確判讀' in pp_multi)
    check('the coverage clause never demands a fixed number of sections',
          '必須輸出' not in pp_multi and '不得省略或合併' in pp_multi)
    # req c2f088ee（Q13）／6bb46227（Q18）：這兩題的指令通篇寫「對象組合」，自己還寫著
    # 「不得新增、省略或調整順序」，不該再被我們要求逐人分段——而且覆蓋率檢查對它們
    # 也只做 by_mention，要求了卻不檢查。
    check('沒有明定逐人分段的多人題庫題不加涵蓋句',
          '逐人分析' not in quiz_multi, repr(quiz_multi[:140]))
    check('單人題庫題 gets the roster but no coverage clause',
          ROSTER_MARKER in assemble(one, both).instruction
          and '逐人分析' not in assemble(one, both).instruction)
    check('自由提問 multi still gets no coverage clause (Victoria / 點名式提問)',
          '逐人分析' not in assemble(two, None, user_query=q).instruction)
    check('題庫題 instruction text itself is untouched',
          quiz_multi.endswith(f'{INSTRUCTION_MARKER}\n{both["instruction_multi"]}'))

    print('\n[前輪脈絡 -- 追問輪的重寫（E-16）]')
    # req c4f3f3b3：使用者問「還有其他建議嗎」，拿到的回答 1838 字裡有 1209 字（72%）
    # 是把上一輪重寫一遍。payload 裡沒有任何一句話說「前面那些已經在畫面上了」。
    no_hist = assemble(two, None, user_query=q).instruction
    with_hist = assemble(two, None, user_query=q, has_history=True).instruction
    check('沒有歷史時不加這個區塊', CONTEXT_MARKER not in no_hist, repr(no_hist[:40]))
    check('有歷史時才加', with_hist.startswith(CONTEXT_MARKER), repr(with_hist[:40]))
    check('題庫題同樣適用（追問輪不分題型）',
          CONTEXT_MARKER in assemble(two, both, has_history=True).instruction)
    check('順序是 前輪脈絡 -> 本輪判讀對象 -> 任務指令',
          with_hist.index(CONTEXT_MARKER) < with_hist.index(ROSTER_MARKER)
          < with_hist.index(INSTRUCTION_MARKER))
    check('指令原文一字未改',
          with_hist.endswith(f'{INSTRUCTION_MARKER}\n{q}'), repr(with_hist[-40:]))
    check('約束的是「不要重新輸出已經給過的內容」',
          '不要重述、改寫或重新輸出先前已經給過的內容' in CONTEXT_BLOCK)
    # e4147c25 的提問是「換 蔡雨築 是否同樣的結論說明」——本來就該用同樣的結構分析
    # 另一個人。措辭寫太死會變成答非所問，那比重讀更糟。
    check('沒有把「換一個對象／角度」一起擋掉',
          '換一個對象' in CONTEXT_BLOCK and '直接就新的對象或角度作答' in CONTEXT_BLOCK)
    check('區塊只有一行，不會把 payload 撐大',
          CONTEXT_BLOCK.count(chr(10)) == 0 and len(CONTEXT_BLOCK) < 200,
          len(CONTEXT_BLOCK))
    check('沒有歷史時，payload 與加這個區塊之前完全一樣',
          len(with_hist) - len(no_hist)
          == len(CONTEXT_MARKER) + 1 + len(CONTEXT_BLOCK) + 2)

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

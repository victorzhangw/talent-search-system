"""Cross-cutting acceptance for the answer-calibration traits (事項 11).

Usage:
    python scripts/verify_calibration.py

「校準零工序」 is easy to misread as "nothing to implement". It means only that no separate
[作答校準] block is written and no narrative text is authored by the program -- the three
calibration traits (CIA_33 / ANI_23 / SPA_12) still have to be recognised in three places:
interaction selection, sub-block grouping, and the post-answer evidence check.

Those three live in different modules, so a per-module test can pass while the behaviour
as a whole is wrong. This runs the whole assembly and checks all three at once, following
the acceptance table in `_ LOG 實作補充說明 for victor.txt` verbatim -- including its last
row, where emitting any standalone calibration block is a failure.
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
from api_v2.services.interaction_selector import select_interactions  # noqa: E402
from api_v2.services.completeness_check import check_answer, EVIDENCE_TERMS  # noqa: E402
from api_v2.services.endpoint_registry import registry  # noqa: E402

CALIB = table.calibration_traits
failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def scoped_of(question):
    ids = set()
    for group in (question.get('scoped_traits') or {}).values():
        ids.update(group)
    return ids


def main():
    print(f'\ncalibration traits: {sorted(CALIB)}')
    registry.refresh()
    check('all three are registered as calibration endpoints',
          {t for t, _ in registry.pairs_for_type('calibration')} == CALIB)
    check('they are trait-level, so any band hits',
          all(registry.types_for(t, b) for t in CALIB for b in 'ABC'))

    # The item's worked example: S = {CIA_16, CIA_18}, respondent also has CIA_33_A.
    q = table.get('如何面對困難、壓力、挑戰')
    S = scoped_of(q)
    check('the worked example is representative: CIA_16/CIA_18 scoped, CIA_33 not',
          {'CIA_16', 'CIA_18'} <= S and 'CIA_33' not in S)

    # Bands are chosen so the 08 sheet actually pairs these traits with CIA_33: CIA_05_C
    # gives a scoped-end pair (-> 本題相關) and CIA_03_A an unscoped one (-> 校準與風險提示).
    # Picking bands that happen to have no CIA_33 pair would leave both sub-blocks empty
    # and the grouping assertions would pass without ever exercising the grouping.
    scores = {'CIA_16': 'A', 'CIA_18': 'A', 'CIA_33': 'A', 'CIA_11': 'B',
              'CIA_01': 'A', 'CIA_05': 'C', 'CIA_03': 'A', 'CIA_04': 'A'}
    resp = [Respondent('王智弘', 'R1', scores)]
    log = assemble(resp, q)
    text = log.to_log_text()

    print('\n[1] 校準特質未被匡列 -> 留在索引區，不升完整區塊')
    split = split_traits(scores, q)
    check('CIA_33 is in the index region', ('CIA_33', 'A') in split.index)
    check('CIA_33 is not a full block', ('CIA_33', 'A') not in split.full)
    check('and that is visible in the payload',
          re.search(r'^- CIA_33_A｜', text, re.M) is not None
          and '[特質 | CIA_33_A' not in text)

    print('\n[2] 校準特質被題目匡列 -> 依一般規則進入完整區塊')
    forced = dict(q, scoped_traits={'CIA': sorted(S | {'CIA_33'})})
    split_forced = split_traits(scores, forced)
    check('scoping it promotes it like any other trait',
          ('CIA_33', 'A') in split_forced.full and ('CIA_33', 'A') not in split_forced.index)

    print('\n[3] 交互選列與子區塊分組')
    blocks = {b.block_key: b for b in select_interactions(scores, q, S)}
    related = blocks.get('related')
    calib_risk = blocks.get('calib_risk')
    check('both sub-blocks are present', related is not None and calib_risk is not None,
          sorted(blocks))

    def pairs(block):
        return {frozenset(it.ends) for it in (block.items if block else [])}

    touching_calib_and_scoped = [
        it for it in (related.items if related else [])
        if any(e in CALIB for e in it.ends) and any(e in S for e in it.ends)]
    only_calib = [
        it for it in (calib_risk.items if calib_risk else [])
        if any(e in CALIB for e in it.ends)]
    check('a pair with one scoped end and one calibration end -> 本題相關',
          touching_calib_and_scoped, [str(i) for i in touching_calib_and_scoped[:2]])
    check('a pair selected only because of the calibration trait -> 作答校準與風險提示',
          only_calib, [str(i) for i in only_calib[:2]])
    check('no calibration-only pair leaked into 本題相關',
          not [it for it in (related.items if related else [])
               if any(e in CALIB for e in it.ends) and not any(e in S for e in it.ends)])
    check('the two sub-blocks do not share a pair', not (pairs(related) & pairs(calib_risk)))

    print('\n[4] 不得出現獨立的 [作答校準] 區塊（驗收表最後一列）')
    for marker in ('[作答校準', '作答校準|', '#### 作答校準\n', '[校準'):
        check(f'payload contains no {marker!r}', marker not in text)
    headers = re.findall(r'^#### .+$', text, re.M)
    check('the only 作答校準 header is the interaction sub-block',
          [h for h in headers if '作答校準' in h] == ['#### 交互作用——作答校準與風險提示'],
          [h for h in headers if '作答校準' in h])
    # 「校準」 does appear in the payload -- System rules 12 and 15 use it, and they are
    # static text copied verbatim. What must not appear is a block the program wrote.
    body = text.split('## 【輸入數據】', 1)[1].split('[任務指令]', 1)[0]
    stray = [l for l in body.splitlines()
             if '校準' in l and l != '#### 交互作用——作答校準與風險提示']
    check('no calibration wording in the data section beyond the sub-block header',
          not stray, stray[:2])

    print('\n[5] 資料自帶校準語意（零工序的實際意思）')
    index_line = next(l for l in text.splitlines() if l.startswith('- CIA_33_A｜'))
    check('the index line already carries the credibility sentence',
          '佐證' in index_line or '可信度' in index_line, index_line[-40:])

    print('\n[6] 回答後的佐證措辭檢查')
    answer = ''.join(f'{i + 1}. {s}\n內容。\n\n' for i, s in enumerate(q['expected_sections']))
    res = check_answer(answer, resp, q, CALIB)
    check('A-band calibration with no evidence wording -> failed',
          res.calibration_evidence == 'failed' and res.status == 'failed')
    check('the reason names the requirement', '佐證' in res.reason(), res.reason())
    for wording in ('建議搭配實際行為事例確認', '可再參考工作樣本或主管觀察'):
        r2 = check_answer(answer + f'\n\n{wording}。\n\n', resp, q, CALIB)
        check(f'「{wording}」 satisfies it', r2.calibration_evidence == 'passed')

    # 事項 11 offers a third example sentence that the b §8 wordlist does not match.
    # Reported rather than papered over: loosening the wordlist here would be us deciding
    # what counts as evidence wording, which b §8 reserves for the content side.
    doc_example = '不宜只根據單次自陳結果判斷'
    r_doc = check_answer(answer + f'\n\n{doc_example}。\n\n', resp, q, CALIB)
    check('spec inconsistency is present and behaves per b §8 (wordlist wins)',
          r_doc.calibration_evidence == 'failed', r_doc.calibration_evidence)
    print(f'  [NOTE] 事項 11 lists 「{doc_example}」 as acceptable evidence wording, but b §8')
    print(f'         matches on {EVIDENCE_TERMS} -- 「不以單次」 is a specific phrasing that this')
    print('         sentence does not contain. A compliant answer written the way the item')
    print('         document suggests would be judged as missing evidence. Raised as 乙-6.')

    print('\n[7] 非 A 段不要求佐證')
    for band in ('B', 'C'):
        r3 = check_answer(answer, [Respondent('王', 'R', dict(scores, CIA_33=band))], q, CALIB)
        check(f'CIA_33 band {band} -> n/a', r3.calibration_evidence == 'n/a')

    print('\n[8] 另外兩個校準特質行為一致')
    for trait_id, project in (('ANI_23', 'ANI'), ('SPA_12', 'SPA')):
        other = f'{project}_01'
        s2 = {trait_id: 'A', other: 'A'}
        q_other = table.get('個人使用說明書(主管)')      # whole-person, so no index region
        sp = split_traits(s2, table.get('如何面對困難、壓力、挑戰'))
        check(f'{trait_id} stays in the index when unscoped',
              (trait_id, 'A') in sp.index, sp.index)
        r4 = check_answer('內容。', [Respondent('王', 'R', s2)], q_other, CALIB)
        check(f'{trait_id} A-band triggers the evidence check',
              r4.calibration_evidence == 'failed')

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

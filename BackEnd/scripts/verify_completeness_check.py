"""Acceptance for the b §8 completeness checks.

Usage:
    python scripts/verify_completeness_check.py

The heading cases come from the acceptance table in `_ LOG 實作補充說明 for victor.txt`;
the rest cover the empty-sections logging rule, the multi-person name rule, free-form
length, calibration evidence, and the incremental (segment-by-segment) path.
"""

import os
import sys

# Windows consoles default to cp950 here, which cannot encode the Chinese in the section
# names this script prints -- without this the whole report comes out mojibake.
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

from api_v2.services.question_table import table  # noqa: E402
from api_v2.services.log_assembler import Respondent  # noqa: E402
from api_v2.services.completeness_check import (  # noqa: E402
    CompletenessChecker, check_answer, heading_candidates, normalize_heading,
    expected_sections_for, SKIP_LOG, UNSPLIT_LOG, EVIDENCE_TERMS, FREE_FORM_MAX_CHARS)

CALIB = table.calibration_traits
failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def sections_answer(q, headings, extra_body=''):
    return '\n\n'.join(headings) + ('\n\n' + extra_body if extra_body else '')


def main():
    q5 = table.get('如何面對困難、壓力、挑戰')
    r1 = [Respondent('王智弘', 'R1', {'CIA_05': 'B'})]

    print('\n[1] Heading matching -- the spec acceptance table')
    cases = [
        ('4. 主管使用提醒', '主管使用提醒', True),
        ('四、主管使用提醒：', '主管使用提醒', True),
        ('以下提供主管使用提醒', '主管使用提醒', False),
        ('主管注意事項', '主管使用提醒', False),
        ('## 主管使用提醒', '主管使用提醒', True),
        ('**主管使用提醒**', '主管使用提醒', True),
        ('第四部分，主管使用提醒', '主管使用提醒', True),
    ]
    for line, expected, should_match in cases:
        got = normalize_heading(line) == normalize_heading(expected)
        check(f'{line!r} vs {expected!r} -> {"match" if should_match else "no match"}',
              got == should_match, f'normalized to {normalize_heading(line)!r}')

    print('\n[1b] 標題與內文同一行（2026-08-25 req f1d36fbb 的六段全滅）')
    # 指令教的就是這個寫法，所以這不是模型不聽話，是比對方式對不上格式。
    inline = [
        ('- **主要領導風格**：推進驅動型', '主要領導風格', True),
        ('2. 主要風險：列出 3 項，每項都要包含', '主要風險', True),
        ('第三部分，需要避免的溝通方式：列出2項', '需要避免的溝通方式', True),
        ('## 溝通風格摘要', '溝通風格摘要', True),
        # 沒有標記的散文不提供標題，即使裡面有冒號
        ('他在壓力下的反應是：話會變少', '他在壓力下的反應是', False),
        # 標籤對不上就是對不上，切分不會放寬這件事
        ('- **主要領導風格**：推進驅動型', '次要領導風格', False),
    ]
    for line, expected, should_match in inline:
        got = normalize_heading(expected) in heading_candidates(line)
        check(f'{line[:26]!r} -> {expected!r} {"命中" if should_match else "不該命中"}',
              got == should_match, heading_candidates(line))

    print('\n[1c] 斜線的空白與全形半形不算差異')
    slash = [
        ('## 四、同組織／專案角色分配建議', '同組織 / 專案角色分配建議', True),
        ('## 四、同組織 / 專案角色分配建議', '同組織／專案角色分配建議', True),
        ('## 同組織/專案角色分配建議', '同組織 / 專案角色分配建議', True),
        ("## 管理 Do / Don't", "管理 Do/Don't", True),
        ("## 管理 Do/Don't", "管理 Do / Don't", True),
        # Do 與 Don't 之間的空白可以收，中英之間的不能——收掉就變成另一個詞了
        ("## 管理Do / Don't", "管理 Do / Don't", False),
        # 收斂不等於放寬：不同的段落名還是不同
        ('## 同組織／團隊角色分配建議', '同組織 / 專案角色分配建議', False),
    ]
    for line, expected, should_match in slash:
        got = normalize_heading(line) == normalize_heading(expected)
        check(f'{line[:24]!r} vs {expected[:20]!r} -> {"命中" if should_match else "不該命中"}',
              got == should_match,
              f'{normalize_heading(line)!r} vs {normalize_heading(expected)!r}')

    print('\n[1d] 全形／半形標點不算差異')
    width = [
        # 指令寫半形，模型在中文句子裡幾乎都輸出全形
        ('## 2. 需要結構或空間？', '需要結構或空間?', True),
        ('## 2. 共同或個別？', '共同或個別?', True),
        ('## 錄用後行動與發展建議（僅供參考）', '錄用後行動與發展建議(僅供參考)', True),
        # 沒有 ASCII 等價物的中文標點維持原樣，不可被當成相同
        ('## 互補、重疊與高風險組合', '互補,重疊與高風險組合', False),
        ('## 需要結構或時間？', '需要結構或空間?', False),
    ]
    for line, expected, should_match in width:
        got = normalize_heading(line) == normalize_heading(expected)
        check(f'{line[:22]!r} vs {expected[:18]!r} -> {"命中" if should_match else "不該命中"}',
              got == should_match,
              f'{normalize_heading(line)!r} vs {normalize_heading(expected)!r}')

    print('\n[2] Subset test on a real question')
    full = sections_answer(q5, q5['expected_sections'])
    res = check_answer(full, r1, q5, CALIB)
    check('all expected headings present -> passed', res.status == 'passed', res.missing_sections)
    res = check_answer(full + '\n\n額外補充\n\n內容', r1, q5, CALIB)
    check('extra headings are allowed', res.status == 'passed', res.missing_sections)
    res = check_answer(sections_answer(q5, q5['expected_sections'][:-1]), r1, q5, CALIB)
    check('a missing heading -> failed', res.status == 'failed'
          and res.missing_sections == [q5['expected_sections'][-1]], res.missing_sections)
    check('reason() names what is missing', '缺少段落' in res.reason(), res.reason())
    res = check_answer('本文提到 ' + ' 和 '.join(q5['expected_sections']), r1, q5, CALIB)
    check('expected text in running prose does NOT count', res.status == 'failed',
          res.missing_sections)

    print('\n[3] Empty expected_sections must be logged, never silently passed')
    for idx in (14, 15, 22):
        q = table.get(idx)
        n = 2 if q['audience'] == 'multi_only' else 1
        rs = [Respondent(f'受測者{i}', f'R{i}', {'CIA_05': 'B'}) for i in range(1, n + 1)]
        res = check_answer('任意回答', rs, q, CALIB)
        check(f'idx {idx}: skipped and logged', res.status in ('skipped', 'failed')
              and SKIP_LOG in res.log_lines, res.log_lines)
    check('the log line is the spec wording verbatim',
          SKIP_LOG == '本題未做段落齊全檢查（原因：指令未定義固定段落標題）')

    print('\n[4] 事項 13: single/multi split with a reported fallback')
    single, note = expected_sections_for(q5, 1)
    multi, note_m = expected_sections_for(q5, 2)
    check('no question has the split fields yet -> fallback used',
          note == UNSPLIT_LOG and single == multi == q5['expected_sections'])
    check('the fallback is recorded in the result log',
          UNSPLIT_LOG in check_answer(full, r1, q5, CALIB).log_lines)
    split_q = dict(q5, expected_sections_single=['甲'], expected_sections_multi=['乙', '丙'])
    check('split fields are preferred when present',
          expected_sections_for(split_q, 1)[0] == ['甲']
          and expected_sections_for(split_q, 2)[0] == ['乙', '丙'])
    check('no fallback note once the data is split', expected_sections_for(split_q, 1)[1] is None)

    print('\n[5] Multi-person: each respondent needs their own heading')
    two = [Respondent('王智弘', 'R1', {'CIA_05': 'B'}),
           Respondent('林孟德', 'R2', {'CIA_05': 'B'})]
    body = sections_answer(q5, q5['expected_sections'])
    res = check_answer('## 王智弘\n\n' + body + '\n\n## 林孟德\n\n' + body, two, q5, CALIB)
    check('both names present as headings -> passed', res.status == 'passed',
          res.missing_respondents)
    res = check_answer('## 王智弘\n\n' + body, two, q5, CALIB)
    check('a missing respondent -> failed', res.status == 'failed'
          and res.missing_respondents == ['林孟德'], res.missing_respondents)
    res = check_answer(body + '\n\n關於林孟德的部分寫在內文', two, q5, CALIB)
    check('a name only in running prose does not count',
          '林孟德' in res.missing_respondents, res.missing_respondents)
    check('single-person answers are not name-checked',
          not check_answer(body, r1, q5, CALIB).missing_respondents)

    print('\n[6] Free-form: length only')
    res = check_answer('短短的回答。', r1, None, CALIB)
    check('short free-form answer passes', res.status == 'passed', res.char_count)
    res = check_answer('字' * (FREE_FORM_MAX_CHARS + 1), r1, None, CALIB)
    check(f'over {FREE_FORM_MAX_CHARS} chars -> failed', res.status == 'failed', res.char_count)
    res = check_answer('字' * 500 + ' \n' * 800, r1, None, CALIB)
    check('whitespace is not counted', res.status == 'passed', res.char_count)
    check('free-form is not section-checked', not check_answer('x', r1, None, CALIB).missing_sections)

    print('\n[7] Calibration evidence (社會期望反應 A 段)')
    calib_r = [Respondent('王智弘', 'R1', {'CIA_05': 'B', 'CIA_33': 'A'})]
    res = check_answer(body, calib_r, q5, CALIB)
    check('A-band calibration without evidence wording -> failed',
          res.calibration_evidence == 'failed' and res.status == 'failed')
    check('reason() asks for the evidence wording', '佐證' in res.reason(), res.reason())
    for term in EVIDENCE_TERMS:
        res = check_answer(body + f'\n\n建議以{term}進一步確認。', calib_r, q5, CALIB)
        check(f'evidence term 「{term}」 satisfies the check',
              res.calibration_evidence == 'passed')
    res = check_answer(body, [Respondent('王智弘', 'R1', {'CIA_05': 'B', 'CIA_33': 'B'})],
                       q5, CALIB)
    check('B-band calibration does not require evidence', res.calibration_evidence == 'n/a')

    print('\n[8] Incremental accumulation (客戶裁定丙-1)')
    checker = CompletenessChecker(r1, q5, CALIB)
    for i, sec in enumerate(q5['expected_sections']):
        checker.observe(f'{i + 1}. {sec}\n內容內容。\n')
        if i < len(q5['expected_sections']) - 1:
            check(f'no verdict is possible mid-answer (after section {i + 1})',
                  checker.finalize().status == 'failed')
    check('passes once every segment has arrived', checker.finalize().status == 'passed',
          checker.finalize().missing_sections)
    one_shot = check_answer(''.join(f'{i + 1}. {s}\n內容內容。\n'
                                    for i, s in enumerate(q5['expected_sections'])), r1, q5, CALIB)
    check('segment-by-segment and one-shot agree',
          one_shot.status == checker.finalize().status)

    print('\n[9] Data risk scan (informational)')
    stale = []
    for q in table.all():
        for sec in q.get('expected_sections') or []:
            key = 'instruction_multi' if q['audience'] == 'multi_only' else 'instruction_single'
            if sec not in (q.get(key) or ''):
                stale.append((q['idx'], sec))
    print(f'  {len(stale)} expected_sections entries do not appear verbatim in their instruction:')
    for idx, sec in stale[:8]:
        print(f'    idx {idx}: {sec!r}')
    print('  These will be reported as missing even from a compliant answer. b §8 treats a')
    print('  miss as a soft failure (one regeneration, then manual), so this degrades')
    print('  gracefully -- but the wording needs aligning content-side.')

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

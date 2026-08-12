"""The respondent's database id must never reach the reader.

Reproduces a production answer that carried 「許品優（55）」 and 「游品堯（63）」 as section
headings. 55 and 63 are Traitty candidate_ids: the LOG header is `### [受測者 | 姓名 | ID]`
(b §5) and we were filling the ID field with the raw candidate_id, so the model read the
number as part of how to refer to that person. The exit scanner did not stop it -- it
matches score shapes (digits followed by 分, band letters, trait codes), and a bare number
in parentheses is none of those.

Two layers are checked here:
  甲  the payload carries a position token (RESP_01), so the model never sees the real id
  乙  the scanner rejects both identifiers, so putting one back cannot silently ship

Needs the trait spec in PostgreSQL, because assembling a LOG reads the trait rows.
"""

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api_v2', '.env'),
            encoding='utf-8-sig')

from api_v2.services.exit_scanner import ExitScanner  # noqa: E402
from api_v2.services.log_assembler import (  # noqa: E402
    LOG_LABEL_PREFIX, Respondent, assemble, log_label_for)
from api_v2.services.question_table import table  # noqa: E402

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}"
          f"{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def main():
    q = table.get('打造高效會議團隊') or table.get('如何面對困難、壓力、挑戰')
    people = [Respondent('許品優', '55', {'CIA_05': 'B'}),
              Respondent('游品堯', '63', {'CIA_05': 'A'})]
    log = assemble(people, q)
    text = log.to_log_text()

    print('\n[甲-1] LOG 本體不含真實 candidate_id')
    check('標頭用位置代號', '### [受測者 | 許品優 | RESP_01]' in text,
          [l for l in text.splitlines() if '受測者 |' in l])
    check('第二位是 RESP_02', '### [受測者 | 游品堯 | RESP_02]' in text)
    check('「許品優 | 55」不再出現', '許品優 | 55' not in text)
    check('「游品堯 | 63」不再出現', '游品堯 | 63' not in text)

    print('\n[甲-2] 真實 candidate_id 仍完整保留在稽核記錄（可追溯性）')
    audits = log.audit['respondents']
    check('respondent_id 是真實 id',
          [a['respondent_id'] for a in audits] == ['55', '63'],
          [a['respondent_id'] for a in audits])
    check('log_label 一併記錄，兩者對得起來',
          [a['log_label'] for a in audits] == ['RESP_01', 'RESP_02'],
          [a['log_label'] for a in audits])

    print('\n[甲-3] 代號格式與客戶 v7 範例同型（RESP_ 前綴、位置編號）')
    check('log_label_for 從 01 起算', log_label_for(0) == 'RESP_01', log_label_for(0))
    check('補零到兩位', log_label_for(9) == 'RESP_10', log_label_for(9))
    check('前綴常數一致', LOG_LABEL_PREFIX == 'RESP_')

    print('\n[乙-1] 掃描器攔得住兩種識別碼')
    scanner = ExitScanner.for_log(log)
    for bad in ('2. 各候選人的會議角色定位\n許品優（55）\n他在目標明確時推進很快。',
                '游品堯（63）偏好依循既定程序。',
                '許品優 55 的節奏偏快。',
                '受測者 RESP_01 的表現如下。'):
        hits = scanner.scan(bad)
        check(f'攔下 {bad.splitlines()[-1][:14]}…', len(hits) >= 1,
              [h.text for h in hits])

    print('\n[乙-2] 交給改寫器的是識別碼本身，不是連姓名一起')
    hits = scanner.scan('許品優（55）在目標明確時推進很快。')
    terms = scanner.banned_terms(hits)
    check('禁用詞是 55', terms == ['55'], terms)
    check('禁用詞不含姓名（否則等於叫模型別提這個人）',
          all('許品優' not in t for t in terms), terms)

    print('\n[乙-3] 不誤傷一般數字（裸數字不封鎖，只封鎖緊接姓名的）')
    for ok_text in ('1955 年的研究指出這一點。',
                    '約有 55% 的會議缺乏議程。',
                    '許品優在第 3 次討論時提出建議。',
                    '建議會議人數控制在 5 人以內。',
                    '游品堯負責追蹤 63 項待辦中的前 10 項。'):
        hits = scanner.scan(ok_text)
        check(f'放行「{ok_text[:16]}…」', hits == [], [h.text for h in hits])

    print('\n[乙-4] 正常回答仍然乾淨')
    clean = ('許品優在目標明確時能快速推進討論，游品堯則擅長把散亂的討論整理成待辦清單。'
             '兩人搭配時建議由游品堯先釐清目標，再由許品優提出做法。')
    check('無誤報', scanner.scan(clean) == [], [h.text for h in scanner.scan(clean)])

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

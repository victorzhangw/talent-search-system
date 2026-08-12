"""The completion pass must not repeat a closing sentence the answer already showed.

Reproduces what session af4d3e45 produced in production: the answer omitted the evidence
wording (b §8), the completeness check failed, and the completer -- a fresh model call
that still sees system prompt rule 6, 「每次回答文末以溫和語氣附一句」 -- appended the
supplement with the closing sentence on the end. The user read the same sentence twice.

Runs against a scripted model and needs no database: `strip_duplicate_closer` is a pure
string function, and the wiring check builds the pipeline object without `__init__` so
that `assemble()` (which reads trait rows from PostgreSQL) is never called.
"""

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api_v2', '.env'),
            encoding='utf-8-sig')

from api_v2.services.completeness_check import CompletenessChecker  # noqa: E402
from api_v2.services.exit_scanner import ExitScanner  # noqa: E402
from api_v2.services.log_assembler import Respondent  # noqa: E402
from api_v2.services.log_pipeline import (  # noqa: E402
    COMPLETION_INSTRUCTION, LogPipeline, MIN_DUPLICATE_CLOSER_CHARS,
    strip_duplicate_closer)
from api_v2.services.question_table import table  # noqa: E402
from api_v2.services.segment_gate import (  # noqa: E402
    SegmentGate, STATUS_MANUAL_REVIEW)

CLOSER = '本分析旨在提供觀點與輔助，最終決策請結合多方資訊綜合考量。'

ANSWER = ('1. 團隊合作價值\n\n他習慣憑當下判斷把事情快速兜起來。\n\n'
          '4. 共同合作策略\n\n分工建議：讓他負責需要快速反應的環節。\n\n' + CLOSER)

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}"
          f"{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def main():
    print('\n[1] 補生成又寫了一次結語 -> 砍掉，補充內容原封不動')
    supplement = (f'佐證類措辭補充\n\n1. 團隊合作價值：宜搭配實際行為事例佐證。\n\n'
                  f'2. 最能互補：可透過工作樣本加以驗證。\n\n{CLOSER}')
    out = strip_duplicate_closer(supplement, ANSWER)
    check('結語不再出現於補充內容', CLOSER not in out, f'{out.count(CLOSER)} 次')
    check('補充內容完整保留',
          '行為事例佐證' in out and '工作樣本' in out and out.startswith('佐證類措辭補充'))
    check('沒有留下尾端空白', out == out.rstrip(), repr(out[-6:]))

    print('\n[2] 沒重複時不動它（避免砍掉真正的新內容）')
    supplement = '佐證類措辭補充\n\n宜搭配實際行為事例佐證，並參考工作樣本綜合判斷。'
    check('原樣返回', strip_duplicate_closer(supplement, ANSWER) == supplement)

    print('\n[3] 整段只有一句話 -> 不動（砍掉等於補充內容整個消失）')
    only = '宜搭配實際行為事例佐證，並參考工作樣本綜合判斷。'
    check('原樣返回', strip_duplicate_closer(only, ANSWER + '\n\n' + only) == only)

    print(f'\n[4] 太短的重複句不砍（門檻 {MIN_DUPLICATE_CLOSER_CHARS} 字，避免誤刪）')
    short = '宜搭配實際行為事例佐證，並參考工作樣本。以上。'
    check('原樣返回', strip_duplicate_closer(short, '前面提過。以上。') == short)

    print('\n[5] 結語句沒有寫死在程式裡（客戶改寫那句話後仍然有效）')
    custom = '這是一句完全不同的自訂結語，長度足夠。'
    out = strip_duplicate_closer('補充內容補充內容。' + custom, '內容內容。' + custom)
    check('自訂結語同樣被砍', out == '補充內容補充內容。', out)

    print('\n[6] 空字串與純空白不會炸')
    check("'' 安全", strip_duplicate_closer('', ANSWER) == '')
    check('純空白安全', strip_duplicate_closer('   ', ANSWER) == '   ')

    print('\n[7] 補生成指令有明講不要再附結語')
    check('COMPLETION_INSTRUCTION 含該指示',
          '文末不要再附上結語句' in COMPLETION_INSTRUCTION)

    print('\n[8] _complete 真的有接上（純函式存在但沒人呼叫，就是這類 bug 的溫床）')
    # 繞過 __init__：那裡的 assemble() 會去 PostgreSQL 讀特質正本，而這裡要驗的只是
    # 「followup_fn 的輸出有沒有經過 strip_duplicate_closer」。
    p = LogPipeline.__new__(LogPipeline)
    p.messages = [{'role': 'system', 'content': 'x'}]
    p.followup_fn = lambda messages, instruction: (
        f'宜搭配實際行為事例佐證，並參考工作樣本綜合判斷。\n\n{CLOSER}')
    p.checker = type('C', (), {'text': ANSWER})()
    out = p._complete('需加入佐證類措辭')
    check('_complete 的輸出不含重複結語', CLOSER not in out, out)
    check('_complete 仍帶回佐證措辭', '行為事例' in out and '工作樣本' in out, out)

    # ---- 補生成該不該啟動 --------------------------------------------------------
    # 上面的字串修正只擋得住「補充區塊尾巴多一句結語」。第二次通報的情形更嚴重：模型把
    # 整份回答重寫了一遍，第二份結尾沒有結語句，字串修正完全不會觸發。根因是補生成被
    # 用在一個「附加文字無法修好」的失敗上。
    print('\n[9] 只有佐證措辭沒過 -> 不呼叫補生成，改判 manual_review')
    calib = sorted(table.calibration_traits)[0]
    r = [Respondent('張詠婕', 'R1', {calib: 'A'})]
    q = table.get('如何面對困難、壓力、挑戰')
    answer = '\n\n'.join(f'{s}\n內容內容內容。' for s in (q['expected_sections'] or []))

    called = []
    gate = SegmentGate(ExitScanner(injected_names=set(), injected_labels=set()),
                       checker=CompletenessChecker(r, q, table.calibration_traits),
                       completer=lambda reason: called.append(reason) or '補生成的內容。')
    out = ''.join(gate.run([answer]))
    res = gate.result
    check('補生成沒有被呼叫', called == [], called)
    check('completion_attempts 是 0', res.completion_attempts == 0, res.completion_attempts)
    check('status 是 manual_review', res.status == STATUS_MANUAL_REVIEW, res.status)
    check('沒有把回答重播一次', out.count('內容內容內容。') == len(q['expected_sections']),
          out.count('內容內容內容。'))
    check('稽核仍記錄佐證未過',
          res.completeness.calibration_evidence == 'failed',
          res.completeness.calibration_evidence)
    check('reason() 仍完整說明（給稽核看）',
          '佐證' in res.completeness.reason(), res.completeness.reason())
    check('appendable_reason() 是空的（給補生成看）',
          res.completeness.appendable_reason() == '',
          res.completeness.appendable_reason())

    print('\n[10] 缺段落 -> 補生成照常啟動（附加文字修得好的才跑）')
    called = []
    partial = '\n\n'.join(f'{s}\n內容內容內容。' for s in q['expected_sections'][:2])
    gate = SegmentGate(ExitScanner(injected_names=set(), injected_labels=set()),
                       checker=CompletenessChecker(r, q, table.calibration_traits),
                       completer=lambda reason: called.append(reason) or '補生成的內容。')
    list(gate.run([partial]))
    check('補生成有被呼叫', len(called) == 1, called)
    check('傳給模型的理由只提缺段落，不提佐證',
          called and '缺少段落' in called[0] and '佐證' not in called[0], called)

    print('\n[11] 自由提問超過字數 -> 不補生成（補下去只會更長）')
    called = []
    gate = SegmentGate(ExitScanner(injected_names=set(), injected_labels=set()),
                       checker=CompletenessChecker(r, None, table.calibration_traits),
                       completer=lambda reason: called.append(reason) or '補生成的內容。')
    list(gate.run(['太長。' * 400 + '行為事例佐證。']))
    check('補生成沒有被呼叫', called == [], called)
    check('status 是 manual_review', gate.result.status == STATUS_MANUAL_REVIEW,
          gate.result.status)

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

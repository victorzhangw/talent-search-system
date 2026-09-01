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
    COMPLETION_INSTRUCTION, COMPLETION_SEPARATOR, LogPipeline,
    MIN_DUPLICATE_CLOSER_CHARS, closing_sentence, strip_completion_preamble,
    strip_duplicate_closer, strip_trailing_closer)
from api_v2.services.question_table import table  # noqa: E402
from api_v2.services.segment_gate import (  # noqa: E402
    SegmentGate, STATUS_MANUAL_REVIEW)

CLOSER = '本分析旨在提供觀點與輔助，最終決策請結合多方資訊綜合考量。'

ANSWER = ('1. 團隊合作價值\n\n他習慣憑當下判斷把事情快速兜起來。\n\n'
          '4. 共同合作策略\n\n分工建議：讓他負責需要快速反應的環節。\n\n' + CLOSER)

failures = []


def verify_preamble_and_separator():
    """2026-08-25 的兩個現場：補生成的寒暄開場，以及補充內容黏在結語句後面。

    req f1d36fbb 顯示給使用者的是
      「…與後續面談綜合判斷。好的，補上各候選人領導摘要中缺少的段落。」
    req 030c09f8 是
      「…最終決策請結合多方資訊綜合考量。## 溝通風格摘要」
    兩者都擠在同一行，看起來像輸出壞掉而不像補充。
    """
    print('\n[13] 補生成的寒暄開場要被剝掉')
    cases = [
        ('好的，補上各候選人領導摘要中缺少的段落。\n\n## 二、個別候選人領導摘要', True),
        ('了解，以下補上缺少的部分。\n\n## 需要避免的溝通方式', True),
        ('以下為補充內容：\n\n## 跨情境溝通提醒', True),
    ]
    for text, should_strip in cases:
        out = strip_completion_preamble(text)
        first = out.split('\n')[0]
        check(f'{text.split(chr(10))[0][:20]!r} -> 剝掉', first.startswith('##') == should_strip,
              repr(first))

    keep = [
        '## 溝通風格摘要\n\n他偏好結論先行。',              # 標題不是寒暄
        '- **主要領導風格**：推進驅動型',                    # 條列也不是
        '好奇心是他最明顯的特徵，這一段補充如下。\n\n## 補充',  # 「好」開頭但是實質內容
    ]
    for text in keep:
        check(f'不該剝：{text.split(chr(10))[0][:22]!r}',
              strip_completion_preamble(text) == text, repr(strip_completion_preamble(text)[:40]))

    print('\n[14] 補充內容不可黏在結語句後面')
    p = LogPipeline.__new__(LogPipeline)
    p.messages = [{'role': 'system', 'content': 'x'}]
    p.followup_fn = lambda messages, instruction: (
        '好的，補上缺少的段落。\n\n## 跨情境溝通提醒\n\n一對一時他較願意表達。')
    p.checker = type('C', (), {'text': ANSWER})()
    out = p._complete('缺少段落：跨情境溝通提醒')
    check('開頭是分隔而不是內文', out.startswith(COMPLETION_SEPARATOR), repr(out[:12]))
    check('寒暄已被剝掉', '好的，補上' not in out, out[:40])
    check('補充內容保留', '跨情境溝通提醒' in out and '一對一' in out, out[:60])
    glued = (ANSWER + out).replace(COMPLETION_SEPARATOR, '\n')
    check('接上去之後結語句自成一行',
          any(l.strip() == CLOSER for l in glued.split('\n')),
          [l[-30:] for l in glued.split('\n') if CLOSER[:8] in l])

    print('\n[15] 補生成整段為空時不要留下孤兒分隔線')
    p.followup_fn = lambda messages, instruction: '好的，補上缺少的段落。'
    check('只有寒暄 -> 回空字串', p._complete('缺少段落：X') == '',
          repr(p._complete('缺少段落：X')))
    p.followup_fn = lambda messages, instruction: '   \n  '
    check('純空白 -> 回空字串', p._complete('缺少段落：X') == '')


def verify_rewrite_closer():
    """2026-08-31：結語句改從「改寫」那條路出來，而改寫完全沒有後處理。

    req f1ea065d 的 idx 10 段被改寫後，畫面上是
      「…較快的檢核節奏。本分析旨在提供觀點與輔助…綜合考量。這份「及早發現」的用心是…」
    一個段落被結語句從中間切開。同一天 672f08ca 與 f632397b 也是同一個形狀：結語句後面
    沒有任何換行，下一段文字直接接上。而這 21 筆請求的補生成一次都沒跑（completeness
    retry 全 0），改寫跑了 63 次——8/25 只修補生成的那次修正因此完全沒被觸發。
    """
    print('\n[16] 結語句是從 system prompt 讀出來的，不是寫死的')
    check('讀得到第 6 條那句', closing_sentence() == CLOSER, repr(closing_sentence()))

    print('\n[17] 改寫輸出尾端的結語句要被剝掉')
    body = '他在工作上會自我要求、按計畫推進，對品質有清楚的期待。'
    cases = [
        (body + CLOSER, body, '黏在句尾'),
        (body + '\n\n' + CLOSER + '\n', body, '自成一段'),
        (body, body, '沒有結語句時不動'),
    ]
    for text, want, label in cases:
        check(f'{label}', strip_trailing_closer(text) == want,
              repr(strip_trailing_closer(text)[-24:]))
    check('整段只有結語句 -> 回空字串（閘門會當成一次失敗的嘗試）',
          strip_trailing_closer(CLOSER).strip() == '', repr(strip_trailing_closer(CLOSER)))
    check('讀不到那句話時什麼都不做（客戶改寫正本的退路）',
          strip_trailing_closer(body + CLOSER, closer='') == body + CLOSER)

    print('\n[18] _rewrite 串起寒暄剝除與結語句剝除')
    p = LogPipeline.__new__(LogPipeline)
    p.messages = [{'role': 'system', 'content': 'x'}]
    p.followup_fn = lambda messages, instruction: (
        '好的，以下是改寫後的段落。\n\n' + body + CLOSER)
    out = p._rewrite('原本的段落。', ['高度自律'])
    check('寒暄開場被剝掉', not out.startswith('好的'), out[:20])
    check('結語句被剝掉', CLOSER not in out, out[-24:])
    check('改寫內容保留', body in out, out[:24])

    p.followup_fn = lambda messages, instruction: CLOSER
    check('模型只回一句結語句 -> 空字串', not p._rewrite('原本的段落。', ['x']).strip())

    print('\n[19] 模型自己重複的結語句：只釋出最後一次（req 43c1f019）')
    # 那一筆 retry_count 是 {leakage: 0, completeness: 0}——完全沒有後續模型呼叫，
    # 兩句結語句都出自同一條串流，所以只能在閘門這一層處理。
    scanner = ExitScanner(injected_names=set(), injected_labels=set())
    stream = ('### 第 7 順位｜Bryce-test\n\n適配性相對有限。\n\n' + CLOSER + '\n\n'
              '---\n\n## 總結\n\n綜合排序：柳宇賸 → 簡玥瀅 → 陳冠享。\n\n' + CLOSER)
    gate = SegmentGate(scanner, closer=CLOSER)
    out = ''.join(gate.run([stream]))
    check('結語句只出現一次', out.count(CLOSER) == 1, out.count(CLOSER))
    check('而且在最後', out.rstrip().endswith(CLOSER), repr(out[-24:]))
    check('中段的內容一段都沒少',
          '適配性相對有限' in out and '## 總結' in out and '綜合排序' in out)
    check('沒有結語句時行為不變',
          ''.join(SegmentGate(scanner, closer=CLOSER).run(['一般內容。\n\n第二段。'])) ==
          '一般內容。\n\n第二段。')

    print('\n[20] 補充內容排在結語句之前，不是之後')
    # strip_duplicate_closer 的 docstring 記著這個取捨：已釋出的段落不能收回，所以結語句
    # 必然停在第一輪的結尾、補充落在它後面。延後釋出把這個取捨也解掉了。
    q = table.get('如何面對困難、壓力、挑戰')
    sections = q['expected_sections'] or []
    r = [Respondent('王智弘', 'R1', {'CIA_05': 'B'})]
    partial = ''.join(f'{i + 1}. {s}\n內容。\n\n' for i, s in enumerate(sections[:-1]))
    gate = SegmentGate(scanner, checker=CompletenessChecker(r, q, table.calibration_traits),
                       completer=lambda reason: f'{len(sections)}. {sections[-1]}\n補上的內容。\n\n',
                       closer=CLOSER)
    out = ''.join(gate.run([partial + CLOSER]))
    check('補上的段落有出現', sections[-1] in out, out[-60:])
    check('結語句在補充內容之後', out.index(CLOSER) > out.index('補上的內容'),
          repr(out[-40:]))
    check('結語句仍然只有一次', out.count(CLOSER) == 1, out.count(CLOSER))


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

    verify_preamble_and_separator()

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

    print('\n[12] 只有 blocked 會通知使用者；manual_review 只進稽核日誌')
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                            'api_v2', 'routes', 'chat.py'), encoding='utf-8').read()
    # `if packed is not None:` also guards where the stream is obtained, so anchor on
    # finish() -- the only place the audit status is read.
    notice = src[src.index('packer_audit = packed.finish()'):]
    notice = notice[:notice.index('\n\n')]
    check('條件是 status == STATUS_BLOCKED',
          "== STATUS_BLOCKED" in notice, notice.splitlines()[-2:])
    check('不再用「!= ok」（那會把 manual_review 也送出去）',
          "!= 'ok'" not in notice)
    check('舊的「已轉人工複核」文案已移除', '已轉人工複核' not in src)
    check('blocked 的文案講的是「中途停止」而非「未通過檢查」',
          '中途停止' in notice, notice.splitlines()[-1][:80])

    verify_rewrite_closer()

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

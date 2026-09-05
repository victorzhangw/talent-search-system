"""Segment gate acceptance: segmentation, per-segment scanning, rewrite, state machine.

Usage:
    python scripts/verify_segment_gate.py

Runs against a scripted fake model so the behaviour is deterministic and no API calls are
made. What matters here is not that a real model produces clean text, but that nothing
dirty is ever yielded to the caller.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

from api_v2.services.question_table import table  # noqa: E402
from api_v2.services.log_assembler import Respondent  # noqa: E402
from api_v2.services.exit_scanner import ExitScanner  # noqa: E402
from api_v2.services.completeness_check import CompletenessChecker  # noqa: E402
from api_v2.services.segment_gate import (  # noqa: E402
    Segmenter, SegmentGate, STATUS_OK, STATUS_BLOCKED, STATUS_MANUAL_REVIEW,
    SEGMENT_MAX_CHARS)

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def tokens_of(text, size=3):
    return [text[i:i + size] for i in range(0, len(text), size)]


def main():
    q5 = table.get('如何面對困難、壓力、挑戰')
    r1 = [Respondent('王智弘', 'R1', {'CIA_05': 'B'})]
    scanner = ExitScanner(injected_names={'衝動管理'}, injected_labels={'情境波動'})

    print('\n[1] Segmenter')
    seg = Segmenter()
    text = '第一段內容。\n\n第二段內容。\n\n第三段。'
    out = []
    for t in tokens_of(text):
        out.extend(seg.feed(t))
    out.extend(seg.flush())
    check('splits on blank lines', len(out) == 3, [s.strip() for s in out])
    check('concatenation reproduces the stream exactly', ''.join(out) == text)

    seg = Segmenter(max_chars=50)
    long_para = '這是一個很長的段落。' * 12
    out = []
    for t in tokens_of(long_para):
        out.extend(seg.feed(t))
    out.extend(seg.flush())
    check('long paragraph is cut before the cap', all(len(s) <= 60 for s in out),
          [len(s) for s in out])
    check('cuts land on sentence ends', all(s.rstrip().endswith('。') for s in out[:-1]),
          [s[-3:] for s in out[:-1]])
    check('no text is lost when cutting', ''.join(out) == long_para)
    check(f'default cap is {SEGMENT_MAX_CHARS}', Segmenter().max_chars == SEGMENT_MAX_CHARS)

    print('\n[2] Clean stream passes straight through')
    clean = '他在高壓下多能維持節奏。\n\n建議主管在連續高壓期主動關心。\n\n'
    gate = SegmentGate(scanner)
    emitted = list(gate.run(tokens_of(clean)))
    check('all segments released', ''.join(emitted) == clean)
    check('status ok', gate.result.status == STATUS_OK)
    check('no rewrites', gate.result.retry_count['leakage'] == 0)

    print('\n[3] A dirty segment is never yielded before it is clean')
    dirty = '他的 CIA_05 表現不錯。\n\n第二段沒有問題。\n\n'
    calls = []

    def rewriter(segment, banned):
        calls.append((segment, tuple(banned)))
        return '他在壓力下的自制表現不錯。\n\n'

    gate = SegmentGate(scanner, rewriter=rewriter)
    emitted = list(gate.run(tokens_of(dirty)))
    check('nothing emitted contains the marker',
          all('CIA_05' not in e for e in emitted), emitted)
    check('the rewriter was given the offending term',
          calls and 'CIA_05' in calls[0][1], calls[:1])
    check('one rewrite recorded', gate.result.retry_count['leakage'] == 1)
    check('status ok after a successful rewrite', gate.result.status == STATUS_OK)
    check('the clean second segment still came through', '第二段沒有問題' in ''.join(emitted))

    print('\n[4] A segment that cannot be cleaned blocks it and everything after')
    def stubborn(segment, banned):
        return segment                      # model keeps producing the same leak

    gate = SegmentGate(scanner, rewriter=stubborn)
    emitted = list(gate.run(tokens_of(dirty)))
    check('the dirty segment is not emitted', not emitted, emitted)
    check('later segments are withheld too', '第二段' not in ''.join(emitted))
    check('status blocked', gate.result.status == STATUS_BLOCKED)
    check('rewrites capped at 2', gate.result.retry_count['leakage'] == 2,
          gate.result.retry_count)
    check('the surviving terms are recorded for audit',
          'CIA_05' in gate.result.as_audit()['leakage_hits'],
          gate.result.as_audit()['leakage_hits'])

    print('\n[5] Already-released segments cannot be recalled (丙-3)')
    late = '第一段乾淨。\n\n他的 CIA_05 有問題。\n\n'
    gate = SegmentGate(scanner, rewriter=stubborn)
    emitted = list(gate.run(tokens_of(late)))
    check('the clean first segment was released', '第一段乾淨' in ''.join(emitted))
    check('the dirty second one was not', 'CIA_05' not in ''.join(emitted))
    check('status blocked, not ok', gate.result.status == STATUS_BLOCKED)

    print('\n[6] Cross-boundary marker (丁-2 overlap window)')
    # The realistic case is a long paragraph cut at the character cap, not a blank line:
    # a blank line would itself separate the two halves and no pattern could span it.
    # With max_chars=10 the cut lands inside the id, so neither half trips on its own.
    split_marker = '參考參考參考參考參CIA_05的表現'
    halves = Segmenter(max_chars=10).feed(split_marker) or []
    check('the test really does split the marker in two',
          halves and 'CIA_05' not in halves[0], [h for h in halves])

    gate = SegmentGate(scanner, rewriter=stubborn, max_chars=10)
    list(gate.run(tokens_of(split_marker)))
    check('the split marker is caught', gate.result.status == STATUS_BLOCKED,
          gate.result.as_audit()['leakage_hits'])
    gate_no_overlap = SegmentGate(scanner, rewriter=stubborn, max_chars=10, overlap=0)
    list(gate_no_overlap.run(tokens_of(split_marker)))
    check('and would slip through without the overlap window',
          gate_no_overlap.result.status == STATUS_OK)

    print('\n[7] Completeness runs at the end, on cleared segments only (丙-1)')
    sections = q5['expected_sections']
    full = ''.join(f'{i + 1}. {s}\n內容。\n\n' for i, s in enumerate(sections))
    checker = CompletenessChecker(r1, q5, table.calibration_traits)
    gate = SegmentGate(scanner, checker=checker)
    list(gate.run(tokens_of(full)))
    check('complete answer -> ok', gate.result.status == STATUS_OK,
          gate.result.completeness)
    check('completeness result is in the audit',
          gate.result.as_audit()['expected_sections_check'] == 'passed')

    print('\n[8] Missing section -> one completion, appended not regenerated (丙-2)')
    partial = ''.join(f'{i + 1}. {s}\n內容。\n\n' for i, s in enumerate(sections[:-1]))
    reasons = []

    def completer(reason):
        reasons.append(reason)
        return f'{len(sections)}. {sections[-1]}\n補充內容。\n\n'

    checker = CompletenessChecker(r1, q5, table.calibration_traits)
    gate = SegmentGate(scanner, checker=checker, completer=completer)
    emitted = list(gate.run(tokens_of(partial)))
    check('the completer was told what was missing',
          reasons and sections[-1] in reasons[0], reasons[:1])
    check('the missing section was appended', sections[-1] in ''.join(emitted))
    check('earlier segments were not regenerated', ''.join(emitted).startswith('1. '))
    check('status ok after completion', gate.result.status == STATUS_OK)
    check('completeness retry counted separately',
          gate.result.retry_count == {'leakage': 0, 'completeness': 1},
          gate.result.retry_count)

    print('\n[9] Completion that still misses -> manual_review')
    checker = CompletenessChecker(r1, q5, table.calibration_traits)
    gate = SegmentGate(scanner, checker=checker, completer=lambda reason: '無關內容。\n\n')
    list(gate.run(tokens_of(partial)))
    check('status manual_review', gate.result.status == STATUS_MANUAL_REVIEW)
    check('only one completion attempt', gate.result.retry_count['completeness'] == 1)
    check('no completer at all -> manual_review too',
          _no_completer_status(scanner, r1, q5, partial) == STATUS_MANUAL_REVIEW)

    print('\n[10] The two budgets do not share a counter (b §7)')
    one_bad = '他的 CIA_05 有問題。\n\n' + partial

    def fix_once(segment, banned):
        return '他的表現有起伏。\n\n'

    checker = CompletenessChecker(r1, q5, table.calibration_traits)
    gate = SegmentGate(scanner, checker=checker, rewriter=fix_once, completer=completer)
    list(gate.run(tokens_of(one_bad)))
    check('a leakage rewrite did not consume the completeness budget',
          gate.result.retry_count == {'leakage': 1, 'completeness': 1},
          gate.result.retry_count)
    check('status ok', gate.result.status == STATUS_OK)

    print('\n[11] Segments are released while the model is still producing')
    # Records how much of the stream had been consumed as each segment came out. Draining
    # the whole token iterator before gating anything would show every segment at the
    # final count -- which is what the first live run actually did.
    src = '第一段內容。\n\n第二段內容。\n\n第三段內容。\n\n'
    consumed_at = []

    def counting():
        counting.seen = 0
        for t in tokens_of(src, 4):
            counting.seen += len(t)
            yield t

    gate_t = SegmentGate(scanner)
    for _ in gate_t.run(counting()):
        consumed_at.append(counting.seen)
    check('a segment is released before the whole stream has arrived',
          consumed_at and consumed_at[0] < len(src), consumed_at)
    check('release points advance with the stream',
          consumed_at == sorted(consumed_at) and consumed_at[0] < consumed_at[-1],
          consumed_at)

    print('\n[12] Audit shape for 事項 12')
    audit = gate.result.as_audit()
    check('carries status / retry_count / per-segment records',
          {'status', 'retry_count', 'segments', 'leakage_hits'} <= set(audit),
          sorted(audit))
    check('per-segment records include rewrites and release state',
          all({'index', 'released', 'rewrites'} <= set(s) for s in audit['segments']))

    print('\n[13] A rewrite keeps the paragraph break it replaced')
    # 2026-08-31 req f1ea065d: three consecutive table rows were rewritten, each reply
    # came back without the trailing blank line the segmenter had attached, and the rows
    # glued into one line. A GFM renderer drops the cells past the header's column count,
    # so Eddy and Eva H vanished from the table and the next heading went with them.
    header = ('| 新人 | 觀察 | 線索 | 判斷 | 其他原因 |\n'
              '| :--- | :--- | :--- | :--- | :--- |\n')
    rows = ['| **Roger** | 求快 | 高能量快節奏 | 部分相符 | 訓練設計 |\n\n',
            '| **Eddy** | 都還好 | 部分包裝 | 部分相符 | 心理安全感 |\n\n',
            '| **Eva H** | 多留 30 分鐘 | 品質苛求 | 相符線索明顯 | 自我要求 |\n\n']
    table_text = header + '\n' + ''.join(rows) + '## 二、待驗證的行為假設\n\n'
    label_scanner = ExitScanner(injected_names=set(),
                                injected_labels={'高能量快節奏', '部分包裝', '品質苛求'})

    def row_rewriter(segment, banned):
        # Replies with the row restated and no trailing newline -- what the model does.
        return segment.strip().replace('高能量快節奏', '步調快、重視效率') \
                              .replace('部分包裝', '較少主動揭露') \
                              .replace('品質苛求', '對細節要求高')

    gate = SegmentGate(label_scanner, rewriter=row_rewriter)
    released = ''.join(gate.run(tokens_of(table_text)))
    check('all three rewrites happened', gate.result.retry_count['leakage'] == 3,
          gate.result.retry_count)
    check('status ok', gate.result.status == STATUS_OK)
    check('no two table rows share a line', '||' not in released,
          [ln for ln in released.split('\n') if ln.count('| **') > 1])
    check('every row is still its own line',
          all(sum(1 for ln in released.split('\n') if name in ln) == 1
              for name in ('**Roger**', '**Eddy**', '**Eva H**')),
          [ln[:28] for ln in released.split('\n') if '| **' in ln])
    check('the following heading was not swallowed by a row',
          any(ln.startswith('## 二、') for ln in released.split('\n')),
          [ln[-24:] for ln in released.split('\n') if '二、' in ln])
    check('the banned labels are gone', all(t not in released for t in
          ('高能量快節奏', '部分包裝', '品質苛求')))

    print('\n[14] A reply that already ends in a blank line is not double-spaced')
    def tidy_rewriter(segment, banned):
        return '他在壓力下的自制表現不錯。\n\n'

    gate = SegmentGate(scanner, rewriter=tidy_rewriter)
    released = ''.join(gate.run(tokens_of('他的 CIA_05 表現不錯。\n\n第二段沒有問題。\n\n')))
    check('exactly one blank line between the two paragraphs',
          '\n\n\n' not in released, repr(released))

    print('\n[15] An empty rewrite is a failed attempt, not a clean segment')
    # `packer_followup` returns '' when the call fails, and '' scans clean -- so the gate
    # used to release nothing at all and drop the paragraph with no trace in the audit.
    for label, reply in (('empty string', ''), ('whitespace only', '   \n  ')):
        gate = SegmentGate(scanner, rewriter=lambda segment, banned, r=reply: r)
        released = ''.join(gate.run(tokens_of('他的 CIA_05 表現不錯。\n\n第二段沒有問題。\n\n')))
        check(f'{label} -> nothing released', not released.strip(), repr(released[:40]))
        check(f'{label} -> status blocked', gate.result.status == STATUS_BLOCKED)
        check(f'{label} -> the surviving term is recorded',
              'CIA_05' in gate.result.as_audit()['leakage_hits'],
              gate.result.as_audit()['leakage_hits'])
        check(f'{label} -> the attempt is not retried into the cap',
              gate.result.retry_count['leakage'] == 1, gate.result.retry_count)

    print('\n[16] Each rewrite turn is recorded, input and output')
    # Until this existed the audit held only counts. 2026-08-31 ran 63 rewrites across 21
    # requests and none of them left a trace, so the first reading of those reports blamed
    # the completion pass -- the one path that had not run at all.
    dirty2 = '他的 CIA_05 表現不錯。\n\n第二段沒有問題。\n\n'

    gate = SegmentGate(scanner, rewriter=tidy_rewriter)
    list(gate.run(tokens_of(dirty2)))
    rec = next(s for s in gate.result.as_audit()['segments'] if s['rewrites'])
    check('the rewritten segment carries rewrite_attempts', 'rewrite_attempts' in rec,
          sorted(rec))
    att = rec['rewrite_attempts'][0]
    check('the input is what the model was given',
          att['before'].startswith('他的 CIA_05'), att['before'][:24])
    check('the output is what came back', '自制表現不錯' in att['after'], att['after'][:24])
    check('both exact lengths are kept',
          att['before_len'] == len('他的 CIA_05 表現不錯。\n\n')
          and att['after_len'] == len(tidy_rewriter('', [])),
          (att['before_len'], att['after_len']))
    check('and what the scan found afterwards', att.get('after_hits') == [], att.get('after_hits'))
    check('untouched segments carry no attempts key',
          all('rewrite_attempts' not in s
              for s in gate.result.as_audit()['segments'] if not s['rewrites']))

    gate = SegmentGate(scanner, rewriter=stubborn)
    list(gate.run(tokens_of(dirty2)))
    rec = gate.result.as_audit()['segments'][0]
    check('a stubborn segment records every attempt',
          len(rec['rewrite_attempts']) == 2, len(rec['rewrite_attempts']))
    check('each one shows the term that survived it',
          all('CIA_05' in a.get('after_hits', []) for a in rec['rewrite_attempts']),
          [a.get('after_hits') for a in rec['rewrite_attempts']])

    gate = SegmentGate(scanner, rewriter=lambda segment, banned: '')
    list(gate.run(tokens_of(dirty2)))
    att = gate.result.as_audit()['segments'][0]['rewrite_attempts'][0]
    check('an empty reply is recorded rather than looking like a success',
          att['after_len'] == 0 and att['before_len'] > 0,
          (att['before_len'], att['after_len']))

    def exploding(segment, banned):
        raise RuntimeError('upstream 503')

    gate = SegmentGate(scanner, rewriter=exploding)
    list(gate.run(tokens_of(dirty2)))
    att = gate.result.as_audit()['segments'][0]['rewrite_attempts'][0]
    check('a failed call records why', 'upstream 503' in att.get('error', ''),
          att.get('error'))
    check('and still blocks', gate.result.status == STATUS_BLOCKED)

    print('\n[17] Long text is elided but the lengths stay exact')
    long_dirty = '他的 CIA_05 ' + '表現很不錯。' * 120 + '\n\n'
    gate = SegmentGate(scanner, rewriter=lambda segment, banned: '改寫。' * 200,
                       max_chars=2000)
    list(gate.run([long_dirty]))
    att = gate.result.as_audit()['segments'][0]['rewrite_attempts'][0]
    check('the recorded text is capped', len(att['before']) < att['before_len'],
          (len(att['before']), att['before_len']))
    check('and says how much was cut', 'chars)' in att['before'], att['before'][-24:])
    check('after_len is the real length', att['after_len'] == len('改寫。' * 200),
          att['after_len'])

    print('\n[標題段落被改寫成整段（修正計畫 Unit 4a）]')
    # 實測四次：24->1270、26->779、34->932、35->737 字，全都是只有一行標題的段落。
    # 那一整段被釋出，接著模型自己原本要寫的內容也串流進來、也被釋出，讀者看到兩次。
    heading = '## 四、面談時的情境波動評估\n\n'
    whole_section = '## 四、面談時的評估\n\n' + '模型自己又寫了一整段內容。' * 40
    gate = SegmentGate(scanner, rewriter=lambda s, b: whole_section, max_chars=2000)
    out = ''.join(gate.run([heading]))
    rec = gate.result.as_audit()['segments'][0]
    check('撐大的改寫被當成失敗的嘗試，不會釋出',
          whole_section not in out and rec['rewrite_attempts'][0].get('rejected') == 'overgrown',
          rec['rewrite_attempts'][0].get('rejected'))
    # 長度相稱的改寫照常接受——這條擋的是「模型另外寫了一段」，不是「改寫比原文長一點」。
    gate = SegmentGate(scanner, rewriter=lambda s, b: '## 四、面談時的自我節制評估\n\n',
                       max_chars=2000)
    out = ''.join(gate.run([heading]))
    check('長度相稱的標題改寫照常釋出', '自我節制' in out and gate.result.status != STATUS_BLOCKED,
          (out.strip(), gate.result.status))
    # 正常長度的段落多寫幾個字不受影響。
    body = '他在壓力下的情境波動值得留意。' * 8
    gate = SegmentGate(scanner, rewriter=lambda s, b: body.replace('情境波動', '自我節制') + '補充一句。',
                       max_chars=2000)
    out = ''.join(gate.run([body + '\n\n']))
    check('一般段落的自然增減不受門檻影響', '自我節制' in out and '情境波動' not in out)

    print('\n[標題用專屬的改寫指令]')
    from api_v2.services.log_pipeline import is_heading_only
    check('只有標題的一段判為 heading', is_heading_only('## 四、面談時需要確認的能力\n\n'))
    check('標題加內文不算', not is_heading_only('## 標題\n\n這裡是內文。' * 5))
    check('沒有標題標記的短句不算', not is_heading_only('這是一句話。\n\n'))
    check('多行純標題也算', is_heading_only('### 第一優先\n**風險**\n'))

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


def _no_completer_status(scanner, respondents, question, partial):
    checker = CompletenessChecker(respondents, question, table.calibration_traits)
    gate = SegmentGate(scanner, checker=checker)
    list(gate.run(tokens_of(partial)))
    return gate.result.status


if __name__ == '__main__':
    sys.exit(main())

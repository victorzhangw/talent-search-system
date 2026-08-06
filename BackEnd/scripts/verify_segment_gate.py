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

    print('\n[11] Audit shape for 事項 12')
    audit = gate.result.as_audit()
    check('carries status / retry_count / per-segment records',
          {'status', 'retry_count', 'segments', 'leakage_hits'} <= set(audit),
          sorted(audit))
    check('per-segment records include rewrites and release state',
          all({'index', 'released', 'rewrites'} <= set(s) for s in audit['segments']))

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


def _no_completer_status(scanner, respondents, question, partial):
    checker = CompletenessChecker(respondents, question, table.calibration_traits)
    gate = SegmentGate(scanner, checker=checker)
    list(gate.run(tokens_of(partial)))
    return gate.result.status


if __name__ == '__main__':
    sys.exit(main())

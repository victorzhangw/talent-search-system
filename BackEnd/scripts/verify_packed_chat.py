"""The switch between the packer path and the legacy path.

Usage:
    python scripts/verify_packed_chat.py

What matters is the decision, not the model: for each request shape, does the packer
serve it or hand it back? Handing it back must be the outcome whenever anything is
missing, because the caller then runs the untouched legacy route.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

from sqlalchemy import text  # noqa: E402
from api_v2.database.connection import get_db_engine  # noqa: E402
from api_v2.services.packed_chat import try_packed_stream, PackedStream  # noqa: E402
from api_v2.services.respondent_adapter import from_trait_reports  # noqa: E402

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


class FakeRag:
    """Scripted stand-in for RAGService: same two methods the packer uses."""

    def __init__(self, answer, followup=''):
        self.answer = answer
        self.followup = followup
        self.stream_calls = 0

    def packer_stream(self, messages):
        self.stream_calls += 1
        for i in range(0, len(self.answer), 9):
            yield self.answer[i:i + 9]

    def packer_followup(self, messages, instruction):
        return self.followup


def trait_report(names_scores, abbrev='CIA'):
    return {'project_name_abbreviation': abbrev,
            'traits': [{'name': n, 'score': s} for n, s in names_scores]}


def main():
    with get_db_engine().connect() as c:
        rows = c.execute(text("""SELECT d.name_en, b.min_score, b.max_score
                                 FROM trait_definitions d JOIN trait_bands b USING (trait_id)
                                 WHERE d.trait_id IN ('CIA_01','CIA_05','CIA_16','CIA_18')
                                   AND b.band = 'A'""")).fetchall()
    traits = [(en, (lo + hi) // 2) for en, lo, hi in rows]
    reports = {'C1': trait_report(traits)}
    basics = [{'candidate_id': 'C1', 'name': '王智弘'}]

    print(f'\n[0] Frontend payload resolves ({len(traits)} traits)')
    resp = from_trait_reports(reports, basics)
    check('one respondent built', len(resp) == 1, [r.name for r in resp])
    check('scores resolved to bands', resp and len(resp[0].scores) == len(traits),
          resp[0].scores if resp else None)

    print('\n[1] Quick-question request is served by the packer')
    rag = FakeRag('1. 壓力情境下的典型反應模式\n以行為事例佐證。\n\n')
    packed = try_packed_stream(rag, 'mgmt_pressure', '', 'expert', reports, basics, 'S1')
    check('packer accepts', isinstance(packed, PackedStream))
    chunks = list(packed) if packed else []
    check('yields chunk-shaped objects',
          chunks and all(hasattr(ch, 'choices') and hasattr(ch, 'usage') for ch in chunks),
          len(chunks))
    check('content is on choices[0].delta.content',
          chunks and chunks[0].choices[0].delta.content.startswith('1. '))
    check('the model was called once', rag.stream_calls == 1)

    print('\n[2] Free-form request (no module) is served')
    rag = FakeRag('他在指導他人時通常有耐心。\n\n')
    packed = try_packed_stream(rag, None, '他適合帶新人嗎？', 'expert', reports, basics, 'S2')
    check('packer accepts free-form', isinstance(packed, PackedStream))
    list(packed)
    check('audit records a free-form question_id of None',
          packed.finish() == {} and packed.finished)

    print('\n[3] Falls back to the legacy path when it cannot serve')
    rag = FakeRag('x')
    check('unknown module_id -> None',
          try_packed_stream(rag, 'no_such_module', '', 'expert', reports, basics, 'S3') is None)
    check('no trait reports -> None',
          try_packed_stream(rag, 'mgmt_pressure', '', 'expert', {}, basics, 'S4') is None)
    check('report without project_name_abbreviation -> None',
          try_packed_stream(rag, 'mgmt_pressure', '', 'expert',
                            {'C1': {'traits': [{'name': 'Hope', 'score': 80}]}},
                            basics, 'S5') is None)
    check('unresolvable trait names -> None',
          try_packed_stream(rag, 'mgmt_pressure', '', 'expert',
                            {'C1': trait_report([('NotARealTrait', 50)])}, basics, 'S6') is None)
    check('audience mismatch -> None (legacy behaviour preserved)',
          try_packed_stream(rag, 'recruit_interview', '', 'expert',
                            {'C1': trait_report(traits), 'C2': trait_report(traits)},
                            basics + [{'candidate_id': 'C2', 'name': '林孟德'}],
                            'S7') is None)
    check('the model was never called on any fallback', rag.stream_calls == 0)

    print('\n[4] Status is surfaced so the route can notify the user')
    rag = FakeRag('1. 壓力情境下的典型反應模式\n他的 CIA_05 有問題。\n\n',
                  followup='他的 CIA_05 還是在。\n\n')
    packed = try_packed_stream(rag, 'mgmt_pressure', '', 'expert', reports, basics, 'S8')
    out = ''.join(ch.choices[0].delta.content for ch in packed)
    check('nothing leaked to the caller', 'CIA_05' not in out, out[:60])
    check('status is blocked', packed.status == 'blocked', packed.status)

    rag = FakeRag('1. 壓力情境下的典型反應模式\n以行為事例佐證。\n\n')
    packed = try_packed_stream(rag, 'mgmt_pressure', '', 'expert', reports, basics, 'S9')
    list(packed)
    check('a complete answer reports manual_review or ok, never blocked',
          packed.status in ('ok', 'manual_review'), packed.status)

    print('\n[5] finish() is idempotent (the route may call it after iteration)')
    rag = FakeRag('內容。\n\n')
    packed = try_packed_stream(rag, 'mgmt_pressure', '', 'expert', reports, basics, 'S10')
    list(packed)
    first = packed.finished
    second = packed.finish()
    check('already finished after iteration', first)
    check('a second call is a no-op', second == {})

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

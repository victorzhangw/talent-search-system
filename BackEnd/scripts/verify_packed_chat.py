"""The switch between the packer path and the legacy path.

Usage:
    python scripts/verify_packed_chat.py

What matters is the decision, not the model: for each request shape, does the packer
serve it or hand it back? Handing it back must be the outcome whenever anything is
missing, because the caller then runs the untouched legacy route.
"""

import os
import sys
from datetime import datetime

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

    def __init__(self, answer, followup='', history=None):
        self.answer = answer
        self.followup = followup
        self.history = history or []
        self.stream_calls = 0
        self.last_messages = None

    def load_history(self, session_id):
        return list(self.history)

    def packer_stream(self, messages):
        self.stream_calls += 1
        self.last_messages = messages
        for i in range(0, len(self.answer), 9):
            yield self.answer[i:i + 9]

    def packer_followup(self, messages, instruction):
        return self.followup


def _clean_dropped_total(rag, reports, basics):
    packed = try_packed_stream(rag, None, '他適合帶新人嗎？', 'expert', reports, basics, 'S14')
    list(packed)
    return packed.finish()['dropped_traits']['total']


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
          packed.finish().get('question_id') is None and packed.finished)

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
    # The route calls finish() after the loop, and iteration has already finished it; a
    # second call must still hand back the audit or the user is never told about a
    # blocked/manual_review answer.
    check('a repeat call returns the same audit, not an empty dict',
          second and second.get('status') == packed.status, second.get('status') if second else second)

    print('\n[6] Conversation history reaches the model')
    # Without this the packer path is stateless: 「那他呢？」 arrives with nothing to
    # resolve the pronoun against, while the legacy path carries MAX_HISTORY_TURNS turns.
    prior = [{'role': 'user', 'content': '他抗壓性如何？'},
             {'role': 'assistant', 'content': '他在高壓情境下傾向維持穩定。'}]
    rag = FakeRag('內容。\n\n', history=prior)
    packed = try_packed_stream(rag, 'mgmt_pressure', '', 'expert', reports, basics, 'S_H')
    list(packed)
    sent = rag.last_messages or []
    check('history is threaded into the messages', len(sent) == 2 + len(prior), len(sent))
    check('it sits between the system payload and the task instruction',
          len(sent) > 3 and sent[0]['role'] == 'system'
          and sent[1:3] == prior and sent[-1]['role'] == 'user')

    rag = FakeRag('內容。\n\n')
    packed = try_packed_stream(rag, 'mgmt_pressure', '', 'expert', reports, basics, 'S_H2')
    list(packed)
    check('an empty history still yields a well-formed 2-message payload',
          rag.last_messages and len(rag.last_messages) == 2, len(rag.last_messages or []))

    print('\n[7] The assembled LOG is written to prompts.log (事項 07 §3)')
    # Reading the real log file rather than a mock: the point of this check is that the
    # audit trail exists on disk after a request, which a captured logger cannot prove.
    log_path = os.path.join(os.path.dirname(__file__), '..', 'api_v2', 'logs',
                            datetime.now().strftime('%Y-%m-%d'), 'prompts.log')
    before = os.path.getsize(log_path) if os.path.exists(log_path) else 0

    rag = FakeRag('內容。\n\n')
    packed = try_packed_stream(rag, 'mgmt_pressure', '', 'expert', reports, basics, 'S11')
    check('packer served the request', isinstance(packed, PackedStream))
    written = ''
    if os.path.exists(log_path):
        with open(log_path, encoding='utf-8') as f:
            f.seek(before)
            written = f.read()
    check('prompts.log grew', bool(written.strip()), f'{len(written)} chars appended')
    check('header names the session and question',
          'SESSION: S11' in written and 'USE_CASE: log_packer' in written)

    payload = packed._pipeline.log.to_log_text() if packed else ''
    check('the payload is recorded verbatim (same string DoD 1 diffs)',
          payload and payload in written, f'{len(payload)} chars')
    check('三段式結構齊全',
          all(m in written for m in ('[SYSTEM PROMPT]', '## 【輸入數據】', '[任務指令]')))
    # The three things that were invisible before this was added.
    check('特質屬性 blocks present', '[特質 | ' in written,
          written.count('[特質 | '))
    check('交互敘事 present', '[交互 | ' in written, written.count('[交互 | '))
    check('分段（子區塊標頭）present', '#### ' in written, written.count('#### '))

    before = os.path.getsize(log_path) if os.path.exists(log_path) else 0
    try_packed_stream(rag, 'no_such_module', '', 'expert', reports, basics, 'S12')
    after = os.path.getsize(log_path) if os.path.exists(log_path) else 0
    check('a declined request logs no payload', after == before, f'{after - before} bytes')

    # ---- 被丟棄的特質要出現在稽核紀錄裡 -------------------------------------------
    # 2026-08-31：235 個特質被丟棄，其中一份報告 79 個只有 18 個進得了 payload，而稽核
    # 紀錄裡完全沒有這件事——traits_total 記的是「進來的」，不是「送出的」，所以讀 log
    # 的人看不出這份分析是用殘缺資料寫的。
    print('\n[13] Dropped traits are counted, per respondent')
    mixed = {'C1': trait_report(traits + [('NotARealTrait', 50), ('AlsoNotReal', 60)])}
    rag = FakeRag('他在指導他人時通常有耐心。\n\n')
    packed = try_packed_stream(rag, None, '他適合帶新人嗎？', 'expert', mixed, basics, 'S13')
    check('a report with unresolvable traits is still served',
          isinstance(packed, PackedStream))
    list(packed)
    audit = packed.finish()
    check('the audit carries a dropped_traits block',
          audit.get('dropped_traits', {}).get('total') == 2, audit.get('dropped_traits'))
    dropped_names = {d['display_name']
                     for d in audit['dropped_traits']['by_respondent'].get('C1', [])}
    check('attributed to the respondent, by name',
          dropped_names == {'NotARealTrait', 'AlsoNotReal'}, dropped_names)
    check('and to the vendor id field even when the payload had none',
          all('api_trait_id' in d
              for d in audit['dropped_traits']['by_respondent']['C1']))
    r0 = audit['respondents'][0]
    check('the respondent row reports sent vs packed',
          r0['traits_dropped'] == 2 and r0['traits_sent'] == r0['traits_total'] + 2,
          {k: r0[k] for k in ('traits_total', 'traits_dropped', 'traits_sent')})
    check('a clean request reports zero rather than omitting the block',
          _clean_dropped_total(rag, reports, basics) == 0)

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

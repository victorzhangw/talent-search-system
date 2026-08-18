"""Verify that prompts.log records the history the model reads -- offline, no model calls.

Usage:
    python scripts/verify_prompt_log_history.py

Covers V-1..V-11 of docs/0818/history-in-prompt-log.md.

Why this can run offline
------------------------
Everything under test happens before the model is reached. `log_payload()` writes the
record at packed_chat.py:153, *before* `PackedStream` is even constructed, so driving
`try_packed_stream()` and never iterating the result produces a genuine record and sends
nothing anywhere. The one place a model would normally be called -- the stub's
`packer_stream` -- raises instead, which is the assertion that this stayed true.

The load: `load_history` reads the session store, so V-5 (truncation) swaps in a fake
store rather than a fake history. The truncation arithmetic is the thing being tested and
it lives in `load_history`, not in the caller; handing the caller a pre-trimmed list would
test nothing.

Output goes to scripts/verify_logs/ so a verification run never lands in the real daily
audit trail.
"""

import os
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, '..'))
sys.path.insert(0, SCRIPT_DIR)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(SCRIPT_DIR, '..', 'api_v2', '.env'), encoding='utf-8-sig')

VERIFY_LOG_DIR = os.path.join(SCRIPT_DIR, 'verify_logs')
SEPARATOR = '=' * 60

failures = []


def check(label, ok, detail=''):
    print(f"  [{'OK' if ok else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not ok:
        failures.append(label)


class _Rag:
    """Everything try_packed_stream asks of a RAGService, and nothing more."""

    def __init__(self, history=None):
        self._history = history or []

    def load_history(self, session_id):
        return list(self._history)

    def packer_stream(self, messages):
        raise AssertionError('the model must not be called from verify_prompt_log_history.py')

    def packer_followup(self, messages, instruction):
        raise AssertionError('the model must not be called from verify_prompt_log_history.py')


class _Msg:
    """A ChatMessage as far as load_history cares: a role and a body."""

    def __init__(self, role, content):
        self.role = role
        self.content = content


def redirect_logs():
    """Point the prompt and packer-audit loggers at verify_logs/ and clear it.

    Both are redirected: V-6 joins prompts.log to log_packer_audit.log on REQ, and reading
    a stale audit file would let that check pass on last run's data.
    """
    from datetime import datetime
    from api_v2.utils.logger import get_daily_logger, get_prompt_logger
    if os.path.isdir(VERIFY_LOG_DIR):
        shutil.rmtree(VERIFY_LOG_DIR)
    for logger in (get_prompt_logger(), get_daily_logger('LogPacker', 'log_packer_audit.log')):
        for h in logger.handlers:
            if not hasattr(h, 'base_dir'):
                continue
            h.base_dir = VERIFY_LOG_DIR
            h.current_date = None      # force _get_file() to reopen under the new base_dir
            if h.file_output:
                h.file_output.close()
                h.file_output = None
    return os.path.join(VERIFY_LOG_DIR, datetime.now().strftime('%Y-%m-%d'))


def read(path):
    return open(path, encoding='utf-8').read() if os.path.exists(path) else ''


def records(text):
    """prompts.log records, split on the `REQ:` header line."""
    out, cur = [], None
    for line in text.splitlines():
        if line.startswith('REQ: '):
            cur = {'header': line, 'lines': []}
            out.append(cur)
        elif cur is not None:
            cur['lines'].append(line)
    for r in out:
        r['body'] = '\n'.join(r['lines'])
        r['text'] = r['header'] + '\n' + r['body']
    return out


def history_block(record):
    """The `[CONVERSATION HISTORY]` block, up to but excluding the `====` separator."""
    body = record['body']
    start = body.find('[CONVERSATION HISTORY]')
    end = body.find(SEPARATOR)
    return body[start:end] if start >= 0 and end > start else ''


def turn(rag, session_id, query, reports, basics, req_id):
    from api_v2.services.packed_chat import try_packed_stream
    return try_packed_stream(rag, None, query, 'free', reports, basics, session_id, req_id)


def main():
    from flask import Flask
    from api_v2.config.settings import Config
    from run_packer_live import build_trait_report

    app = Flask(__name__)
    app.config.from_object(Config)

    with app.app_context():
        day_dir = redirect_logs()
        prompts = os.path.join(day_dir, 'prompts.log')
        audit = os.path.join(day_dir, 'log_packer_audit.log')
        per_session_dir = os.path.join(day_dir, 'prompts')

        report, _ = build_trait_report('CIA', 36, 'mixed')
        reports = {'C1': report}
        basics = [{'candidate_id': 'C1', 'name': '王智弘'}]

        # === V-1..V-4, V-8: three turns with per-session logging OFF ==================
        print('\n[V-1..V-4, V-8] 三輪對話（PROMPT_LOG_PER_SESSION=off）')
        app.config['PROMPT_LOG_PER_SESSION'] = False

        q1, a1 = '他在高壓下的管理重點是什麼？', '（第一輪回覆：關於高壓下的管理重點……）'
        q2, a2 = '那他適合帶新人嗎？', '（第二輪回覆：關於帶新人的適配性……）'
        q3 = '他跟同事相處會有什麼摩擦？'

        turn(_Rag(), 'VERIFY-A', q1, reports, basics, 'reqaaa01')
        h2 = [{'role': 'user', 'content': q1}, {'role': 'assistant', 'content': a1}]
        turn(_Rag(h2), 'VERIFY-A', q2, reports, basics, 'reqaaa02')
        h3 = h2 + [{'role': 'user', 'content': q2}, {'role': 'assistant', 'content': a2}]
        streams = turn(_Rag(h3), 'VERIFY-A', q3, reports, basics, 'reqaaa03')

        recs = records(read(prompts))
        check('three records written', len(recs) == 3, len(recs))
        if len(recs) != 3:
            return finish()
        r1, r2, r3 = recs

        # -- V-1 --------------------------------------------------------------------
        check('V-1 first turn marks the history as empty',
              '(none -- first turn of this session)' in history_block(r1),
              history_block(r1).strip().replace('\n', ' / '))

        # -- V-2 --------------------------------------------------------------------
        b2, b3 = history_block(r2), history_block(r3)
        check('V-2 turn 2 carries 2 messages, turn 3 carries 4',
              b2.count('--- #') == 2 and b3.count('--- #') == 4,
              f'turn2={b2.count("--- #")} turn3={b3.count("--- #")}')
        # 逐字，不是「有出現」：摘要或截斷都會讓下面這個相等失敗。
        check('V-2 turn 3 reproduces both earlier turns verbatim',
              b3 == ('[CONVERSATION HISTORY] oldest first, verbatim, 4 messages\n'
                     f'--- #1 USER ---\n{q1}\n--- #2 ASSISTANT ---\n{a1}\n'
                     f'--- #3 USER ---\n{q2}\n--- #4 ASSISTANT ---\n{a2}\n'),
              repr(b3[:60]))

        # -- V-3 --------------------------------------------------------------------
        ok = True
        for r in recs:
            m = re.search(r'HISTORY_MSGS: (\d+) \((\d+) turns, cap=(\d+) turns/(\d+) msgs\)',
                          r['header'])
            if not m or int(m.group(1)) != history_block(r).count('--- #') \
                    or int(m.group(2)) != int(m.group(1)) // 2 \
                    or int(m.group(4)) != int(m.group(3)) * 2:
                ok = False
        check('V-3 HISTORY_MSGS matches the block and its own arithmetic', ok,
              [re.search(r'HISTORY_MSGS.*', r['header']).group(0) for r in recs])

        # -- V-4: the invariant the whole layout exists to protect --------------------
        # 從 [SYSTEM PROMPT] 到記錄結尾必須逐字等於 to_log_text()，也就是與「沒有歷史區塊」
        # 時完全相同，客戶拿去和 v7 範例逐行比對才不會因為這次改動而對不上。
        tail = r3['text'][r3['text'].index('[SYSTEM PROMPT]'):]
        tail = tail.rstrip().rstrip('=').rstrip()
        canonical = streams._pipeline.log.to_log_text().rstrip()
        check('V-4 LOG body is byte-identical to to_log_text()', tail == canonical,
              f'{len(tail)} vs {len(canonical)} chars')

        # -- V-8 --------------------------------------------------------------------
        check('V-8 no prompts/ directory while the flag is off',
              not os.path.isdir(per_session_dir), per_session_dir)

        # === V-5: truncation, driven through the real load_history ====================
        print('\n[V-5] 超過上限時丟最舊的（MAX_HISTORY_TURNS=2）')
        app.config['MAX_HISTORY_TURNS'] = 2
        from api_v2.services import session_store as store_mod
        from api_v2.services.rag_engine import RAGService

        stored = []
        for i in range(1, 5):
            stored += [_Msg('user', f'Q{i}'), _Msg('assistant', f'A{i}')]
        stored.append(_Msg('user', 'Q5'))     # 當輪 query，chat.py 已先寫入 DB
        real_store = store_mod.SqlSessionStore
        store_mod.SqlSessionStore = lambda: type('S', (), {'get_messages': lambda s, sid: stored})()
        try:
            trimmed = RAGService.load_history(object(), 'VERIFY-B')
        finally:
            store_mod.SqlSessionStore = real_store

        check('V-5 cap of 2 turns keeps 4 messages',
              [m['content'] for m in trimmed] == ['Q3', 'A3', 'Q4', 'A4'],
              [m['content'] for m in trimmed])
        app.config['MAX_HISTORY_TURNS'] = 6

        # === V-6: one REQ joins prompts.log and log_packer_audit.log ==================
        print('\n[V-6] REQ 貫穿三份 log')
        streams.finish()   # writes the packer audit record
        audit_text = read(audit)
        check('V-6 REQ in prompts.log', 'REQ: reqaaa03 |' in read(prompts))
        check('V-6 req_id in log_packer_audit.log', '"req_id": "reqaaa03"' in audit_text,
              audit_text[-120:].replace('\n', ' ') if audit_text else '(empty)')
        # conversations.log is written by the route, which needs a live request; guard the
        # two call sites at source level instead so removing REQ there cannot pass silently.
        chat_src = read(os.path.join(SCRIPT_DIR, '..', 'api_v2', 'routes', 'chat.py'))
        check('V-6 conversations.log [USER] and [AI] lines carry REQ',
              chat_src.count('REQ: {req_id}') >= 3,
              f"{chat_src.count('REQ: {req_id}')} call sites")

        # === V-7, V-9, V-10: per-session logging ON ===================================
        print('\n[V-7, V-9, V-10] per-session 檔（PROMPT_LOG_PER_SESSION=on）')
        app.config['PROMPT_LOG_PER_SESSION'] = True

        turn(_Rag(h2), 'VERIFY-C', q2, reports, basics, 'reqccc01')
        per_file = os.path.join(per_session_dir, 'VERIFY-C.log')
        check('V-7 per-session file written', os.path.exists(per_file), per_file)
        if os.path.exists(per_file):
            agg = read(prompts)
            rec = agg[agg.rindex('REQ: reqccc01'):]
            rec = rec[:rec.index(SEPARATOR, rec.index('[SYSTEM PROMPT]'))]
            check('V-7 per-session content matches the aggregate record',
                  rec.strip() in read(per_file), f'{len(rec)} chars compared')

        # -- V-9 --------------------------------------------------------------------
        turn(_Rag(), '../evil', q1, reports, basics, 'reqddd01')
        escaped = os.path.abspath(os.path.join(per_session_dir, '..', '..', 'evil.log'))
        check('V-9 a traversing session id lands in unknown.log',
              os.path.exists(os.path.join(per_session_dir, 'unknown.log'))
              and not os.path.exists(escaped), escaped)

        # -- V-10: the aggregate must survive a per-session failure -------------------
        # 失敗注入用「把目錄位置換成一個同名檔案」，makedirs 會真的失敗，走的是產品程式碼
        # 自己的 except 分支，而不是測試替身模擬出來的分支。
        shutil.rmtree(per_session_dir)
        with open(per_session_dir, 'w', encoding='utf-8') as f:
            f.write('not a directory')
        turn(_Rag(h2), 'VERIFY-E', q2, reports, basics, 'reqeee01')
        agg = read(prompts)
        # 先確認失敗真的發生了。少了這一條，注入失效時 V-10 仍會通過——彙總檔本來就寫得成，
        # 它證明不了「per-session 失敗不會連累彙總檔」。
        check('V-10 the injected per-session failure actually happened',
              not os.path.isdir(per_session_dir), per_session_dir)
        check('V-10 aggregate record still complete when per-session write fails',
              'REQ: reqeee01 |' in agg
              and agg[agg.rindex('REQ: reqeee01'):].count('[SYSTEM PROMPT]') == 1,
              'record present with its LOG body')
        os.remove(per_session_dir)

    # === V-11 ========================================================================
    print('\n[V-11] demo_prompt_log.py 仍然全綠')
    proc = subprocess.run([sys.executable, os.path.join(SCRIPT_DIR, 'demo_prompt_log.py')],
                          capture_output=True, text=True, encoding='utf-8',
                          cwd=os.path.join(SCRIPT_DIR, '..'))
    check('V-11 demo_prompt_log.py exits clean', proc.returncode == 0,
          (proc.stdout or '').strip().splitlines()[-1] if proc.stdout else proc.returncode)

    return finish()


def finish():
    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

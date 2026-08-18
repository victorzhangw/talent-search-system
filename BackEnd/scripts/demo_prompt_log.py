"""Produce a prompts.log that answers the client's 2026-08-10 review, without spending tokens.

Usage:
    python scripts/demo_prompt_log.py            # writes scripts/demo_logs/<date>/prompts.log
    python scripts/demo_prompt_log.py --check    # only re-check the file already written

Why this exists
---------------
The client reviewed `docs/0730/0810-Prompts.log` and raised three things. Two of them
(missing 可用於／禁止, missing 交互作用) turned out to be UAT data faults, now fixed; the
third (no free-form / follow-up log) was never a defect at all -- the behaviour is
implemented, the demonstration was simply missing. All three are claims about the
**payload**, and the payload is written by `packed_chat.log_payload()` at line 153 of
packed_chat.py -- *before* `PackedStream` is constructed and long before the model is
called. So driving `try_packed_stream()` and never iterating the result produces a
byte-for-byte genuine prompts.log entry and sends nothing anywhere.

What is real here and what is not:

    real  - question table, module map, trait rows, interaction rows, endpoint registry
    real  - assemble(), the b §6 unit checks, split_traits(), the interaction selector
    real  - log_payload() and the prompts.log formatter, i.e. the exact file the client reads
    stub  - the model (never called), and the conversation history (see _Rag.load_history)

The history is synthetic because `try_packed_stream` loads it from the session store, and
seeding three turns of real chat history would mean three real model calls. What the client
asked to see is not the wording of the history but whether the **trait scope reverts to the
full set on a follow-up**, and that is decided by `question is None`, which this drives for
real. HISTORY_MSGS is reported from `len(pipeline.messages) - 2`, so the synthetic history
exercises that arithmetic too.

Output goes to scripts/demo_logs/ rather than api_v2/logs/ so a demonstration run never
gets mixed into the real daily audit trail.
"""

import argparse
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, '..'))
sys.path.insert(0, SCRIPT_DIR)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(SCRIPT_DIR, '..', 'api_v2', '.env'), encoding='utf-8-sig')

DEMO_LOG_DIR = os.path.join(SCRIPT_DIR, 'demo_logs')

# Q5 匡列 CIA_16/17/18/19 and CIA_36; the client's log stopped at CIA_12 because
# run_packer_live.py's --traits defaults to 12. 36 covers the whole assessment.
ALL_CIA = 36

failures = []


def check(label, ok, detail=''):
    print(f"  [{'OK' if ok else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not ok:
        failures.append(label)


class _Rag:
    """Everything `try_packed_stream` asks of a RAGService, and nothing more.

    Deliberately not a real RAGService: that one builds an LLM client from the API key,
    and the whole point of this script is that no request can leave the machine even by
    accident. `packer_stream` / `packer_followup` are handed to PackedStream, which this
    script never iterates, so they are never called.
    """

    def __init__(self, history=None):
        self._history = history or []

    def load_history(self, session_id):
        return list(self._history)

    def packer_stream(self, messages):
        raise AssertionError('the model must not be called from demo_prompt_log.py')

    def packer_followup(self, messages, instruction):
        raise AssertionError('the model must not be called from demo_prompt_log.py')


def redirect_prompt_log():
    """Point the prompt logger at demo_logs/ and return the file it will write.

    The file is removed first. The handler appends, so a second run on the same day used
    to leave 10 entries behind and `five entries written` failed on a run that had in fact
    produced a correct log -- a check that only passes once a day is not a check.
    """
    from datetime import datetime
    from api_v2.utils.logger import get_prompt_logger
    logger = get_prompt_logger()
    for h in logger.handlers:
        h.base_dir = DEMO_LOG_DIR
        h.current_date = None      # force _get_file() to reopen under the new base_dir
        if h.file_output:
            h.file_output.close()
            h.file_output = None
    path = os.path.join(DEMO_LOG_DIR, datetime.now().strftime('%Y-%m-%d'), 'prompts.log')
    if os.path.exists(path):
        os.remove(path)
    return path


def turn(rag, session_id, module_id, query, reports, basics, note):
    from api_v2.services.packed_chat import try_packed_stream
    print(f'\n  -> {note}')
    stream = try_packed_stream(rag, module_id, query, 'quick' if module_id else 'free',
                               reports, basics, session_id)
    if stream is None:
        check(note, False, 'try_packed_stream returned None (would fall back to the legacy path)')
        return None
    # Not iterated on purpose: iterating is what calls the model. The payload is already
    # in prompts.log by now.
    audit = stream._pipeline.log.audit
    per = audit['respondents'][0]
    print(f'     question={audit.get("question_id")} type={audit.get("question_type")} '
          f'full={per["full_blocks"]} index={per["index_lines"]} '
          f'interactions={per["interaction_blocks"]}')
    return stream


def generate():
    from flask import Flask
    from api_v2.config.settings import Config
    from run_packer_live import build_trait_report

    app = Flask(__name__)
    app.config.from_object(Config)

    with app.app_context():
        path = redirect_prompt_log()
        report, chosen = build_trait_report('CIA', ALL_CIA, 'mixed')
        print(f'respondent traits: {len(report["traits"])} CIA '
              f'(bands {sorted(set(chosen.values()))})')

        # --- Case 1: the Q5 the client reviewed, with the whole assessment this time ---
        print('\n[Case 1] Q5 管理壓力 -- 匡列題／單人（客戶問題 1a + 1b + 3）')
        turn(_Rag(), 'DEMO-Q5', 'mgmt_pressure', '', {'C1': report},
             [{'candidate_id': 'C1', 'name': '王智弘'}], 'Q5 quick question')

        # --- Case 2: a two-person scoped question ---
        print('\n[Case 2] Q14 團隊互補 -- 匡列題／多人（客戶問題 1a + 1b）')
        turn(_Rag(), 'DEMO-Q14', 'team_complement', '',
             {'C1': report, 'C2': report},
             [{'candidate_id': 'C1', 'name': '王智弘'},
              {'candidate_id': 'C2', 'name': '李明翰'}], 'Q14 quick question')

        # --- Case 3: the log the client explicitly asked for ---
        # 快速提問 -> 追問 -> 再追問. The frontend clears currentModuleId in its finally
        # block (useChatLogic.js:1208), so every follow-up arrives with module_id=null,
        # which is what module_id=None models here. Whether the follow-up is topically
        # related is irrelevant by design: the scope reverts on *any* follow-up.
        print('\n[Case 3] 快速提問 -> 追問兩輪（客戶問題 2）')
        sid = 'DEMO-FOLLOWUP'
        reports, basics = {'C1': report}, [{'candidate_id': 'C1', 'name': '王智弘'}]
        turn(_Rag(), sid, 'mgmt_pressure', '', reports, basics,
             'turn 1 -- 快速提問 Q5（匡列特質）')

        h2 = [{'role': 'user', 'content': '（快速提問 Q5：他在高壓下的管理重點）'},
              {'role': 'assistant', 'content': '（第一輪回覆）'}]
        turn(_Rag(h2), sid, None, '他適合帶新人嗎？', reports, basics,
             'turn 2 -- 追問（相關）：他適合帶新人嗎？')

        h3 = h2 + [{'role': 'user', 'content': '他適合帶新人嗎？'},
                   {'role': 'assistant', 'content': '（第二輪回覆）'}]
        turn(_Rag(h3), sid, None, '他跟同事相處會有什麼摩擦？', reports, basics,
             'turn 3 -- 追問（不相關）：他跟同事相處會有什麼摩擦？')

    return path


# Records gained a leading `REQ:` field; `SESSION:` is still accepted so this can also be
# pointed at a log written before that landed.
ENTRY_PREFIXES = ('REQ: ', 'SESSION: ')


def split_entries(text):
    """prompts.log entries, keyed by the header line."""
    entries, cur = [], None
    for line in text.splitlines():
        if line.startswith(ENTRY_PREFIXES):
            cur = {'header': line, 'body': []}
            entries.append(cur)
        elif cur is not None:
            cur['body'].append(line)
    for e in entries:
        e['body'] = '\n'.join(e['body'])
    return entries


def header_field(header, key):
    m = re.search(rf'{key}: ([^|]+)', header)
    return m.group(1).strip() if m else None


# `HISTORY_MSGS: 4 (2 turns, cap=6 turns/12 msgs)` -- header_field() would hand back the
# whole string including the parenthetical, so the count gets its own parser.
HISTORY_RE = re.compile(r'HISTORY_MSGS: (\d+) \((\d+) turns, cap=(\d+) turns/(\d+) msgs\)')


def verify(path):
    print(f'\n{"=" * 70}\n驗收：逐項對照客戶 2026-08-10 的三點質問\n{"=" * 70}')
    if not os.path.exists(path):
        check('prompts.log written', False, path)
        return
    text = open(path, encoding='utf-8').read()
    entries = split_entries(text)
    print(f'file: {path}')
    print(f'entries: {len(entries)}')
    check('five entries written', len(entries) == 5, len(entries))

    # -- 1a: 交互作用 ------------------------------------------------------------
    print('\n[1a] 交互作用區塊')
    for e in entries:
        mod = header_field(e['header'], 'MODULE')
        subs = re.findall(r'^#### 交互作用——(.+)$', e['body'], re.M)
        check(f'{mod}: 交互作用 sub-block present', bool(subs), subs or '(none)')

    # -- 1b: 四行特質塊 -----------------------------------------------------------
    print('\n[1b] 判讀主體特質每塊四行（行為面向／管理重點／可用於／禁止）')
    for e in entries:
        mod = header_field(e['header'], 'MODULE')
        heads = len(re.findall(r'^\[特質 \| ', e['body'], re.M))
        do = len(re.findall(r'^可用於：', e['body'], re.M))
        dont = len(re.findall(r'^禁止：', e['body'], re.M))
        check(f'{mod}: 可用於／禁止 count matches full blocks',
              heads > 0 and heads == do == dont,
              f'blocks={heads} 可用於={do} 禁止={dont}')

    # -- 2: 自由提問／追問 --------------------------------------------------------
    print('\n[2] 快速提問 -> 追問兩輪：特質範圍是否切回全量')
    followup = [e for e in entries if 'DEMO-FOLLOWUP' in e['header']]
    check('three turns recorded for one session', len(followup) == 3, len(followup))
    if len(followup) == 3:
        t1, t2, t3 = followup
        check('turn 1 is the scoped quick question',
              header_field(t1['header'], 'TYPE') == 'scoped'
              and '#### 判讀主體特質' in t1['body']
              and '#### 其他特質索引' in t1['body'],
              f"TYPE={header_field(t1['header'], 'TYPE')}, 有索引區")
        for n, t in (('turn 2', t2), ('turn 3', t3)):
            whole = '#### 判讀主體特質（全人型＝全部特質）' in t['body']
            no_index = '#### 其他特質索引' not in t['body']
            check(f'{n} reverted to every trait (全人型, 無索引區)', whole and no_index,
                  f'MODULE={header_field(t["header"], "MODULE")} '
                  f'QUESTION={header_field(t["header"], "QUESTION")}')
        parsed = [HISTORY_RE.search(t['header']) for t in followup]
        check('every header states msgs, turns and cap', all(parsed),
              [t['header'].split('| HISTORY')[-1] for t in followup])
        if all(parsed):
            msgs = [m.group(1) for m in parsed]
            check('HISTORY_MSGS grows with the conversation', msgs == ['0', '2', '4'], msgs)
            # 這兩條擋的是改名時最容易留下的殘骸：數字對、換算錯。
            check('turns is half the message count',
                  all(int(m.group(2)) == int(m.group(1)) // 2 for m in parsed),
                  [(m.group(1), m.group(2)) for m in parsed])
            check('cap msgs is twice cap turns',
                  all(int(m.group(4)) == int(m.group(3)) * 2 for m in parsed),
                  [(m.group(3), m.group(4)) for m in parsed])

    # -- 3: 特質涵蓋 --------------------------------------------------------------
    print('\n[3] 特質涵蓋（客戶指出 CIA_16/17/18/19 與 CIA_36 沒出現）')
    q5 = next((e for e in entries if 'DEMO-Q5' in e['header']), None)
    if q5:
        want = ['CIA_16', 'CIA_17', 'CIA_18', 'CIA_19', 'CIA_36']
        missing = [t for t in want
                   if not re.search(rf'^\[特質 \| {t}_', q5['body'], re.M)]
        check('Q5 匡列的 CIA_16/17/18/19 與 CIA_36 都是完整特質塊',
              not missing, f'missing={missing}' if missing else 'all present')
        ids = sorted(set(re.findall(r'^\[特質 \| (CIA_\d+)_', q5['body'], re.M))
                     | set(re.findall(r'^- (CIA_\d+)_', q5['body'], re.M)))
        check('Q5 涵蓋整份 CIA（36 個特質，非前 12 個）', len(ids) == ALL_CIA, len(ids))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='verify the most recent demo_logs file without regenerating it')
    args = ap.parse_args()

    if args.check:
        from datetime import datetime
        path = os.path.join(DEMO_LOG_DIR, datetime.now().strftime('%Y-%m-%d'), 'prompts.log')
    else:
        path = generate()
    verify(path)

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

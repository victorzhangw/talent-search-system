"""Export the conversation log from one environment (default PRD) with the personal
data removed, as a single timestamped Markdown document.

Usage:
    python scripts/export_deidentified_chat_log.py                    # PRD -> docs/customer/
    python scripts/export_deidentified_chat_log.py --db uat
    python scripts/export_deidentified_chat_log.py --skip-empty       # drop 0-message sessions
    python scripts/export_deidentified_chat_log.py --emit-key         # also write the re-id key

What counts as personal data here
---------------------------------
Not emails or phone numbers -- a scan of chat_messages found zero of either. The
identifying content in this product is the **names of the people being assessed**.
They are recorded per session in chat_sessions.metadata.candidates[].name, and then
appear all through the message bodies and the generated titles.

So the substitution is driven by that candidates list, expanded to the variants the
model actually writes:

    劉凱琳老師  ->  the honorific stripped (劉凱琳) and the given name alone (凱琳)
    許　檸      ->  the ideographic space removed (許檸) and as an ASCII space
    GT Liu      ->  matched whole-word, case-insensitively

Every person gets one pseudonym for the whole corpus (對象01, 對象02, ...), assigned in
order of first appearance, so "the same person was assessed three times" survives the
scrub while the identity does not. Accounts become 帳號A.., session UUIDs become S001...

Longest variant wins: 劉凱琳老師 is replaced before 劉凱琳, which is replaced before 凱琳,
so a replacement can never chop a longer name in half.

Verification
------------
After the document is built it is scanned for every original name, variant, account
address and session UUID. A single hit fails the run and nothing is written. A second,
advisory scan reports leftovers that look like names but were not in any candidates
list -- that one prints a warning rather than failing, because it cannot tell a missed
person from an ordinary word.

Read-only: the connection is opened readonly.
"""

import argparse
import json
import os
import re
import sys
from collections import OrderedDict
from datetime import datetime, timedelta
from difflib import SequenceMatcher

sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from purge_user_chat_history import DBS, connect, load_env

REPO_ROOT = os.path.join(SCRIPT_DIR, '..', '..')
BACKUP_DIR = os.path.join(SCRIPT_DIR, 'backups')
TW_OFFSET = timedelta(hours=8)

HONORIFICS = ['老師', '先生', '小姐', '女士', '教授', '醫師', '律師', '同學', '學長',
              '學姊', '學姐', '經理', '總監', '主管', '執行長', '董事長', '協理', '副理']

# People the metadata never recorded. metadata.candidates is not the whole story: in
# these sessions the user typed the group's names straight into the prompt and only one
# of them (or none) reached the candidates list, so the model then wrote the rest out in
# full. Each was confirmed by reading its context -- all appear in "#### **<name>**"
# section headings addressed to that person -- and each is confined to a single session,
# which is what a real name looks like here and a vocabulary word does not.
#
# They are data subjects like any other, so they get pseudonyms rather than a mask.
# Populating this list is the manual half of the job: run the export, read the advisory
# scans it prints, confirm each hit in context, then add it here and re-run.
EXTRA_SUBJECT_NAMES = [
    '楊凱婷', '賴秋婷', '洪秀琴',            # S114
    '張天心', '何佳玲', '劉于緁',            # S117
    '李聖亞', '李家嬅',                      # S118
    '周旻圯', '盧育寬', '黃子生',            # S119
    '王靖綸',                                # S120
    '蔡承妤',                                # S123
]

# Name-shaped tokens that cannot be attributed to anyone. 'Tim' sits in a person slot in
# S097 ("最大的潛在風險來自於 **Tim** 的 **被動**") among five candidates who are already
# pseudonymised, so it is very likely one of them under an English name -- but guessing
# which would invent a link that is not in the data, and minting a new pseudonym would
# imply a sixth person. Masked instead.
MASKED_NAMES = ['Tim']

# Cited authors of published leadership frameworks (Hersey & Blanchard, Marshall
# Goldsmith, John C. Maxwell, Simon Sinek, Sharon Melnick). They are references in the
# model's answers, not people being assessed, so they stay -- listed here so the advisory
# scan's output can be read without re-deciding this every run.
KNOWN_PUBLIC_AUTHORS = {'Hersey', 'Blanchard', 'Goldsmith', 'Maxwell', 'Sinek',
                        'Melnick', 'Sharon', 'John', 'Covey', 'Drucker', 'Kotter'}

MASK = '[已移除:姓名]'

ROLE_LABEL = {'user': '使用者', 'assistant': 'AI 回覆', 'system': '系統'}
LOG_ROLE = {'user': 'USER', 'assistant': 'ASSISTANT', 'system': 'SYSTEM'}

CJK = re.compile(r'[一-鿿]')
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
TW_MOBILE_RE = re.compile(r'(?<!\d)09\d{2}[-\s]?\d{3}[-\s]?\d{3}(?!\d)')
TW_ID_RE = re.compile(r'(?<![A-Za-z0-9])[A-Z][12]\d{8}(?![A-Za-z0-9])')
UUID_RE = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I)

failures = []


def check(label, ok, detail=''):
    print(f"  [{'OK' if ok else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not ok:
        failures.append(label)


def q(cur, sql, args=None):
    cur.execute(sql, args) if args else cur.execute(sql)
    return cur.fetchall()


def tw(dt):
    return dt + TW_OFFSET if dt else None


def parse_meta(md):
    if isinstance(md, str):
        try:
            md = json.loads(md)
        except Exception:
            return {}
    return md if isinstance(md, dict) else {}


def latin_pattern(variant):
    r"""Whole-token match for a Latin name, as the model actually writes it.

    The lookarounds bound on ASCII alphanumerics rather than \b because Python's \w
    counts CJK as a word character: with \b, 與Ina的 would not match, while 'Ina'
    inside 'China' would -- exactly backwards.

    Two tolerances, both taken from what the corpus contains:
      - a trailing possessive or plural 's', because 'Roger' is written 'Rogers';
      - a stray space between letters, because 'Victoria' is written 'Victor ia'.
        That one is allowed only from 5 letters up. At 3 letters it would make 'Ina'
        match the ordinary English phrase 'In a', which appears in this data.
    """
    words = [w for w in re.split(r'[\s　]+', variant) if w]
    letters = sum(len(w) for w in words)
    inner = r'\s?' if letters >= 5 else ''
    body = r'\s+'.join(inner.join(re.escape(c) for c in w) for w in words)
    return r'(?<![A-Za-z0-9])' + body + r"(?:['’]s|s)?(?![A-Za-z0-9])"


def name_variants(name):
    """[(variant, tier)] -- every spelling of `name` worth substituting.

    tier 0 is the name as recorded, tier 1 a form that is still plainly this person
    (honorific dropped, or one word of a multi-word Latin name), tier 2 a weaker
    fragment (a Chinese given name without its surname). The tier decides who wins
    when two people can lay claim to the same string.

    Splitting Latin names matters: the candidates list holds 'Evan Wale' and 'GT Liu',
    but the body text says 'Evan' and 'GT', so a whole-name-only rule leaves the real
    first name sitting in the document.
    """
    out = {}

    def add(v, tier):
        v = v.strip()
        if len(v) >= 2 and tier < out.get(v, 99):
            out[v] = tier

    collapsed = re.sub(r'[\s　]+', '', name)
    add(name, 0)
    add(collapsed, 0)
    add(re.sub(r'[\s　]+', ' ', name), 0)

    if CJK.search(name):
        cores = {collapsed}
        for h in HONORIFICS:
            for v in list(cores):
                if v.endswith(h) and len(v) > len(h):
                    cores.add(v[:-len(h)])
        for core in cores:
            add(core, 1)
            if len(core) >= 3:
                add(core[1:], 2)    # 陳嘉展 -> 嘉展
    else:
        for part in re.split(r'[\s　]+', name):
            if part.isalpha():
                add(part, 1)        # 'Evan Wale' -> 'Evan', 'Wale'

    return sorted(out.items(), key=lambda kv: len(kv[0]), reverse=True)


def build_name_map(sessions):
    """Pseudonym per person, numbered by first appearance over time.

    The reviewed extras are appended after everything metadata knew about, so adding
    one does not renumber the people already in the list and two runs of this script
    stay comparable.
    """
    people = OrderedDict()
    for s in sessions:
        for c in (parse_meta(s['metadata']).get('candidates') or []):
            n = (c or {}).get('name') if isinstance(c, dict) else None
            if n and n.strip() and n not in people:
                people[n] = f'對象{len(people) + 1:02d}'
    for n in EXTRA_SUBJECT_NAMES:
        if n not in people:
            people[n] = f'對象{len(people) + 1:02d}'
    return people


def build_rules(people):
    """(pattern_or_literal, replacement, is_regex) ordered so longer forms win.

    When two people claim the same string, whoever holds it at the stronger tier takes
    it: 'Eva' is person Eva's own name (tier 0) and merely one word of 'Eva H'
    (tier 1), so it goes to Eva. A tie at the same tier is genuinely ambiguous, and is
    dropped and reported rather than guessed at. Note that either outcome still
    removes the real name -- a tie costs attribution accuracy, never privacy.
    """
    owners = {}
    for name, pseudo in people.items():
        for variant, tier in name_variants(name):
            owners.setdefault(variant, []).append((tier, pseudo))

    rules, dropped = [], []
    for variant, claims in owners.items():
        best = min(t for t, _ in claims)
        winners = sorted({p for t, p in claims if t == best})
        if len(winners) > 1:
            dropped.append((variant, winners))
            continue
        pseudo = winners[0]
        if CJK.search(variant):
            rules.append((variant, pseudo, False))
        else:
            rules.append((re.compile(latin_pattern(variant), re.I), pseudo, True))

    for name in MASKED_NAMES:
        if CJK.search(name):
            rules.append((name, MASK, False))
        else:
            rules.append((re.compile(latin_pattern(name), re.I), MASK, True))

    # Longest first, so 劉凱琳老師 is consumed before 劉凱琳 and 凱琳.
    rules.sort(key=lambda r: len(r[0] if not r[2] else r[0].pattern), reverse=True)
    return rules, dropped


def build_prefix_map(people):
    """{prefix -> replacement} for names chopped off by a length cap.

    chat_messages stores the generated title as '[System] 產生標題: ...' truncated at 35
    characters, which slices the last name in the list mid-word: 'Stella' arrives as
    'Stel', 'Roger' as 'Ro', 'Lim' as 'Li'. Those fragments are still the start of a real
    name, so they are matched only where the truncation happens -- at the very end of a
    title -- and never mid-sentence, where 'Li' or 'Ro' would be ordinary text.

    A prefix that fits more than one person is masked instead of substituted.
    """
    owners = {}
    for name, pseudo in people.items():
        forms = {re.sub(r'[\s　]+', '', name)}
        forms.update(w for w in re.split(r'[\s　]+', name) if len(w) >= 3)
        for form in forms:
            for cut in range(2, len(form)):
                owners.setdefault(form[:cut], set()).add(pseudo)
    return {p: (next(iter(v)) if len(v) == 1 else MASK) for p, v in owners.items()}


def trim_truncated_name(text, prefixes):
    """Substitute a name fragment left dangling at the end of a truncated title."""
    if not text:
        return text
    for cut in range(min(len(text), 12), 1, -1):     # longest fragment first
        frag = text[-cut:]
        if frag not in prefixes:
            continue
        head = text[:-cut]
        # For a Latin fragment the character before it must not be a letter, or this
        # would be chopping the tail off a longer word rather than a truncated name.
        if not CJK.search(frag) and head and re.match(r'[A-Za-z0-9]', head[-1]):
            continue
        return head + prefixes[frag]
    return text


def scrub(text, rules, accounts, counts):
    if not text:
        return text

    # Addresses first: a name can be a substring of an email local part, and turning
    # the address into a token before name substitution keeps the two from colliding.
    def _email(m):
        counts['email'] = counts.get('email', 0) + 1
        return accounts.get(m.group(0).lower(), '[已移除:EMAIL]')
    text = EMAIL_RE.sub(_email, text)

    for pattern, pseudo, is_regex in rules:
        if is_regex:
            text, n = pattern.subn(pseudo, text)
        else:
            n = text.count(pattern)
            if n:
                text = text.replace(pattern, pseudo)
        if n:
            counts[pseudo] = counts.get(pseudo, 0) + n

    for label, rx in (('TWID', TW_ID_RE), ('PHONE', TW_MOBILE_RE)):
        text, n = rx.subn(f'[已移除:{label}]', text)
        if n:
            counts[label] = counts.get(label, 0) + n

    return text


def detect_misspellings(doc, people, threshold=0.85, min_len=4):
    """Latin tokens still in the document that are near-misses for a recorded name.

    The model mistypes the names it is given: 'Victoria' comes back as 'Victorica',
    'Stella' as 'Stell'. Those are still the person, but no exact rule matches them.

    A token is claimed only from `min_len` characters up. Below that, similarity stops
    discriminating -- 'Ina' and 'Ida' score 0.67 against each other and so would half
    the dictionary. Short leftovers are reported by the advisory census instead.
    """
    targets = {}
    for name, pseudo in people.items():
        if CJK.search(name):
            continue
        for variant, tier in name_variants(name):
            if tier <= 1 and len(variant) >= 3 and variant.isalpha():
                targets.setdefault(variant.lower(), pseudo)

    found = {}
    tokens = set(re.findall(r'(?<![A-Za-z0-9])[A-Z][a-z]{%d,15}(?![A-Za-z0-9])'
                            % (min_len - 1), doc))
    for tok in tokens:
        if tok in KNOWN_PUBLIC_AUTHORS or tok.lower() in targets:
            continue
        best = max(((SequenceMatcher(None, tok.lower(), t).ratio(), t, p)
                    for t, p in targets.items()), default=(0, '', ''))
        if best[0] >= threshold:
            found[tok] = (best[2], best[1], best[0])
    return found


def fetch(cur):
    sessions = [dict(zip(('session_id', 'user_id', 'started_at', 'last_active_at',
                          'status', 'metadata'), r))
                for r in q(cur, """SELECT session_id, user_id, started_at, last_active_at,
                                          status, metadata
                                   FROM chat_sessions ORDER BY started_at, session_id""")]
    messages = {}
    for sid, role, content, created, tok in q(cur, """
            SELECT session_id, role, content, created_at, token_usage
            FROM chat_messages ORDER BY session_id, created_at, id"""):
        messages.setdefault(sid, []).append(
            {'role': role, 'content': content, 'created_at': created, 'tokens': tok or 0})
    return sessions, messages


def blockquote(text):
    """Quote the body so its own '#' headings cannot hijack this document's outline."""
    return '\n'.join('> ' + line if line.strip() else '>' for line in text.split('\n'))


def iter_sessions(sessions, messages, people, rules, accounts, prefixes, skip_empty,
                  counts):
    """Yield each session with every field already de-identified.

    Both writers below consume this, so the log file and the Markdown document cannot
    drift apart on what they redact -- they differ only in how they lay the records out.
    """
    for idx, s in enumerate(sessions, start=1):
        msgs = messages.get(s['session_id'], [])
        if skip_empty and not msgs:
            continue

        meta = parse_meta(s['metadata'])
        title = trim_truncated_name(
            scrub(meta.get('title') or '', rules, accounts, counts), prefixes
        ) or '（未產生標題）'
        cands = [c.get('name') for c in (meta.get('candidates') or [])
                 if isinstance(c, dict) and c.get('name')]

        records = []
        for m in msgs:
            body = scrub(m['content'], rules, accounts, counts)
            # The title-generation trace carries the same 35-character truncation as the
            # title itself, so it can end on half a name too.
            if m['content'].startswith('[System] 產生標題'):
                body = trim_truncated_name(body, prefixes)
            records.append({'ts': tw(m['created_at']), 'role': m['role'],
                            'tokens': m['tokens'], 'body': body})

        yield {
            'code': f'S{idx:03d}',
            'account': accounts.get((s['user_id'] or '').lower(), '(no-account)'),
            'started': tw(s['started_at']),
            'last': tw(s['last_active_at']),
            'title': ' '.join(title.split()),
            'subjects': [people[n] for n in cands if n in people],
            'messages': records,
        }


def build_log(sessions, messages, people, rules, accounts, prefixes, db_label, dbname,
              skip_empty, counts):
    """Plain log file: records only, no prose and no markup.

    Every record opens at column 0 with 'YYYY-MM-DD HH:MM:SS [Snnn] [帳號X] [ROLE]', so
    grepping a date, a session or a role returns whole records. The body is indented four
    spaces underneath rather than folded onto the header line: an assistant answer runs to
    13,000 characters here, and flattening that onto one line makes the file unreadable.
    A continuation line is therefore any line that does not begin with a digit.
    """
    L = []
    for s in iter_sessions(sessions, messages, people, rules, accounts, prefixes,
                           skip_empty, counts):
        stamp = f'[{s["code"]}] [{s["account"]}]'
        fields = [f'title={s["title"]}',
                  f'subjects={",".join(s["subjects"]) if s["subjects"] else "-"}',
                  f'messages={len(s["messages"])}']
        if s['last']:
            fields.append(f'last_active={s["last"]:%Y-%m-%d %H:%M:%S}')
        L.append(f'{s["started"]:%Y-%m-%d %H:%M:%S} {stamp} [SESSION] ' + ' '.join(fields))

        for m in s['messages']:
            role = LOG_ROLE.get(m['role'], m['role'].upper())
            tok = f' tokens={m["tokens"]}' if m['tokens'] else ''
            L.append(f'{m["ts"]:%Y-%m-%d %H:%M:%S} {stamp} [{role}]{tok}')
            for line in m['body'].split('\n'):
                L.append('    ' + line if line.strip() else '')
    return '\n'.join(L) + '\n'


def build_document(sessions, messages, people, rules, accounts, prefixes, db_label,
                   dbname, skip_empty, counts):
    total_msgs = sum(len(v) for v in messages.values())
    kept = [s for s in sessions if messages.get(s['session_id']) or not skip_empty]
    spans = [tw(s['started_at']) for s in sessions if s['started_at']]

    L = []
    L.append(f'# {db_label} 對話 LOG（去識別化）')
    L.append('')
    L.append(f'- 產出時間：{datetime.now():%Y-%m-%d %H:%M:%S}')
    L.append(f'- 資料來源：PostgreSQL `{dbname}` 的 `chat_sessions` / `chat_messages`（唯讀查詢）')
    L.append(f'- 涵蓋期間：{min(spans):%Y-%m-%d} ~ {max(spans):%Y-%m-%d}（台灣時間 UTC+8）')
    L.append(f'- 內容量：{len(sessions)} 個 session、{total_msgs} 則訊息、'
             f'{len(people)} 位受評對象、{len(accounts)} 個使用帳號')
    if skip_empty:
        L.append(f'- 已略過 {len(sessions) - len(kept)} 個沒有任何訊息的 session')
    L.append('')
    L.append('## 去識別化說明')
    L.append('')
    L.append('本文件已移除下列個人資料，未經處理的原始資料僅存在於資料庫中：')
    L.append('')
    L.append('| 原始欄位 | 本文件的呈現方式 |')
    L.append('|---|---|')
    L.append('| 受評對象姓名（`metadata.candidates[].name`，以及該姓名在內文中的各種寫法：'
             '去掉稱謂、只稱名不稱姓、模型打錯字或多打空格） | `對象01`、`對象02` … |')
    L.append(f'| 使用者直接打在提示詞裡、未經 `metadata` 記錄的姓名（共 {len(EXTRA_SUBJECT_NAMES)} 位，'
             '以人工複核逐一確認後納入） | 同樣給予 `對象NN` 代號 |')
    L.append('| 無法對應到特定對象的人名 | `[已移除:姓名]` |')
    L.append('| 使用者帳號 email（`chat_sessions.user_id`） | `帳號A`、`帳號B` … |')
    L.append('| Session UUID（`chat_sessions.session_id`） | `S001`、`S002` … |')
    L.append('| 內文中的 email／手機／身分證字號 | `[已移除:EMAIL]`、`[已移除:PHONE]`、`[已移除:TWID]` |')
    L.append('')
    L.append('未被代換的英文人名為公開出版的管理學作者（Hersey、Blanchard、Goldsmith、Maxwell、'
             'Sinek、Melnick 等），屬模型引用的文獻來源，非受評對象。')
    L.append('')
    L.append('代號在整份文件中全域一致：同一位對象無論出現在哪個 session 都是同一個代號，'
             '因此「同一個人被重複評估」這件事仍看得出來，但代號無法回推到真實身分。'
             '代號與真實姓名的對照表**不包含在本文件內**。')
    L.append('')
    L.append('每則訊息的時間標籤為台灣時間（UTC+8）；資料庫存的是 naive UTC，輸出時已加 8 小時。')
    L.append('')
    L.append('---')
    L.append('')
    L.append('## 對話內容')
    L.append('')

    for s in iter_sessions(sessions, messages, people, rules, accounts, prefixes,
                           skip_empty, counts):
        L.append(f'### {s["code"]}　{s["started"]:%Y-%m-%d %H:%M:%S}　{s["account"]}')
        L.append('')
        L.append(f'- 標題：{s["title"]}')
        L.append(f'- 起訖：{s["started"]:%Y-%m-%d %H:%M:%S} ~ {s["last"]:%Y-%m-%d %H:%M:%S}'
                 if s['last'] else f'- 起訖：{s["started"]:%Y-%m-%d %H:%M:%S}')
        L.append(f'- 訊息則數：{len(s["messages"])}')
        L.append(f'- 受評對象：{"、".join(s["subjects"]) if s["subjects"] else "（未指定）"}')
        L.append('')
        if not s['messages']:
            L.append('> （此 session 沒有任何訊息紀錄）')
            L.append('')
            continue

        for m in s['messages']:
            label = ROLE_LABEL.get(m['role'], m['role'])
            tok = f'，{m["tokens"]:,} tokens' if m['tokens'] else ''
            L.append(f'**[{m["ts"]:%Y-%m-%d %H:%M:%S}] {label}**{tok}')
            L.append('')
            L.append(blockquote(m['body']))
            L.append('')
        L.append('---')
        L.append('')

    return '\n'.join(L)

def verify(doc, people, accounts, sessions):
    print('\n  verification (nothing is written unless every check passes):')

    # CJK is checked as a plain substring -- Chinese runs together, so any occurrence
    # at all is a hit. Latin is checked with the same token boundaries the substitution
    # used, otherwise 'Lim' would "fail" on the word 'Limited'.
    leaked = []
    for name in people:
        for v, _tier in name_variants(name):
            n = doc.count(v) if CJK.search(v) else len(re.findall(latin_pattern(v), doc, re.I))
            if n:
                leaked.append((name, v, n))
    check('no original name or name variant survives in the document', not leaked,
          '; '.join(f'{n!r} via {v!r} x{c}' for n, v, c in leaked[:8]))

    addr = [a for a in accounts if a in doc.lower()]
    check('no account address survives', not addr, addr[:5])

    uuids = UUID_RE.findall(doc)
    check('no session UUID survives', not uuids, uuids[:3])

    mails = EMAIL_RE.findall(doc)
    check('no email pattern anywhere in the document', not mails, mails[:5])
    check('no national-ID pattern', not TW_ID_RE.findall(doc))
    check('no mobile-number pattern', not TW_MOBILE_RE.findall(doc))

    # Advisory only, and it cannot fail the run: neither of these can tell a person the
    # candidates list never recorded from an ordinary word. They exist so a human can
    # eyeball what is left rather than trust the substitution blindly.
    suspects = {}
    for m in re.finditer(r'(?:擔任者|負責人|姓名|對象)\s*[:：]\s*([A-Za-z一-鿿]{2,4})', doc):
        tok = m.group(1)
        if not tok.startswith('對象'):
            suspects[tok] = suspects.get(tok, 0) + 1
    if suspects:
        print(f'  [WARN] {len(suspects)} token(s) sit in a name-like slot but were in no '
              f'candidates list -- review before release:')
        for tok, n in sorted(suspects.items(), key=lambda x: -x[1])[:15]:
            print(f'         {tok!r} x{n}')
    else:
        print('  [OK] advisory: no name-shaped leftovers in name-like slots')

    # A real name listed alongside pseudonyms -- '對象01、王小明' -- is the shape a missed
    # Chinese name takes here, and it is specific enough not to drown in false hits.
    beside = {}
    for m in re.finditer(r'對象\d\d\s*[、,，和與及]\s*([一-鿿]{2,3})(?![一-鿿\d])', doc):
        if m.group(1) != '對象':      # a pseudonym listed after a pseudonym
            beside[m.group(1)] = beside.get(m.group(1), 0) + 1
    if beside:
        print(f'  [WARN] {len(beside)} Chinese token(s) appear in a list next to a '
              f'pseudonym -- review before release:')
        for tok, n in sorted(beside.items(), key=lambda x: -x[1])[:15]:
            print(f'         {tok!r} x{n}')
    else:
        print('  [OK] advisory: no Chinese name-shaped tokens listed beside a pseudonym')

    # The document is overwhelmingly Chinese, so the capitalised Latin tokens in it are
    # few enough to read through -- and a missed Western given name would show up here.
    latin = {}
    for tok in re.findall(r'(?<![A-Za-z0-9])[A-Z][a-z]{1,15}(?![A-Za-z0-9])', doc):
        latin[tok] = latin.get(tok, 0) + 1
    print(f'  [INFO] advisory: {len(latin)} distinct capitalised Latin tokens remain '
          f'(review for missed given names):')
    for tok, n in sorted(latin.items(), key=lambda x: (-x[1], x[0]))[:25]:
        print(f'         {tok!r} x{n}')

    return not failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', choices=sorted(DBS), default='prd')
    ap.add_argument('--out', default=None)
    ap.add_argument('--format', choices=('log', 'md'), default='log',
                    help="'log' (default) writes a plain record-per-line .log file; "
                         "'md' writes the annotated Markdown document")
    ap.add_argument('--skip-empty', action='store_true',
                    help='omit sessions that have no messages')
    ap.add_argument('--emit-key', action='store_true',
                    help='also write the pseudonym -> real name key to scripts/backups/ '
                         '(re-identifies the document; keep it out of any delivery)')
    args = ap.parse_args()

    dbname = DBS[args.db]
    label = args.db.upper()
    conn = connect(load_env(), dbname, readonly=True)
    try:
        sessions, messages = fetch(conn.cursor())
    finally:
        conn.close()

    if not sessions:
        print('[WARN] No sessions found; nothing written.')
        return 1

    people = build_name_map(sessions)
    rules, dropped = build_rules(people)
    accounts = OrderedDict()
    for s in sessions:
        uid = (s['user_id'] or '').lower()
        if uid and uid not in accounts:
            accounts[uid] = f'帳號{chr(ord("A") + len(accounts))}'

    print(f'{label} {dbname}')
    print(f'  sessions          : {len(sessions)}')
    print(f'  messages          : {sum(len(v) for v in messages.values())}')
    print(f'  people pseudonyms : {len(people)}')
    print(f'  account pseudonyms: {len(accounts)}')
    print(f'  substitution rules: {len(rules)}')
    if dropped:
        print(f'  [WARN] {len(dropped)} ambiguous variant(s) shared by more than one person, '
              f'left unsubstituted: ' + ', '.join(f'{v!r}->{p}' for v, p in dropped[:8]))

    counts = {}
    prefixes = build_prefix_map(people)
    builder = build_log if args.format == 'log' else build_document
    doc = builder(sessions, messages, people, rules, accounts, prefixes, label,
                         dbname, args.skip_empty, counts)

    # Second pass: whatever the exact rules could not match, because the model spelled
    # the name wrong. Rebuilding is cheaper than trying to patch the assembled text,
    # and keeps every substitution going through the same code path.
    misspelled = detect_misspellings(doc, people)
    if misspelled:
        print(f'\n  {len(misspelled)} misspelled name(s) found in the first pass, '
              f'substituting and rebuilding:')
        for tok, (pseudo, matched, score) in sorted(misspelled.items()):
            print(f'    {tok!r} -> {pseudo} (matches {matched!r}, similarity {score:.2f})')
            rules.insert(0, (re.compile(latin_pattern(tok), re.I), pseudo, True))
        rules.sort(key=lambda r: len(r[0] if not r[2] else r[0].pattern), reverse=True)
        counts = {}
        doc = builder(sessions, messages, people, rules, accounts, prefixes,
                             label, dbname, args.skip_empty, counts)

    replaced = sum(v for k, v in counts.items() if k.startswith('對象'))
    print(f'\n  name substitutions made: {replaced} across '
          f'{sum(1 for k in counts if k.startswith("對象"))} people')
    for k in ('email', 'PHONE', 'TWID'):
        if counts.get(k):
            print(f'  {k} redactions: {counts[k]}')

    if not verify(doc, people, accounts, sessions):
        print(f'\n  ABORTED -- {len(failures)} check(s) failed: {failures}')
        print('  No file was written.')
        return 1

    out = args.out or os.path.join(
        REPO_ROOT, 'docs', 'customer',
        f'{label}-對話LOG-去識別化-{datetime.now():%Y%m%d}.{args.format}')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(doc)
    print(f'\n[OK] Wrote {os.path.abspath(out)}  ({len(doc):,} chars)')

    if args.emit_key:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        key_path = os.path.join(
            BACKUP_DIR, f'deid-key-{args.db}-{datetime.now():%Y%m%d-%H%M%S}.json')
        with open(key_path, 'w', encoding='utf-8') as f:
            json.dump({'db': dbname, 'people': people, 'accounts': accounts},
                      f, ensure_ascii=False, indent=2)
        print(f'[OK] Wrote re-identification key {key_path}')
        print('     This file re-identifies the document. Do not ship it with the log.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

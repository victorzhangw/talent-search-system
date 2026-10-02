"""把 log_packer_audit.log 依題號整理成統計表：通過、缺段、漏人、改寫。

用法：
    python scripts/audit_question_stats.py                          # 今天
    python scripts/audit_question_stats.py --date 2026-10-02
    python scripts/audit_question_stats.py --from 2026-10-02 --to 2026-10-09
    python scripts/audit_question_stats.py --log-dir <UAT 拉回來的 logs 目錄>
    python scripts/audit_question_stats.py --csv out.csv            # 另存逐題明細
    python scripts/audit_question_stats.py --strict                 # 有問題或有題目沒測到就 exit 1

讀的是 `api_v2/logs/<日期>/log_packer_audit.log` 裡每筆請求一行的 JSON 稽核紀錄。

四件容易算錯的事，這支都先處理掉：

  1. 驗收腳本的紀錄也寫在同一個檔。verify_* 用 S1、S_H 這類短 session、沒有 req_id；
     真實請求是 UUID session 加 req_id。預設只算真實請求（--include-test 才納入），
     否則 Q5 那種「一半都缺段」的數字其實是測試雜訊。
  2. 題號在 v10（2026-10-02）整批重編。沒有 question_table_version 的紀錄一律視為 v9，
     題名欄標出它對應的 v10 題號（依題庫 source_idx_0917），但不和 v10 混算。
  3. `leakage_hits` 只記「改寫後仍殘留」的命中；第一次掃描觸發改寫的字詞在
     segments[].hits。前者列為「殘留」欄，後者彙整成「觸發改寫的字詞」——只看前者的話，
     改寫成功的那些（大多數）會完全看不到。
  4. 自由提問沒有題號，單獨一列。

輸出不用 emoji（Windows cp950 主控台會 UnicodeEncodeError，見 CLAUDE.md）。
"""

import argparse
import collections
import csv
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, BACKEND)

DEFAULT_LOG_DIR = os.path.join(BACKEND, 'api_v2', 'logs')
LOG_NAME = 'log_packer_audit.log'
UUID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
AUDIENCE_LABEL = {'single': '單人', 'multi': '多人'}
COLUMNS = [('版本', 14, False), ('題', 4, True), ('題名', 26, False), ('人數', 5, False),
           ('筆數', 5, True), ('通過', 5, True), ('缺段', 5, True), ('略過', 5, True),
           ('漏人', 5, True), ('待人工', 7, True), ('改寫', 5, True), ('殘留', 5, True)]


def pad(text, width, right=False):
    """以終端機顯示寬度補空白：中文字佔兩格，str.ljust 把它當一格而對不齊。"""
    out, used = '', 0
    for ch in str(text):
        w = 2 if unicodedata.east_asian_width(ch) in ('W', 'F') else 1
        if used + w > width:
            break
        out, used = out + ch, used + w
    fill = ' ' * (width - used)
    return fill + out if right else out + fill


def row_text(values, suffix=''):
    return ' '.join(pad(v, w, r) for v, (_, w, r) in zip(values, COLUMNS)) + suffix


def load_table():
    """直接讀檔，不經 question_table 模組的單例，避免為了出報表載入整個服務設定。"""
    from api_v2.services.question_table import _CONFIG
    with open(os.path.abspath(_CONFIG), encoding='utf-8') as f:
        return json.load(f)


def is_real_request(rec):
    req = rec.get('req_id')
    return bool(req) and req != '-' and bool(UUID_RE.match(str(rec.get('session_id') or '')))


def iter_records(log_dir, days):
    for d in days:
        path = os.path.join(log_dir, d, LOG_NAME)
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8', errors='replace') as f:
            for line in f:
                i = line.find('{')
                if i < 0 or '"question_id"' not in line:
                    continue
                try:
                    yield json.loads(line[i:])
                except ValueError:
                    continue


def day_range(args):
    if args.date:
        return [args.date]
    if args.date_from or args.date_to:
        start = datetime.strptime(args.date_from or args.date_to, '%Y-%m-%d').date()
        end = datetime.strptime(args.date_to or args.date_from, '%Y-%m-%d').date()
        return [(start + timedelta(n)).isoformat() for n in range((end - start).days + 1)]
    return [date.today().isoformat()]


class Bucket:
    def __init__(self):
        self.n = 0
        self.status = collections.Counter()
        self.sections = collections.Counter()
        self.missing = collections.Counter()
        self.miss_resp = 0
        self.residual = 0
        self.rewrites = 0
        self.terms = collections.Counter()
        self.req_ids = []

    def add(self, rec):
        self.n += 1
        self.status[rec.get('status') or '-'] += 1
        self.sections[rec.get('expected_sections_check') or '-'] += 1
        self.missing.update(rec.get('missing_sections') or [])
        if rec.get('missing_respondents'):
            self.miss_resp += 1
        if rec.get('leakage_hits'):
            self.residual += 1
        for seg in rec.get('segments') or []:
            self.terms.update(seg.get('hits') or [])
        self.rewrites += int((rec.get('retry_count') or {}).get('leakage') or 0)
        if rec.get('req_id') and rec['req_id'] != '-':
            self.req_ids.append(rec['req_id'])

    @property
    def skipped(self):
        return self.sections.get('skipped', 0) + self.sections.get('data_gap', 0)

    def needs_check(self):
        return bool(self.sections.get('failed', 0) or self.miss_resp or self.residual)


def main():
    ap = argparse.ArgumentParser(description='依題號統計快速提問的稽核結果')
    ap.add_argument('--date', help='單日 YYYY-MM-DD（預設今天）')
    ap.add_argument('--from', dest='date_from', help='起日 YYYY-MM-DD')
    ap.add_argument('--to', dest='date_to', help='迄日 YYYY-MM-DD')
    ap.add_argument('--log-dir', default=DEFAULT_LOG_DIR)
    ap.add_argument('--include-test', action='store_true', help='納入驗收腳本產生的紀錄')
    ap.add_argument('--csv', help='另存逐題明細 CSV（UTF-8 BOM，Excel 可直接開）')
    ap.add_argument('--strict', action='store_true',
                    help='現行版本有缺段／漏人／殘留命中，或有題目×人數沒測到時 exit 1')
    args = ap.parse_args()

    table = load_table()
    version = table.get('version')
    titles = {q['idx']: q['title'] for q in table['questions']}
    v9_to_v10 = {q['source_idx_0917']: q['idx'] for q in table['questions']
                 if q.get('source_idx_0917')}

    days = day_range(args)
    buckets = collections.defaultdict(Bucket)
    free = Bucket()
    skipped_test = 0
    for rec in iter_records(args.log_dir, days):
        if not args.include_test and not is_real_request(rec):
            skipped_test += 1
            continue
        qid = rec.get('question_id')
        if qid is None:
            free.add(rec)
            continue
        ver = rec.get('question_table_version') or 'v9'
        buckets[(ver, qid, rec.get('audience') or '-')].add(rec)

    print(f'期間：{days[0]} ~ {days[-1]}　log：{os.path.abspath(args.log_dir)}')
    print(f'現行題庫：{version}　略過測試紀錄：{skipped_test} 筆'
          + ('（--include-test 已納入）' if args.include_test else ''))
    if not buckets and not free.n:
        print('\n這段期間沒有符合條件的紀錄。')
        return 1 if args.strict else 0

    print('\n' + row_text([c[0] for c in COLUMNS]))
    print('-' * (sum(w for _, w, _ in COLUMNS) + len(COLUMNS) - 1))
    rows = []
    order = sorted(buckets.items(),
                   key=lambda kv: (kv[0][0] != version, kv[0][0], kv[0][1], kv[0][2]))
    for (ver, qid, aud), b in order:
        if ver == version:
            name = titles.get(qid, '?')
        else:
            to = v9_to_v10.get(qid)
            name = f'=現Q{to} {titles.get(to, "")}' if to else '(v9 題號)'
        print(row_text([ver, qid, name, AUDIENCE_LABEL.get(aud, aud), b.n,
                        b.sections.get('passed', 0), b.sections.get('failed', 0), b.skipped,
                        b.miss_resp, b.status.get('manual_review', 0), b.rewrites, b.residual],
                       ' <- 需檢查' if b.needs_check() else ''))
        rows.append((ver, qid, name, aud, b))
    if free.n:
        print(row_text(['自由提問', '-', '', '', free.n, '', '', '', free.miss_resp,
                        free.status.get('manual_review', 0), free.rewrites, free.residual],
                       ' <- 需檢查' if free.miss_resp or free.residual else ''))

    print('\n[缺段明細]')
    shown = False
    for ver, qid, name, aud, b in rows:
        if b.missing:
            shown = True
            parts = '、'.join(f'{s}×{c}' for s, c in b.missing.most_common())
            more = ' …' if len(b.req_ids) > 5 else ''
            print(f'  {ver} Q{qid} {AUDIENCE_LABEL.get(aud, aud)}：{parts}')
            if b.req_ids:
                print(f'      req_id：{", ".join(b.req_ids[:5])}{more}')
    if not shown:
        print('  無')

    print('\n[觸發改寫的字詞]（第一次掃描命中、要求模型改寫；「殘留」欄是改寫後仍未消除的筆數）')
    terms = collections.Counter()
    for *_, b in rows:
        terms.update(b.terms)
    terms.update(free.terms)
    print('\n'.join(f'  {t}：{c}' for t, c in terms.most_common(15)) or '  無')

    seen = {(qid, aud) for (ver, qid, aud) in buckets if ver == version}
    untested = [f"Q{q['idx']}{AUDIENCE_LABEL[aud]}"
                for q in table['questions']
                for aud, ok in (('single', q['audience'] != 'multi_only'),
                                ('multi', q['audience'] != 'single_only'))
                if ok and (q['idx'], aud) not in seen]
    print(f'\n[{version} 尚未測到的題目×人數]（共 {len(untested)} 組）')
    print('  ' + ('、'.join(untested) if untested else '全部都有'))

    if args.csv:
        with open(args.csv, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(['版本', '題號', '題名', '人數', '筆數', '通過', '缺段', '略過', '漏人',
                        '待人工', '改寫次數', '殘留命中', '缺漏段落', '觸發字詞', 'req_id'])
            for ver, qid, name, aud, b in rows:
                w.writerow([ver, qid, name, AUDIENCE_LABEL.get(aud, aud), b.n,
                            b.sections.get('passed', 0), b.sections.get('failed', 0), b.skipped,
                            b.miss_resp, b.status.get('manual_review', 0), b.rewrites, b.residual,
                            '、'.join(f'{s}×{c}' for s, c in b.missing.most_common()),
                            '、'.join(f'{t}×{c}' for t, c in b.terms.most_common()),
                            ' '.join(b.req_ids)])
        print(f'\n[OK] 明細已寫出：{os.path.abspath(args.csv)}')

    if args.strict:
        current_bad = any(b.needs_check() for ver, _, _, _, b in rows if ver == version)
        return 1 if current_bad or untested else 0
    return 0


if __name__ == '__main__':
    sys.exit(main())

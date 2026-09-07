"""從 prompts.log 抽出自由提問語料，供「使用者這輪只問了誰」的判定做離線比對。

用法：
    python scripts/extract_focus_corpus.py                 # 掃所有日期
    python scripts/extract_focus_corpus.py --date 2026-09-05
    python scripts/extract_focus_corpus.py --out D:/tmp/corpus.tsv

背景（E-12）：覆蓋率檢查假設「每一則自由提問都是在問整個名單」。使用者一旦點名
「請只針對 X 說明」，模型正確地只寫 X，檢查卻判定漏了其他人。E-12 已經把「漏人」
降級成只記錄，所以現在不會再硬接內容；但要恢復自動補生成，得先讓檢查看懂
「這輪只問了誰」。

在寫那個判定之前，先把真實語料抽出來——0818／0901／0905／0906／0907 的自由提問
都在 `prompts.log` 裡，payload 本身就帶著 `[本輪判讀對象]`（當時的名單）與
`[任務指令]`（使用者原句）。有了這份表才談得上量準確率，否則只能兩個演算法互相
驗證，而那證明不了誰對。

判定用的是**生產版那一支**（`api_v2/services/focus_detect.py`），不是這裡另寫一份——
量的必須跟上線的是同一個東西，否則量出來的準確率不代表線上行為。

輸出同時給「演算法判定」與空白的「人工判定」兩欄。先看到演算法答案會有錨定效應，
所以標註時建議先把演算法那幾欄遮起來，或先標完再比對。

輸出到 `api_v2/logs/<今天>/focus_corpus.tsv`（`logs/` 在 .gitignore 裡，語料含真實
姓名，不進版控）。
"""

import argparse
import io
import os
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from api_v2.services.focus_detect import detect_focus, names_in  # noqa: E402

LOGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api_v2', 'logs')

RECORD_SEP = '=' * 60
ROSTER_MARKER = '[本輪判讀對象]'
INSTRUCTION_MARKER = '[任務指令]'
RESPONDENT_HEADER_RE = re.compile(r'###\s*\[受測者\s*\|\s*([^|\]]+?)\s*\|')

_WS = re.compile(r'\s+')
_ORG_SUFFIX = re.compile(r'[-－]')
_CJK = re.compile(r'^[一-鿿]+$')

HEADER = ['日期', '時間', 'req', 'session', '第幾輪', '名單人數', '名單',
          '提問', '前一輪提問',
          '演算法判定_來源', '演算法判定_對象', '演算法判定_矛盾',
          '人工判定_對象', '演算法對嗎(Y/N)', '備註']


def verdict_of(query, roster, history):
    """生產版的判定。history 只需要 user 訊息，這裡用前幾輪的提問組出來。"""
    return detect_focus(query, roster, history=history)


def parse_records(text):
    """`prompts.log` 是以 60 個等號分隔的區塊，一筆請求佔連續兩個區塊（標頭、內文）。

    不去猜區塊邊界，直接以 `TIME:` 當錨點切，再在每一筆裡找兩個標記——標記是打包器
    自己寫的常數（`log_assembler.ROSTER_MARKER` / `INSTRUCTION_MARKER`），比正則穩。
    """
    for chunk in re.split(r'\nTIME: ', text)[1:]:
        head, _, body = chunk.partition('\n')
        if 'TYPE: free' not in chunk or INSTRUCTION_MARKER not in body:
            continue                     # 題庫題不在這份語料的範圍內
        query = body.split(INSTRUCTION_MARKER, 1)[1].split(RECORD_SEP, 1)[0].strip()

        # 名單有兩個來源，因為 `[本輪判讀對象]` 是 Unit 1（d30171a，2026-09-05）才加的：
        # 之後的記錄直接讀它；之前的記錄退回去讀受測者標頭
        # `### [受測者 | 姓名 | RESP_xx]`——那是 b §5 的格式，從第一版就在。
        # 兩者取到的是同一批人，所以兩個時期的語料可以混在一起量。
        roster = []
        if ROSTER_MARKER in body:
            roster_text = body.split(ROSTER_MARKER, 1)[1].split(INSTRUCTION_MARKER, 1)[0]
            m = re.search(r'共\s*(\d+)\s*位：(.+?)。', roster_text)
            if m:
                roster = [n.strip() for n in m.group(2).split('、') if n.strip()]
        if not roster:
            seen = []
            for name in RESPONDENT_HEADER_RE.findall(body):
                name = name.strip()
                if name and name not in seen:
                    seen.append(name)
            roster = seen
        if not roster:
            continue

        meta = {}
        for field in ('REQ', 'SESSION', 'HISTORY_MSGS'):
            mm = re.search(rf'{field}: ([^|\n]+)', chunk)
            meta[field] = mm.group(1).strip() if mm else ''
        yield {
            'time': head.strip(),
            'req': meta['REQ'],
            'session': meta['SESSION'],
            'history_msgs': meta['HISTORY_MSGS'],
            'count': len(roster),
            'roster': roster,
            'query': ' '.join(query.split()),
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', action='append', help='只抽指定日期，可重複')
    ap.add_argument('--out', help='輸出路徑（預設 logs/<今天>/focus_corpus.tsv）')
    args = ap.parse_args()

    days = args.date or sorted(d for d in os.listdir(LOGS)
                               if os.path.isdir(os.path.join(LOGS, d)))
    rows = []
    for day in days:
        path = os.path.join(LOGS, day, 'prompts.log')
        if not os.path.exists(path):
            continue
        text = io.open(path, encoding='utf-8', errors='replace').read()
        found = list(parse_records(text))
        for r in found:
            r['day'] = day
        rows.extend(found)
        print(f'  {day}: {len(found)} 筆自由提問')

    # 同一個 session 內排序，好標「追問繼承」——前一輪問了什麼是判斷「他」指誰的依據。
    rows.sort(key=lambda r: (r['session'], r['time']))
    seq, prev_q = {}, {}
    for r in rows:
        i = seq.get(r['session'], 0) + 1
        seq[r['session']] = i
        r['turn'] = i
        r['prev_query'] = prev_q.get(r['session'], '')
        prev_q[r['session']] = r['query']
    rows.sort(key=lambda r: (r['day'], r['time']))

    out = args.out or os.path.join(LOGS, str(date.today()), 'focus_corpus.tsv')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # 判定要看歷史，所以先把每個 session 之前的提問組成 user 訊息串。
    seen_q = {}
    for r in sorted(rows, key=lambda x: (x['session'], x['time'])):
        r['history'] = [{'role': 'user', 'content': q}
                        for q in seen_q.get(r['session'], [])]
        seen_q.setdefault(r['session'], []).append(r['query'])

    with io.open(out, 'w', encoding='utf-8-sig', newline='') as f:
        f.write('\t'.join(HEADER) + '\n')
        for r in rows:
            v = verdict_of(r['query'], r['roster'], r['history'])
            f.write('\t'.join([
                r['day'], r['time'].split()[-1], r['req'], r['session'][:8],
                str(r['turn']), str(r['count']), '、'.join(r['roster']),
                r['query'], r['prev_query'],
                v['source'], '、'.join(v['names']), 'Y' if v['conflict'] else '',
                '', '', '',
            ]) + '\n')

    by_source = {}
    for r in rows:
        v = verdict_of(r['query'], r['roster'], r['history'])
        by_source[v['source']] = by_source.get(v['source'], 0) + 1
    named = sum(1 for r in rows if names_in(r['query'], r['roster']))
    followups = sum(1 for r in rows if r['turn'] > 1)
    multi = sum(1 for r in rows if r['count'] > 1)
    print(f'\n  合計 {len(rows)} 筆自由提問')
    print(f'    多人名單            {multi} 筆（單人名單不需要判斷「問誰」）')
    print(f'    提問裡出現名單姓名  {named} 筆')
    print(f'    是追問（非第一輪）  {followups} 筆')
    print(f'    演算法判定分佈      {dict(sorted(by_source.items(), key=lambda kv: -kv[1]))}')
    print(f'\n  輸出：{os.path.abspath(out)}')
    print('  「人工判定_對象」與「演算法對嗎」兩欄留空，標註後才能算準確率。')
    print('  標註時建議先遮住演算法那三欄，避免錨定。')
    return 0


if __name__ == '__main__':
    sys.exit(main())

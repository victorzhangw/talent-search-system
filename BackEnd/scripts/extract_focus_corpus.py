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

**這支腳本不做判定**。`提問中出現的姓名` 只是一個透明的資料欄位（見 `strict_forms`），
不是「這輪要問誰」的答案；答案那一欄留空給人標。不先填是刻意的：先填會把標註的人
錨定在演算法的答案上，量出來的準確率就沒有意義了。

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

LOGS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api_v2', 'logs')

RECORD_SEP = '=' * 60
ROSTER_MARKER = '[本輪判讀對象]'
INSTRUCTION_MARKER = '[任務指令]'
RESPONDENT_HEADER_RE = re.compile(r'###\s*\[受測者\s*\|\s*([^|\]]+?)\s*\|')

_WS = re.compile(r'\s+')
_ORG_SUFFIX = re.compile(r'[-－]')
_CJK = re.compile(r'^[一-鿿]+$')

HEADER = ['日期', '時間', 'req', 'session', '第幾輪', '名單人數', '名單',
          '提問', '前一輪提問', '提問中出現的姓名', '實際要問誰（人工標註）', '備註']


def strict_forms(name):
    """比 `completeness_check.name_forms` 嚴格的姓名寫法。

    生產用的那一支刻意偏寬，因為它的用途是「回答裡有沒有寫到這個人」——判成沒寫到的
    代價（在完整回答尾巴硬接一段）比較大，所以寧可多命中。

    拿來掃**提問**時代價方向是反的：誤中一個名字就把範圍縮到錯的人身上，真正該被檢查
    的那位反而不再被檢查。所以這裡砍掉兩字的截斷形——`呂 佳珍教育訓練課` 會產生
    `呂佳珍`（保留，使用者真的會這樣打）與 `呂佳`（丟掉，會命中「呂佳玲」）。
    """
    raw = (name or '').strip()
    if not raw:
        return []
    forms = {raw}
    head = _ORG_SUFFIX.split(raw)[0].strip()
    forms.add(head)
    forms |= {_WS.sub('', f) for f in tuple(forms)}

    parts = head.split()
    if len(parts) >= 2:
        first, rest = parts[0], ''.join(parts[1:])
        if _CJK.match(first):
            # 只取「姓 + 名的前兩字」，不取前一字：三字以下的截斷形誤中率太高。
            if len(rest) >= 2:
                forms.add(first + rest[:2])
        elif len(first) >= 3:
            forms.add(first)
    return sorted({f for f in forms if len(f) >= 3}, key=len, reverse=True)


def names_in(query, roster):
    """名單裡有哪些人的姓名出現在提問中。純資料，不是判定。"""
    flat = _WS.sub('', query or '')
    out = []
    for name in roster:
        if any(_WS.sub('', f) in flat for f in strict_forms(name)):
            out.append(name)
    return out


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
    with io.open(out, 'w', encoding='utf-8-sig', newline='') as f:
        f.write('\t'.join(HEADER) + '\n')
        for r in rows:
            hit = names_in(r['query'], r['roster'])
            f.write('\t'.join([
                r['day'], r['time'].split()[-1], r['req'], r['session'][:8],
                str(r['turn']), str(r['count']), '、'.join(r['roster']),
                r['query'], r['prev_query'], '、'.join(hit), '', '',
            ]) + '\n')

    named = sum(1 for r in rows if names_in(r['query'], r['roster']))
    followups = sum(1 for r in rows if r['turn'] > 1)
    multi = sum(1 for r in rows if r['count'] > 1)
    print(f'\n  合計 {len(rows)} 筆自由提問')
    print(f'    多人名單            {multi} 筆（單人名單不需要判斷「問誰」）')
    print(f'    提問裡出現名單姓名  {named} 筆')
    print(f'    是追問（非第一輪）  {followups} 筆')
    print(f'\n  輸出：{os.path.abspath(out)}')
    print('  第 11 欄「實際要問誰」留空，請人工標註後才能算準確率。')
    return 0


if __name__ == '__main__':
    sys.exit(main())

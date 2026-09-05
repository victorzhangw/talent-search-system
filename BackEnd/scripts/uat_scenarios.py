"""在真實環境重跑使用者回報的四個症狀（劇本驅動）。

用法：
    python scripts/uat_scenarios.py --env prd          # 打 PRD（會扣真實額度）
    python scripts/uat_scenarios.py --env default      # 打 UAT
    python scripts/uat_scenarios.py --env prd --only S1

跑完用 `verify_uat_scenarios.py` 讀 log 判定通過與否。兩支分開是因為提問要花錢：
分析可以重跑幾十次，提問不行。

**這支會消耗受測帳號的真實額度**（每次提問呼叫一次 /v1/ai/usage/daily-settlement）。
劇本刻意設計成共用回答——S5 直接判 S1／S7 的產出，不另外提問——全部跑完 5 次提問。

它走的是和 widget 完全相同的 HTTP 路徑（登入 → 候選人 → reports/batch → /chat/ SSE），
所以後端看到的東西與真人操作一致。UI 專屬的劇本（跨頁鎖定、切換歷史對話）不在這裡，
那兩個只有瀏覽器驗得到。

每個劇本用自己的 session_id，log 因此可以精準 join，不必靠時間戳去猜。
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import date

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE = os.environ.get('WIDGET_BACKEND', 'http://localhost:5000')
EMAIL = os.environ.get('UAT_EMAIL', 'a080697@gmail.com')
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'api_v2', 'logs', str(date.today()))
MANIFEST = os.path.join(LOG_DIR, 'uat_scenarios_manifest.json')

# 0904 那批人。用同一批而不是隨便挑，是為了讓失敗可以和原始 log 逐筆對照。
CAST = {
    '620': '邱 佳玲-聯醫', '624': '陳 冠享-一站式服務', '658': '蘇 緯弘',
    '679': '呂 佳珍教育訓練課', '682': '柳 宇賸-人資發展課', '683': '沈 家賢',
    '692': '簡 玥瀅-高雄非專', '704': '游 璧碩', '705': 'Howard Hsu',
    '706': 'Bryce-test',
}

RANK_Q = ('請針對本次選取的人選，分析誰較適合擔任客服營運高階主管，並提供相對排序。'
          '請為每一位人選說明適配優勢與需要留意的風險。')


def post(path, body, token=None, timeout=60):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(BASE + path, json.dumps(body).encode(), headers)
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def get(path, token, timeout=90):
    req = urllib.request.Request(BASE + path, headers={'Authorization': f'Bearer {token}'})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def login(env):
    """widget 在每次提問前都會換一張新 token（有效期 2 分鐘），這裡照做。"""
    return post('/auth/login', {'email': EMAIL, 'env': env})['data']['token']


def load_cast(env):
    """把 CAST 的 candidate_id 對到 PRD 上的完整候選人物件。"""
    token = login(env)
    out, offset = {}, 0
    while offset < 600 and len(out) < len(CAST):
        rows = (get(f'/api/v2/candidates/?limit=100&offset={offset}', token).get('data') or [])
        if not rows:
            break
        for c in rows:
            cid = str(c.get('candidate_id'))
            if cid in CAST:
                out[cid] = c
        offset += 100
    missing = sorted(set(CAST) - set(out), key=int)
    if missing:
        raise SystemExit(f'這些候選人在 {env} 上找不到：{missing}')
    return out


def trait_reports_for(env, people):
    """和 widget 一樣：用 latest_assessment.assessment_id 去抓，再以 candidate_id 為 key。"""
    token = login(env)
    ids = [p['latest_assessment']['assessment_id'] for p in people]
    reports = post('/api/v2/reports/batch', {'assessment_ids': ids}, token,
                   timeout=120)['data']['reports']
    out = {}
    for r in reports:
        for p in people:
            if str(p['latest_assessment']['assessment_id']) == str(r['assessment_id']):
                out[str(p['candidate_id'])] = r
    return out


def info_for(people):
    return [{'candidate_id': p['candidate_id'], 'name': p.get('name'),
             'email': p.get('email', ''), 'latest_assessment': p.get('latest_assessment')}
            for p in people]


def ask(env, session_id, query, people, trait_reports, label, read_timeout=240):
    """送一次提問並把 SSE 收完。回傳這一輪的觀察結果。

    `trait_reports` 是分開傳的，因為有一個劇本要故意送「比名單多」的報告——那正是
    前端快取沒清乾淨的樣子，也是 Unit 3 要擋掉的東西。
    """
    token = login(env)
    body = {
        'query': query,
        'module_id': None,
        'candidate_ids': [p['candidate_id'] for p in people],
        'candidates_info': info_for(people),
        'trait_reports': trait_reports,
        'session_id': session_id,
        'user_id': EMAIL,
        'mode': 'auto',
    }
    req = urllib.request.Request(BASE + '/chat/', json.dumps(body).encode(),
                                 {'Content-Type': 'application/json',
                                  'Authorization': f'Bearer {token}'})
    started = time.time()
    answer, notices, errors = [], [], []
    # 逾時要接住並記成這一輪的結果，不能讓它殺掉整支腳本——不然前面已經花掉的額度
    # 連 manifest 都寫不出來，等於白花。實測 2026-09-05 就發生過一次串流中途停住。
    try:
        with urllib.request.urlopen(req, timeout=read_timeout) as resp:
            for raw in resp:
                line = raw.decode('utf-8', 'replace').strip()
                if not line.startswith('data: '):
                    continue
                try:
                    ev = json.loads(line[6:])
                except Exception:
                    continue
                kind = ev.get('type')
                if kind == 'token':
                    answer.append(ev.get('content') or '')
                elif kind == 'notice':
                    notices.append({'code': ev.get('code'), 'message': ev.get('message')})
                elif kind == 'error':
                    errors.append({'code': ev.get('code'), 'message': ev.get('message')})
    except urllib.error.HTTPError as e:
        errors.append({'code': f'HTTP_{e.code}',
                       'message': e.read().decode('utf-8', 'replace')[:400]})
    except Exception as e:
        # 串流中途斷掉時，已經收到的字仍然有分析價值（可以看出停在哪一段）。
        errors.append({'code': type(e).__name__, 'message': str(e)[:200],
                       'partial_chars': len(''.join(answer))})

    text = ''.join(answer)
    print(f'    [{label}] {len(people)} 位 / {len(trait_reports)} 份報告 -> '
          f'{len(text)} 字 / {time.time() - started:.0f}s'
          + (f' / notice={notices}' if notices else '')
          + (f' / error={errors}' if errors else ''))
    return {'label': label, 'session_id': session_id, 'query': query,
            'roster': [str(p['candidate_id']) for p in people],
            'roster_names': [p.get('name') for p in people],
            'trait_report_keys': sorted(trait_reports),
            'answer_chars': len(text), 'answer': text,
            'notices': notices, 'errors': errors}


# ---------------------------------------------------------------- 劇本 ------

def s1_roster_grows(env, cast, run):
    """S1 — 名單中途新增一位。重現 43c1f019：7 位加到 8 位，回答漏掉的正好是新增那位。

    驗的是 Unit 1（[本輪判讀對象] 壓不壓得過歷史）。
    """
    sid = f'uat-s1-{run}'
    seven = [cast[c] for c in ('620', '624', '679', '682', '692', '705', '706')]
    eight = seven + [cast['704']]
    r7 = trait_reports_for(env, seven)
    r8 = trait_reports_for(env, eight)
    return [ask(env, sid, RANK_Q, seven, r7, 'S1-turn1-7人'),
            ask(env, sid, '再一次排序。', eight, r8, 'S1-turn2-新增游璧碩')]


def s2_stale_cache(env, cast, run):
    """S2 — 名單縮小，但前端快取還留著被移除者的報告。驗 Unit 3。

    `trait_reports` 故意送 8 份、`candidate_ids` 只給 6 位——這就是前端漏清快取的樣子。
    後端必須以 candidate_ids 為準，稽核要說得出丟掉了誰。
    """
    sid = f'uat-s2-{run}'
    eight = [cast[c] for c in ('620', '624', '679', '682', '692', '704', '705', '706')]
    six = [p for p in eight if str(p['candidate_id']) not in ('705', '706')]
    stale = trait_reports_for(env, eight)          # 8 份（含已移除的 705 / 706）
    return [ask(env, sid, RANK_Q, six, stale, 'S2-移除705和706但快取還在')]


def s7_single_to_multi(env, cast, run):
    """S7 — 從 1 位變成 8 位。重現 4920eef8：回答宣稱「僅 Howard Hsu 一位有資料」。

    這是四個症狀裡最戲劇化的一筆，也是 Unit 1 最強的驗收標的。
    """
    sid = f'uat-s7-{run}'
    one = [cast['705']]
    eight = [cast[c] for c in ('620', '624', '658', '679', '682', '683', '692', '705')]
    r1 = trait_reports_for(env, one)
    r8 = trait_reports_for(env, eight)
    return [ask(env, sid, RANK_Q, one, r1, 'S7-turn1-只有Howard'),
            ask(env, sid, RANK_Q, eight, r8, 'S7-turn2-加到8位')]


SCENARIOS = {'S1': s1_roster_grows, 'S2': s2_stale_cache, 'S7': s7_single_to_multi}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--env', default='prd', choices=('prd', 'default'))
    ap.add_argument('--only', action='append', choices=sorted(SCENARIOS),
                    help='只跑指定劇本，可重複')
    args = ap.parse_args()

    names = args.only or sorted(SCENARIOS)
    print(f'環境：{args.env}   帳號：{EMAIL}   劇本：{names}')

    token = login(args.env)
    init = get('/api/v2/init/', token).get('data') or {}
    quota = init.get('quota_summary') or {}
    print(f'額度：{quota}')
    if quota.get('remaining', 0) < 10:
        raise SystemExit('剩餘額度不足 10，先不要跑。')

    cast = load_cast(args.env)
    print(f'候選人已對到 {len(cast)} 位\n')

    run = time.strftime('%H%M%S')
    turns = []
    for name in names:
        print(f'  {name}')
        turns.extend(SCENARIOS[name](args.env, cast, run))

    after = (get('/api/v2/init/', login(args.env)).get('data') or {}).get('quota_summary') or {}
    manifest = {'env': args.env, 'email': EMAIL, 'run': run,
                'started': time.strftime('%Y-%m-%d %H:%M:%S'),
                'quota_before': quota, 'quota_after': after,
                'cast': {k: v.get('name') for k, v in cast.items()},
                'turns': turns}
    # 累加而不是覆蓋：一次只重跑一個劇本是常態（提問要花錢），覆蓋會把前面跑過的
    # 結果洗掉，分析時就少了對照組。同一個 label 以最後一次為準。
    os.makedirs(LOG_DIR, exist_ok=True)
    if os.path.exists(MANIFEST):
        try:
            with open(MANIFEST, encoding='utf-8') as f:
                previous = json.load(f)
            kept = [t for t in previous.get('turns', [])
                    if t['label'] not in {x['label'] for x in turns}]
            manifest['turns'] = kept + manifest['turns']
            manifest['quota_before'] = previous.get('quota_before', quota)
        except Exception as e:
            print(f'  （讀不到舊 manifest，這次會蓋掉：{e}）')
    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(f'\n額度：{quota} -> {after}')
    print(f'manifest: {os.path.abspath(MANIFEST)}')
    print('接著跑：python scripts/verify_uat_scenarios.py')


if __name__ == '__main__':
    main()

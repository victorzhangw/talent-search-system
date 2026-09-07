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
import random
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


def load_any(env, count):
    """這個環境上任意 N 位有評測資料的候選人。

    CAST 是 0904 那批 PRD 的 id，重現劇本必須用它；但 S8 驗的是「問法」不是那批人，
    綁死 id 會讓它只能在 PRD 上跑，而 PRD 的每一次提問都花真實額度。
    """
    token = login(env)
    out, offset = [], 0
    while offset < 600 and len(out) < count:
        rows = (get(f'/api/v2/candidates/?limit=100&offset={offset}', token).get('data') or [])
        if not rows:
            break
        for c in rows:
            if (c.get('latest_assessment') or {}).get('assessment_id'):
                out.append(c)
                if len(out) >= count:
                    break
        offset += 100
    if len(out) < count:
        raise SystemExit(f'{env} 上有評測資料的候選人不足 {count} 位（只有 {len(out)}）')
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


def ask(env, session_id, query, people, trait_reports, label, read_timeout=240,
        focus=None):
    """送一次提問並把 SSE 收完。回傳這一輪的觀察結果。

    `trait_reports` 是分開傳的，因為有一個劇本要故意送「比名單多」的報告——那正是
    前端快取沒清乾淨的樣子，也是 Unit 3 要擋掉的東西。

    `focus` 是「這一輪只問這幾位」——使用者在自由提問裡點名某人時，回答本來就不該
    寫到名單上的每一位，判定要跟著換（見 verify_uat_scenarios.py）。名單宣告與打包
    範圍仍然是完整名單，那兩件事不因為點名而改變。
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
            'focus': list(focus or []),
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


def s8_focus_chain(env, cast, run):
    """S8 — 自由提問裡指定候選人，然後換人問、追問、中途加人比較。

    前面三個劇本問的都是同一句 `RANK_Q`（整批排序），驗的是「名單對不對」。但真實
    使用者不是這樣用的：他們會在多人名單裡點名某一位問，得到答案之後換另一位問，
    再不點名地追問下去。這條路徑有三件事只有這樣問才驗得到：

    1. **點名之後，名單宣告與打包範圍不能跟著縮小。** `[本輪判讀對象]` 仍應是完整
       名單——縮小的話，下一輪追問就沒有其他人的資料可用了。
    2. **換人問的時候，回答要真的換人。** 這是 Unit 1 的另一面：上一輪的主角就在
       歷史裡，模型很容易繼續寫他。
    3. **不點名的追問要接得住上下文。** 「他在壓力下如何」的「他」是上一輪那位，
       不是名單第一位、也不是全部。

    順帶：點名之後其餘的人本來就不會被寫到，所以這是目前唯一可能讓後端的覆蓋率
    檢查判定「漏人」的情境——A-2（補生成）至今沒有樣本，這裡有機會生出第一個。

    四輪共用一個 session，因為第 3 輪的「他」要靠歷史才解得出來。
    """
    sid = f'uat-s8-{run}'
    people = load_any(env, 6)
    five, sixth = people[:5], people[5]
    a, b = five[0].get('name'), five[3].get('name')
    c = sixth.get('name')
    r5 = trait_reports_for(env, five)
    r6 = trait_reports_for(env, five + [sixth])
    print(f'    S8 名單 5 位：{[p.get("name") for p in five]}；第 4 輪加入 {c}')

    return [
        ask(env, sid, f'請只針對 {a} 說明他的溝通風格，以及面談時需要留意的風險。',
            five, r5, 'S8-turn1-指定甲', focus=[a]),
        ask(env, sid, f'那 {b} 呢？同樣的角度說明。',
            five, r5, 'S8-turn2-換人問乙', focus=[b]),
        ask(env, sid, '他在壓力之下的表現如何？請再補充一點。',
            five, r5, 'S8-turn3-不點名追問乙', focus=[b]),
        ask(env, sid, f'請比較 {b} 與 {c} 在團隊合作上的差異。',
            five + [sixth], r6, 'S8-turn4-加人並比較乙丙', focus=[b, c]),
    ]



# --------------------------------------------------------------- S9 隨機劇本 ---
#
# 問法的樣板。每一種對應「使用者這輪在問誰」的一種形狀，`shape` 會寫進 manifest，
# 人工標註時可以直接看出這一輪原本想測什麼。
#
# 不用 LLM 生成提問：樣板可重現（給定 seed 就跑得出同一串），而且形狀分佈可控——
# 隨機生成的句子有九成會落在「泛稱」那一類，正好是我們已經有 92 筆的那一類。
TURN_SHAPES = (
    ('named_one',   '請只針對 {a} 說明他的溝通風格，以及面談時需要留意的風險。'),
    ('named_one',   '{a} 適合什麼樣的工作型態？'),
    ('switch',      '那 {b} 呢？同樣的角度說明。'),
    ('switch',      '換成 {b} 來看，會有什麼不同？'),
    ('followup',    '他在壓力之下的表現如何？請再補充一點。'),
    ('followup',    '那他在跨部門協作上呢？'),
    ('compare',     '請比較 {a} 與 {b} 在團隊合作上的差異。'),
    ('exclude',     '除了 {a} 之外，其他人呢？'),
    ('generic',     '這幾位個別適合什麼崗位？'),
    ('generic',     '他們之中誰比較適合帶團隊？'),
    ('whole',       '請針對本次選取的人選做一次相對排序，並說明各自的適配優勢。'),
)


def s9_random_chain(env, cast, run, seed=None, turns=5, size=None):
    """隨機挑名單、隨機挑問法，跑一串多輪對話。

    為什麼要有這支：E-12（點名式提問被補生成硬接上沒問的人）修好之後，要不要把
    「使用者這輪只問了誰」接進判定，取決於它判得準不準。而 0810-0907 的語料裡點名式
    提問是 0 筆——真實流量全是泛稱，量不出東西來。所以這裡刻意製造各種形狀的提問，
    連同稽核記錄一起產出，讓人可以逐筆核對演算法判得對不對。

    `--seed` 固定就能重跑出同一串對話，對照修改前後的判定。
    """
    rng = random.Random(seed)
    pool = load_any(env, 8)
    # 第 1 輪沒有前文，接續式的問法在那裡沒有意義：實測 S9-303-t1 的「換成 X 來看」
    # 被模型當成整批比較，回答寫了全名單——那一筆量不到任何東西。
    opening = [t for t in TURN_SHAPES if t[0] in ('named_one', 'generic', 'whole')]
    size = size or rng.randint(3, 5)
    people = pool[:size]
    spare = pool[size]                       # 留一位給「中途加人」
    reports = trait_reports_for(env, people)
    reports_plus = trait_reports_for(env, people + [spare])

    sid = f'uat-s9-{run}-{seed}'
    names = [p.get('name') for p in people]
    print(f'    S9 seed={seed} 名單 {len(people)} 位：{names}；備用 {spare.get("name")}')

    out, current, roster, cur_reports = [], list(people), list(names), reports
    last_named = None
    # 每串至少保證一次 followup：它是「繼承」路徑唯一的樣本來源，而隨機抽了 15 輪
    # 一次都沒中（11 選 1、每輪獨立）。位置放在點名之後的任一輪。
    forced_followup = rng.randint(2, turns) if turns >= 2 else None

    for i in range(turns):
        if i == 0:
            shape, template = rng.choice(opening)
        elif i + 1 == forced_followup and last_named:
            shape, template = rng.choice([t for t in TURN_SHAPES if t[0] == 'followup'])
        else:
            shape, template = rng.choice(TURN_SHAPES)
        # followup 要有上一輪的點名才有意義；沒有就換一個形狀，不然測不到繼承。
        if shape == 'followup' and not last_named:
            shape, template = TURN_SHAPES[0]
        a = rng.choice(roster)
        b = rng.choice([n for n in roster if n != a]) if len(roster) > 1 else a
        query = template.format(a=a, b=b)

        # 每一串隨機插入一次「中途加人」，重現名單變動那條路徑。
        if i == turns - 2 and spare.get('name') not in roster:
            current = current + [spare]
            roster = roster + [spare.get('name')]
            cur_reports = reports_plus

        focus_hint = []
        if shape in ('named_one',):
            focus_hint, last_named = [a], [a]
        elif shape == 'switch':
            focus_hint, last_named = [b], [b]
        elif shape == 'compare':
            focus_hint, last_named = [a, b], [a, b]
        elif shape == 'followup':
            focus_hint = list(last_named or [])

        turn = ask(env, sid, query, current, cur_reports,
                   f'S9-{seed}-t{i + 1}-{shape}', focus=focus_hint)
        turn['shape'] = shape
        out.append(turn)
    return out


SCENARIOS = {'S1': s1_roster_grows, 'S2': s2_stale_cache, 'S7': s7_single_to_multi,
             'S8': s8_focus_chain,
             'S9': s9_random_chain}

# 需要 0904 那批固定 id 的劇本。S8 自己動態選角，所以在 UAT 上也跑得起來。
NEEDS_FIXED_CAST = {'S1', 'S2', 'S7'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--env', default='prd', choices=('prd', 'default'))
    ap.add_argument('--only', action='append', choices=sorted(SCENARIOS),
                    help='只跑指定劇本，可重複')
    ap.add_argument('--runs', type=int, default=1, help='S9 要跑幾串（每串一個 seed）')
    ap.add_argument('--turns', type=int, default=5, help='S9 每串幾輪')
    ap.add_argument('--seed', type=int, action='append', help='S9 指定 seed，可重複')
    args = ap.parse_args()

    names = args.only or sorted(SCENARIOS)
    print(f'環境：{args.env}   帳號：{EMAIL}   劇本：{names}')

    token = login(args.env)
    init = get('/api/v2/init/', token).get('data') or {}
    quota = init.get('quota_summary') or {}
    print(f'額度：{quota}')
    planned = (args.runs * args.turns) if 'S9' in names else 0
    planned += sum(2 if n in ('S1', 'S7') else 1 for n in names if n != 'S9')
    if quota.get('remaining', 0) < max(10, planned + 5):
        raise SystemExit(f'剩餘額度不足（這一輪預計花 {planned} 次），先不要跑。')

    if set(names) & NEEDS_FIXED_CAST:
        cast = load_cast(args.env)
        print(f'候選人已對到 {len(cast)} 位\n')
    else:
        cast = {}
        print('（本輪劇本不需要 0904 那批固定 id，改為動態選角）\n')

    run = time.strftime('%H%M%S')
    turns = []
    for name in names:
        print(f'  {name}')
        if name == 'S9':
            seeds = args.seed or [random.randrange(10000) for _ in range(args.runs)]
            for seed in seeds:
                turns.extend(s9_random_chain(args.env, cast, run, seed=seed,
                                             turns=args.turns))
        else:
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

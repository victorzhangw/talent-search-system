"""判定 `uat_scenarios.py` 那一輪跑出來的東西有沒有問題。

用法：
    python scripts/verify_uat_scenarios.py
    python scripts/verify_uat_scenarios.py --date 2026-09-05

只讀 log，不打網路、不花額度，所以可以重跑到你滿意為止。判定的依據是三份 log 加上
driver 寫下的 manifest，用 session_id join：

    uat_scenarios_manifest.json   這一輪送了什麼（名單、快取內容、收到的回答）
    log_packer_audit.log          後端實際打包了誰、閘門判了什麼
    prompts.log                   送進模型的 payload 本體

每一條判定都對應到修正計畫（docs/0905_名單不同步與漏人_修正計畫.md）的一個單元，
失敗時印出對照用的原始欄位，不要只說 FAIL。
"""

import argparse
import json
import os
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api_v2.services.completeness_check import name_forms          # noqa: E402

LOGS = os.path.join(os.path.dirname(__file__), '..', 'api_v2', 'logs')

failures = []


def check(label, condition, detail=''):
    print(f"    [{'OK' if condition else 'FAIL'}] {label}"
          f"{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def flat(s):
    return re.sub(r'\s+', '', s or '')


def mentions(answer, name):
    """回答有沒有寫到這個人。用和覆蓋率檢查同一組姓名寫法——payload 存的是
    『柳 宇賸-人資發展課』，模型寫的是『柳宇賸』。"""
    a = flat(answer)
    return any(flat(f) in a for f in name_forms(name))


def load(day):
    root = os.path.join(LOGS, day)
    with open(os.path.join(root, 'uat_scenarios_manifest.json'), encoding='utf-8') as f:
        manifest = json.load(f)

    audits = {}
    path = os.path.join(root, 'log_packer_audit.log')
    if os.path.exists(path):
        for line in open(path, encoding='utf-8', errors='replace'):
            m = re.search(r'\| (\{.*\})\s*$', line)
            if not m:
                continue
            try:
                d = json.loads(m.group(1))
            except Exception:
                continue
            if 'respondents' in d and d.get('session_id'):
                audits.setdefault(d['session_id'], []).append(d)

    payloads = {}
    path = os.path.join(root, 'prompts.log')
    if os.path.exists(path):
        text = open(path, encoding='utf-8', errors='replace').read()
        for m in re.finditer(r'REQ: (\S+) \| SESSION: (\S+) \| USE_CASE: log_packer'
                             r'.*?(?=\nREQ: \S+ \| SESSION:|\Z)', text, re.S):
            payloads.setdefault(m.group(2), []).append(m.group(0))
    return manifest, audits, payloads


def audit_for(audits, turn, index):
    rows = audits.get(turn['session_id'], [])
    return rows[index] if index < len(rows) else None


def payload_for(payloads, turn, index):
    rows = payloads.get(turn['session_id'], [])
    return rows[index] if index < len(rows) else None


# --------------------------------------------------------------- 判定 ------

def judge_turn(turn, audit, payload, seq):
    """每一輪都要成立的事，與劇本無關。"""
    print(f'\n  [{turn["label"]}]  {len(turn["roster"])} 位 / 回答 {turn["answer_chars"]} 字')

    check('沒有串流錯誤', not turn['errors'], turn['errors'])
    check('有拿到回答', turn['answer_chars'] > 0)
    if audit is None:
        check('稽核記錄找得到', False, turn['session_id'])
        return
    if payload is None:
        check('prompts.log 記到這一輪', False, turn['session_id'])
        return

    # Unit 3：名單以 candidate_ids 為準
    roster = audit.get('roster') or {}
    packed = [str(r['respondent_id']) for r in audit.get('respondents', [])]
    check('打包的人就是這一輪指定的人（Unit 3）',
          sorted(packed) == sorted(turn['roster']),
          f'packed={sorted(packed)} vs roster={sorted(turn["roster"])}')
    stale = sorted(set(turn['trait_report_keys']) - set(turn['roster']))
    if stale:
        check('快取裡多出來的人被擋掉，且稽核說得出是誰（Unit 3）',
              sorted(roster.get('dropped') or []) == stale,
              f'dropped={roster.get("dropped")} 應為 {stale}')

    # Unit 1：自由提問要有名單宣告，且只列姓名
    body = payload.split('=' * 60, 1)[-1]
    if '[本輪判讀對象]' in body:
        declared = body.split('[本輪判讀對象]', 1)[1].split('[任務指令]', 1)[0]
        check('名單宣告的人數正確（Unit 1）',
              f'共 {len(turn["roster"])} 位' in declared,
              declared.strip().splitlines()[0] if declared.strip() else '(空)')
        check('名單宣告列出每一位（Unit 1）',
              all(n and flat(n) in flat(declared) for n in turn['roster_names']))
        check('名單宣告不含 RESP_xx（Unit 1）', not re.search(r'RESP_\d+', declared))
    else:
        check('自由提問帶了 [本輪判讀對象]（Unit 1）', False, '區塊不存在')

    # Unit 4a：不得整串截斷；已釋出的段落不得重複
    check('回覆沒有被閘門截斷（Unit 4a）', audit.get('status') != 'blocked',
          f'status={audit.get("status")} hits={audit.get("leakage_hits")}')
    grown = [a for s in audit.get('segments', []) for a in (s.get('rewrite_attempts') or [])
             if a.get('rejected') == 'overgrown']
    if grown:
        print(f'      註：擋下 {len(grown)} 次「改寫變成整段」'
              f'（{[f"{a['before_len']}->{a['after_len']}" for a in grown]}）')

    # Unit 2：多人回答的覆蓋率
    if len(turn['roster']) > 1:
        missed = [n for n in turn['roster_names'] if not mentions(turn['answer'], n)]
        check('回答寫到每一位（Unit 2）', not missed, missed)
        check('稽核的 missing_respondents 與實際一致（Unit 2）',
              sorted(audit.get('missing_respondents') or []) == sorted(
                  [n for n in turn['roster_names'] if n in missed]),
              f'audit={audit.get("missing_respondents")} 實際漏={missed}')

    # Unit 4a：已釋出的內容不得重複。這是「標題被改寫成整段」的病徵——改寫器補出來的
    # 整段被釋出，接著模型自己原本要寫的內容也串流進來，讀者看到同一段兩次。
    # 逐字比對 30 字以上的句子：正常寫作不會一字不差地重複那麼長。
    sentences = [x for x in re.split(r'(?<=[。！？])', flat(turn['answer'])) if len(x) >= 30]
    repeated = sorted({x for x in sentences if sentences.count(x) > 1})
    check('回答沒有整段重複（Unit 4a）', not repeated,
          f'{len(repeated)} 句重複，例：{repeated[0][:40]}…' if repeated else '')
    closer = flat(turn['answer']).count('本分析旨在提供觀點與輔助')
    check('結語句只出現一次（Unit 4a）', closer <= 1, f'出現 {closer} 次')

    # Unit 6：特質不該被丟掉
    dropped = (audit.get('dropped_traits') or {}).get('total', 0)
    names = {d.get('display_name')
             for v in (audit.get('dropped_traits') or {}).get('by_respondent', {}).values()
             for d in v}
    check('沒有特質因為名稱對不上被丟掉（Unit 6）', dropped == 0,
          f'丟了 {dropped} 個：{sorted(n for n in names if n)}')


def judge_scenarios(manifest, audits, payloads):
    """劇本層級的判定：跨輪次才看得出來的事。"""
    by_label = {t['label']: t for t in manifest['turns']}

    for tag, first, second, added in (
            ('S1', 'S1-turn1-7人', 'S1-turn2-新增游璧碩', '游 璧碩'),
            ('S7', 'S7-turn1-只有Howard', 'S7-turn2-加到8位', None)):
        a, b = by_label.get(first), by_label.get(second)
        if not (a and b):
            continue
        print(f'\n  [{tag} 跨輪：名單變動之後，回答有沒有跟著更新]')
        grew = sorted(set(b['roster']) - set(a['roster']))
        check(f'{tag} 第二輪確實變更了名單', bool(grew), f'新增 {grew}')
        if added:
            check(f'{tag} 新增的「{added}」出現在第二輪的回答裡（Unit 1 主驗收）',
                  mentions(b['answer'], added),
                  '這正是 43c1f019 漏掉的那一位')
        newcomers = [n for cid, n in zip(b['roster'], b['roster_names']) if cid in grew]
        missed = [n for n in newcomers if not mentions(b['answer'], n)]
        check(f'{tag} 所有新增的人都進了回答', not missed, missed)
        # 4920eef8 的病徵：宣稱大部分人沒有資料
        bad = [p for p in ('未包含可供分析', '沒有提供特質', '未提供特質資料',
                           '無法取得其特質', '僅有') if p in b['answer']]
        check(f'{tag} 第二輪沒有宣稱受測者缺資料', not bad,
              f'命中話術：{bad}' if bad else '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=str(date.today()))
    args = ap.parse_args()

    manifest, audits, payloads = load(args.date)
    print(f'環境：{manifest["env"]}   帳號：{manifest["email"]}   '
          f'時間：{manifest["started"]}')
    print(f'額度：{manifest["quota_before"].get("remaining")} -> '
          f'{manifest["quota_after"].get("remaining")}')

    seen = {}
    for turn in manifest['turns']:
        i = seen.get(turn['session_id'], 0)
        seen[turn['session_id']] = i + 1
        judge_turn(turn, audit_for(audits, turn, i), payload_for(payloads, turn, i), i)

    judge_scenarios(manifest, audits, payloads)

    # 出口掃描器的成本，放在最後當觀察值而不是判定——它不是本輪修改的驗收條件，但改寫率
    # 是 B-1／B-2／B-3（詞表誤判）該不該做的直接證據。
    seg = rew = over = 0
    hit = {}
    for rows in audits.values():
        for d in rows:
            if not str(d.get('session_id', '')).startswith('uat-'):
                continue
            seg += len(d.get('segments', []))
            for s in d.get('segments', []):
                rew += s.get('rewrites', 0)
                for h in s.get('hits', []):
                    hit[h] = hit.get(h, 0) + 1
                over += sum(1 for a in (s.get('rewrite_attempts') or [])
                            if a.get('rejected') == 'overgrown')
    print(f'\n  [觀察] 出口掃描器：{seg} 段 / 改寫 {rew} 次'
          f'（每段 {rew / max(seg, 1):.3f}） / 撐大被退回 {over} 次')
    if hit:
        print(f'           命中詞：{dict(sorted(hit.items(), key=lambda kv: -kv[1])[:6])}')

    print(f'\n{"[DONE] all checks passed" if not failures else "[FAILED] " + "; ".join(failures)}')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

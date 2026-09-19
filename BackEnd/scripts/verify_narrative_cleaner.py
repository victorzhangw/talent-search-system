"""Re-clean every interaction narrative in the client's v7 LOG examples and diff.

Usage:
    python scripts/verify_narrative_cleaner.py

Takes each [交互 | …] block the client's pipeline produced, looks the pair up in
trait_interactions, runs our cleaner over the stored narrative, and requires a
character-for-character match. Also asserts the properties the exit scanner depends on
across all 2,389 rows, not just the ones the examples happen to cover.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

from sqlalchemy import text  # noqa: E402
from api_v2.database.connection import get_db_engine  # noqa: E402
from api_v2.services.narrative_cleaner import cleaner  # noqa: E402

# 2026-09-18：客戶簽核通過後改指 V7 產出的 v9 範例。原 v8 範例的敘事是 V6.2
# 產出的，而 DB 已匯入 V7，基準與資料不同版本就不可能綠。新範例由
# scripts/regen_log_examples.py 以同一批受測者、同一題重跑產生，總行數與原範例
# 完全相同（294 / 860 / 1139），差異只有內容文字。
PKG = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', '0918',
                   '範例_V7_已簽核')
EXAMPLES = ['07_新版LOG範例_匡列型_壓力題_v9_V7.txt',
            '06_新版LOG範例_全人型_雙測驗_v9_V7.txt',
            '08_新版LOG範例_多人型_會議團隊_v9_V7.txt']

HEADER_RE = re.compile(r'^\[交互 \| ([A-Z]{3}_\d+)_([ABC]) × ([A-Z]{3}_\d+)_([ABC]) \| (.+)\]$')
TRAIT_ID_RE = re.compile(r'[A-Z]{3}_\d+')

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def main():
    eng = get_db_engine()
    with eng.connect() as c:
        rows = c.execute(text("""SELECT primary_trait_id, split_part(primary_band,'(',1) pb,
                                        trigger_trait_id, trigger_band, narrative
                                 FROM trait_interactions
                                 WHERE narrative IS NOT NULL ORDER BY id""")).fetchall()
    by_pair = {}
    for r in rows:
        by_pair.setdefault((r.primary_trait_id, r.pb.strip(), r.trigger_trait_id, r.trigger_band),
                           r.narrative)
    print(f'\nloaded {len(rows)} narratives, regex_pack {cleaner.version}')

    total = matched = 0
    unmatched_lookup = []
    mismatched = []

    for name in EXAMPLES:
        lines = open(os.path.join(PKG, name), encoding='utf-8').read().split('\n')
        for i, line in enumerate(lines):
            m = HEADER_RE.match(line)
            if not m:
                continue
            a, ab, b, bb, _ = m.groups()
            body = lines[i + 1] if i + 1 < len(lines) else ''
            if not body.strip():          # header with no narrative line in the example
                continue
            total += 1
            stored = by_pair.get((a, ab, b, bb)) or by_pair.get((b, bb, a, ab))
            if stored is None:
                unmatched_lookup.append(f'{a}_{ab} x {b}_{bb}')
                continue
            actual = cleaner.clean(stored)
            if actual == body:
                matched += 1
            else:
                mismatched.append((name, f'{a}_{ab} x {b}_{bb}', body, actual))

    print(f'\n[1] Narratives re-cleaned and compared ({total} interaction blocks in the examples)')
    check('every pair in the examples exists in trait_interactions',
          not unmatched_lookup, unmatched_lookup[:3])
    check('every narrative matches character for character',
          not mismatched, f'{len(mismatched)} mismatched, {matched} matched')
    for name, pair, exp, act in mismatched[:3]:
        print(f'       {name} {pair}')
        print(f'         expected: {exp[:100]}')
        print(f'         actual  : {act[:100]}')

    print('\n[2] Properties across all 2,389 stored narratives')
    cleaned = [cleaner.clean(r.narrative) for r in rows]
    check('no lead-in clause survives',
          not [t for t in cleaned if t.startswith('與')],
          len([t for t in cleaned if t.startswith('與')]))
    check('no trait id survives in any body',
          not [t for t in cleaned if TRAIT_ID_RE.search(t)],
          len([t for t in cleaned if TRAIT_ID_RE.search(t)]))
    check('no 聯動 wording survives', not [t for t in cleaned if '聯動' in t],
          len([t for t in cleaned if '聯動' in t]))
    check('no empty parens', not [t for t in cleaned if re.search(r'[（(]\s*[)）]', t)])
    check('cleaning never empties a narrative', all(t.strip() for t in cleaned))

    print('\n[3] The cleaner is body-only (must never be run over an assembled LOG)')
    header = '[特質 | CIA_05_B | 情境波動]'
    check('a block header would lose its ID if cleaned -- documented, not a bug',
          'CIA_05' not in cleaner.clean(header), repr(cleaner.clean(header)))

    print('\n[4] band 段落寫法不得殘留（附錄 D-1：曝光歸零全靠這條規則）')
    # V7 把 19 處 `B 段` 與 3 處 `B 屬` 改寫成「中段」，而出口掃描的 `band_code` 抓
    # `[ABC]\s*段`、`band_zone_zh` 抓「中分區」，兩者都抓不到「中段」——等於把一個
    # 「會被攔下重寫」的字樣換成「會直接送到讀者眼前」的字樣。擋住它的是正則包的
    # `rewrite_band_zone_zhong`，而那是一條**資料相依**規則（它自己的 note 寫著
    # 「每次 SPEC 更版必須重新清點『中段』用法並更新本條」）。
    #
    # 在補這一段之前沒有任何驗收測過它：2026-09-19 重查附錄 D-1 才發現本檔測的是
    # 開頭子句、特質代號、聯動、空括號與鏈式寫法，唯獨沒測這條。規則一旦因為下一版
    # SPEC 改了措辭而失效，會靜默地失效。
    BAND_ZONE_RE = re.compile(r'[ABC]\s*[段屬](?!落)')
    zone_hits = [t for t in cleaned if BAND_ZONE_RE.search(t)]
    check('no [ABC]段 / [ABC]屬 survives in any cleaned narrative',
          not zone_hits, f'{len(zone_hits)} 列殘留')
    for t in zone_hits[:3]:
        print(f'       {t[:90]}')

    # 構念義的「中段」＝句首（承 `。` 或 `；`）後面接 V7 實際出現的那五種詞。
    # 日常義的「在推進中段」「任務中段」前面有 在/的，不在此列，也不該被改寫。
    CONSTRUCT_ZHONG_RE = re.compile(r'(?<=[。；])中段(?=情境敏感|呈|屬|狀態受|的務實)')
    zhong_hits = [t for t in cleaned if CONSTRUCT_ZHONG_RE.search(t)]
    check('no construct-sense 中段 survives', not zhong_hits, f'{len(zhong_hits)} 列殘留')
    for t in zhong_hits[:3]:
        print(f'       {t[:90]}')

    # 反向：日常義必須**原封不動**。剝得太兇的代價與 `31–60 天` 那類問題是同一個
    # 道理——只改該改的。
    everyday = [
        '這代表他的成長曲線容易在中段趨緩，不是能力到頂。',
        '管理上宜在任務中段設確認點，幫助他把主動的衝勁轉成完整交付。',
        '他常一邊把新任務快速歸進既有的流程框架，一邊在執行中段回頭確認時程。',
    ]
    kept = [t for t in everyday if cleaner.clean(t) == t]
    check('everyday 中段 (在/的 + 中段) is left alone', len(kept) == len(everyday),
          f'{len(everyday) - len(kept)} 句被誤改')

    # 正向：構念義的確被改掉。用正則包 example_in / example_out 的那一對。
    construct_in = '別誤把他初期的保留當成冷漠。中段屬情境敏感、非固定的調節狀態。'
    construct_out = '別誤把他初期的保留當成冷漠。此組合屬情境敏感、非固定的調節狀態。'
    check('construct 中段 is rewritten', cleaner.clean(construct_in) == construct_out,
          repr(cleaner.clean(construct_in)))

    print('\n[5] Defensive rule for the chained lead-in (V6.1 had 4, V6.2/V6.3 have 0)')
    chained = '與 CIA_06 (條理性) C 與 CIA_07 (完美主義) A：表現為「同時要求流程與細節的人」。'
    out = cleaner.clean(chained)
    check('chained form is stripped', out == '表現為「同時要求流程與細節的人」。', repr(out))
    keeps = '與同儕協作時：他偏好先把話講清楚。'
    check('a body that merely starts with 與 is left alone', cleaner.clean(keeps) == keeps,
          repr(cleaner.clean(keeps)))

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

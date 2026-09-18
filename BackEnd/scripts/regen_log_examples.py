"""用目前資料庫裡的特質資料，重新產生客戶的三份 LOG 範例（b §5 / DoD 1）。

用法：
    python scripts/regen_log_examples.py --out ../docs/0918/範例_V7
    python scripts/regen_log_examples.py --out ... --diff-only   # 只印差異，不寫檔

為什麼需要這支
--------------
`verify_log_assembler` / `verify_trait_blocks` / `verify_narrative_cleaner` /
`verify_interaction_selector` 四支都拿客戶凍結的 LOG 範例當比對基準，而那三份範例的
敘事是 V6.2 產出的。2026-09-18 匯入 V7 之後，基準與資料屬於不同版本，這四支就不可能
綠——差異全部落在敘事本文與 `CIA_33_A` 的 K 欄，結構面（標頭、條數、順序、區塊歸屬、
名單區塊、任務指令、System 區塊）完全相同。

所以要做的是把範例換成 V7 產出的版本。

產出的形狀
----------
刻意與現行範例**逐行同形**，只有資料文字不同：

  * 名單區塊 `[本輪判讀對象]` 拿掉——客戶範例是在這個區塊存在之前產出的，
    `verify_log_assembler.split_roster()` 本來就會把它從實際產出中剝掉再比對。
  * 輸出語言規則（第 21 條）拿掉——同理，E-17 是我方增補，範例裡沒有。
  * 保留原範例第一行的檔案註解（`[SYSTEM PROMPT]（以下為…）`）。

這樣新範例與舊範例的 diff 就**只剩內容文字**，客戶審閱時看到的是純粹的內容變更，
而四支腳本既有的剝除邏輯一行都不用改。

這支不做的事
------------
**不會自動替換 `docs/` 裡的範例，也不會改任何 verify 腳本的指向。** 範例是 DoD 第 1
條的驗收基準，等於驗收標準本身——換掉它必須經客戶簽核。這支只產出候選檔與 diff。

還有一件事要講明白：由我方產生範例，會讓那四支從「獨立驗收」退化成「自我比對」。
`verify_narrative_cleaner` 原本的意義是「我方清洗器的輸出，與客戶獨立產出的範例逐字
相同」；若範例改由我方用同一套程式、同一個資料庫產生，那條斷言就只有在程式不具決定性
時才會失敗。所以簽核**不能只簽 diff**，客戶要實際讀過新範例的敘事內容。
"""

import argparse
import difflib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv                                          # noqa: E402
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'),
            encoding='utf-8-sig')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_log_assembler import (PKG, CASES, parse_respondents,        # noqa: E402
                                  split_roster, table)
from verify_system_prompt import strip_language_rule                    # noqa: E402
from api_v2.services.log_assembler import assemble                      # noqa: E402


def regenerate(filename, title):
    """回傳 (原範例行, 新範例行)。兩者同形，只有資料文字可能不同。"""
    raw = open(os.path.join(PKG, filename), encoding='utf-8').read()
    expected = raw.split('\n')
    while expected and not expected[-1].strip():
        expected.pop()

    question = table.get(title)
    respondents = parse_respondents(expected)
    log = assemble(respondents, question)

    actual, _roster = split_roster(log.to_log_text().split('\n'))
    actual, _language = strip_language_rule(actual)

    # 範例檔第一行是人閱註解（`[SYSTEM PROMPT]（以下為 a 文件第一部分全文，靜態）`），
    # 打包器產出的是純 `[SYSTEM PROMPT]`。沿用原範例那一行，diff 才不會多一筆雜訊。
    if expected and actual and expected[0] != actual[0] \
            and expected[0].startswith('[SYSTEM PROMPT]') \
            and actual[0].startswith('[SYSTEM PROMPT]'):
        actual[0] = expected[0]

    return expected, actual


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', help='輸出目錄；不給就只印差異')
    ap.add_argument('--diff-only', action='store_true', help='只印差異，不寫檔')
    ap.add_argument('--context', type=int, default=0, help='diff 的上下文行數')
    args = ap.parse_args()

    out_dir = None
    if args.out and not args.diff_only:
        out_dir = os.path.abspath(args.out)
        os.makedirs(out_dir, exist_ok=True)

    grand_total = 0
    for filename, title in CASES:
        expected, actual = regenerate(filename, title)
        diff = [l for l in difflib.unified_diff(
            expected, actual, 'v8(V6.2 敘事)', 'v9(V7 敘事)',
            lineterm='', n=args.context)]
        changed = sum(1 for l in diff if l.startswith('-') and not l.startswith('---'))
        grand_total += changed

        print(f'\n{"=" * 78}')
        print(f'{filename}')
        print(f'  題目：{title}')
        print(f'  總行數 {len(expected)} -> {len(actual)}｜有差異的行 {changed}')
        print(f'{"=" * 78}')
        for l in diff:
            print(l)

        if out_dir:
            new_name = filename.replace('_v8_260917.txt', '_v9_V7.txt')
            if new_name == filename:
                new_name = os.path.splitext(filename)[0] + '_v9_V7.txt'
            path = os.path.join(out_dir, new_name)
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(actual) + '\n')
            print(f'\n[Regen] 已寫出 {path}')

    print(f'\n[Regen] 三份合計有差異的行：{grand_total}')
    if out_dir:
        print(f'[Regen] 輸出目錄：{out_dir}')
    print('[Regen] 這些檔案尚未生效——需客戶簽核後才可替換基準並改指 verify 腳本。')
    return 0


if __name__ == '__main__':
    sys.exit(main())

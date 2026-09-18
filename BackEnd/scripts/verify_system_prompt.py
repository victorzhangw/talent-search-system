"""Verify the stored System block against the client's source documents.

Usage:
    python scripts/verify_system_prompt.py

Two independent sources are checked:
  1. `a_LOG完成版模板_v2_20260727.md` 第一部分 -- the defined source (b §5).
  2. The System region embedded in the three `新版LOG範例_*_v7.txt` files -- what the
     client's own pipeline actually rendered (DoD 第 1 條 compares against these).

They agree on everything except rule 15; that single known divergence is reported
rather than silently tolerated. Any other difference is a failure.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api_v2.services.log_system_prompt import load_system_prompt  # noqa: E402

# 2026-09-18：改指 0917 交付包。客戶在 0917 更新了全域輸出規範第 8 條（加上適任／
# 排序提問時的制式提醒句），a 文件與三份範例都跟著出了新版；比對基準若還停在 0730，
# 規則八一改就必然對不上。
PKG = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', '0917',
                   'Traitty_調整_20260917')
A_DOC = os.path.join(PKG, 'a_LOG完成版模板_v2_20260917.md')
EXAMPLES = [os.path.join(PKG, f) for f in (
    '07_新版LOG範例_匡列型_壓力題_v8_260917.txt',
    '06_新版LOG範例_全人型_雙測驗_v8_260917.txt',
    '08_新版LOG範例_多人型_會議團隊_v8_260917.txt',
)]

KNOWN_DIVERGENCE_PREFIX = '15. 自濾授權'

# E-17：客戶正本沒有規定輸出字體，而 2026-09-09 req cf3dcd60 整篇回答是簡體字
# （2791 字裡簡體 259、繁體 32）。第 21 條是我們加的，措辭沿用客戶自己在
# `prompts/modules/*.txt` 已經在用的說法。1-20 條一個字都沒動——那些編號被 v7 範例、
# 驗收腳本與 a 文件互相引用（例如 `verify_log_assembler` 的 'a-doc rule 15 clause'），
# 重編會全部連動。
LANGUAGE_HEADING = '### 戊、輸出語言'
LANGUAGE_RULE_PREFIX = '21. 所有輸出必須使用繁體中文'
RULE_COUNT_A_DOC = '## 【全域輸出規範】（唯一正本，共 20 條；取代各題原本重複的禁止段與判讀規範段）'
RULE_COUNT_STORED = RULE_COUNT_A_DOC.replace('共 20 條', '共 21 條')


def strip_language_rule(lines):
    """把第 21 條與它的小節標題取出來，並把條數還原成客戶正本的寫法。

    取出來單獨檢查、其餘仍要求與 a 文件逐字相同——這樣只要增補的形狀跑掉（多一行、
    少一行、位置不對），剩下的部分就會對不齊而爆掉，比整份放寬安全。
    """
    rest, taken = [], []
    i = 0
    while i < len(lines):
        if lines[i] == LANGUAGE_HEADING:
            taken = lines[i:i + 2]
            if rest and not rest[-1].strip():
                rest.pop()                 # 小節前面那個空行也是我們加的
            i += 2
            continue
        rest.append(RULE_COUNT_A_DOC if lines[i] == RULE_COUNT_STORED else lines[i])
        i += 1
    return rest, taken

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def a_doc_section():
    lines = open(A_DOC, encoding='utf-8').read().split('\n')
    s = next(i for i, l in enumerate(lines) if l.startswith('# 第一部分：'))
    e = next(i for i, l in enumerate(lines) if l.startswith('# 第二部分：'))
    block = lines[s:e]
    while block and not block[-1].strip():
        block.pop()
    return block


def example_section(path):
    """The System region of a rendered LOG: everything between the [SYSTEM PROMPT]
    marker line and 【輸入數據】, minus the assembler's own trailing separator."""
    lines = open(path, encoding='utf-8').read().split('\n')
    end = next(i for i, l in enumerate(lines) if l.startswith('## 【輸入數據】'))
    block = lines[1:end]
    while block and not block[-1].strip():
        block.pop()
    if block and block[-1] == '---':      # separator the assembler inserts before 【輸入數據】
        block.pop()
    while block and not block[-1].strip():
        block.pop()
    while block and not block[0].strip():
        block.pop(0)
    return block


def main():
    stored = load_system_prompt().split('\n')
    while stored and not stored[-1].strip():
        stored.pop()

    print('\n[1] Stored file vs a-document 第一部分 (the defined source, b §5)')
    a = a_doc_section()
    base, language = strip_language_rule(stored)
    check('byte-identical once the E-17 language rule is taken out', base == a,
          f'base {len(base)} lines, a-doc {len(a)} lines')
    if base != a:
        import difflib
        for d in list(difflib.unified_diff(a, base, 'a-doc', 'stored', lineterm=''))[:12]:
            print('       ', d[:150])
    check('the only addition is the language section', len(language) == 2, language)

    print('\n[2] Structure')
    # Two independent numbered lists: 【系統角色與判讀引導】 1-6, then 【全域輸出規範】 1-20.
    split_at = next(i for i, l in enumerate(stored) if l.startswith('## 【全域輸出規範】'))

    def numbers(lines):
        return [int(l.split('.', 1)[0]) for l in lines
                if l.split('.', 1)[0].strip().isdigit()]

    check('判讀引導 numbered 1..6', numbers(stored[:split_at]) == list(range(1, 7)),
          numbers(stored[:split_at]))
    check('全域輸出規範 numbered 1..21 (heading says 共 21 條)',
          numbers(stored[split_at:]) == list(range(1, 22)), numbers(stored[split_at:]))
    check('條數宣告與實際條數一致',
          stored[split_at] == RULE_COUNT_STORED, stored[split_at])
    check('five category headings present',
          [l for l in stored if l.startswith('### ')] == [
              '### 甲、禁止揭露（系統出口掃描器會攔截，命中即重寫）',
              '### 乙、語言紀律',
              '### 丙、資料使用規範（怎麼讀注入的資料）',
              '### 丁、建議性輸出強化',
              LANGUAGE_HEADING])

    print('\n[2b] E-17：輸出語言是硬性規定')
    rule = next((l for l in stored if l.startswith(LANGUAGE_RULE_PREFIX)), '')
    check('第 21 條存在且要求繁體中文', bool(rule), rule[:60])
    check('明講是硬性規定', '硬性規定' in rule, rule[-60:])
    # cf3dcd60 是第 8 則歷史之後才飄掉的，所以要把「不因輪次或歷史長度而改變」寫進去。
    check('點名不因提問語言／輪次／歷史長度而改變',
          '不因提問語言' in rule and '歷史長度' in rule, rule[-60:])
    check('沿用客戶自己的措辭（台灣用語）', '台灣用語' in rule)
    check('簡體字三個字有出現在規則裡', '簡體字' in rule)
    check('ends with the section separator', stored[-1] == '---', repr(stored[-1]))
    check('is a constant, not a template', '{' not in ''.join(stored))

    print('\n[3] Cross-check against the three rendered LOG examples')
    sections = {os.path.basename(p): example_section(p) for p in EXAMPLES}
    ref_name, ref = next(iter(sections.items()))
    check('all three examples embed an identical System block',
          all(v == ref for v in sections.values()))

    diffs = [(i, s, r) for i, (s, r) in enumerate(zip(base, ref)) if s != r]
    known = [d for d in diffs if d[1].startswith(KNOWN_DIVERGENCE_PREFIX)]
    unknown = [d for d in diffs if not d[1].startswith(KNOWN_DIVERGENCE_PREFIX)]
    check('same line count as the examples once E-17 is taken out',
          len(base) == len(ref), f'{len(base)} vs {len(ref)}')
    check('no unexpected difference from the examples', not unknown,
          [d[0] for d in unknown])
    if known:
        print('  [NOTE] known divergence, deliberate -- a-document is the defined source:')
        print(f'         a-doc/stored: {known[0][1][:60]}...{known[0][1][-30:]}')
        print(f'         examples    : {known[0][2][:60]}...{known[0][2][-12:]}')
        print('         The examples predate the 2026-07-28 全注入 ruling that this clause states.')

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

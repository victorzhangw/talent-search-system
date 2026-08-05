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

PKG = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', '0730',
                   'Traitty_調整_20260728＿final')
A_DOC = os.path.join(PKG, 'a_LOG完成版模板_v2_20260727.md')
EXAMPLES = [os.path.join(PKG, f) for f in (
    '新版LOG範例_匡列型_壓力題_v7.txt',
    '新版LOG範例_全人型_雙測驗_v7.txt',
    '新版LOG範例_多人型_會議團隊_v7.txt',
)]

KNOWN_DIVERGENCE_PREFIX = '15. 自濾授權'

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
    check('byte-identical', stored == a,
          f'stored {len(stored)} lines, a-doc {len(a)} lines')
    if stored != a:
        import difflib
        for d in list(difflib.unified_diff(a, stored, 'a-doc', 'stored', lineterm=''))[:12]:
            print('       ', d[:150])

    print('\n[2] Structure')
    # Two independent numbered lists: 【系統角色與判讀引導】 1-6, then 【全域輸出規範】 1-20.
    split_at = next(i for i, l in enumerate(stored) if l.startswith('## 【全域輸出規範】'))

    def numbers(lines):
        return [int(l.split('.', 1)[0]) for l in lines
                if l.split('.', 1)[0].strip().isdigit()]

    check('判讀引導 numbered 1..6', numbers(stored[:split_at]) == list(range(1, 7)),
          numbers(stored[:split_at]))
    check('全域輸出規範 numbered 1..20 (heading says 共 20 條)',
          numbers(stored[split_at:]) == list(range(1, 21)), numbers(stored[split_at:]))
    check('four category headings present',
          [l for l in stored if l.startswith('### ')] == [
              '### 甲、禁止揭露（系統出口掃描器會攔截，命中即重寫）',
              '### 乙、語言紀律',
              '### 丙、資料使用規範（怎麼讀注入的資料）',
              '### 丁、建議性輸出強化'])
    check('ends with the section separator', stored[-1] == '---', repr(stored[-1]))
    check('is a constant, not a template', '{' not in ''.join(stored))

    print('\n[3] Cross-check against the three rendered LOG examples')
    sections = {os.path.basename(p): example_section(p) for p in EXAMPLES}
    ref_name, ref = next(iter(sections.items()))
    check('all three examples embed an identical System block',
          all(v == ref for v in sections.values()))

    diffs = [(i, s, r) for i, (s, r) in enumerate(zip(stored, ref)) if s != r]
    known = [d for d in diffs if d[1].startswith(KNOWN_DIVERGENCE_PREFIX)]
    unknown = [d for d in diffs if not d[1].startswith(KNOWN_DIVERGENCE_PREFIX)]
    check('same line count as the examples', len(stored) == len(ref),
          f'{len(stored)} vs {len(ref)}')
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

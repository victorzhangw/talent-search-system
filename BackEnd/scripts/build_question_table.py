"""由客戶的快速提問 xlsx 正本建出 runtime 題庫與模組清單。

用法（以 v10 為例）：
    python scripts/build_question_table.py \
        --xlsx ../docs/1002/快速提問整合版_20261001_v2.xlsx \
        --prev-table <前一版 question_injection_table.json> \
        --prev-modules <前一版 quick_modules.json> \
        --curation ../docs/1002/question_table_v10_curation.json \
        --out-dir <輸出目錄>

前一版不在工作目錄時，用 git 取出，例如：
    git show 18dbce5:BackEnd/api_v2/config/question_injection_table_v9.json > prev_table.json

輸出 `question_injection_table_<版本前綴>.json` 與 `quick_modules.json` 到 --out-dir，
不直接覆寫 config/：替換 runtime 檔是另一個動作，要先 diff 過、跑過 verify_all。

為什麼有這支
------------
2026-10-02 匯入 v10 時，這段邏輯放在 scratchpad 的一次性腳本裡。下一次客戶改題庫，
同樣的比對與檢查要重做一遍，不收進來就只能重新寫。

哪些是程式做的、哪些不是
------------------------
  程式：指令逐字複製、題型與適用對象、匡列清單、module id 沿用、衍生欄位。
  人工：每題的段落清單（expected_sections_single/multi）、逐人分段（per_person）、
        新題的 module id。這些寫在 --curation 檔，因為 b §8 明講從指令推導輸出結構是
        語意判斷，程式只負責驗它，不負責生它。

建置時一定會檢查、任一條不過就不寫檔：
  1. 判定檔的每個段落名，都逐字出現在它所屬的指令裡（空白、全半形斜線與問號不計）。
  2. 適用的單人／多人版一定有段落清單；不適用的一定是空的。
  3. 匡列型題目的匡列清單與前一版集合相同（--allow-scope-change 才放行）。
  4. 全人型題目的匡列欄位是空的，或只寫「不另設固定匡列」。
  5. 每題都有 module id，且不重複。
"""

import argparse
import copy
import json
import os
import re
import sys

import openpyxl

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AUDIENCE = {'僅單人': 'single_only', '單人/多人': 'both', '僅多人': 'multi_only'}
TYPE = {'匡列型': 'scoped', '全人型': 'whole_person'}
NO_SCOPE = '不另設固定匡列'
TESTS = ('ANI', 'CIA', 'SPA', 'CSR')
SHEET_MASTER = '題庫正本'
SHEET_CROSSWALK = '說明'


class BuildError(Exception):
    pass


def trait_ids(cell):
    return re.findall(r'(?:ANI|CIA|SPA|CSR)_\d+', cell or '')


def _flat(text):
    """段落名與指令比對用：去空白、斜線與問號收斂成半形。"""
    text = (text or '').replace('／', '/').replace('？', '?')
    return re.sub(r'\s+', '', text)


def read_workbook(path):
    wb = openpyxl.load_workbook(path)
    rows = [[c.value for c in r] for r in wb[SHEET_MASTER].iter_rows(min_row=2)
            if r[0].value is not None]
    crosswalk = {}
    for r in wb[SHEET_CROSSWALK].iter_rows(min_row=3):
        v = [c.value for c in r]
        if v[0] is None:
            continue
        crosswalk[int(v[0])] = None if v[3] == '新增' else int(v[3])
    return rows, crosswalk


def build(xlsx, prev_table, prev_modules, curation, allow_scope_change=False):
    rows, crosswalk = read_workbook(xlsx)
    cur_q = {int(k): v for k, v in curation['questions'].items()}
    source_field = curation['source_field']
    problems = []

    old_by_idx = {q['idx']: q for q in prev_table['questions']}
    old_title_to_idx = {q['title']: q['idx'] for q in prev_table['questions']}
    old_idx_to_module = {old_title_to_idx[cfg['display_name']]: mid
                         for mid, cfg in prev_modules.items()}
    template_whole = old_by_idx[curation['template_whole_person_idx']]

    questions, modules = [], {}
    for v in rows:
        n = int(v[0])
        if n not in crosswalk:
            problems.append(f'Q{n}: 「{SHEET_CROSSWALK}」分頁沒有對照列')
            continue
        if n not in cur_q:
            problems.append(f'Q{n}: 判定檔沒有這一題')
            continue
        src = crosswalk[n]
        typ, aud = TYPE[v[3]], AUDIENCE[v[4]]
        q = copy.deepcopy(old_by_idx[src] if src else template_whole)
        q['idx'] = n
        q['category'] = v[1]
        q['title'] = v[2]
        q['type'] = typ
        q['audience'] = aud
        q['instruction_single'] = v[5]
        q['instruction_multi'] = v[6]

        scoped = {t: trait_ids(v[7 + i]) for i, t in enumerate(TESTS)}
        if typ == 'whole_person':
            for i in range(7, 11):
                if v[i] is not None and NO_SCOPE not in v[i]:
                    problems.append(f'Q{n}: 全人型卻有匡列內容：{v[i]!r}')
            q['scoped_traits'] = {t: [] for t in TESTS}
            q['scoped_total'] = 0
            q['injection_set'] = None
            q['gap'] = []
        elif src is None:
            problems.append(f'Q{n}: 新增的匡列型題目需要另外產生 injection_set，本工具不支援')
        else:
            prev = q['scoped_traits'] or {}
            for t in TESTS:
                if set(scoped[t]) != set(prev.get(t, [])):
                    msg = (f'Q{n} {t}: 匡列與前一版不同 '
                           f'(-{sorted(set(prev.get(t, [])) - set(scoped[t]))} '
                           f'+{sorted(set(scoped[t]) - set(prev.get(t, [])))})')
                    if not allow_scope_change:
                        problems.append(msg + '；injection_set 等衍生欄位需重算，'
                                        '確認後以 --allow-scope-change 執行並另行重算')
        if not src:
            q['note'] = curation['new_question_note']
            q['cleanup'] = {'removed': [], 'uncertain': [], 'chars_before': [0, 0],
                            'chars_after': [0, 0]}
        q[source_field] = src

        c = cur_q[n]
        single, multi = list(c.get('single') or []), list(c.get('multi') or [])
        for side, heads, key, applicable in (
                ('單人', single, 'instruction_single', aud != 'multi_only'),
                ('多人', multi, 'instruction_multi', aud != 'single_only')):
            if bool(heads) != applicable:
                problems.append(f'Q{n} {side}版：適用={applicable} 但判定檔有 {len(heads)} 個段落')
            text = _flat(q[key])
            for h in heads:
                if _flat(h) not in text:
                    problems.append(f'Q{n} {side}版：段落「{h}」不在指令裡')
        q['expected_sections_single'] = single
        q['expected_sections_multi'] = multi
        q['expected_sections'] = list(single or multi)
        q.pop('expected_sections_note', None)
        q['per_person_sections'] = bool(c.get('per_person'))
        q['per_person_sections_note'] = curation['per_person_sections_note']
        questions.append(q)

        mid = c.get('module_id') or (old_idx_to_module.get(src) if src else None)
        if not mid:
            problems.append(f'Q{n}: 沒有 module id（新題要在判定檔寫 module_id）')
        elif mid in modules:
            problems.append(f'Q{n}: module id {mid} 重複')
        else:
            modules[mid] = {'category': v[1], 'display_name': v[2], 'candidate_mode': aud}

    extra = sorted(set(cur_q) - {int(v[0]) for v in rows})
    if extra:
        problems.append(f'判定檔有正本沒有的題目：{extra}')
    if problems:
        raise BuildError(problems)

    table = copy.deepcopy(prev_table)
    table['version'] = curation['version']
    table['questions'] = questions
    table['note'] = prev_table['note'] + curation['note_append']
    table['expected_sections_note'] = curation['expected_sections_note']
    table['_source_of_truth'] = curation['source_of_truth']
    return table, modules


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--xlsx', required=True)
    ap.add_argument('--prev-table', required=True)
    ap.add_argument('--prev-modules', required=True)
    ap.add_argument('--curation', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--allow-scope-change', action='store_true')
    args = ap.parse_args()

    load = lambda p: json.load(open(p, encoding='utf-8'))  # noqa: E731
    curation = load(args.curation)
    try:
        table, modules = build(args.xlsx, load(args.prev_table), load(args.prev_modules),
                               curation, args.allow_scope_change)
    except BuildError as e:
        print(f'ERROR: 建置失敗，{len(e.args[0])} 項問題，未寫出任何檔案：')
        for p in e.args[0]:
            print(f'  - {p}')
        return 1

    os.makedirs(args.out_dir, exist_ok=True)
    prefix = curation['version'].split('-')[0]
    out_table = os.path.join(args.out_dir, f'question_injection_table_{prefix}.json')
    out_modules = os.path.join(args.out_dir, 'quick_modules.json')
    with open(out_table, 'w', encoding='utf-8') as f:
        json.dump(table, f, ensure_ascii=False, indent=2)
    with open(out_modules, 'w', encoding='utf-8') as f:
        json.dump(modules, f, ensure_ascii=False, indent=2)
    print(f'[OK] {len(table["questions"])} 題 -> {out_table}')
    print(f'[OK] {len(modules)} 個模組 -> {out_modules}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

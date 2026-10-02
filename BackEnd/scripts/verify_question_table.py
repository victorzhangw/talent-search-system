"""驗 runtime 題庫（question_injection_table）與模組清單本身，而不是個別機制。

Usage:
    python scripts/verify_question_table.py

其他 verify 各自拿一兩題來驗某個機制；這支反過來，把**每一題**都過一遍。2026-10-02
匯入 v10 時這些檢查放在 scratchpad 的一次性腳本，收進來之後，任何人改題庫或改
段落檢查器，verify_all 都會跑到。

  [1] 載入：題號連續、28 個模組與題目一對一、題名一致（ModuleMap 在 import 就會驗）。
  [2] 段落清單逐字出現在對應指令裡；適用的單人／多人版一定有，不適用的一定沒有。
  [3] 以正式的 CompletenessChecker 跑合成回答：6 種標題寫法下完整回答要過、逐段刪除
      要剛好抓到被刪的那段；「##呈現補充」的成果標題與 ▪ 前置重點不能被當成段落。
  [4] 必寫字串（段落名、成果標題、▪ 項目名）不能命中出口掃描器的常駐規則——那些規則
      不會依當次注入的特質縮小，命中就是每一次都要改寫。
  [5] 以真實受測者（v10 範例的三組）把每題 × 每種適用人數各組一次 payload：unit_check
      要綠、[任務指令] 逐字等於題庫、逐人涵蓋句只出現在 per_person 題。
  [6] /modules/ 的分類順序等於題號順序，且 routes/modules.py 的 category_order 涵蓋全部分類。
"""

import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

from api_v2.services.question_table import table  # noqa: E402
from api_v2.services.module_map import module_map  # noqa: E402
from api_v2.services.completeness_check import (check_answer, section_key,  # noqa: E402
                                                normalize_heading_keep_numbering)
from api_v2.services.exit_scanner import ExitScanner  # noqa: E402
from api_v2.services.log_assembler import assemble, INSTRUCTION_MARKER, COVERAGE_CLAUSE  # noqa: E402

failures = []


def check(label, condition, detail=''):
    if not condition:
        failures.append(label)
        print(f'  [FAIL] {label}' + (f' -- {detail}' if detail != '' else ''))


def applicable(q, multi):
    return q['audience'] != ('single_only' if multi else 'multi_only')


def instruction_key(multi):
    return 'instruction_multi' if multi else 'instruction_single'


def expected(q, multi):
    return q['expected_sections_multi' if multi else 'expected_sections_single']


def flat(text):
    return re.sub(r'\s+', '', (text or '').replace('／', '/').replace('？', '?'))


def preamble(q, multi):
    """「##呈現補充」要求的成果標題與 ▪ 前置重點，含一種模型常見的變體寫法。"""
    text = q[instruction_key(multi)] or ''
    lines = []
    m = re.search(r'獨立輸出「([^」]+)」', text)
    if m:
        lines.append(f'# {m.group(1)}')
    for label in re.findall(r'^▪\s*([^｜\n]+)｜', text, re.M):
        lines += [f'▪ {label}｜一句簡短重點。\n', f'- **{label}**｜一句簡短重點。\n']
    return lines


class R:
    def __init__(self, name):
        self.name, self.respondent_id, self.scores = name, name, {}


NAMES = ['林孟德', '陳亭羽', '洪宗瑋']
STYLES = {
    'md_numbered': lambda i, h: f'## {i}. {h}\n內容說明。',
    'bold_inline': lambda i, h: f'**{i}. {h}**：這段是內容。',
    'plain_numbered': lambda i, h: f'{i}. {h}\n內容說明。',
    'md_plain': lambda i, h: f'### {h}\n內容說明。',
    'part_style': lambda i, h: f'第{"一二三四五六七八九十"[i - 1]}部分，{h}：內容說明。',
    'bracket': lambda i, h: f'【{h}】\n內容說明。',
}


def synthetic_answer(q, multi, style, drop=None):
    out = preamble(q, multi)
    for i, h in enumerate(expected(q, multi), 1):
        if h == drop:
            continue
        out.append(STYLES[style](i, h))
        if multi and q.get('per_person_sections') and i == 2:
            out += [f'### {n}\n{n}的內容。' for n in NAMES]
        elif multi and i == 1 and not q.get('per_person_sections'):
            out.append('、'.join(NAMES) + '的差異說明。')
    out.append('本分析旨在提供觀點與輔助，最終決策請結合多方資訊綜合考量。')
    return '\n'.join(out)


def main():
    questions = table.all()

    print(f'[1] 載入 {table.version}')
    check('題號從 1 起連續', [q['idx'] for q in questions] == list(range(1, len(questions) + 1)))
    check('模組與題目一對一', len(module_map) == len(questions), (len(module_map), len(questions)))
    for mid, cfg in module_map.modules.items():
        check(f'{mid} 的題名一致', module_map.question_for(mid)['title'] == cfg['display_name'])

    print('[2] 段落清單逐字出現在指令裡')
    for q in questions:
        for multi in (False, True):
            heads = expected(q, multi)
            check(f"Q{q['idx']}{'M' if multi else 'S'} 適用就有段落、不適用就沒有",
                  bool(heads) == applicable(q, multi), heads)
            text = flat(q[instruction_key(multi)])
            for h in heads:
                check(f"Q{q['idx']} 段落「{h}」在指令裡", flat(h) in text)

    print('[2b] 人工判定與判定檔一致')
    # 段落清單與逐人分段是人工判定（見 build_question_table.py），題庫只是它的產物。
    # 不對照判定檔的話，直接改題庫裡的 per_person_sections，上下游每一項檢查都會跟著
    # 這個欄位一起變，什麼都抓不到——2026-10-02 變異測試就是這樣漏的。
    import glob
    import json
    prefix = table.version.split('-')[0]
    found = glob.glob(os.path.join(os.path.dirname(__file__), '..', '..', 'docs', '*',
                                   f'question_table_{prefix}_curation.json'))
    check(f'找得到 {prefix} 的判定檔', len(found) == 1, found)
    if len(found) == 1:
        curation = json.load(open(found[0], encoding='utf-8'))
        cq = curation['questions']
        check('判定檔版本與題庫一致', curation['version'] == table.version)
        check('判定檔題數與題庫一致', sorted(map(int, cq)) == [q['idx'] for q in questions])
        for q in questions:
            c = cq.get(str(q['idx']), {})
            check(f"Q{q['idx']} 單人段落與判定檔一致",
                  q['expected_sections_single'] == (c.get('single') or []))
            check(f"Q{q['idx']} 多人段落與判定檔一致",
                  q['expected_sections_multi'] == (c.get('multi') or []))
            check(f"Q{q['idx']} per_person 與判定檔一致",
                  q['per_person_sections'] == bool(c.get('per_person')))

    print('[3] 合成回答 × 正式的 CompletenessChecker')
    runs = 0
    for q in questions:
        for multi in (False, True):
            if not applicable(q, multi):
                continue
            tag = f"Q{q['idx']}{'M' if multi else 'S'}"
            heads = expected(q, multi)
            people = [R(n) for n in (NAMES if multi else NAMES[:1])]
            keys = [section_key(normalize_heading_keep_numbering(h)) for h in heads]
            check(f'{tag} 段落正規化後互不相撞', len(keys) == len(set(keys)), keys)
            res = check_answer('\n'.join(preamble(q, multi)), people, q)
            check(f'{tag} 只有成果標題與前置重點時，所有段落都判缺', res.missing_sections == heads,
                  res.missing_sections)
            # 「第X部分，」只在指令本身這樣寫的題目測：段落名以數字或「一」開頭時，檢查器
            # 會把序號連同開頭一起剝掉（既有限制，見決策紀錄 §4），而那些題不會這樣寫。
            styles = [s for s in STYLES
                      if s != 'part_style' or '部分，' in (q[instruction_key(multi)] or '')]
            for style in styles:
                res = check_answer(synthetic_answer(q, multi, style), people, q)
                runs += 1
                check(f'{tag} {style} 完整回答通過',
                      res.sections_check == 'passed' and not res.missing_respondents,
                      (res.sections_check, res.missing_sections, res.missing_respondents))
                for h in heads:
                    res = check_answer(synthetic_answer(q, multi, style, drop=h), people, q)
                    runs += 1
                    check(f'{tag} {style} 刪掉「{h}」要剛好抓到它', res.missing_sections == [h],
                          res.missing_sections)
    print(f'  {runs} 次檢查器實跑')

    print('[4] 必寫字串不命中出口掃描器的常駐規則')
    hard = ExitScanner(injected_names=[], injected_labels=[])
    for q in questions:
        for multi in (False, True):
            if not applicable(q, multi):
                continue
            for s in expected(q, multi) + preamble(q, multi):
                hits = hard.scan(s)
                check(f"Q{q['idx']} 必寫字串被攔：{s.strip()}", not hits, hits)

    print('[5] 真實受測者組裝每題 payload')
    import verify_log_assembler as vla
    def load(fn):
        lines = open(os.path.join(vla.PKG, fn), encoding='utf-8').read().split('\n')
        return vla.parse_respondents(lines)
    groups = {
        'single': load('07_新版LOG範例_匡列型_壓力題_v10.txt')[:1],
        'dual': load('06_新版LOG範例_全人型_雙測驗_v10.txt')[:1],
        'multi': load('08_新版LOG範例_多人型_會議團隊_v10.txt'),
    }
    built = 0
    for q in questions:
        for tag, people in groups.items():
            multi = len(people) > 1
            if not applicable(q, multi):
                continue
            label = f"Q{q['idx']} {tag}"
            try:
                log = assemble(people, q)          # run_checks=True：unit_check 不過就 raise
            except Exception as e:
                check(f'{label} 組裝成功', False, f'{type(e).__name__}: {e}')
                continue
            built += 1
            text = log.to_log_text()
            body = text.split(INSTRUCTION_MARKER + '\n', 1)[1]
            check(f'{label} [任務指令] 逐字等於題庫',
                  body.rstrip() == (q[instruction_key(multi)] or '').rstrip())
            wants = multi and bool(q['per_person_sections'])
            check(f'{label} 逐人涵蓋句只在 per_person 題出現',
                  (COVERAGE_CLAUSE.format(n=len(people)) in text) == wants)
            check(f'{label} 稽核帶題庫版本',
                  log.audit.get('question_table_version') == table.version)
    print(f'  {built} 份 payload')

    print('[6] /modules/ 的分類順序')
    from flask import Flask
    from api_v2.routes import modules as modules_route
    app = Flask(__name__)
    app.register_blueprint(modules_route.bp)
    resp = app.test_client().get('/modules/')
    cats = resp.get_json()['data']['categories']
    by_idx = []
    for q in questions:
        if q['category'] not in by_idx:
            by_idx.append(q['category'])
    check('分類順序等於題號順序', list(cats) == by_idx, (list(cats), by_idx))
    check('每個分類都寫在 category_order 裡',
          all(f"'{c}'" in open(modules_route.__file__, encoding='utf-8').read() for c in by_idx))
    check('題目總數', sum(len(v) for v in cats.values()) == len(questions))

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures[:20])}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

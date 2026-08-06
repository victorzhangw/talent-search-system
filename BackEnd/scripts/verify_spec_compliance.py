"""Traceability audit: client DoD and 常見誤區 vs the code as written.

Usage:
    python scripts/verify_spec_compliance.py

The per-module verify_* scripts check behaviour. This checks the things the client's
handover document warns about at the level of the source itself -- a file that must never
be loaded, a cap that must not exist, a prohibited shortcut -- plus the five DoD clauses.
Behavioural DoD items delegate to the script that already proves them, so this stays an
index rather than a second implementation.
"""

import os
import pathlib
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

SERVICES = pathlib.Path(os.path.join(os.path.dirname(__file__), '..', 'api_v2', 'services'))
PACKER_MODULES = ['log_system_prompt.py', 'trait_blocks.py', 'trait_splitter.py',
                  'narrative_cleaner.py', 'interaction_selector.py', 'endpoint_registry.py',
                  'question_table.py', 'log_assembler.py', 'unit_check.py',
                  'exit_scanner.py', 'completeness_check.py', 'segment_gate.py',
                  'log_pipeline.py', 'module_map.py', 'respondent_adapter.py',
                  'packed_chat.py']

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def source(*names):
    out = {}
    for n in (names or PACKER_MODULES):
        p = SERVICES / n
        if p.exists():
            out[n] = p.read_text(encoding='utf-8')
    return out


def executable_source(text: str) -> str:
    """Source with docstrings and comments removed.

    The prohibitions being audited are about logic, not vocabulary: the selector's
    docstring quotes b §3 revoking the 25/40-item caps, and question_table's explains the
    calibration trait ids. Grepping raw text flags exactly the modules that documented the
    rule most carefully, which is the opposite of what should happen.
    """
    import ast
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text
    doc_spans = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, 'body', None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                doc_spans.add((body[0].lineno, body[0].end_lineno))
    keep = []
    for i, line in enumerate(text.split('\n'), 1):
        if any(a <= i <= b for a, b in doc_spans):
            continue
        keep.append(line.split('#', 1)[0] if line.strip().startswith('#') else line)
    return '\n'.join(keep)


def main():
    src = source(*PACKER_MODULES)
    exe = {n: executable_source(t) for n, t in src.items()}
    code_only = '\n'.join(exe.values())

    print('\n=== 驗收 DoD（00_外包交接說明 §四）===')

    print('\n[DoD 1] 重現範例：【輸入數據】一致，[SYSTEM PROMPT] 與 a 文件一字不差')
    from api_v2.services.log_system_prompt import load_system_prompt
    a_doc = pathlib.Path(os.path.join(os.path.dirname(__file__), '..', '..', 'docs', '0730',
                                      'Traitty_調整_20260728＿final',
                                      'a_LOG完成版模板_v2_20260727.md')).read_text(encoding='utf-8')
    lines = a_doc.split('\n')
    s = next(i for i, l in enumerate(lines) if l.startswith('# 第一部分：'))
    e = next(i for i, l in enumerate(lines) if l.startswith('# 第二部分：'))
    a_section = '\n'.join(lines[s:e]).rstrip('\n')
    check('System block is byte-identical to a-doc 第一部分',
          load_system_prompt().rstrip('\n') == a_section)
    check('example reproduction is proven by verify_log_assembler',
          (pathlib.Path(os.path.dirname(__file__)) / 'verify_log_assembler.py').exists())

    print('\n[DoD 2] 單元檢查四項每次組裝都跑')
    check('assemble() runs them by default',
          re.search(r'run_checks: bool = True', src['log_assembler.py']) is not None)
    check('and raises rather than warning',
          'raise UnitCheckFailed' in src['log_assembler.py'])
    check('check 3 is scoped to narrative body, not the whole payload',
          'body_lines' in src['unit_check.py']
          and 'reg.body_lines' in src['unit_check.py'])

    print('\n[DoD 3] 完整性檢查掛上（子集寬鬆判定＋佐證措辭）')
    check('subset test, extra headings allowed',
          'not in heading_set' in src['completeness_check.py'])
    check('evidence wordlist is the b §8 one',
          "EVIDENCE_TERMS = ('佐證', '行為事例', '工作樣本', '不以單次')"
          in src['completeness_check.py'])

    print('\n[DoD 4] 出口掃描掛上，per-request 動態縮小，紅隊殘留 0')
    check('scanner narrows per request',
          'injected_names' in src['exit_scanner.py'] and 'for_log' in src['exit_scanner.py'])
    check('red-team suite exists',
          (pathlib.Path(os.path.dirname(__file__)) / 'redteam_packer.py').exists())

    print('\n[DoD 5] 標頭 ID 必須保留在 payload')
    from api_v2.services.question_table import table
    from api_v2.services.log_assembler import Respondent, assemble
    q = table.get('如何面對困難、壓力、挑戰')
    log = assemble([Respondent('王', 'R1', {'CIA_05': 'B', 'CIA_01': 'A', 'CIA_33': 'A'})], q)
    text = log.to_log_text()
    check('trait headers keep their ID', '[特質 | CIA_05_B |' in text)
    check('index lines keep their ID', re.search(r'^- CIA_01_A｜', text, re.M) is not None)
    check('interaction headers keep both IDs',
          re.search(r'^\[交互 \| [A-Z]{3}_\d+_[ABC] × [A-Z]{3}_\d+_[ABC] \|', text, re.M)
          is not None)

    print('\n=== 常見誤區（00_外包交接說明 §五）===')

    print('\n[誤區 1] 匡列特質來自題庫表欄位，不是程式算的')
    check('S comes from scoped_traits', "get('scoped_traits')" in src['question_table.py'])
    check('whole-person/free-form use all of P',
          'is_whole_person' in src['trait_splitter.py'])

    print('\n[誤區 2] 風險／校準特質不升全塊區')
    check('the splitter never consults the endpoint registry',
          'endpoint_registry' not in exe['trait_splitter.py']
          and 'registry' not in exe['trait_splitter.py'])
    check('proven behaviourally by verify_trait_splitter / verify_calibration',
          (pathlib.Path(os.path.dirname(__file__)) / 'verify_calibration.py').exists())

    print('\n[誤區 3] 交互選列無題意截斷上限')
    caps = re.findall(r'\b(?:25|40|90)\b', exe['interaction_selector.py'])
    check('no 25/40/90 cap constants in the selector', not caps, caps)
    for word in ('覆蓋輪', '補充輪', 'coverage_round', 'supplement'):
        check(f'no {word} logic', word not in code_only)

    print('\n[誤區 4] 校準零工序：不另寫校準邏輯、不合成 meta 塊')
    check('no standalone calibration block is emitted',
          '[作答校準' not in code_only)
    check('calibration is data-driven, not a hard-coded list in the packer',
          'CIA_33' not in code_only, [m for m in exe if 'CIA_33' in exe[m]])

    print('\n[誤區 5] expected_sections 是唯一來源，不自行解析指令')
    check('the checker never reads instruction text',
          'instruction_single' not in exe['completeness_check.py']
          and 'instruction_multi' not in exe['completeness_check.py'])
    check('empty expected_sections is skipped AND logged',
          'SKIP_LOG' in src['completeness_check.py'])
    check('a miss is soft (one regeneration), not a hard block',
          'MAX_COMPLETION_ATTEMPTS = 1' in src['segment_gate.py'])

    print('\n[誤區 6] everyday 詞只擋構念式用法；白名單鍵是巢狀的')
    check('nested paths are used',
          "names.get('everyday_words')" in src['exit_scanner.py']
          and "labels.get('everyday_labels')" in src['exit_scanner.py'])
    check('an empty whitelist raises instead of hard-blocking everything',
          'came back empty' in src['exit_scanner.py'])

    print('\n[誤區 7] 組裝前必查 audience，不符即拒絕')
    check('check_audience runs before assembly', 'check_audience(respondents, question)'
          in src['log_assembler.py'])
    check('it raises', 'raise AudienceMismatch' in src['log_assembler.py'])
    check('the placeholder string is never packed',
          '僅適用單人' not in text and '僅適用多人' not in text)

    print('\n[誤區 8] 四欄「缺則補、有則不重複加」')
    check('prefix is conditional', 'text if text.startswith' in src['trait_blocks.py'])

    print('\n[誤區 9] construct_families_v1.json 僅供稽核，程式不需載入')
    check('no packer module references it', 'construct_families' not in code_only)
    check('no runtime family expansion', 'famil' not in code_only.lower())

    print('\n[誤區 10] 內容原文一字不改')
    check('four columns come from the verbatim cell text',
          "get('do_raw')" in src['trait_blocks.py'])
    check('narrative stripping is data-driven from regex_pack',
          'regex_pack' in src['narrative_cleaner.py'])
    check('narrative cleaner is body-only by contract',
          'body' in src['narrative_cleaner.py'].lower())

    print('\n=== 已知且已回報的偏離 ===')
    known = [
        ('乙-3', 'System 第 15 條採 a 文件版本（範例較舊）', 'verify_system_prompt 標示'),
        ('b §2', 'SPA 欄名前綴：依 b §2 補上，範例未補', 'verify_trait_blocks 標示'),
        ('乙-6', '佐證詞表依 b §8 字面，事項 11 舉例過不了', 'verify_calibration 標示'),
        ('客戶骨架', 'to_messages() 拆 system/user，骨架為單一字串', 'verify_log_assembler 斷言可重接'),
        ('b §1.1', 'audience 不符時 packer 讓路給既有路徑而非拒絕', 'packed_chat 註記，旗標關閉時無影響'),
    ]
    for tag, what, where in known:
        print(f'  [NOTE] {tag}: {what}  ({where})')

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

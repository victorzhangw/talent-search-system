"""每一份現行的 prompt 都必須帶著「輸出必須是繁體中文」這條硬性規定（E-17）。

用法：
    python scripts/verify_output_language.py

背景：2026-09-09 req `cf3dcd60`（「換成 行銷單位角度來看，會有什麼不同？」）的回答**整篇
是簡體字**——2791 字裡簡體 259、繁體 32，占 89%。全語料唯一一筆。

根因不是模型壞掉，是**整套 prompt 從頭到尾沒有一條規定字體**。`log_system_prompt.txt` 的
「乙、語言紀律」講的是措辭分寸（不得貼標、不得診斷、不得下品格判定），沒有一條講字體；
一直靠「輸入是繁體，模型就跟著寫繁體」——而 `deepseek-v4-flash` 是簡體語料為主的模型，
歷史一長就飄掉了。

這支腳本檢查的是**規定有沒有到位**，不是輸出有沒有遵守。後者要靠稽核的字體偵測，
還沒做（見 E-17）。提示層的規則本來就是盡力而為，把規則寫齊只是必要條件。

不打網路；[3] 會實際組一次 payload，所以需要 DB（特質區塊要查庫）。
"""

import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(HERE, '..', 'api_v2', '.env'), encoding='utf-8-sig')

PROMPTS = os.path.join(HERE, '..', 'api_v2', 'prompts')
CODE_DIRS = [os.path.join(HERE, '..', 'api_v2')]

# 「繁體中文」是最低要求；「台灣用語」是客戶自己在 modules/*.txt 用的說法。
RULE_RE = re.compile(r'繁體中文|正體中文')

failures = []
notes = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}"
          f"{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def prompt_files():
    for root, _, files in os.walk(PROMPTS):
        for f in sorted(files):
            if f.endswith('.txt'):
                yield os.path.join(root, f)


def code_text():
    out = []
    for d in CODE_DIRS:
        for root, _, files in os.walk(d):
            if '__pycache__' in root:
                continue
            for f in files:
                if f.endswith('.py'):
                    out.append(open(os.path.join(root, f), encoding='utf-8').read())
    return '\n'.join(out)


def main():
    code = code_text()
    files = list(prompt_files())

    print('\n[1] 現行的 prompt（被程式讀到的）都要有這條規定')
    live, dead = [], []
    for p in files:
        name = os.path.basename(p)
        # U7 之前 modules/ 底下的 40 份 prompt 是 `_route_by_module` 依 module_id 組出
        # 路徑載入的，檔名不會逐一出現在程式碼裡，所以整個目錄被視為現行。那條路徑與
        # 那些檔案都已移除，現在單純看檔名有沒有出現在程式碼裡就夠了。
        referenced = name in code
        (live if referenced else dead).append(p)

    check('至少找得到 log_system_prompt.txt', any(
        os.path.basename(p) == 'log_system_prompt.txt' for p in live))
    for p in live:
        text = open(p, encoding='utf-8').read()
        rel = os.path.relpath(p, PROMPTS).replace(os.sep, '/')
        check(f'{rel} 帶著繁體中文的規定', bool(RULE_RE.search(text)))

    print('\n[2] 沒有被任何程式讀到的 prompt（不列入要求，但要知道它們在）')
    for p in dead:
        rel = os.path.relpath(p, PROMPTS).replace(os.sep, '/')
        has = 'has rule' if RULE_RE.search(open(p, encoding='utf-8').read()) else 'no rule'
        print(f'  [NOTE] {rel} -- 沒有程式引用（{has}）')
    check('死檔案數量沒有暴增（超過 5 個就該清一清）', len(dead) <= 5, len(dead))

    print('\n[3] LOG 打包路徑：規則必須進到每一次呼叫')
    from api_v2.services.log_system_prompt import load_system_prompt  # noqa: E402
    from api_v2.services.log_assembler import Respondent, assemble  # noqa: E402
    from api_v2.services.question_table import table  # noqa: E402

    sys_text = load_system_prompt()
    check('system prompt 本身有第 21 條',
          bool(RULE_RE.search(sys_text)) and '21. ' in sys_text)
    check('明講是硬性規定', '硬性規定' in sys_text)

    one = [Respondent('甲', 'R1', {'CIA_01': 'A'})]
    two = one + [Respondent('乙', 'R2', {'CIA_01': 'B'})]
    q = table.get('如何面對困難、壓力、挑戰')
    for label, log in (('題庫題單人', assemble(one, q)),
                       ('題庫題多人', assemble(two, q)),
                       ('自由提問', assemble(one, None, user_query='他適合帶新人嗎？')),
                       ('追問輪', assemble(one, None, user_query='還有其他建議嗎',
                                          has_history=True))):
        check(f'{label} 的 payload 帶著規則', bool(RULE_RE.search(log.to_log_text())))
        # 改寫與補生成是另外的模型呼叫，但它們送的是 `messages`，第一則就是 system 區塊。
        check(f'{label} 的 system message 帶著規則',
              bool(RULE_RE.search(log.to_messages()[0]['content'])))

    print('\n[4] 改寫／補生成的追加呼叫也吃得到（它們沿用同一組 messages）')
    src = open(os.path.join(HERE, '..', 'api_v2', 'services', 'log_pipeline.py'),
               encoding='utf-8').read()
    check('_rewrite 送的是 self.messages + 這一段', 'self.messages + [' in src)
    check('_complete 送的也是 self.messages + 這一段',
          src.count('self.messages + [') >= 2, src.count('self.messages + ['))

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

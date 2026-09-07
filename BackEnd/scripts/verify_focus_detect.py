"""「使用者這輪在問名單上的誰」的判定（E-12 後續）。

用法：
    python scripts/verify_focus_detect.py

這支判定**只寫進稽核記錄**，不參與 missing_respondents 的計算、也不影響任何攔截。
所以這裡釘的是「它判得對不對」與「它沒有被接進判定」兩件事。

不打網路、不需要 DB。
"""

import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api_v2', '.env'),
            encoding='utf-8-sig')

from api_v2.services.focus_detect import (  # noqa: E402
    detect_focus, strict_forms, names_in, SOURCE_NAMED, SOURCE_INHERITED,
    SOURCE_EXCLUDED, SOURCE_NONE)
from api_v2.services.log_assembler import Respondent  # noqa: E402

failures = []

ROSTER = ['林慧嵐', '吳美慧', '吳詩瑩', '劉碧雯', '張姵荀']
HIST_NAMED_ONE = [{'role': 'user', 'content': '請只針對 林慧嵐 說明他的溝通風格。'},
                  {'role': 'assistant', 'content': '（回答）'}]
HIST_NAMED_TWO = [{'role': 'user', 'content': '請比較 林慧嵐 與 劉碧雯 的差異。'},
                  {'role': 'assistant', 'content': '（回答）'}]


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}"
          f"{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def verdict(query, history=None, roster=None, respondents=None):
    return detect_focus(query, roster or ROSTER, history=history, respondents=respondents)


def main():
    print('\n[1] 點名')
    v = verdict('請只針對 林慧嵐 說明他的溝通風格，以及需要留意的風險。')
    check('點一位 -> named', v['source'] == SOURCE_NAMED and v['names'] == ['林慧嵐'], v)
    v = verdict('請比較 劉碧雯 與 張姵荀 在團隊合作上的差異。')
    check('點兩位 -> 兩位都收', v['names'] == ['劉碧雯', '張姵荀'], v)
    v = verdict('那 劉碧雯 呢？同樣的角度說明。')
    check('換人問也算點名', v['source'] == SOURCE_NAMED and v['names'] == ['劉碧雯'], v)

    print('\n[2] 沒點名 -> 不縮小')
    for q in ('個別適合什麼崗位', '誰比較適合從事市場行銷規劃', '排序',
              '這兩位會不會與同事起衝突？'):
        v = verdict(q)
        check(f'「{q}」-> none', v['source'] == SOURCE_NONE and not v['names'], v)

    print('\n[3] 排除語 -> 不縮小（不做反向運算）')
    for q in ('除了 林慧嵐 之外，其他人呢？', '林慧嵐 以外的人呢', '不含 劉碧雯 的話呢'):
        v = verdict(q)
        check(f'「{q}」-> excluded 且不縮小',
              v['source'] == SOURCE_EXCLUDED and v['names'] == [], v)
    # 這是關鍵：不加排除語偵測的話，下面這句會把範圍縮成「使用者明講不要的那位」。
    v = verdict('除了 林慧嵐 之外，其他人呢？')
    check('排除語壓過點名（不會縮成被排除的那位）', '林慧嵐' not in v['names'], v)

    print('\n[4] 追問繼承（無狀態：從歷史重跑同一支判定）')
    v = verdict('他在壓力之下的表現如何？請再補充一點。', HIST_NAMED_ONE)
    check('不點名的追問 -> 繼承上一輪的焦點',
          v['source'] == SOURCE_INHERITED and v['names'] == ['林慧嵐'], v)
    v = verdict('他在壓力之下的表現如何？')
    check('沒有歷史就沒得繼承 -> none', v['source'] == SOURCE_NONE, v)

    print('\n[5] 數量相容：複數指涉 vs 單人焦點')
    v = verdict('他們兩個誰比較適合？', HIST_NAMED_ONE)
    check('繼承來的只有一位、本輪說「他們兩個」-> 不繼承並記下矛盾',
          v['source'] == SOURCE_NONE and v['conflict'] is True, v)
    v = verdict('這幾位的溝通風格差異？', HIST_NAMED_ONE)
    check('泛稱同樣不繼承', v['source'] == SOURCE_NONE and not v['names'], v)
    v = verdict('他們兩個誰比較適合？', HIST_NAMED_TWO)
    check('繼承來的是兩位、本輪說「他們兩個」-> 數量相容，繼承',
          v['source'] == SOURCE_INHERITED and v['names'] == ['林慧嵐', '劉碧雯'], v)

    print('\n[6] 名單變動自動重設焦點（不必另外寫一條規則）')
    other = ['吳美慧', '吳詩瑩', '劉碧雯']          # 林慧嵐 已不在名單上
    v = verdict('他在壓力之下的表現如何？', HIST_NAMED_ONE, roster=other)
    check('上一輪點的人已不在名單 -> 比不中，退回 none',
          v['source'] == SOURCE_NONE and not v['names'], v)

    print('\n[7] 姓名比對比生產版嚴格（掃提問時代價方向相反）')
    check('`呂 佳珍教育訓練課` 收得到乾淨寫法 `呂佳珍`', '呂佳珍' in strict_forms('呂 佳珍教育訓練課'))
    check('但不收兩字截斷形 `呂佳`（它會命中「呂佳玲」）',
          '呂佳' not in strict_forms('呂 佳珍教育訓練課'), strict_forms('呂 佳珍教育訓練課'))
    check('「呂佳玲也可以嗎」不會誤中呂佳珍',
          names_in('呂佳玲也可以嗎', ['呂 佳珍教育訓練課']) == [],
          names_in('呂佳玲也可以嗎', ['呂 佳珍教育訓練課']))
    check('英文名取 first name（Howard）',
          names_in('Howard 的溝通風格如何', ['Howard Hsu']) == ['Howard Hsu'])
    check('兩字母縮寫太短，不收', strict_forms('GT Wang') == ['GT Wang', 'GTWang'],
          strict_forms('GT Wang'))

    print('\n[8] 自稱豁免：提問者本人不是被問的對象')
    vic = [Respondent('Victoria', 'R1', {'CIA_05': 'B'}),
           Respondent('梁婉婷', 'R2', {'CIA_05': 'B'})]
    v = verdict('我是 Victoria，我想了解 梁婉婷 的溝通風格。',
                roster=['Victoria', '梁婉婷'], respondents=vic)
    check('「我是 Victoria」-> 焦點只有梁婉婷',
          v['names'] == ['梁婉婷'], v)

    print('\n[9] 邊界')
    check('空名單 -> none', verdict('隨便問', roster=[])['source'] == SOURCE_NONE)
    check('空提問 -> none', verdict('', roster=ROSTER)['source'] == SOURCE_NONE)

    print('\n[10] 只記錄，沒有被接進判定')
    services = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                            'api_v2', 'services')
    comp = open(os.path.join(services, 'completeness_check.py'), encoding='utf-8').read()
    check('completeness_check 沒有引用 focus_detect（判定不受影響）',
          'focus_detect' not in comp)
    packed = open(os.path.join(services, 'packed_chat.py'), encoding='utf-8').read()
    check('focus 只寫進稽核欄位', "audit['focus']" in packed)
    m = re.search(r'if question is None:\s*\n\s*try:\s*\n\s*focus = detect_focus', packed)
    check('只在自由提問算（題庫題的提問是模組指令，判「問誰」沒有意義）', bool(m))

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

"""Boundary checks for services/title_zh.py -- the Traditional-Chinese safety net.

The regression this guards is the 2026-08-24 client report: history titles came back with
respondents' names misspelled (游 -> 遊) because `OpenCC('s2twp')` ran on every title,
including the ones that were already correct Traditional Chinese.

So the load-bearing assertion here is the boring one: correct Traditional text must come
out byte-identical. The conversion branch is checked too, but it is the rarer path -- it
only exists for the titles that really do come back Simplified.

Needs opencc installed (it is in api_v2/requirements.txt); no DB and no model.
"""

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import api_v2.services.title_zh as tz  # noqa: E402
from api_v2.services.title_zh import (  # noqa: E402
    MIAN_FOOD_WORDS, contains_simplified, fix_known_misconversions, normalize_title,
    restore_names, simplified_only_chars)

failures = []


class convert_enabled:
    """Force tz.CONVERT_ENABLED for a block, whatever .env says on this machine.

    Both states have to be verified here regardless of local configuration: the default
    (off) is what ships, and the on path is the one a future TITLE_OPENCC_ENABLED=1 would
    take, so neither may go unchecked just because .env happens to pick the other.
    """

    def __init__(self, value):
        self.value = value

    def __enter__(self):
        self.saved = tz.CONVERT_ENABLED
        tz.CONVERT_ENABLED = self.value

    def __exit__(self, *exc):
        tz.CONVERT_ENABLED = self.saved


def check(label, ok, detail=''):
    print(f"  [{'OK' if ok else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not ok:
        failures.append(label)


# The exact strings s2twp corrupted, measured against the shipped dictionaries. Every one
# of these is correct Traditional Chinese and must survive untouched.
CORRUPTED_BY_S2TWP = [
    ('游淑芬的領導風格分析', '游'),
    ('余明哲：抗壓性與情緒穩定度', '余'),
    ('范姜偉：跨部門協作模式', '范'),
    ('台北團隊的溝通落差', '台'),
    ('主管干預時機評估', '干'),
    ('公布考核結果的方式', '公布'),
    ('了解他的學習節奏', '了解'),
    ('采訪紀錄摘要', '采'),
    ('會議布置與角色分工', '布置'),
]

# Names as the DB spells them, including the three surnames the bug hit.
NAMES = ['游淑芬', '余明哲', '范姜偉', '林孟德']


def main():
    print('[1] 簡體偵測：兩用字與正確繁體不可誤判')
    chars = simplified_only_chars()
    check('字典載入成功（非空集合）', len(chars) > 3000, f'{len(chars)} chars')
    for ch in '游余范面台干布公了采後臺髮乾著鍾沈周週制姜向注制':
        check(f'「{ch}」不算簡體', ch not in chars)
    for ch in '对习汉简这说时会个还应该实际风险团队领导评让为业':
        check(f'「{ch}」算簡體', ch in chars)

    print('\n[2] 正確繁體標題必須原樣返回（本次客訴的核心，兩種開關都要成立）')
    for enabled in (False, True):
        with convert_enabled(enabled):
            state = 'CC 關' if not enabled else 'CC 開'
            for text, why in CORRUPTED_BY_S2TWP:
                check(f'[{state}] {text}（舊版會改壞「{why}」）',
                      normalize_title(text, NAMES) == text, normalize_title(text, NAMES))
    check('不含簡體字時 contains_simplified 為 False',
          not any(contains_simplified(t) for t, _ in CORRUPTED_BY_S2TWP))

    print('\n[3] TITLE_OPENCC_ENABLED=1 時，真的是簡體才轉換')
    with convert_enabled(True):
        check('偵測得到簡體', contains_simplified('游淑芬的沟通风格与团队协作'))
        check('簡體標題會被轉為繁體',
              normalize_title('沟通风格与团队协作评估', NAMES) == '溝通風格與團隊協作評估',
              normalize_title('沟通风格与团队协作评估', NAMES))
        check('轉換後姓名仍是資料庫的寫法（游不會變遊）',
              normalize_title('游淑芬的沟通风格评估', NAMES) == '游淑芬的溝通風格評估',
              normalize_title('游淑芬的沟通风格评估', NAMES))
        check('余、范同樣不被改寫',
              normalize_title('余明哲与范姜伟的协作模式', NAMES) == '余明哲與范姜偉的協作模式',
              normalize_title('余明哲与范姜伟的协作模式', NAMES))
        check('候選人名單為空時仍完成轉換',
              normalize_title('团队沟通评估', None) == '團隊溝通評估',
              normalize_title('团队沟通评估', None))
        check('姓名本身是簡體時，轉換是我們要的',
              normalize_title('张伟的抗压性', ['張偉']) == '張偉的抗壓性',
              normalize_title('张伟的抗压性', ['張偉']))

    print('\n[3b] 預設（TITLE_OPENCC_ENABLED=0）完全不做簡繁轉換')
    check('預設值就是關閉', tz.CONVERT_ENABLED is False, tz.CONVERT_ENABLED)
    with convert_enabled(False):
        check('簡體標題原樣保留（交給 prompt 約束，不再轉譯）',
              normalize_title('沟通风格与团队协作评估', NAMES) == '沟通风格与团队协作评估',
              normalize_title('沟通风格与团队协作评估', NAMES))
        check('關閉時 麵 -> 面 仍然生效（那不是簡繁轉換）',
              normalize_title('如何麵對壓力', NAMES) == '如何面對壓力',
              normalize_title('如何麵對壓力', NAMES))

    print('\n[4] restore_names：長名優先，避免半截替換')
    check('較長的名字先還原',
          restore_names('遊淑芬與遊淑', ['游淑芬', '游淑']) == '游淑芬與游淑',
          restore_names('遊淑芬與遊淑', ['游淑芬', '游淑']))
    check('沒被改到的名字不動', restore_names('林孟德分析', NAMES) == '林孟德分析')
    check('None / 空字串安全', restore_names('abc', None) == 'abc'
          and restore_names('abc', ['', None]) == 'abc')

    print('\n[5] 模型自己的誤字：麵 -> 面')
    check('麵對 -> 面對', fix_known_misconversions('如何麵對壓力') == '如何面對壓力',
          fix_known_misconversions('如何麵對壓力'))
    check('麵試 -> 面試', fix_known_misconversions('麵試表現評估') == '面試表現評估')
    check('方麵 -> 方面', fix_known_misconversions('管理方麵的建議') == '管理方面的建議')
    check('normalize_title 同樣會修（且不需要有簡體字）',
          normalize_title('游淑芬：如何麵對衝突', NAMES) == '游淑芬：如何面對衝突',
          normalize_title('游淑芬：如何麵對衝突', NAMES))
    check('麵食詞彙不被誤改',
          all(fix_known_misconversions(w) == w for w in MIAN_FOOD_WORDS),
          [w for w in MIAN_FOOD_WORDS if fix_known_misconversions(w) != w])
    check('正確的「面」不受影響',
          fix_known_misconversions('面對面談的正面評價') == '面對面談的正面評價')

    print('\n[6] 邊界輸入')
    check('None -> 空字串', normalize_title(None, NAMES) == '')
    check('空字串 -> 空字串', normalize_title('', NAMES) == '')
    check('純英數不動', normalize_title('KPI Q3 review', NAMES) == 'KPI Q3 review')
    check('標點與全形符號不動',
          normalize_title('林孟德：高潛人才識別要點', NAMES) == '林孟德：高潛人才識別要點')

    print('\n[7] 字典讀不到時安全降級（不轉換，不丟例外）')
    saved_cache, saved_loader = tz._simplified_only, tz._load_simplified_only
    tz._simplified_only = None
    tz._load_simplified_only = lambda: (_ for _ in ()).throw(IOError('simulated'))
    try:
        check('降級後不再偵測到簡體', not contains_simplified('沟通'))
        check('降級後繁體標題仍原樣', normalize_title('游淑芬的領導風格分析', NAMES)
              == '游淑芬的領導風格分析')
        check('降級後仍會修 麵 -> 面', normalize_title('如何麵對壓力', NAMES) == '如何面對壓力')
    finally:
        tz._simplified_only, tz._load_simplified_only = saved_cache, saved_loader

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

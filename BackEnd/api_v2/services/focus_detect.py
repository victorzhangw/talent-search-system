"""使用者這一輪在問名單上的誰——**只記錄，不參與任何判定**。

為什麼要有這個檔（E-12）：覆蓋率檢查假設「每一則自由提問都是在問整個名單」。
使用者一旦點名「請只針對 X 說明」，模型正確地只寫 X，檢查卻判定漏了其他人，補生成
就把沒問的人硬接在後面。E-12 已經把自由提問的「漏人」降級成只記錄，傷害沒了；要恢復
自動補生成，前提是檢查先看得懂「這輪只問了誰」。

這一版**刻意只寫進稽核記錄**（`focus` 欄位），不碰 `missing_respondents` 的計算、
也不影響任何攔截。理由是代價方向：目前 `missing` 只用於觀察，判太寬只是稽核多一筆
噪音，判太窄會讓真漏人被靜默吸收——而漏人正是整個修正計畫的起點（43c1f019）。
所以先把判定跑起來、累積可標註的樣本，準確率夠了再談要不要接進判定。

**無狀態**：焦點繼承不靠跨請求的狀態，而是把同樣的偵測跑在歷史裡最近一則使用者訊息上。
好處有二——離線可以拿舊 log 完整重放；名單一變動，前一輪點名的人若已不在名單裡就自然
比不中，等於「名單變動就重設焦點」不必另外寫一條規則。

判定順序與理由：

    1. 有排除語（「除了 X 之外」）-> 不縮小。
       排除語的正確語義是 `名單 - {X}`，而點名偵測會把它縮成 `{X}`，正好相反。
       反向運算樣本太少、寫錯的代價又跟 E-12 同型，所以保守退回整個名單。
    2. 提問裡點到名 -> 就是那幾位（扣掉自稱者）。
    3. 沒點名 -> 從歷史繼承最近一次的點名，但要**數量相容**：
       本輪用複數指涉（「他們兩個」）而繼承來的焦點只有一位，是矛盾，退回整個名單。
    4. 其餘 -> 不縮小。

第 3 條的數量相容是有必要的：聚焦一位之後問「他在壓力下如何」該繼承，問「他們兩個誰
比較適合」不該繼承——兩者都沒有姓名，差別只在指涉的數量。
"""

import re
from typing import List, Optional

from .completeness_check import self_introduced_names

_WS = re.compile(r'\s+')
_ORG_SUFFIX = re.compile(r'[-－]')
_CJK = re.compile(r'^[一-鿿]+$')

# 出現任何一個就不縮小。寧可漏掉縮小的機會，也不要縮到使用者明講不要的那位身上。
EXCLUSION_MARKERS = ('除了', '除外', '以外', '不含', '不包括', '不用看', '其餘', '其他人')

# 複數指涉。用來檢查「繼承來的焦點」數量對不對得上；順序無關，只看有沒有出現。
PLURAL_MARKERS = ('他們', '她們', '這幾位', '那幾位', '這些人', '各位', '大家',
                  '全部', '所有人', '每一位', '每位', '兩位', '兩個', '三位', '三個',
                  '這兩位', '這兩個')

SOURCE_NAMED = 'named'
SOURCE_INHERITED = 'inherited'
SOURCE_EXCLUDED = 'excluded'
SOURCE_NONE = 'none'


def strict_forms(name: str) -> List[str]:
    """比 `completeness_check.name_forms` 嚴格的姓名寫法。

    那一支刻意偏寬，因為它問的是「回答裡有沒有寫到這個人」——判成沒寫到的代價（在完整
    回答尾巴硬接一段）比較大，所以寧可多命中。

    拿來掃**提問**時代價方向是反的：誤中一個名字就把範圍縮到錯的人身上，真正該被檢查的
    那位反而不再被檢查。所以這裡砍掉兩字的截斷形——`呂 佳珍教育訓練課` 會產生 `呂佳珍`
    （保留，使用者真的會這樣打）與 `呂佳`（丟掉，它會命中「呂佳玲」）。
    """
    raw = (name or '').strip()
    if not raw:
        return []
    forms = {raw}
    head = _ORG_SUFFIX.split(raw)[0].strip()
    forms.add(head)
    forms |= {_WS.sub('', f) for f in tuple(forms)}

    parts = head.split()
    if len(parts) >= 2:
        first, rest = parts[0], ''.join(parts[1:])
        if _CJK.match(first):
            if len(rest) >= 2:
                forms.add(first + rest[:2])
        elif len(first) >= 3:
            forms.add(first)
    return sorted({f for f in forms if len(f) >= 3}, key=len, reverse=True)


def names_in(text: Optional[str], roster_names) -> List[str]:
    """名單裡有哪些人的姓名出現在這段文字中。順序照名單，不照出現順序。"""
    flat = _WS.sub('', text or '')
    if not flat:
        return []
    return [n for n in roster_names
            if any(_WS.sub('', f) in flat for f in strict_forms(n))]


def has_exclusion(text: Optional[str]) -> bool:
    return any(m in (text or '') for m in EXCLUSION_MARKERS)


def has_plural(text: Optional[str]) -> bool:
    return any(m in (text or '') for m in PLURAL_MARKERS)


def detect_focus(user_query: Optional[str], roster_names, history=None,
                 respondents=None) -> dict:
    """回一筆可以直接塞進稽核記錄的判定。

    `respondents` 只用來算自稱豁免（「我是 Victoria」——她是提問者，不是被問的對象）；
    傳 None 就跳過那一步。
    """
    roster_names = [n for n in (roster_names or []) if n]
    verdict = {'names': [], 'source': SOURCE_NONE, 'conflict': False}
    if not roster_names:
        return verdict

    if has_exclusion(user_query):
        verdict['source'] = SOURCE_EXCLUDED
        return verdict

    exempt = set()
    if respondents:
        exempt = set(self_introduced_names(user_query, respondents))

    named = [n for n in names_in(user_query, roster_names) if n not in exempt]
    if named:
        return {'names': named, 'source': SOURCE_NAMED, 'conflict': False}

    # 沒點名：往回找最近一則有點到名的使用者訊息。歷史是舊到新，所以反著走。
    for msg in reversed(list(history or [])):
        if (msg or {}).get('role') != 'user':
            continue
        prior = names_in(msg.get('content'), roster_names)
        if not prior:
            continue
        if has_plural(user_query) and len(prior) == 1:
            # 「他們兩個誰比較適合」而繼承來的只有一位——矛盾，不繼承。
            return {'names': [], 'source': SOURCE_NONE, 'conflict': True}
        return {'names': prior, 'source': SOURCE_INHERITED, 'conflict': False}

    return verdict

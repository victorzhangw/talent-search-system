"""受測者姓名的顯示形態（a §4 / b §8）。

廠商姓名欄帶著格式雜訊：姓與名之間一個半形空白，後面直接黏上單位——
`邱 佳玲-聯醫`、`呂 佳珍教育訓練課`、`蘇 緯弘`、`Howard Hsu`。

而 a §4 要求模型「一律以真實姓名稱呼，不得附加企業、職位或身分前綴」，模型也確實
照做：0916 的正式環境語料裡，乾淨姓名出現 36 次（呂佳珍 15、蘇緯弘 10、邱佳玲 9、
簡玥瀅 2），單位字樣（聯醫／教育訓練課／一站式服務／高雄非專）出現 **0 次**。

於是 b §8 的「每位受測者姓名皆出現」如果照字面比對，對帶後綴的人必然 100% 判缺。
`completeness_check.name_forms()` 早就用多種寫法容錯擋住了這件事，但那條規則只活在
程式碼裡——b 文件仍寫「姓名皆出現」，任何依文件重寫的實作都會回歸。

這裡把正規化提前到打包入口：**payload 裡的姓名，就是模型會寫出來的那個字串**。
`name_forms()` 的容錯保留不動，那是第二道防線，不是被取代。

刻意不做的事
------------
**不還原「黏接式單位」**（`呂 佳珍教育訓練課`），原樣送出。

這件事無法確定性判斷：看到那個字串，無從得知名字是「佳」「佳珍」還是「佳珍教」。
`name_forms()` 現有的「取名的前 2 字」是**比對用**的啟發式——它一次產生多種寫法，
多給幾種的代價只是判定寬鬆一點。拿同一招來決定**顯示**姓名則完全不同：四字名
（`歐陽 建志豪`）會被截成 `歐陽建志`，等於系統主動把人名寫錯，再要求模型照著錯的
名字稱呼人。那比現在的誤判嚴重得多。

所以分工是：顯示只做可逆、無歧義的處理（分隔符後綴、內部空白）；黏接式單位交給
比對層吸收。根治在資料源頭——請廠商統一姓名欄格式。
"""

import re
from typing import List

# 單位後綴的分隔符。全形半形都收。
_SEPARATORS = '-－/／_（(【['
_SEP_RE = re.compile('[' + re.escape(_SEPARATORS) + ']')
_WHITESPACE_RE = re.compile(r'\s+')
_ASCII_ALPHA_RE = re.compile(r'[A-Za-z]')

MIN_DISPLAY_LEN = 2
# 「姓 名」的名最多幾個字。`歐陽 建志豪` 的 3 字要收，`佳珍教育訓練課` 的 7 字要排除。
MAX_GIVEN_NAME_LEN = 3


def display_name(raw: str) -> str:
    """送進 payload 的姓名。冪等：`display_name(display_name(x)) == display_name(x)`。

    剝除單位後綴**要有正面證據**，不用長度啟發式。證據是分隔符前面那個「姓 名」空白：
    廠商送來的每一筆帶後綴的姓名都有它（`邱 佳玲-聯醫`、`柳 宇賸-人資發展課`、
    `陳 冠享-一站式服務`、`簡 玥瀅-高雄非專`、`游 雅鳳-FDA`），而假想中的前綴式寫法
    `聯醫-邱佳玲` 沒有。

    一開始寫的是「被剝掉的比留下的長就退回」這種長度規則，結果 `柳 宇賸-人資發展課`
    （名 3 字、單位 5 字）被判成前綴式而整串退回——為了防一個資料裡不存在的假想情況，
    弄壞了四筆真實資料中的一筆。要正面證據就不會有這種事：沒有證據就原樣送出，而原樣
    送出是安全的，`name_forms()` 仍然比得到。
    """
    if not raw:
        return raw
    name = raw.strip()
    if not name:
        return raw

    m = _SEP_RE.search(name)
    if m:
        head = name[:m.start()]
        # head 帶 ASCII 字母 -> 可能是 `Anne-Marie Chen` 這種連字號姓名，不是單位後綴。
        if _ASCII_ALPHA_RE.search(head):
            return name
        # 沒有「姓 名」空白就沒有證據，原樣送出（`聯醫-邱佳玲` 走這條）。
        if not _WHITESPACE_RE.search(head):
            return name
        head_clean = _WHITESPACE_RE.sub('', head)
        if len(head_clean) < MIN_DISPLAY_LEN:
            return name
        return head_clean

    # 沒有分隔符。含 ASCII 字母的整串不動（`Howard Hsu`）。
    if _ASCII_ALPHA_RE.search(name):
        return name

    # 只有在「空白後面短到像是名字本身」時才去空白。
    #
    # 這一條是被實測逼出來的。原本寫的是無條件去空白，結果 `呂 佳珍教育訓練課` 變成
    # `呂佳珍教育訓練課`——單位還在（沒有分隔符可剝），卻順手把 `name_forms()` 用來
    # 還原 `呂佳珍` 的那個「姓 名」分界毀掉了，於是模型明明寫了「呂佳珍」卻被判成漏人。
    # 去空白對這種字串一點好處也沒有（拿掉之後仍然不是模型會寫的那個名字），代價卻是
    # 破壞第二道防線。
    parts = name.split()
    if len(parts) == 2 and len(parts[1]) <= MAX_GIVEN_NAME_LEN:
        return ''.join(parts)
    return name


def resolve_roster_names(respondents) -> bool:
    """整份名單的碰撞守門。有碰撞就把**全體**還原成廠商原字串，回傳是否碰撞過。

    `王 小明-北區` 與 `王 小明-南區` 正規化後會變成同一個 `王小明`。兩個人被併成一個，
    §8 的漏人檢查會永遠判「都寫到了」——比現在的誤判危險得多，因為它是靜默的。

    全體退回而不是只退碰撞的那兩位：名單裡一半乾淨一半帶單位，讀起來更像是系統把
    某些人的單位挑出來寫，反而不一致。

    判斷基準是 `display_name(raw_name)`，不是當下的 `name`。差別在重跑：拿 `name` 判的
    話，第一次退回原字串之後，第二次就不再撞名、旗標翻回 False，而名字其實還是原字串
    ——稽核會記到一個與事實相反的值。以 `raw_name` 為基準，旗標與狀態都冪等。
    """
    seen = {}
    for r in respondents:
        raw = getattr(r, 'raw_name', None) or getattr(r, 'name', None)
        if raw is None:
            continue
        seen.setdefault(display_name(raw), []).append(r)

    collided = any(len(v) > 1 for v in seen.values())
    if collided:
        for r in respondents:
            raw = getattr(r, 'raw_name', None)
            if raw:
                r.name = raw
    return collided


def name_variants(raw: str) -> List[str]:
    """顯示形態與原字串，去重後長的排前面。供出口掃描綁定識別碼時兩種寫法都收。"""
    out = []
    for n in (raw, display_name(raw)):
        if n and n not in out:
            out.append(n)
    return sorted(out, key=len, reverse=True)

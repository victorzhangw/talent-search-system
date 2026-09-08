"""量「這一輪的回答有多少是把上一輪重寫一遍」（E-16）。

**只記錄，不參與任何判定**。放進稽核的 `repeat` 欄位，理由與 `focus_detect` 相同：
要證明修改有沒有用，得先有一個修改前後可以直接比的數字，而這個數字必須由生產路徑
自己產出——離線另寫一份量出來的東西不代表線上行為。

背景（E-16）：2026-09-08 18:12→18:13 同一個 session，使用者問「還有其他建議嗎」，
拿到的回答第一行就是上一輪的標題，1838 字裡有 1209 字（72%）與上一輪相同，真正新增
的段落從第 1307 字才開始。標點從半形變全形，所以是模型重新生成了一次，不是串接錯誤
——payload、閘門、補生成全都正常。

全語料 61 個追問輪的基線：4 筆（6.6%）重複率 ≥ 40%，最嚴重的一筆是 6042 字有 80%
是重讀。形狀一致，都是短的、指涉前一輪的追問（換人／再一次／還有／除了…之外）。

為什麼比對「上一輪」而不是「全部歷史」：觀察到的形狀是**接續前一輪**，而拿全部歷史
去比會把「這個 session 一直在談同一批人」的正常重複也算進去——同一份特質資料寫出來
的句子本來就會像。比對範圍窄一點，數字才指向我們要修的那件事。
"""

import difflib
import re
from typing import List, Optional

# 標點不算內容差異：E-16 那一筆的重寫版把半形逗號換成了全形（「整合資源,推動」→
# 「整合資源，推動」），逐字比對會因此把 72% 的重複算成 0%。
_NOISE_RE = re.compile(r'[\s,，.。;；:：、！？!?~～]+')

# 太短的回答比出來的比例沒有意義（一句「好的」跟另一句「好的」是 100%）。
MIN_CHARS = 200
# SequenceMatcher 是 O(n*m)，而這支在 finish() 跑、不在串流的熱路徑上。上限只是別讓
# 極端長的回答把一次請求的收尾拖住；語料裡最長的回答是 8886 字。
MAX_CHARS = 20000


def normalize(text: str) -> str:
    return _NOISE_RE.sub('', text or '')


def previous_answer(history: Optional[List[dict]]) -> Optional[str]:
    """歷史裡最後一則 assistant 訊息，也就是使用者上一輪讀到的東西。"""
    for msg in reversed(history or []):
        if msg.get('role') == 'assistant' and (msg.get('content') or '').strip():
            return msg['content']
    return None


def measure(answer: str, history: Optional[List[dict]]) -> dict:
    """本輪回答與上一輪的重複程度。沒有前一輪、或任一邊太短就回 `{}`。

    `ratio` 是「本輪有多少比例是上一輪就給過的」，分母是本輪——所以一篇把前文重寫一遍
    再多加兩段的回答，比例會落在 0.5-0.8，而一篇只回答新問題的回答會很低。

    `longest_run` 是**最長的一段逐字重複**有多少字。它跟 `ratio` 分辨的是兩件不同的事：

      * 大 ratio + 大 longest_run ＝ 真的把前一輪整段搬過來（`e4147c25` 0.80/2654、
        `c4f3f3b3` 0.72/369）。
      * 大 ratio + 小 longest_run ＝ 順著同樣的次序、逐句改寫（`896b2143`「再一次排序」
        0.68/69、`ffe409c4`「除了 X 之外，其他人呢」0.52/31）。同一份特質資料寫出來的
        句子本來就會像，這一類不見得是缺陷。

    共同片段是**保序**的（`SequenceMatcher` 找的是最長共同子序列，不是集合交集），所以
    量到高 ratio 代表「順著同樣的次序重講一遍」，而不只是「用了同一批詞」。

    只看 ratio 會把這兩類混在一起，而 E-16 要修的是前者。
    """
    prev = previous_answer(history)
    if not prev or not answer:
        return {}
    a, b = normalize(prev), normalize(answer)
    if len(b) < MIN_CHARS or len(a) < MIN_CHARS:
        return {}
    if len(a) > MAX_CHARS or len(b) > MAX_CHARS:
        return {'skipped': 'too_long', 'prev_chars': len(a), 'chars': len(b)}

    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    blocks = [bl for bl in matcher.get_matching_blocks() if bl.size]
    same = sum(bl.size for bl in blocks)
    return {
        'ratio': round(same / len(b), 3),
        'longest_run': max((bl.size for bl in blocks), default=0),
        'prev_chars': len(a),
        'chars': len(b),
    }

"""Output completeness checks on the answer (事項 10 / 13, b §8).

    題庫題    every expected section heading is present (subset test -- extra headings
              are fine). Length is not checked.
    自由提問  answer stays within 1,000 characters.
    共同      a multi-person answer needs a heading per respondent, minus anyone the
              current question introduces in the first person (see
              `self_introduced_names`).
    共同      if a respondent scores A on 社會期望反應, the answer has to carry evidence
              wording (佐證 / 行為事例 / 工作樣本 / 不以單次).

Accumulated incrementally: observe() is fed each segment as it is cleared for display and
finalize() judges once the answer is complete. Under the segment-gated streaming design a
verdict cannot be reached mid-answer -- a heading that is "missing" at segment 3 may
simply not have been written yet.

Two things this deliberately does NOT do:

  * It never parses the instruction text to derive sections. b §8 makes
    `expected_sections` the single source, because deriving them is a semantic act.
  * A plain `sec in answer` test is not enough. The acceptance table requires
    「以下提供主管使用提醒」 in running text to FAIL while 「4. 主管使用提醒」 and
    「四、主管使用提醒：」 pass, so matching is done per line against a normalized heading,
    not against the whole answer.

`expected_sections` is best-effort data ("第X部分型可靠；巢狀編號型可能不全"), which is why
a miss is a soft failure feeding one regeneration rather than a hard block.
"""

import re
from typing import Dict, List, Optional

# b §8 evidence wordlist.
EVIDENCE_TERMS = ('佐證', '行為事例', '工作樣本', '不以單次')
# b §8 的自由提問字數上限。**只記錄，不判失敗**（U10）。
#
# 它從來沒有可行動的意義：超字屬於「補生成修不了」的失敗（append 只會更長，見
# appendable_reason()），所以它唯一的效果就是把 status 打成 manual_review。而實測上
# 幾乎每一筆真實回答都超過——全語料 75 筆自由提問 64 筆超過（85%，中位數 1489、
# 最長 7559）；2026-09-09 的 prd UAT 14 筆全部超過（最短 1022），其中 11 筆缺段、
# 漏人、佐證全部乾淨，唯一病因就是字數。結果是 manual_review 對自由提問永遠亮著，
# 真正需要人看的缺段與佐證問題反而被淹沒。
#
# 規格值本身保留，並改以 `free_form_length_check` 記進稽核（passed / over_limit），
# 所以「b §8 的字數檢查」仍然每一筆都查得到，只是不再影響 status。
FREE_FORM_MAX_CHARS = 1000

SKIP_LOG = '本題未做段落齊全檢查（原因：指令未定義固定段落標題）'
UNSPLIT_LOG = '本題 expected_sections 尚未拆分 single/multi，退回使用單一欄位'
# 「刻意留空」與「資料沒填」原本走同一條路徑、log 同一句話，於是 Q2／Q6／Q11 這種
# 「指令明明有編號段落、只是沒人填進資料」的情況，會被讀成「本題指令未定義固定段落
# 標題」——一個與事實相反的理由。區分依據是 `expected_sections_note`：有 note 表示
# 內容方確認過這題沒有固定段落（Q14／Q15／Q22），沒有 note 而為空就是資料缺口。
DATA_GAP_LOG = '本題 expected_sections 未填，段落齊全檢查未執行（資料缺口，非指令特性）'

# Leading ordinal/bullet/markdown noise that a heading may carry.
_HEADING_PREFIX_RE = re.compile(
    r'^[#>\s]*'
    r'(?:第\s*[0-9一二三四五六七八九十]+\s*(?:部分|節|章|段)?\s*[、,，.．:：]?\s*)?'
    r'(?:[0-9]+|[一二三四五六七八九十]+)?\s*[、,，.．)）:：\]】\-–—*•]*\s*'
)
_HEADING_SUFFIX_RE = re.compile(r'[\s:：。]*$')
_BOLD_RE = re.compile(r'\*\*|__')
# Separates a heading from the text that shares its line. See `heading_candidates`.
_COLON_SPLIT_RE = re.compile(r'[:：]')
# 斜線兩側的空白與全形／半形差異不是段落名的一部分。指令裡寫的是
# 「4. 同組織 / 專案角色分配建議」與「管理 Do / Don't」，模型輸出常見的是全形無空格的
# 「同組織／專案角色分配建議」——不收斂的話，這種條目就跟「（2項）」一樣永遠不會命中。
_SLASH_RE = re.compile(r'\s*[/／]\s*')
_WHITESPACE_RE = re.compile(r'\s+')
# 同理，標點是全形還是半形也不是段落名的一部分。指令裡寫的是半形——
# 「2. 需要結構或空間?」「2. 共同或個別?」——而模型在中文句子裡幾乎都會輸出全形「？」。
# 不收斂的話，這兩段就是下一組「永遠不會命中」的條目。
# 只收「有對應 ASCII 的」那幾個；、。「」等中文標點沒有等價物，維持原樣。
_FULLWIDTH_PUNCT = str.maketrans('？！（），；', '?!(),;')

# A line carrying an explicit heading marker: markdown hash, bold wrapper, bullet, or an
# ordinal prefix. The section test can afford to look at every line because it demands an
# exact match; the respondent-name test cannot, because it matches on substring -- a prose
# line like 「關於林孟德的部分寫在內文」 would otherwise count as that person's own section.
_MARKED_HEADING_RE = re.compile(
    r'^\s*(?:#{1,6}\s|\*\*|__|[-*•]\s|'
    r'第\s*[0-9一二三四五六七八九十]+\s*(?:部分|節|章|段)|'
    r'(?:[0-9]+|[一二三四五六七八九十]+)\s*[、,，.．)）:：])')

# 提問者本人不需要一個「介紹自己」的段落。a6718cb3 的提問是「我是 Victoria，帶領一個 8 人的
# 電話客服團隊」、6920b8fb 的是「我是連鎖餐飲門市的責任主管 鄭皓仁」——兩人的特質都在
# payload 裡（模型要據此給建議），但回答是寫「給」他們看的，沒有他們自己的段落是對的。
#
# 這一條是有實據的：調查中一度把這兩位算成「被漏掉的分析對象」，得出「有歷史就有 32% 機率
# 漏人」的結論，剔除後真正漏人只有 2 筆。沒有這個豁免，覆蓋率檢查會把同一個誤判做成一次
# 補生成，在回答尾巴補一段沒人要的自我分析。
#
# 自稱與姓名之間允許一段頭銜（「責任主管 鄭皓仁」），但不跨句：越過逗號句號就不算自稱。
_SELF_INTRO_MARKERS = ('我是', '我叫', '本人')
_SELF_INTRO_GAP = r'[^，。！？!?,;；\n]{0,20}'

_CJK_RE = re.compile(r'^[一-鿿]+$')
_ORG_SUFFIX_RE = re.compile(r'[-－]')
# 段落標籤開頭可能有的裝飾：括號、引號、星號、項目符號。名字前面只允許這些，
# 不允許實字——「與洪玉芳溝通時」的那個「與」就是實字，見 owns_section()。
_LABEL_LEAD_RE = re.compile(r'^[\s（(【\[「『《〈*＊·•\-–—]+')

# 模型在開場白自報的人數。2026-09-08 req e332a385 的第一句是「根據您提供的八位成員特質
# 資料」，名單其實是 11 位——這個缺陷在回答的第一句就自己說出來了，只是沒有人在讀。
# 只掃開場的前 200 字：後文的「建議每場 5 位以內」之類是會議建議，不是在數名單。
# 只在題庫題比對，理由見 finalize()。
_STATED_COUNT_SCAN_CHARS = 200
_STATED_COUNT_RE = re.compile(r'(?<![0-9])([0-9]{1,2}|[一二三四五六七八九十兩]{1,3})\s*[位名](?![0-9])')
_CJK_DIGITS = {'一': 1, '二': 2, '兩': 2, '三': 3, '四': 4, '五': 5,
               '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}


def _to_int(token: str):
    if token.isdigit():
        return int(token)
    if token == '十':
        return 10
    if token.startswith('十'):                      # 十一 ~ 十九
        return 10 + _CJK_DIGITS.get(token[1:], 0)
    if token.endswith('十'):                        # 二十 ~ 九十
        return _CJK_DIGITS.get(token[:-1], 0) * 10
    if len(token) == 3 and token[1] == '十':        # 二十一 ~ 九十九
        return _CJK_DIGITS.get(token[0], 0) * 10 + _CJK_DIGITS.get(token[2], 0)
    return _CJK_DIGITS.get(token)


def stated_count(answer: str):
    """回答開場白裡自報的人數；沒有就 None。只記錄，不影響 status。"""
    m = _STATED_COUNT_RE.search(answer[:_STATED_COUNT_SCAN_CHARS])
    return _to_int(m.group(1)) if m else None


def is_marked_heading(line: str) -> bool:
    return bool(_MARKED_HEADING_RE.match(line))


def normalize_heading(line: str) -> str:
    """Strip numbering, bullets, markdown emphasis and trailing colons.

    Also collapses runs of whitespace, the spacing/width of a slash, and the width of the
    punctuation that has an ASCII equivalent -- so 「同組織 / 專案角色分配建議」 and
    「同組織／專案角色分配建議」 are the same heading, and so are 「共同或個別?」 and
    「共同或個別？」. Applied to both sides of the comparison, so the expected list and the
    answer meet in the middle rather than the data having to guess which form the model
    will emit. Guessing is how 「（2項）」 got into the data.
    """
    text = _BOLD_RE.sub('', line).strip()
    text = _HEADING_PREFIX_RE.sub('', text, count=1)
    text = _HEADING_SUFFIX_RE.sub('', text)
    text = _WHITESPACE_RE.sub(' ', text)
    text = _SLASH_RE.sub('/', text)
    return text.translate(_FULLWIDTH_PUNCT).strip()


def heading_candidates(line: str) -> List[str]:
    """Every form of `line` that could be the section heading it carries.

    A heading does not always sit on a line of its own. The instructions teach
    「2. 主要風險：列出 3 項」 and the models answer 「- **主要領導風格**：推進驅動型」 --
    label and value on one line. `normalize_heading` only strips a *trailing* colon, so the
    value stays attached and an exact-match test against 「主要領導風格」 never fires. The
    section is then reported missing while it is plainly on screen: 2026-08-25 req
    f1d36fbb lost all six sections that way, and the completion pass it triggered wrote
    them again in the same format, so they were still missing afterwards.

    Only marked lines are split, and only on the first colon -- an ordinary sentence that
    happens to contain a colon is not offering a heading. A candidate that is not a section
    name is inert anyway, because the test is equality against the expected list.
    """
    norm = normalize_heading(line)
    if not norm:
        return []
    candidates = [norm]
    if is_marked_heading(line):
        label = _COLON_SPLIT_RE.split(norm, 1)[0].strip()
        if label and label != norm:
            candidates.append(label)
    return candidates


def name_forms(name: str) -> List[str]:
    """模型可能拿來當段落標題的每一種姓名寫法。

    廠商送來的姓名帶著格式雜訊——姓與名之間一個空白，後面直接黏上單位：
    `柳 宇賸-人資發展課`、`呂 佳珍教育訓練課`、`游 璧碩`。模型寫標題時一律用乾淨的
    `柳宇賸`／`呂佳珍`／`游璧碩`，所以原本的 `r.name in heading` 一次都不會命中。
    req c5e0ef45 的回覆八個人全部寫到了，用原本的比法卻會判成漏了七個——啟用自由提問的
    覆蓋率檢查以前必須先修掉，否則補生成會在完整的回答後面再補一次。

    寧可多給幾種寫法：判成「有寫到」的代價是漏掉一次真正的遺漏，判成「沒寫到」的代價是
    在一篇完整的回答尾巴硬接一段補充。後者對讀者的傷害大得多。
    """
    raw = (name or '').strip()
    if not raw:
        return []
    forms = {raw}
    head = _ORG_SUFFIX_RE.split(raw)[0].strip()      # 去掉 `-單位` 後綴
    forms.add(head)
    forms |= {_WHITESPACE_RE.sub('', f) for f in tuple(forms)}

    parts = head.split()
    if len(parts) >= 2:
        first, rest = parts[0], ''.join(parts[1:])
        if _CJK_RE.match(first):
            # 「姓 名」中間那個空白是可靠的分界；單位是直接黏在名後面的，所以取名的前
            # 一到兩個字就能還原出 `呂 佳珍教育訓練課` -> `呂佳珍`。
            for n in (2, 1):
                if len(rest) >= n:
                    forms.add(first + rest[:n])
        elif len(first) >= 3:
            # 西文姓名，模型常只寫 first name（「Howard 的適配優勢」）。兩個字母的
            # 縮寫（GT）太短，不收。
            forms.add(first)
    return sorted({f for f in forms if len(f) >= 2}, key=len, reverse=True)


def owns_section(label: str, name: str) -> bool:
    """`label` 這個段落標籤，是不是 `name` 這個人自己的段落。

    判準是**以名字開頭**（前面只容許括號、引號、星號這類裝飾），不是「提到他」。

    2026-09-08 req ecae89f3 逼出這條。那篇回答的第 4 節「管理策略與建議」寫成

        - **與洪 玉芳溝通時：** 說明背景與理由，避免只給結論…
        - **與涂 佩吟溝通時：** …
        - **與周 瑋君溝通時：** …

    這三個標籤各只點到一個人，原本的判準因此認定「這篇是照人分段的」，於是把寫在
    1-3 節內文裡的其餘 8 位全判成漏人，補生成在回答尾巴硬接了 1202 字的重複內容
    ——使用者看到的是一段與前文毫無銜接的人名清單。那正是 E-12 的傷害形狀。

    「與洪玉芳溝通時」是**建議事項**，主詞是讀者不是洪玉芳；「（陳惠娟）」「洪 玉芳」
    「陳曉玲——制度推行與關係整合型角色」才是她們自己的段落。差別就在名字是不是開頭。

    刻意不用長度上限：「陳曉玲——制度推行與關係整合型角色」是貨真價實的個人標題，
    只是後綴很長，用長度砍會砍掉它。
    """
    head = _LABEL_LEAD_RE.sub('', label or '')
    return any(head.startswith(_WHITESPACE_RE.sub('', f)) for f in name_forms(name or ''))


def self_introduced_names(user_query: Optional[str], respondents) -> List[str]:
    """受測者中，本輪提問裡以第一人稱自稱的那些人——他們不需要自己的段落。

    姓名與提問的空白都先去掉再比對：payload 存的是「鄭 皓仁」，提問打的是「鄭皓仁」。
    """
    if not user_query:
        return []
    flat = _WHITESPACE_RE.sub('', user_query)
    out = []
    for r in respondents:
        # 使用者打的是乾淨的姓名，payload 存的是帶空白與單位的版本，所以比對走同一組
        # 寫法（`name_forms`）；最長的先試，愈短的愈容易誤中。
        for form in name_forms(r.name or ''):
            form = _WHITESPACE_RE.sub('', form)
            if re.search(f'(?:{"|".join(_SELF_INTRO_MARKERS)}){_SELF_INTRO_GAP}'
                         f'{re.escape(form)}', flat):
                out.append(r.name)
                break
    return out


def expected_sections_for(question: Optional[dict], respondent_count: int):
    """事項 13: prefer the audience-specific list, fall back to the shared one.

    Many questions use different headings for their single- and multi-person instructions,
    so a multi-person answer checked against the single-person list would be judged as
    missing every section. The split fields do not exist in the data yet; until they do,
    the fallback is used and reported rather than silently assumed correct.
    """
    if question is None:
        return [], None
    key = 'expected_sections_multi' if respondent_count > 1 else 'expected_sections_single'
    if question.get(key) is not None:
        return list(question[key]), None
    return list(question.get('expected_sections') or []), UNSPLIT_LOG


class CompletenessResult:
    __slots__ = ('status', 'sections_check', 'missing_sections', 'missing_respondents',
                 'char_count', 'calibration_evidence', 'log_lines',
                 'respondents_appendable', 'stated_count', 'respondents_check',
                 'free_form_length_check')

    def __init__(self):
        # `status` is the verdict for the whole answer; the two *_check fields are the
        # independent sub-results the audit record asks for. Reporting `status` as
        # `expected_sections_check` would make a calibration miss look like a missing
        # section, which is what the first version of this did.
        self.status = 'passed'                  # passed | failed | skipped
        # data_gap 只進稽核，不改 status——它是資料維運訊號，不是這一筆回答的品質問題。
        self.sections_check = 'passed'          # passed | failed | skipped | data_gap | n/a
        self.missing_sections: List[str] = []
        self.missing_respondents: List[str] = []
        self.char_count: Optional[int] = None
        self.calibration_evidence = 'n/a'       # passed | failed | n/a
        self.log_lines: List[str] = []
        # 「漏人」該不該交給補生成去補。題庫題是，自由提問不是——見 appendable_reason()。
        self.respondents_appendable = True
        # 模型在開場白自報的人數（見 stated_count()）。只記錄，不改 status：它的精確度
        # 還沒量過，而 status 會牽動補生成與 manual_review，先不讓沒量過的訊號動它。
        self.stated_count: Optional[int] = None
        # 覆蓋率是怎麼判的：by_section（回答照人分段，比段落標籤）／by_mention（沒有照人
        # 分段，只問有沒有寫到這個人）／n/a（單人）。寫進稽核，省得日後再重新推一次。
        self.respondents_check = 'n/a'
        # b §8 的字數上限查了沒、過了沒。與 stated_count 同樣是「只記錄，不改 status」
        # ——status 會牽動補生成與 manual_review，而超字兩者都幫不上忙（U10）。
        self.free_form_length_check = 'n/a'     # passed | over_limit | n/a

    def as_audit(self) -> dict:
        return {
            'expected_sections_check': self.sections_check,
            'missing_sections': self.missing_sections,
            'missing_respondents': self.missing_respondents,
            'char_count': self.char_count,
            'free_form_length_check': self.free_form_length_check,
            'calibration_evidence_check': self.calibration_evidence,
            'stated_count': self.stated_count,
            'respondents_check': self.respondents_check,
            'log': self.log_lines,
        }

    def _missing_bits(self, for_completion: bool) -> List[str]:
        bits = []
        if self.missing_sections:
            bits.append('缺少段落：' + '、'.join(self.missing_sections))
        if self.missing_respondents and (self.respondents_appendable or not for_completion):
            bits.append('缺少獨立段落的受測者：' + '、'.join(self.missing_respondents))
        return bits

    def appendable_reason(self) -> str:
        """The part of `reason()` that appending more text could actually fix.

        「漏人」只有在**這一題明定逐人分段**時才補（`per_person_sections`，19 題裡只有
        Q15／Q21／Q22）。自由提問不補，沒有明定逐人的題庫題也不補——後者是 2026-09-08
        req ecae89f3 補上的條件：Q13 通篇寫「對象組合」，卻因為判定從回答形狀去猜而觸發
        補生成，硬接了 1202 字的重複人名清單。

        自由提問那一半的理由是實測的觸發紀錄——0816-0904 全語料 34 筆自由提問一次都沒觸發過，
        第一次觸發是 2026-09-07 的 S8 劇本，三輪三次**全部是誤判**：使用者問「請只針對
        林慧嵐說明」，模型正確地只寫了她，覆蓋率檢查卻判定「漏了其他四位」，補生成把
        使用者沒問的四位硬接在後面——5887 字的回答裡約 79% 是沒人要的內容。（E-12）

        傷害來自「自動硬接」，不是來自「判定漏人」，所以拿掉的是補這個動作：
        `missing_respondents` 照樣寫進稽核、`reason()` 照樣說得出是誰、status 仍是
        failed（因此落在 manual_review）。43c1f019 那種真漏人依然看得見，只是不自動補，
        使用者得自己再問一次。

        要恢復自動補，前提是覆蓋率檢查先學會「使用者這輪只問了誰」——那需要點名偵測、
        排除語、泛稱、追問繼承四條規則，不是一個條件的事。在那之前，寧可少補也不要
        硬接：少補的代價是使用者再問一次，硬接的代價是每一次點名提問都拿到不要的內容。

        b §8's completion pass is 丙-2's 「只補上缺少的部分」: it appends, and everything
        already on screen stays there. That works for a missing section -- it is a new
        block of text with its own heading. It does not work for the other two failures,
        and attempting it caused two separate production defects:

          * calibration evidence: the wording has to run through the existing paragraphs,
            so the model either bolted on a 「佐證類措辭補充」 block (session af4d3e45) or
            re-emitted the entire answer with the wording woven in -- the user read the
            whole analysis twice, because released segments cannot be recalled (丙-3).
          * free-form over 1,000 characters: appending makes it longer. The completion
            pass is the opposite of the fix.

        Both now report `manual_review` instead, which is what the status is for. The real
        cure for the first is 乙-6: the evidence wordlist rejects phrasings the client's
        own examples use, so the check fails more often than it should.
        """
        return '；'.join(self._missing_bits(for_completion=True))

    def reason(self) -> str:
        """Everything that failed -- for the audit record and the log."""
        bits = self._missing_bits(for_completion=False)
        if self.calibration_evidence == 'failed':
            bits.append('需加入佐證類措辭（' + '／'.join(EVIDENCE_TERMS) + '）')
        # 超字不再列入：它已經不是失敗（U10），`free_form_length_check` 會記錄它。
        return '；'.join(bits)

    def __repr__(self):
        return f'<CompletenessResult {self.status} missing={self.missing_sections}>'


class CompletenessChecker:
    def __init__(self, respondents, question: Optional[dict],
                 calibration_traits: Optional[set] = None,
                 user_query: Optional[str] = None,
                 history: Optional[List[dict]] = None):
        self.respondents = respondents
        self.question = question
        self.calibration_traits = calibration_traits or set()
        # 自稱要連前幾輪一起看。使用者只在第一輪說一次「我是 Victoria」，後續輪次就直接
        # 問「我照前面的建議…現在有新的情況」——只看本輪的話，a6718cb3 與 6920b8fb 的
        # 後續輪次會把提問者本人判成漏掉的分析對象。
        # 只有自由提問拿得到 user_query（題庫題的「提問」是模組指令），所以豁免名單在
        # 題庫題永遠是空的，那條路徑的行為不變。
        prior = '\n'.join(m.get('content') or '' for m in (history or [])
                          if m.get('role') == 'user')
        self.self_introduced = set(self_introduced_names(
            '\n'.join(t for t in (user_query, prior) if t), respondents))
        # 「這一題要不要逐人分段」是題目的屬性，由題庫資料回答，不從回答的形狀猜。
        # 19 題可多人的題目裡只有 Q15／Q21／Q22 明寫了「逐一／每位／個別成員」。
        # req ecae89f3（Q13）證明猜不得——見 finalize() 裡的說明。
        self.per_person = bool((question or {}).get('per_person_sections'))
        self.expected, self._fallback_note = expected_sections_for(question, len(respondents))
        self._headings: List[str] = []          # every line, for exact section matching
        # 帶標記的行連同它的候選寫法，供 `_section_labels()` 取冒號前的標籤。
        self._marked_candidates: List[tuple] = []
        self._pending = ''                      # 跨 segment 的未完行，見 observe()
        self._text_parts: List[str] = []

    def observe(self, segment: str):
        """Feed one display-ready segment.

        跨 segment 的未完行會留在 `_pending`，等下一段接上或 `finalize()` 收尾。

        原本是對每個 segment 各自 `split()`，於是 **segment 邊界等於行邊界**——而串流的
        切點是閘門決定的，跟 Markdown 的行毫無關係。2026-09-08 req 399ad86d：改寫器回傳
        的文字沒帶回段尾空行（E-14），下一段的 `- **陳 曉玲**：…` 因此黏在前一段的句子
        後面；讀者看到的是行中的 `- `，Markdown 不會把它算成新項目，但這裡卻因為它是
        新 segment 的第一行而把它當成一個段落標題。線上判 `missing_respondents: []`，
        用同一支程式離線重放卻判「缺陳曉玲」。

        線上與離線重放必須一致，這不是潔癖：稽核記錄可以重放，是這整套判定能被檢驗的
        前提，而 0905-0908 的回歸量測全部建立在離線重放上。
        """
        if not segment:
            return
        self._text_parts.append(segment)
        buf = self._pending + segment
        lines = buf.split('\n')
        self._pending = lines.pop()          # 最後一段沒有換行收尾，可能還沒寫完
        for line in lines:
            self._take(line)

    def _take(self, line: str):
        norm = normalize_heading(line)
        if not norm:
            return
        # 兩種比對共用同一批候選寫法：段落齊全檢查要的是相等比對，所以每一種寫法都
        # 收；人名檢查要的是「這一段是誰的」，所以只取最短的那個候選（＝冒號前的
        # 標籤），見 `_section_labels()`。
        cands = heading_candidates(line)
        self._headings.extend(cands)
        if is_marked_heading(line) and cands:
            self._marked_candidates.append((line, cands))

    def _flush(self):
        """把最後一行沒有換行收尾的內容收進來。冪等。"""
        if self._pending:
            line, self._pending = self._pending, ''
            self._take(line)

    @property
    def text(self) -> str:
        return ''.join(self._text_parts)

    def _section_labels(self) -> List[str]:
        """每個帶標記的行，取「冒號前的那個標籤」——也就是它真正的段落名。

        2026-09-08 req e332a385：名單 11 位，第 2 節逐人分析只寫了 7 位，覆蓋率檢查卻判
        `missing_respondents: []`。原因是這裡原本拿整行去比對，而 `_MARKED_HEADING_RE` 把
        任何以 `- ` 開頭的行都當成標題——那篇回答整篇都是 `- **標籤**：一整段內文` 的體例，
        於是第 1 節的第一條 bullet：

            - **偏收斂、重結構…**：…「強力推進組」（簡玥瀅、徐瑋襄、王雅韻、郁晨翰）與
              「穩健支援組」（陳惠娟、劉湘君、秦珮芳、張瑜芳）…

        **一行就讓 8 個人通過覆蓋率檢查**，其中王雅韻從頭到尾沒有自己的段落。重放那一筆，
        11 個人裡 0 個是靠真正的段落標題命中的，全部靠內文。

        `heading_candidates()` 早就算好了冒號前的標籤（那是為了 f1d36fbb 的「標題與內容
        同一行」加的），這裡直接取最短的那個候選：真正的段落標籤是「（陳惠娟）」，內文
        bullet 的標籤是「偏收斂、重結構，但存在兩種動力極端」——姓名自然就掃不到。

        再擋掉「一個標籤裡有兩個以上名單成員」的組合標題，例如第 4 節的
        「**徐瑋襄 vs. 張雅玲**」。那是搭配組合，不是任何一個人的段落；不擋的話張雅玲
        仍然會被它放行。代價是：若模型真的把兩個人合寫成一段，這裡會判兩人皆缺——而多人
        題庫題的指令本來就要求每人一段（Unit A 的名單區塊又補了一句「不得省略或合併」），
        判缺是對的。

        「這個標籤是誰的段落」由 `owns_section()` 判——要以名字開頭，不是提到就算。
        """
        labels = []
        for line, cands in self._marked_candidates:
            label = _WHITESPACE_RE.sub('', min(cands, key=len))
            if self._roster_hits(label) > 1:
                continue
            labels.append(label)
        return labels

    def _roster_hits(self, flat_text: str) -> int:
        """`flat_text`（已去空白）裡出現了幾位名單成員。"""
        n = 0
        for r in self.respondents:
            if any(_WHITESPACE_RE.sub('', f) in flat_text
                   for f in name_forms(r.name or '')):
                n += 1
        return n

    def _needs_evidence(self) -> bool:
        return any(r.scores.get(t) == 'A'
                   for r in self.respondents for t in self.calibration_traits)

    def finalize(self) -> CompletenessResult:
        self._flush()
        result = CompletenessResult()
        # 「漏人」交不交給補生成，看的是這一題有沒有明定逐人分段——不是「是不是題庫題」。
        # 原本寫的是 `self.question is not None`，於是 Q13 這種純組合題也在補，見
        # appendable_reason()。
        result.respondents_appendable = self.per_person
        answer = self.text
        heading_set = set(self._headings)

        if self.question is None:
            result.sections_check = 'n/a'       # free-form has no fixed headings
            result.char_count = len(re.sub(r'\s', '', answer))
            # 只記錄，不動 status。見 FREE_FORM_MAX_CHARS 的註解（U10）。
            result.free_form_length_check = (
                'over_limit' if result.char_count > FREE_FORM_MAX_CHARS else 'passed')
        elif not self.expected:
            result.status = 'skipped'
            if (self.question or {}).get('expected_sections_note'):
                result.sections_check = 'skipped'       # 內容方確認過：本題無固定段落
                result.log_lines.append(SKIP_LOG)
            else:
                result.sections_check = 'data_gap'      # 資料沒填，不是題目特性
                result.log_lines.append(DATA_GAP_LOG)
        else:
            if self._fallback_note:
                result.log_lines.append(self._fallback_note)
            result.missing_sections = [s for s in self.expected
                                       if normalize_heading(s) not in heading_set]
            if result.missing_sections:
                result.status = 'failed'
                result.sections_check = 'failed'

        # 自由提問也要查。以前這裡有 `self.question is not None`，於是 34 筆自由提問的
        # `missing_respondents` 全都是 []——不是「檢查過都在」，是從未檢查，補生成一次都沒
        # 觸發過。而漏人正好只發生在自由提問：43c1f019 名單 7 加到 8，漏掉的正是新增那位；
        # 4920eef8 名單 1 加到 8，回答宣稱其餘七位沒有資料。
        if len(self.respondents) > 1:
            # 題庫題比對的是「段落標籤」（`_section_labels()`），不是整行——整行會被內文
            # bullet 騙掉，見那支函式的說明。
            #
            # 但「照人分段」不是每一道題庫題都成立的假設，而且**不能從回答的形狀去猜**。
            #
            # 猜過一次，代價是線上缺陷：2026-09-08 req ecae89f3（Q13）的第 4 節寫成
            # `- **與洪 玉芳溝通時：** …`，三個這種標籤讓判定認為「這篇是照人分段的」，
            # 於是把寫在 1-3 節內文裡的其餘 8 位全判成漏人，補生成在回答尾巴硬接了
            # 1202 字的重複人名清單——使用者看到的是一段與前文毫無銜接的文字。而 Q13 的
            # 指令從頭到尾寫的是「對象組合」，一句要求逐人的話都沒有。
            #
            # 所以改由題庫資料回答（`per_person_sections`），與 `expected_sections` 同一
            # 種手法：b §8 明講從指令推導輸出結構是語意判斷，那就把判斷留在資料裡，程式
            # 只讀不推。19 題可多人的題目裡只有 Q15／Q21／Q22 是 True。
            #
            # False 的題目退回「有沒有寫到這個人」（整篇比對），而且**只記錄不補**——
            # 2026-08-18 req 5017a070 那種照主題分段的合作題，硬接就是 E-12 的形狀。
            #
            # 題庫題的段落結構是題目指定的，所以「有沒有自己的標題」問得出來。自由提問沒有
            # 指定結構——使用者問「誰最適合，給我排序」，一份不用標題的排序清單、一張表格
            # 都是好答案。拿標題當判準，全語料 29 筆多人回覆會判出 12 筆缺人，其中 9 筆的
            # 人名其實都在（e1cd17fe 用表格、e4989baf 依主題而非依人分段），補生成會在完整
            # 的回答後面硬接一段。自由提問因此只問「有沒有寫到這個人」。
            #
            # 代價寫在這裡，不要之後再重新發現一次：這樣就抓不到 4920eef8 那種「七個人的
            # 名字都列了，但列在『這些人沒有資料』的句子裡」。那是模型謊報資料缺席，屬於
            # 另一種檢查；4920eef8 的根因（歷史蓋過名單）由 Unit 1 的名單宣告處理。
            labels = self._section_labels() if self.per_person else []
            owned = {r.name for r in self.respondents
                     for l in labels if owns_section(l, r.name)}
            if owned:
                haystack = labels
                result.respondents_check = 'by_section'
            else:
                # 整篇比對：沒有指定逐人分段的題目，唯一問得出來的就是「有沒有寫到這個
                # 人」。自由提問一直是這樣（沒有指定輸出結構，一張表格、一份排序清單都是
                # 好答案，全語料 29 筆多人回覆有 9 筆是這種形狀）。
                #
                # 題庫題那一半原本走 `_discussion_lines()`——只認「一行點到 2 位以內」的
                # 行，理由是「一行列 8 個名字是在列名單，不是在寫這些人」。那個理由來自
                # `e332a385`，而 Unit D 之後 `e332a385`（Q15）走的是 `by_section`，
                # 這條防線在它該防的地方已經用不到了；留著只在**組合題**上誤傷：
                # 2026-09-09 req `57b052ba`（Q13、11 位）的回答把成員歸成「四種典型
                # 樣態」，11 個名字全都寫到了，卻因為每行點到 3 位以上而判出 9 位缺席。
                # 全語料掃過，那是唯一一筆差異——9 個全是誤判。
                haystack = [_WHITESPACE_RE.sub('', answer)]
                result.respondents_check = 'by_mention'
            if result.respondents_check == 'by_section':
                covered = owned
            else:
                covered = {r.name for r in self.respondents
                           if any(_WHITESPACE_RE.sub('', form) in h
                                  for form in name_forms(r.name) for h in haystack)}
            result.missing_respondents = [
                r.name for r in self.respondents
                if r.name not in self.self_introduced and r.name not in covered]
            if result.missing_respondents:
                result.status = 'failed'

        # 只在題庫題記。自由提問的名單常常不是回答的範圍——2026-09-08 req fb7eacbd 的提問是
        # 「謝淑玲，簡玥瀅 適合的崗位是什麼？」，名單 10 位，模型正確地寫「兩位」，這裡卻
        # 記成落差。那不是缺陷，是 E-12 講的同一件事：使用者點名幾位，回答就該只有幾位。
        if len(self.respondents) > 1 and self.question is not None:
            n = stated_count(answer)
            if n is not None and n != len(self.respondents):
                result.stated_count = n
                result.log_lines.append(
                    f'模型自報 {n} 位，本輪名單 {len(self.respondents)} 位（只記錄，不影響判定）')

        if self._needs_evidence():
            ok = any(term in answer for term in EVIDENCE_TERMS)
            result.calibration_evidence = 'passed' if ok else 'failed'
            if not ok:
                result.status = 'failed'

        return result


def check_answer(answer: str, respondents, question: Optional[dict],
                 calibration_traits: Optional[set] = None,
                 user_query: Optional[str] = None,
                 history: Optional[List[dict]] = None) -> CompletenessResult:
    """Non-streaming convenience wrapper."""
    checker = CompletenessChecker(respondents, question, calibration_traits,
                                  user_query, history)
    checker.observe(answer)
    return checker.finalize()

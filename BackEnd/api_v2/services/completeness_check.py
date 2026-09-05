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
FREE_FORM_MAX_CHARS = 1000

SKIP_LOG = '本題未做段落齊全檢查（原因：指令未定義固定段落標題）'
UNSPLIT_LOG = '本題 expected_sections 尚未拆分 single/multi，退回使用單一欄位'

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
                 'char_count', 'calibration_evidence', 'log_lines')

    def __init__(self):
        # `status` is the verdict for the whole answer; the two *_check fields are the
        # independent sub-results the audit record asks for. Reporting `status` as
        # `expected_sections_check` would make a calibration miss look like a missing
        # section, which is what the first version of this did.
        self.status = 'passed'                  # passed | failed | skipped
        self.sections_check = 'passed'          # passed | failed | skipped | n/a
        self.missing_sections: List[str] = []
        self.missing_respondents: List[str] = []
        self.char_count: Optional[int] = None
        self.calibration_evidence = 'n/a'       # passed | failed | n/a
        self.log_lines: List[str] = []

    def as_audit(self) -> dict:
        return {
            'expected_sections_check': self.sections_check,
            'missing_sections': self.missing_sections,
            'missing_respondents': self.missing_respondents,
            'char_count': self.char_count,
            'calibration_evidence_check': self.calibration_evidence,
            'log': self.log_lines,
        }

    def _appendable_bits(self) -> List[str]:
        return ([('缺少段落：' + '、'.join(self.missing_sections))] if self.missing_sections else []) \
             + ([('缺少獨立段落的受測者：' + '、'.join(self.missing_respondents))]
                if self.missing_respondents else [])

    def appendable_reason(self) -> str:
        """The part of `reason()` that appending more text could actually fix.

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
        return '；'.join(self._appendable_bits())

    def reason(self) -> str:
        """Everything that failed -- for the audit record and the log."""
        bits = self._appendable_bits()
        if self.calibration_evidence == 'failed':
            bits.append('需加入佐證類措辭（' + '／'.join(EVIDENCE_TERMS) + '）')
        if self.status == 'failed' and self.char_count and self.char_count > FREE_FORM_MAX_CHARS:
            bits.append(f'回答超過 {FREE_FORM_MAX_CHARS} 字（目前 {self.char_count} 字）')
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
        self.expected, self._fallback_note = expected_sections_for(question, len(respondents))
        self._headings: List[str] = []          # every line, for exact section matching
        self._marked_headings: List[str] = []   # explicitly marked lines only, for names
        self._text_parts: List[str] = []

    def observe(self, segment: str):
        """Feed one display-ready segment."""
        if not segment:
            return
        self._text_parts.append(segment)
        for line in segment.split('\n'):
            norm = normalize_heading(line)
            if not norm:
                continue
            # Section matching takes every candidate form of the line; the respondent-name
            # test keeps the whole normalized line, because it matches on substring and a
            # shorter candidate cannot make a name appear that was not already there.
            self._headings.extend(heading_candidates(line))
            if is_marked_heading(line):
                self._marked_headings.append(norm)

    @property
    def text(self) -> str:
        return ''.join(self._text_parts)

    def _needs_evidence(self) -> bool:
        return any(r.scores.get(t) == 'A'
                   for r in self.respondents for t in self.calibration_traits)

    def finalize(self) -> CompletenessResult:
        result = CompletenessResult()
        answer = self.text
        heading_set = set(self._headings)

        if self.question is None:
            result.sections_check = 'n/a'       # free-form has no fixed headings
            result.char_count = len(re.sub(r'\s', '', answer))
            if result.char_count > FREE_FORM_MAX_CHARS:
                result.status = 'failed'
        elif not self.expected:
            result.status = 'skipped'
            result.sections_check = 'skipped'
            result.log_lines.append(SKIP_LOG)
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
            # 題庫題的段落結構是題目指定的，所以「有沒有自己的標題」問得出來。自由提問沒有
            # 指定結構——使用者問「誰最適合，給我排序」，一份不用標題的排序清單、一張表格
            # 都是好答案。拿標題當判準，全語料 29 筆多人回覆會判出 12 筆缺人，其中 9 筆的
            # 人名其實都在（e1cd17fe 用表格、e4989baf 依主題而非依人分段），補生成會在完整
            # 的回答後面硬接一段。自由提問因此只問「有沒有寫到這個人」。
            #
            # 代價寫在這裡，不要之後再重新發現一次：這樣就抓不到 4920eef8 那種「七個人的
            # 名字都列了，但列在『這些人沒有資料』的句子裡」。那是模型謊報資料缺席，屬於
            # 另一種檢查；4920eef8 的根因（歷史蓋過名單）由 Unit 1 的名單宣告處理。
            if self.question is not None:
                haystack = [_WHITESPACE_RE.sub('', h) for h in self._marked_headings]
            else:
                haystack = [_WHITESPACE_RE.sub('', answer)]
            result.missing_respondents = [
                r.name for r in self.respondents
                if r.name not in self.self_introduced
                and not any(_WHITESPACE_RE.sub('', form) in h
                            for form in name_forms(r.name) for h in haystack)]
            if result.missing_respondents:
                result.status = 'failed'

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

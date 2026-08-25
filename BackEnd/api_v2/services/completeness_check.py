"""Output completeness checks on the answer (事項 10 / 13, b §8).

    題庫題    every expected section heading is present (subset test -- extra headings
              are fine); for a multi-person answer, each respondent also needs their own
              heading. Length is not checked.
    自由提問  answer stays within 1,000 characters.
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
                 calibration_traits: Optional[set] = None):
        self.respondents = respondents
        self.question = question
        self.calibration_traits = calibration_traits or set()
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

        if self.question is not None and len(self.respondents) > 1:
            result.missing_respondents = [
                r.name for r in self.respondents
                if not any(r.name in h for h in self._marked_headings)]
            if result.missing_respondents:
                result.status = 'failed'

        if self._needs_evidence():
            ok = any(term in answer for term in EVIDENCE_TERMS)
            result.calibration_evidence = 'passed' if ok else 'failed'
            if not ok:
                result.status = 'failed'

        return result


def check_answer(answer: str, respondents, question: Optional[dict],
                 calibration_traits: Optional[set] = None) -> CompletenessResult:
    """Non-streaming convenience wrapper."""
    checker = CompletenessChecker(respondents, question, calibration_traits)
    checker.observe(answer)
    return checker.finalize()

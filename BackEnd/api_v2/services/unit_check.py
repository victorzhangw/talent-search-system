r"""Pre-delivery unit checks, run on every assembly (事項 08, b §6).

    1. 全塊數 ＝ S∩P 特質數；索引行數 ＝ |P| − 全塊數
    2. 每個交互標頭的兩端 ID 都出現在全塊區或索引區
    3. 全文無 `['`、無空括號；殘留括號代號檢查僅適用敘事本文
    4. 子區塊歸屬正確：本題相關列至少一端 ∈ S

These parse the assembled text rather than reading the assembler's own bookkeeping. If
the builder is wrong, restating its beliefs back at it proves nothing; re-deriving the
answer from the emitted payload catches it.

Check 3 is the one with a trap in it. `XXX_nn` is a legitimate, required marker in block
headers and index lines -- b §6 and DoD 5 both insist it survives, because the runtime
LLM needs it to tell apart same-named traits across assessments. Running the id pattern
over the whole payload would hit hundreds of legal headers, so the scan is restricted to
narrative body lines inside 【輸入數據】. That also keeps it off the task instruction,
where some questions deliberately spell out ids such as 「自主領導（ANI_05）高」.
"""

import re
from typing import Dict, List, Optional

DATA_HEADER = '## 【輸入數據】'
INSTRUCTION_MARKER = '[任務指令]'

RESPONDENT_RE = re.compile(r'^### \[受測者 \| (.+?) \| (.+?)\]$')
SUBJECT_RE = re.compile(r'^#### 判讀主體特質')
INDEX_HEADER_RE = re.compile(r'^#### 其他特質索引')
INTER_HEADER_RE = re.compile(r'^#### 交互作用——(.+)$')
TRAIT_HEADER_RE = re.compile(r'^\[特質 \| ([A-Z]{3}_\d+)_([ABC]) \| ')
INDEX_LINE_RE = re.compile(r'^- ([A-Z]{3}_\d+)_([ABC])｜')
INTER_HEADER_PAIR_RE = re.compile(
    r'^\[交互 \| ([A-Z]{3}_\d+)_([ABC]) × ([A-Z]{3}_\d+)_([ABC]) \| ')

PYTHON_LIST_RE = re.compile(r"\['")
EMPTY_PARENS_RE = re.compile(r'[（(]\s*[)）]')
PAREN_CODE_RE = re.compile(r'[（(]\s*\d{2}\s*[ABC]?(\s*[,，、]\s*\d{2}\s*[ABC]?)*\s*[）)]')
TRAIT_ID_RE = re.compile(r'[A-Z]{3}_\d+')

RELATED_BLOCK_SUFFIX = '本題相關'


class Problem:
    __slots__ = ('code', 'message')

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

    def __repr__(self):
        return f'{self.code}: {self.message}'


class _RespondentRegions:
    def __init__(self, name, rid):
        self.name, self.rid = name, rid
        self.full = []          # [(trait_id, band)]
        self.index = []         # [(trait_id, band)]
        self.interactions = []  # [(block_label, a_id, a_band, b_id, b_band)]
        self.body_lines = []    # narrative / four-column text, ids never legal here


def _parse(log_text: str) -> List[_RespondentRegions]:
    lines = log_text.split('\n')
    try:
        start = lines.index(DATA_HEADER) + 1
    except ValueError:
        return []
    end = next((i for i, l in enumerate(lines) if l.startswith(INSTRUCTION_MARKER)), len(lines))

    out: List[_RespondentRegions] = []
    block_label = None
    for line in lines[start:end]:
        m = RESPONDENT_RE.match(line)
        if m:
            out.append(_RespondentRegions(*m.groups()))
            block_label = None
            continue
        if not out:
            continue
        cur = out[-1]

        if SUBJECT_RE.match(line) or INDEX_HEADER_RE.match(line):
            block_label = None
            continue
        m = INTER_HEADER_RE.match(line)
        if m:
            block_label = m.group(1)
            continue

        m = TRAIT_HEADER_RE.match(line)
        if m:
            cur.full.append(m.groups())
            continue
        m = INDEX_LINE_RE.match(line)
        if m:
            cur.index.append(m.groups())
            continue
        m = INTER_HEADER_PAIR_RE.match(line)
        if m:
            a, ab, b, bb = m.groups()
            cur.interactions.append((block_label, a, ab, b, bb))
            continue

        if line.strip() and line.strip() != '---':
            cur.body_lines.append(line)
    return out


def run_unit_checks(log_text: str, respondents, question: Optional[dict],
                    scoped_ids_by_id: Optional[Dict[str, set]] = None) -> List[Problem]:
    """respondents: the Respondent objects that went in, so P is known independently.
    scoped_ids_by_id: {respondent_id: S}; omit for whole-person/free-form."""
    problems: List[Problem] = []
    # Matched by position, not by the header's ID field: that field now carries a position
    # token (RESP_01) rather than the candidate_id, because the raw id leaked into answers
    # as 「許品優（55）」. b §5 emits one block per respondent in the order given, so the
    # nth block belongs to the nth respondent -- and the name on it is then verified,
    # which is a stronger check than the id lookup it replaces: a block emitted under the
    # wrong person's name used to pass as long as some block carried the right id.
    parsed = _parse(log_text)
    whole = question is None or question.get('type') == 'whole_person'

    if len(parsed) != len(respondents):
        problems.append(Problem('respondent_count',
                                f'{len(parsed)} blocks parsed for {len(respondents)} respondents'))

    for i, r in enumerate(respondents):
        reg = parsed[i] if i < len(parsed) else None
        if reg is None:
            problems.append(Problem('missing_respondent', f'no block for {r.respondent_id}'))
            continue
        if reg.name != r.name:
            problems.append(Problem('respondent_mismatch',
                                    f'block {i + 1} is 「{reg.name}」, expected 「{r.name}」'))
            continue
        S = (scoped_ids_by_id or {}).get(r.respondent_id, set())
        P = r.scores

        # 1. counts
        expected_full = len(P) if whole else len({t for t in P if t in S})
        if len(reg.full) != expected_full:
            problems.append(Problem('full_count',
                                    f'{r.respondent_id}: {len(reg.full)} full blocks, expected {expected_full}'))
        if len(reg.index) != len(P) - expected_full:
            problems.append(Problem('index_count',
                                    f'{r.respondent_id}: {len(reg.index)} index lines, '
                                    f'expected {len(P) - expected_full}'))

        # 2. every interaction end is present as a full block or an index line
        present = {t for t, _ in reg.full} | {t for t, _ in reg.index}
        for label, a, ab, b, bb in reg.interactions:
            for tid in (a, b):
                if tid not in present:
                    problems.append(Problem('dangling_interaction_end',
                                            f'{r.respondent_id}: {tid} in an interaction header '
                                            f'but in neither region'))

        # 4. sub-block membership
        if not whole:
            for label, a, ab, b, bb in reg.interactions:
                if label and label.endswith(RELATED_BLOCK_SUFFIX) and a not in S and b not in S:
                    problems.append(Problem('wrong_subblock',
                                            f'{r.respondent_id}: {a}×{b} is in 本題相關 but '
                                            f'neither end is scoped'))

    # 3. text hygiene
    if PYTHON_LIST_RE.search(log_text):
        problems.append(Problem('python_list_repr', "payload contains \"['\""))
    if EMPTY_PARENS_RE.search(log_text):
        problems.append(Problem('empty_parens', 'payload contains empty parentheses'))
    for reg in parsed:
        for line in reg.body_lines:
            if PAREN_CODE_RE.search(line):
                problems.append(Problem('paren_code',
                                        f'{reg.rid}: residual paren code in body: {line[:60]}'))
            if TRAIT_ID_RE.search(line):
                problems.append(Problem('trait_id_in_body',
                                        f'{reg.rid}: trait id leaked into body: {line[:60]}'))
    return problems

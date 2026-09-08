"""Assemble the final LOG payload (事項 07, b §5).

    [SYSTEM PROMPT]
    <System 靜態規範全文>
    ---
    ## 【輸入數據】
    ### [受測者 | 姓名 | ID]      ← one per respondent
    #### 判讀主體特質 / （全人型＝全部特質）
    #### 其他特質索引…            ← scoped questions only
    #### 交互作用——…              ← sub-blocks from the selector
    ---
    [本輪判讀對象]                 ← 名單與人數，見 roster_block()
    [任務指令]

Everything is joined by exactly one blank line, with one exception carried over from the
client's examples: index lines follow their header immediately, with no blank between.

Two surfaces, same content:

    to_log_text()  the canonical single-string LOG. This is the artifact the DoD compares
                   against the v7 examples and what the audit log stores.
    to_messages()  transport form: the System block plus 【輸入數據】 as the system message,
                   conversation history, then 任務指令 as the user message.

Splitting at that boundary is a deliberate deviation from the client's skeleton, which
sends one blob. Reasons: selecting a quick-question module *is* the user's turn for that
request, so the instruction belongs in the user role; history has to sit between the data
and the current ask, which a single blob cannot express; the stable prefix (System +
respondent data) is what the provider's prefix cache can reuse across questions about the
same respondent; and a failed-segment rewrite can be appended as another turn instead of
re-sending the whole payload. The bytes are otherwise identical and in the same order --
only the standalone `---` document separator is dropped, since the role boundary replaces
it, and to_log_text() puts it back.
"""

from typing import Dict, List, Optional

from .interaction_selector import select_interactions
from .log_system_prompt import load_system_prompt
from .question_table import QuestionTable
from .trait_blocks import TraitBlockRenderer
from .trait_splitter import split_traits, INDEX_HEADER

SYSTEM_MARKER = '[SYSTEM PROMPT]'
DATA_HEADER = '## 【輸入數據】'
INSTRUCTION_MARKER = '[任務指令]'
ROSTER_MARKER = '[本輪判讀對象]'
SEPARATOR = '---'

# b §5 的受測者標頭是 `### [受測者 | 姓名 | ID]`，而客戶三份 v7 範例的 ID 欄都是
# RESP_TEAM_01 / RESP_R2 這種一望即知的內部代號。我們原本填的是 Traitty 的 candidate_id，
# 也就是 55、63 這類兩位數整數——模型看到「許品優 | 55」時把數字當成姓名的一部分，
# 寫進段落標題變成「許品優（55）」，而出口掃描器抓的是分數形態（數字＋分、band 字母），
# 括號裡的裸數字不符合任何一條規則，於是原樣送到客戶眼前。
#
# 改用位置代號後，模型看不到真實 ID 也就無從輸出，而 LOG 本體反而更貼近 v7 範例。
# 真實 candidate_id 仍完整保留在稽核記錄的 `respondent_id` 欄，可追溯性不受影響。
LOG_LABEL_PREFIX = 'RESP_'


def log_label_for(index: int) -> str:
    """位置代號；同一次請求內唯一，跨請求不保證穩定（它只是給模型看的區塊標記）。"""
    return f'{LOG_LABEL_PREFIX}{index + 1:02d}'


# 題庫題多人時追加的一句。約束的是「不准漏人」，不是「湊滿格數」——
# System 規範第 42 條是「缺席不臆測」，Q15 指令第十一節也寫了「若資料不足…不可假裝高度
# 確定」。寫成「必須輸出 N 段」會和這兩條打架，模型面對資料稀薄的人會傾向硬湊；所以這裡
# 明講「資料不足者仍須保留段落並說明只能判讀到什麼程度」，給它一條不違規的出路。
COVERAGE_CLAUSE = (
    '逐人分析的段落必須涵蓋以上全部 {n} 位，不得省略或合併；'
    '若某位的資料不足以明確判讀，仍須為他保留段落，並說明目前只能判讀到什麼程度。'
)


def roster_block(respondents: List['Respondent'],
                 question: Optional[dict] = None) -> str:
    """宣告本輪名單的區塊，放在 `[任務指令]` 之前。

    payload 裡原本沒有任何一句話說「本輪要判讀的是這 N 位」。而 messages 的順序是
    system(資料) → history → user(指令)，歷史因此比資料區更靠近提問——名單一變動，模型
    就照著歷史裡的舊名單作答：

      * b004c655 / req 43c1f019：名單 7 位加到 8 位，回答漏掉的正好只有新增的那一位。
      * 1a534fca / req 4920eef8：名單 1 位加到 8 位，回答宣稱「僅 Howard Hsu 一位有資料，
        其餘七位皆未包含可供分析的內容」——那七個人的特質全塊就在同一份 payload 裡。

    全部語料中名單變動的請求只有這 2 筆，2 筆都失效。所以這個區塊放在 user message 內、
    緊鄰指令，才壓得過歷史；放進【輸入數據】會被歷史隔開，等於沒放。

    只列姓名，不列 RESP_xx：把位置代號寫進指令，等於邀請模型把它抄進標題，而 4de8be30
    整串被截斷的起因正是模型寫出 `### 第一優先：Lim（受測者 | Lim | RESP_03）`。

    **題庫題原本不加這個區塊**，理由是三份 v7 客戶範例都是題庫題，逐行比對必須維持 0 差異。
    2026-09-08 req e332a385 推翻了這個取捨：名單 11 位、11 份特質全數送出，模型第一句寫的
    是「根據您提供的八位成員特質資料」，第 2 節逐人分析只寫了 7 位。指令第九節其實寫了
    「請逐一說明每個人」，但 payload 裡沒有名單可對，那句話沒有錨點——模型得自己數散落在
    2500 行特質資料裡的 11 個 `### [受測者 …]` 標頭。客戶那份會議團隊範例只有 2 個人，
    這個設計從來沒有在 11 人的規模下被驗證過。v7 逐行比對因此改成「先取出名單區塊、其餘
    維持 0 差異」，見 `verify_log_assembler.py`。

    多人題庫題才追加 `COVERAGE_CLAUSE`：

      * 自由提問不加。a6718cb3 的提問是「我是 Victoria，帶領一個 8 人的電話客服團隊」，
        Victoria 本人是提問者，不替她寫一段才是對的；點名式提問（「請只針對林慧嵐說明」）
        更是只該寫一位。自由提問的覆蓋率屬於 `completeness_check`，不在這裡用指令硬逼。
      * 單人題庫題不加：`instruction_single` 本來就是寫給一個人的，那句話沒有意義。
      * 多人題庫題加。它的 `instruction_multi` 本來就規定每人一段，這句只是把「每人」換成
        一個模型可以對照的數字。
    """
    names = '、'.join(r.name for r in respondents)
    lines = [ROSTER_MARKER,
             f'共 {len(respondents)} 位：{names}。',
             '以本節為準；先前對話若提到其他人選，一律不再視為本輪對象。']
    if question is not None and len(respondents) > 1:
        lines.append(COVERAGE_CLAUSE.format(n=len(respondents)))
    return '\n'.join(lines)


class AudienceMismatch(ValueError):
    """b §1.1: 人數與 audience 不符必須拒絕請求，不可繼續組裝."""


class UnknownTrait(ValueError):
    """A (trait_id, band) the loaded spec has no row for."""


class Respondent:
    __slots__ = ('name', 'respondent_id', 'scores', 'tests')

    def __init__(self, name: str, respondent_id: str, scores: Dict[str, str], tests=None):
        self.name = name
        self.respondent_id = respondent_id
        self.scores = scores
        self.tests = tests or sorted({t.split('_')[0] for t in scores})

    def header(self, log_label: str) -> str:
        """`log_label` is the position token, not `respondent_id` -- see LOG_LABEL_PREFIX."""
        # The empty parens that used to follow the name are gone; do not reintroduce them.
        return f'### [受測者 | {self.name} | {log_label}]'


class AssembledLog:
    __slots__ = ('body', 'instruction', 'audit', 'injected_names', 'injected_labels',
                 'log_labels', 'name_bound_ids')

    def __init__(self, body: str, instruction: str, audit: dict,
                 injected_names=None, injected_labels=None,
                 log_labels=None, name_bound_ids=None):
        self.body = body                  # [SYSTEM PROMPT] … 【輸入數據】 …
        # `[本輪判讀對象]\n…\n\n[任務指令]\n…`，見 roster_block()。
        self.instruction = instruction
        self.audit = audit
        # What the exit scanner narrows itself to for this request (b §7 per-request
        # 動態縮小): only names and labels that actually made it into the payload.
        self.injected_names = injected_names or set()
        self.injected_labels = injected_labels or set()
        # Respondent identifiers the answer must not carry. `log_labels` are the RESP_xx
        # tokens that went into the payload; `name_bound_ids` are (name, candidate_id)
        # pairs, which the scanner can only match next to the name -- a bare two-digit id
        # would collide with ordinary numbers.
        self.log_labels = log_labels or set()
        self.name_bound_ids = name_bound_ids or set()

    def to_log_text(self) -> str:
        return f'{self.body}\n\n{SEPARATOR}\n\n{self.instruction}'

    def to_messages(self, history: Optional[List[dict]] = None) -> List[dict]:
        return [{'role': 'system', 'content': self.body},
                *(history or []),
                {'role': 'user', 'content': self.instruction}]


def check_audience(respondents: List[Respondent], question: Optional[dict]):
    """Must run before assembly. A single_only question carries the placeholder string
    「僅適用單人」 in instruction_multi (and vice versa), so assembling anyway would ship a
    five-character task instruction that still produces a plausible-looking answer."""
    if question is None:
        return
    audience = question.get('audience')
    n = len(respondents)
    if n > 1 and audience == 'single_only':
        raise AudienceMismatch(
            f'question idx={question["idx"]} is single_only but {n} respondents were given')
    if n == 1 and audience == 'multi_only':
        raise AudienceMismatch(
            f'question idx={question["idx"]} is multi_only but only 1 respondent was given')


def _respondent_block(respondent: Respondent, question: Optional[dict],
                      renderer: TraitBlockRenderer, log_label: str) -> tuple:
    split = split_traits(respondent.scores, question)

    # A trait_id/band the spec doesn't have would otherwise render as None and surface as
    # a TypeError from the join, several frames away from the actual cause.
    unknown = [f'{t}_{b}' for t, b in split.full + split.index
               if renderer.render_full_block(t, b) is None]
    if unknown:
        raise UnknownTrait(f'{respondent.respondent_id}: not in trait_bands: '
                           f'{", ".join(sorted(unknown))}')

    parts = [respondent.header(log_label), split.subject_header]
    parts += [renderer.render_full_block(t, b) for t, b in split.full]

    if split.has_index_region:
        # Header and its lines form one block: no blank line in between.
        parts.append('\n'.join([INDEX_HEADER]
                               + [renderer.render_index_line(t, b) for t, b in split.index]))

    blocks = select_interactions(respondent.scores, question, split.scoped_ids)
    for block in blocks:
        parts.append(block.header)
        parts += [it.render(renderer) for it in block.items]
        if block.footnote:
            parts.append(block.footnote)

    audit = {
        # The real candidate_id stays here; only the payload sees the position token.
        'respondent_id': respondent.respondent_id,
        'log_label': log_label,
        'traits_total': len(respondent.scores),
        'full_blocks': len(split.full),
        'index_lines': len(split.index),
        'whole_person': split.whole_person,
        'interaction_blocks': {b.block_key: len(b.items) for b in blocks},
        'footnotes': [b.block_key for b in blocks if b.footnote],
    }
    return '\n\n'.join(parts), audit


class UnitCheckFailed(RuntimeError):
    """b §6 checks did not pass; the payload must not be sent."""

    def __init__(self, problems):
        self.problems = problems
        super().__init__('; '.join(str(p) for p in problems))


def assemble(respondents: List[Respondent], question: Optional[dict],
             user_query: Optional[str] = None,
             renderer: Optional[TraitBlockRenderer] = None,
             run_checks: bool = True) -> AssembledLog:
    """question=None means free-form, and then user_query is required (b §1.1).

    b §6 says the unit checks run on every assembly, so they are on by default and raise
    rather than warn -- an opt-in check is one that eventually stops being called.
    """
    if question is None and not (user_query or '').strip():
        raise ValueError('free-form mode requires user_query')
    check_audience(respondents, question)

    renderer = renderer or TraitBlockRenderer()
    blocks, audits = [], []
    scoped_by_id = {}
    names, labels = set(), set()
    log_labels, name_bound_ids = set(), set()
    for i, r in enumerate(respondents):
        label = log_label_for(i)
        text, audit = _respondent_block(r, question, renderer, label)
        blocks.append(text)
        audits.append(audit)
        log_labels.add(label)
        name_bound_ids.add((r.name, str(r.respondent_id)))
        scoped_by_id[r.respondent_id] = split_traits(r.scores, question).scoped_ids
        for trait_id, band in r.scores.items():
            names.add(renderer.name_zh(trait_id))
            labels.add(renderer.semantic_label(trait_id, band))

    body = '\n\n'.join([SYSTEM_MARKER, load_system_prompt().rstrip('\n'),
                        SEPARATOR, DATA_HEADER] + blocks)

    # `free_form_input_contract` 寫的是「[任務指令]＝user_query 原文」，所以名單宣告是一個
    # 平行的具名區塊，不動指令本身——`[任務指令]\n<user_query>` 仍然逐字存在。題庫題同理，
    # `question[key]` 一字未改。加東西，但不改既有那段的內容。
    if question is None:
        body_text = f'{INSTRUCTION_MARKER}\n{user_query.strip()}'
    else:
        key = 'instruction_multi' if len(respondents) > 1 else 'instruction_single'
        body_text = f'{INSTRUCTION_MARKER}\n{question[key]}'
    instruction_text = f'{roster_block(respondents, question)}\n\n{body_text}'

    audit = {
        'question_id': question['idx'] if question else None,
        'question_type': 'free' if question is None
                         else ('whole_person' if QuestionTable.is_whole_person(question)
                               else 'scoped'),
        'audience': 'multi' if len(respondents) > 1 else 'single',
        'respondents': audits,
    }
    log = AssembledLog(body, instruction_text, audit,
                       injected_names={n for n in names if n},
                       injected_labels={l for l in labels if l},
                       log_labels=log_labels,
                       name_bound_ids=name_bound_ids)

    if run_checks:
        from .unit_check import run_unit_checks
        problems = run_unit_checks(log.to_log_text(), respondents, question, scoped_by_id)
        audit['unit_check'] = 'passed' if not problems else [str(p) for p in problems]
        if problems:
            raise UnitCheckFailed(problems)
    return log

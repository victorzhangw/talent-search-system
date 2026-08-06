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
SEPARATOR = '---'


class AudienceMismatch(ValueError):
    """b §1.1: 人數與 audience 不符必須拒絕請求，不可繼續組裝."""


class Respondent:
    __slots__ = ('name', 'respondent_id', 'scores', 'tests')

    def __init__(self, name: str, respondent_id: str, scores: Dict[str, str], tests=None):
        self.name = name
        self.respondent_id = respondent_id
        self.scores = scores
        self.tests = tests or sorted({t.split('_')[0] for t in scores})

    @property
    def header(self) -> str:
        # The empty parens that used to follow the name are gone; do not reintroduce them.
        return f'### [受測者 | {self.name} | {self.respondent_id}]'


class AssembledLog:
    __slots__ = ('body', 'instruction', 'audit')

    def __init__(self, body: str, instruction: str, audit: dict):
        self.body = body                  # [SYSTEM PROMPT] … 【輸入數據】 …
        self.instruction = instruction    # [任務指令]\n…
        self.audit = audit

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
                      renderer: TraitBlockRenderer) -> tuple:
    split = split_traits(respondent.scores, question)
    parts = [respondent.header, split.subject_header]
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
        'respondent_id': respondent.respondent_id,
        'traits_total': len(respondent.scores),
        'full_blocks': len(split.full),
        'index_lines': len(split.index),
        'whole_person': split.whole_person,
        'interaction_blocks': {b.block_key: len(b.items) for b in blocks},
        'footnotes': [b.block_key for b in blocks if b.footnote],
    }
    return '\n\n'.join(parts), audit


def assemble(respondents: List[Respondent], question: Optional[dict],
             user_query: Optional[str] = None,
             renderer: Optional[TraitBlockRenderer] = None) -> AssembledLog:
    """question=None means free-form, and then user_query is required (b §1.1)."""
    if question is None and not (user_query or '').strip():
        raise ValueError('free-form mode requires user_query')
    check_audience(respondents, question)

    renderer = renderer or TraitBlockRenderer()
    blocks, audits = [], []
    for r in respondents:
        text, audit = _respondent_block(r, question, renderer)
        blocks.append(text)
        audits.append(audit)

    body = '\n\n'.join([SYSTEM_MARKER, load_system_prompt().rstrip('\n'),
                        SEPARATOR, DATA_HEADER] + blocks)

    if question is None:
        instruction_text = user_query.strip()
    else:
        key = 'instruction_multi' if len(respondents) > 1 else 'instruction_single'
        instruction_text = question[key]

    audit = {
        'question_id': question['idx'] if question else None,
        'question_type': 'free' if question is None
                         else ('whole_person' if QuestionTable.is_whole_person(question)
                               else 'scoped'),
        'audience': 'multi' if len(respondents) > 1 else 'single',
        'respondents': audits,
    }
    return AssembledLog(body, f'{INSTRUCTION_MARKER}\n{instruction_text}', audit)

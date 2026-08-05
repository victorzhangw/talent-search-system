"""The static System block that every LOG payload starts with.

Source of truth is `a_LOG完成版模板_v2_20260727.md` 第一部分 (b §5: "[SYSTEM PROMPT]
（a 文件第一部分，靜態常數）"). The text is stored verbatim in
prompts/log_system_prompt.txt -- it is a constant, not a template: no placeholders,
no per-request substitution, identical for every question type and every respondent.

It replaces the per-module 禁令 blocks that the 22 module prompts each carry their
own copy of today ("取代各題原本重複的禁止段與判讀規範段"), so a rule change is one
edit here instead of 22.

Known divergence from the three v7 LOG examples, deliberately kept: rule 15 in the
a-document ends with an extra clause about 全人型／自由提問 treating 「其他參考」 as a
whole-person pool. The examples were rendered before that clause was added (it matches
the 2026-07-28 全注入 ruling, which post-dates them). The a-document is the defined
source per b §5, so we follow it; scripts/verify_system_prompt.py reports this one
line explicitly rather than letting it fail an example-diff silently.
"""

import os

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'log_system_prompt.txt')

_cache = None


def load_system_prompt() -> str:
    """Verbatim System block, trailing '---' included (the assembler adds its own
    separator after it, which is why the rendered LOG shows two)."""
    global _cache
    if _cache is None:
        with open(os.path.abspath(_PROMPT_PATH), encoding='utf-8') as f:
            _cache = f.read()
    return _cache


def reset_cache():
    """For tests / after editing the file in a long-running process."""
    global _cache
    _cache = None

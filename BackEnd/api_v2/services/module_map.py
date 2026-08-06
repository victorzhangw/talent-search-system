"""Map the frontend's `module_id` onto a question table `idx` (事項 04).

`GET /api/v2/modules/` returns English ids (`recruit_interview`, …) while the question
table identifies questions by `idx` plus a Chinese title, with no shared key -- the
client's README lists this as an open integration gap ("未補前選題無法自動對接").

The correspondence already exists in practice: `quick_modules.json` and the question
table hold the same 22 entries, in the same order, with identical titles. But it lives
only in the fact that two files happen to be sorted the same way, which breaks silently
the first time either side inserts or reorders an entry.

So the map is built by exact title match, not by position, and validated at import:
every module resolves, no two modules share a question, and each module's
`candidate_mode` agrees with its question's `audience`. A mismatch raises rather than
degrading, because the failure mode it prevents is a wrong-audience task instruction
being packed into a payload that otherwise looks perfectly normal.
"""

import json
import os
from typing import Dict, Optional

from .question_table import table

_MODULES = os.path.join(os.path.dirname(__file__), '..', 'config', 'quick_modules.json')

# 03_API對接說明 §3: single <-> single_only, multi <-> multi_only, both accepts either.
_MODE_TO_AUDIENCE = {'single_only': 'single_only',
                     'multi_only': 'multi_only',
                     'both': 'both'}


class ModuleMap:
    def __init__(self, modules_path: Optional[str] = None):
        with open(os.path.abspath(modules_path or _MODULES), encoding='utf-8') as f:
            self.modules: Dict[str, dict] = json.load(f)

        by_title = {q['title']: q for q in table.all()}
        self._to_idx: Dict[str, int] = {}
        problems = []

        for module_id, cfg in self.modules.items():
            question = by_title.get(cfg.get('display_name'))
            if question is None:
                problems.append(f'{module_id}: no question titled {cfg.get("display_name")!r}')
                continue
            if question['idx'] in self._to_idx.values():
                problems.append(f'{module_id}: idx {question["idx"]} already claimed')
            expected = _MODE_TO_AUDIENCE.get(cfg.get('candidate_mode'))
            if expected != question['audience']:
                problems.append(f'{module_id}: candidate_mode={cfg.get("candidate_mode")} '
                                f'but question audience={question["audience"]}')
            self._to_idx[module_id] = question['idx']

        unmapped = [q['idx'] for q in table.all() if q['idx'] not in self._to_idx.values()]
        if unmapped:
            problems.append(f'questions with no module: {unmapped}')
        if problems:
            raise ValueError('module_id <-> question mapping is inconsistent: '
                             + '; '.join(problems))

    def __len__(self):
        return len(self._to_idx)

    def idx_for(self, module_id: str) -> Optional[int]:
        return self._to_idx.get(module_id)

    def question_for(self, module_id: str) -> Optional[dict]:
        idx = self.idx_for(module_id)
        return table.get(idx) if idx is not None else None

    def module_for(self, idx: int) -> Optional[str]:
        for module_id, mapped in self._to_idx.items():
            if mapped == idx:
                return module_id
        return None

    def as_dict(self) -> Dict[str, int]:
        return dict(self._to_idx)


module_map = ModuleMap()

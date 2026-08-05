"""Access to the quick-question table (T1 in b §0).

Runtime copy of the client's `question_injection_table_v9.json` lives in config/. The
instruction text in it is the client's property -- `_source_of_truth` states the master
is `c_快速提問重構版_v9.xlsx` and that only derived fields are regenerated -- so this
module reads it and never rewrites it.

Questions are identified by `idx` (b §1.1: "請以 idx 為 question_id；title 僅供人閱").
Mapping the frontend's `module_id` onto an idx is a separate, still-open item (事項 04).

Two same-looking fields, easy to confuse and consequential (see 事項 05/06):

    scoped_traits  -- the question's scoped set S, grouped by test. Drives the FULL
                      trait blocks. This is the one this module exposes for splitting.
    injection_set  -- scoped_traits flattened, UNION the three calibration traits.
                      Drives the interaction filter only. Using it for the split would
                      promote CIA_33/ANI_23/SPA_12 to full blocks, which b §2 forbids.
"""

import json
import os
from typing import Dict, Iterable, List, Optional

_CONFIG = os.path.join(os.path.dirname(__file__), '..', 'config',
                       'question_injection_table_v9.json')

WHOLE_PERSON = 'whole_person'
SCOPED = 'scoped'


class QuestionTable:
    def __init__(self, config_path=None):
        with open(os.path.abspath(config_path or _CONFIG), encoding='utf-8') as f:
            data = json.load(f)
        self.version = data.get('version')
        self.calibration_traits = set(data.get('calibration_traits') or [])
        self._by_idx = {q['idx']: q for q in data['questions']}
        self._by_title = {q['title']: q for q in data['questions']}

    def __len__(self):
        return len(self._by_idx)

    def get(self, question_id) -> Optional[dict]:
        """By idx (int or numeric string); falls back to the Chinese title."""
        try:
            return self._by_idx.get(int(question_id))
        except (TypeError, ValueError):
            return self._by_title.get(question_id)

    def all(self) -> List[dict]:
        return [self._by_idx[i] for i in sorted(self._by_idx)]

    @staticmethod
    def is_whole_person(question: Optional[dict]) -> bool:
        """Free-form (no question) follows the whole-person path -- b §2: 自由提問或全人型題
        → S = P 的全部 ID."""
        return question is None or question.get('type') == WHOLE_PERSON

    @staticmethod
    def scoped_ids(question: Optional[dict], tests: Optional[Iterable[str]] = None) -> set:
        """S for a scoped question, restricted to the tests the respondent actually took.
        Empty for whole-person/free-form -- callers use the whole of P there instead.

        No construct-family expansion happens here: b §3 of the design note puts that in
        the data-generation step ("打包程式不得在 runtime 再做一次 S 擴張"), and the family
        table includes the SDR calibration family, so expanding would promote calibration
        traits to full blocks.
        """
        if QuestionTable.is_whole_person(question):
            return set()
        scoped: Dict[str, list] = question.get('scoped_traits') or {}
        keys = list(scoped) if tests is None else [t for t in tests if t in scoped]
        return {tid for k in keys for tid in scoped[k]}


table = QuestionTable()

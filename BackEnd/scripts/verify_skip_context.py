"""Every dropped trait must name the respondent it belonged to (U4).

Usage:
    python scripts/verify_skip_context.py

Runs against a stubbed session, so no database is needed and the branch under test is
chosen by the stub rather than by what happens to be in `trait_definitions`.

Why this exists
---------------
2026-08-31 production: 235 traits were dropped across 21 requests, 183 of them from a
single report that claimed `project_name_abbreviation = 'SPA'` while carrying 79 traits.
The warnings recorded only `project_abbrev` and `display_name`, so the report could not be
attributed to a respondent directly -- it took subtracting the skip sets of two other
sessions to narrow it to one of three people. `candidate_id` is the same key the audit
record uses for `respondent_id`, so with it the two files join.

`api_trait_id` is recorded alongside. Nothing matches on it -- the vendor's ids share no
namespace with the spec's (`68b`/`99f` in a CIA report, `6`..`81` in a CSR one, no
overlap) -- but a skip that names the vendor's own id is the only form the vendor can act
on, and it is the raw material for a future id-keyed lookup.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'),
            encoding='utf-8-sig')

from api_v2.database import TraitBand, TraitDefinition          # noqa: E402
from api_v2.services import respondent_adapter                  # noqa: E402
from api_v2.services.respondent_adapter import from_trait_reports  # noqa: E402

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}"
          f"{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


class _Query:
    def __init__(self, result):
        self._result = result

    def filter(self, *a, **k):
        return self

    def filter_by(self, **k):
        return self

    def first(self):
        return self._result


class _Session:
    """Answers by model class, so a test picks its branch without SQL expressions."""

    def __init__(self, trait_def=None, band_row=None):
        self.trait_def = trait_def
        self.band_row = band_row

    def query(self, model):
        if model is TraitDefinition:
            return _Query(self.trait_def)
        if model is TraitBand:
            return _Query(self.band_row)
        return _Query(None)


class _Row:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def collect(reports, basics=None, trait_def=None, band_row=None):
    """Returns (respondents, [(reason, ctx), ...]) with the session stubbed."""
    skips = []
    original = respondent_adapter.db_session
    respondent_adapter.db_session = _Session(trait_def, band_row)
    try:
        resp = from_trait_reports(reports, basics or [],
                                  on_skip=lambda reason, ctx: skips.append((reason, ctx)))
    finally:
        respondent_adapter.db_session = original
    return resp, skips


# The shape `reports.py` hands the frontend, and the frontend hands back to /chat.
REPORT = {
    '88': {
        'project_name_abbreviation': 'SPA',
        'traits': [
            {'trait_id': '73', 'name': 'Warmth', 'score': 71, 'band': ''},
            {'trait_id': '99f', 'name': 'Extraversion', 'score': 64, 'band': ''},
        ],
    }
}
BASICS = [{'candidate_id': '88', 'name': 'Nathan'}]


def main():
    print('\n[1] no_trait_def_match names the respondent and the vendor id')
    _, skips = collect(REPORT, BASICS, trait_def=None)
    check('both traits were skipped', len(skips) == 2, [s[0] for s in skips])
    check('all of them are no_trait_def_match',
          all(r == 'no_trait_def_match' for r, _ in skips), [r for r, _ in skips])
    check('every skip carries candidate_id',
          all(c.get('candidate_id') == '88' for _, c in skips), [c for _, c in skips])
    check('every skip carries the vendor trait id',
          [c.get('api_trait_id') for _, c in skips] == ['73', '99f'],
          [c.get('api_trait_id') for _, c in skips])
    check('the existing fields are untouched',
          all(c.get('project_abbrev') == 'SPA' and c.get('display_name') for _, c in skips),
          [(c.get('project_abbrev'), c.get('display_name')) for _, c in skips])

    print('\n[2] The id survives the frontend payload -> trait_results hop')
    # respondent_adapter.from_trait_reports used to build trait_results from `name` and
    # `score` only, so the id the frontend already had was gone before resolution started.
    seen = []
    original = respondent_adapter.db_session
    respondent_adapter.db_session = _Session(None)
    real_results_list = respondent_adapter._results_list
    respondent_adapter._results_list = lambda a, c: seen.extend(real_results_list(a, c)) or seen
    try:
        from_trait_reports(REPORT, BASICS, on_skip=lambda r, c: None)
    finally:
        respondent_adapter._results_list = real_results_list
        respondent_adapter.db_session = original
    check('trait_results entries carry trait_id',
          [r.get('trait_id') for r in seen] == ['73', '99f'],
          [sorted(r) for r in seen[:1]])
    check('and still carry the name and score the matcher uses',
          all(r.get('chinese_name') and r.get('score') is not None for r in seen))

    print('\n[3] The other skip reasons carry it too')
    no_score = {'88': {'project_name_abbreviation': 'SPA',
                       'traits': [{'trait_id': '73', 'name': 'Warmth', 'score': None}]}}
    _, skips = collect(no_score, BASICS, trait_def=_Row(trait_id='SPA_04'))
    check('no_score names the vendor id and the resolved id',
          skips and skips[0][0] == 'no_score'
          and skips[0][1].get('api_trait_id') == '73'
          and skips[0][1].get('trait_id') == 'SPA_04', skips)
    check('and the respondent', skips and skips[0][1].get('candidate_id') == '88', skips)

    _, skips = collect(REPORT, BASICS, trait_def=_Row(trait_id='SPA_04'), band_row=None)
    check('no_band_range names the vendor id',
          skips and skips[0][0] == 'no_band_range'
          and skips[0][1].get('api_trait_id') == '73', skips)

    no_name = {'88': {'project_name_abbreviation': 'SPA',
                      'traits': [{'trait_id': '73', 'name': None, 'score': 71}]}}
    _, skips = collect(no_name, BASICS)
    check('no_name names the vendor id',
          skips and skips[0][0] == 'no_name' and skips[0][1].get('api_trait_id') == '73',
          skips)

    no_proj = {'88': {'traits': [{'trait_id': '73', 'name': 'Warmth', 'score': 71}]}}
    _, skips = collect(no_proj, BASICS)
    check('a report with no project_name_abbreviation still reports the respondent',
          skips and skips[0][1].get('candidate_id') == '88', skips)

    print('\n[4] Resolution itself is unchanged')
    band = _Row(band='B', trait_id='SPA_04')
    resp, skips = collect(REPORT, BASICS, trait_def=_Row(trait_id='SPA_04'), band_row=band)
    check('a resolvable report still produces a respondent', len(resp) == 1, resp)
    check('with the name from candidates_info',
          resp and resp[0].name == 'Nathan', [r.name for r in resp])
    check('and the band taken from trait_bands, not the API',
          resp and resp[0].scores == {'SPA_04': 'B'}, [r.scores for r in resp])
    check('nothing was skipped', not skips, skips)

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

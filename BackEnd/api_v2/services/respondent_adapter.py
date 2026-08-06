"""Turn a Talent Chat API candidate payload into packer inputs (事項 03).

The API and our spec do not share keys. Its `trait_id` values (`99f`, `147b`) are unrelated
to the spec's (`CIA_16`), and its `chinese_name` field actually carries the English name
(`Hope`, `Gratitude`). So a trait is resolved by matching that English name against
`trait_definitions.name_en`, restricted to the report's own assessment via
`project_name_abbreviation`, with the Chinese name as a fallback. The band is not taken
from the API either -- it is recomputed from the score against `trait_bands`.

This lives here rather than inside `context_builder` because both the legacy prompt path
and the new LOG packer need the same answer; two copies of this resolution would drift,
and a drifted band silently changes which narrative a respondent is shown.
"""

import re
from typing import Callable, Dict, List, Optional

from sqlalchemy import func

from ..database import db_session, TraitBand, TraitDefinition

_NON_ALNUM_RE = re.compile(r'[^a-zA-Z0-9]')


def normalize_en_name(value: str) -> str:
    """Vendor formatting varies ('Self-Discipline' vs 'Self Discipline'); compare on
    letters and digits only. This does not paper over genuinely different wording."""
    if not value:
        return value
    return _NON_ALNUM_RE.sub('', value).lower()


class ResolvedTrait:
    __slots__ = ('trait_id', 'score', 'band_row')

    def __init__(self, trait_id, score, band_row):
        self.trait_id = trait_id
        self.score = score
        self.band_row = band_row

    @property
    def band(self):
        return self.band_row.band

    def __iter__(self):
        # Kept tuple-compatible for existing callers that unpack (trait_id, score, band_row).
        return iter((self.trait_id, self.score, self.band_row))


def _results_list(assessment: dict, candidate: dict):
    results = (assessment or {}).get('trait_results') or candidate.get('trait_results')
    if not results and isinstance(assessment, (dict, str)) and 'trait_id' in str(assessment):
        results = assessment
    if isinstance(results, dict):
        return list(results.values())
    if isinstance(results, list):
        return results
    return []


def resolve_traits(candidate: dict,
                   on_skip: Optional[Callable[[str, dict], None]] = None
                   ) -> List[ResolvedTrait]:
    """Every trait we could place on the spec's scale. Anything unresolvable is skipped
    and reported through `on_skip(reason, context)` -- never guessed at, because guessing
    the assessment or the band would silently attach the wrong narrative."""
    def skip(reason, **ctx):
        if on_skip:
            on_skip(reason, ctx)

    assessment = candidate.get('assessment', {}) or {}
    out: List[ResolvedTrait] = []

    for res in _results_list(assessment, candidate):
        display_name = res.get('chinese_name') or res.get('trait_name')
        if not display_name:
            skip('no_name', raw_res=res)
            continue

        project_abbrev = assessment.get('project_name_abbreviation')
        if not project_abbrev:
            skip('no_project_abbrev', display_name=display_name)
            continue

        normalized_name_en = func.lower(
            func.regexp_replace(TraitDefinition.name_en, r'[^a-zA-Z0-9]', '', 'g'))
        trait_def = db_session.query(TraitDefinition).filter(
            normalized_name_en == normalize_en_name(display_name),
            TraitDefinition.trait_id.like(f'{project_abbrev}_%')).first()

        if not trait_def:
            trait_def = db_session.query(TraitDefinition).filter(
                func.trim(func.lower(TraitDefinition.name_zh))
                == func.trim(func.lower(display_name)),
                TraitDefinition.trait_id.like(f'{project_abbrev}_%')).first()

        if not trait_def:
            skip('no_trait_def_match', project_abbrev=project_abbrev, display_name=display_name)
            continue

        score = res.get('score')
        if score is None:
            skip('no_score', trait_id=trait_def.trait_id, display_name=display_name)
            continue

        band_row = db_session.query(TraitBand).filter(
            TraitBand.trait_id == trait_def.trait_id,
            TraitBand.min_score <= score,
            TraitBand.max_score >= score).first()

        if not band_row:
            skip('no_band_range', trait_id=trait_def.trait_id, score=score,
                 display_name=display_name)
            continue

        out.append(ResolvedTrait(trait_def.trait_id, score, band_row))
    return out


def scores_of(candidate: dict, on_skip=None) -> Dict[str, str]:
    """{trait_id: band} -- the packer's P."""
    return {t.trait_id: t.band for t in resolve_traits(candidate, on_skip)}


def from_trait_reports(trait_reports: dict, candidates_info: Optional[List[dict]] = None,
                       on_skip=None):
    """Respondents straight from the frontend payload.

    `trait_reports` is `{candidate_id: {project_name_abbreviation, traits: [...]}}` as the
    chat route receives it. This reads it directly instead of going through the legacy
    merge inside `generate_response`, which is inlined there and also serves the
    upstream-fetch path. A report without `project_name_abbreviation` is skipped rather
    than defaulted -- guessing the assessment would resolve the trait against the wrong
    one of the four.
    """
    basics = {str(c.get('candidate_id')): c for c in (candidates_info or [])}
    candidates = []
    for cand_id, report in (trait_reports or {}).items():
        cand_id = str(cand_id)
        project_abbrev = (report or {}).get('project_name_abbreviation')
        if not project_abbrev:
            if on_skip:
                on_skip('no_project_abbrev', {'candidate_id': cand_id})
            continue
        basic = basics.get(cand_id, {})
        candidates.append({
            'candidate_id': cand_id,
            'name': basic.get('name') or f'Candidate-{cand_id}',
            'assessment': {
                'project_name_abbreviation': project_abbrev,
                'trait_results': [{'chinese_name': t.get('name'), 'score': t.get('score')}
                                  for t in (report.get('traits') or [])],
            },
        })
    return to_respondents(candidates, on_skip)


def to_respondents(candidates_data: List[dict], on_skip=None):
    """Packer-ready respondents. Import is local so this module stays usable from
    contexts that do not pull in the assembler."""
    from .log_assembler import Respondent
    out = []
    for candidate in candidates_data:
        cand_id = candidate.get('candidate_id', 'Unknown')
        name = candidate.get('name') or f'Candidate-{cand_id}'
        scores = scores_of(candidate, on_skip)
        if scores:
            out.append(Respondent(name, str(cand_id), scores))
    return out

"""Verify EndpointRegistry against the DB and the client's source-of-truth JSON.

Usage:
    python scripts/verify_endpoint_registry.py

Checks the registry answers the questions the LOG packer will ask it, and that the
answers match `question_injection_table_v9.json` (risk_endpoints.adopted /
calibration_traits) rather than anything hard-coded in our code.
"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

from api_v2.services.endpoint_registry import registry, ANY_BAND  # noqa: E402

SPEC_JSON = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', '0730',
                         'Traitty_調整_20260728＿final', 'question_injection_table_v9.json')

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def main():
    spec = json.load(open(SPEC_JSON, encoding='utf-8'))
    spec_risk = {tuple(x) for x in spec['risk_endpoints']['adopted']}
    spec_calib = set(spec['calibration_traits'])

    registry.refresh()

    print('\n[1] Blocks loaded from DB')
    blocks = registry.blocks
    check('3 blocks present', len(blocks) == 3, sorted(blocks))
    check('headers are the verbatim spec strings',
          registry.header('related') == '#### 交互作用——本題相關'
          and registry.header('calib_risk') == '#### 交互作用——作答校準與風險提示'
          and registry.header('other') == '#### 交互作用——其他參考')
    check('scoped question sees related + calib_risk only',
          [b.block_key for b in registry.ordered_blocks('scoped')] == ['related', 'calib_risk'])
    check('whole_person sees calib_risk + other only',
          [b.block_key for b in registry.ordered_blocks('whole_person')] == ['calib_risk', 'other'])

    print('\n[2] Endpoint set matches the client JSON (not hard-coded)')
    check('endpoint types are exactly risk + calibration',
          registry.endpoint_types() == {'risk', 'calibration'}, registry.endpoint_types())
    db_risk = registry.pairs_for_type('risk')
    check('71 risk endpoints, symmetric difference with JSON is 0',
          db_risk == spec_risk, f'{len(db_risk)} rows, diff {len(db_risk ^ spec_risk)}')
    calib_pairs = registry.pairs_for_type('calibration')
    check('calibration traits match JSON', {t for t, _ in calib_pairs} == spec_calib,
          sorted(t for t, _ in calib_pairs))
    check('calibration is stored trait-level (band = *)',
          all(b == ANY_BAND for _, b in calib_pairs))

    print('\n[3] Hit testing on a respondent')
    # CIA_05_C = risk endpoint; CIA_33 = calibration (any band); CIA_01_A = neither.
    scores = {'CIA_05': 'C', 'CIA_33': 'A', 'CIA_01': 'A'}
    check('R (risk only) == {CIA_05}', registry.hit_trait_ids(scores, 'risk') == {'CIA_05'},
          registry.hit_trait_ids(scores, 'risk'))
    check('trigger set (calibration union R) == {CIA_05, CIA_33}',
          registry.hit_trait_ids(scores) == {'CIA_05', 'CIA_33'}, registry.hit_trait_ids(scores))
    check('calibration hits at any band',
          registry.types_for('CIA_33', 'B') == registry.types_for('CIA_33', 'C') != {})
    check('non-endpoint band of a risk trait does not hit',
          registry.types_for('CIA_05', 'A') == {}, registry.types_for('CIA_05', 'A'))

    print('\n[4] property_peak: both ends of the same trait are endpoints')
    for trait in ('CIA_27', 'SPA_09'):
        check(f'{trait} A and C both hit, B does not',
              registry.types_for(trait, 'A') and registry.types_for(trait, 'C')
              and not registry.types_for(trait, 'B'))

    print('\n[5] Block resolution for one interaction')
    S = {'CIA_01'}
    check('touches S -> related (priority beats endpoint blocks)',
          registry.block_for_interaction(('CIA_01', 'CIA_05'), scores, S, 'scoped') == 'related')
    check('endpoint only -> calib_risk',
          registry.block_for_interaction(('CIA_05', 'CIA_33'), scores, S, 'scoped') == 'calib_risk')
    check('scoped, touches nothing -> None (filtered out upstream)',
          registry.block_for_interaction(('CIA_02', 'CIA_03'), scores, S, 'scoped') is None)
    check('whole_person, touches endpoint -> calib_risk',
          registry.block_for_interaction(('CIA_05', 'CIA_02'), scores, None, 'whole_person')
          == 'calib_risk')
    check('whole_person, touches nothing -> other (fallback, never dropped)',
          registry.block_for_interaction(('CIA_02', 'CIA_03'), scores, None, 'whole_person')
          == 'other')
    check('related is not offered to whole_person questions',
          registry.resolve_block(['related'], 'whole_person') is None)

    print('\n[6] Mixed-type collision (28 such rows exist in sheet 08)')
    # CIA_05_C is a risk endpoint, CIA_33 is calibration: both map to calib_risk today,
    # so the interaction is rendered once. This is the case that needs a tie-break the
    # moment a new endpoint type gets its own block.
    keys = set()
    for t in ('CIA_05', 'CIA_33'):
        keys.update(registry.types_for(t, scores[t]).values())
    check('both types resolve to a single block (rendered once)', len(set(keys)) == 1, keys)

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

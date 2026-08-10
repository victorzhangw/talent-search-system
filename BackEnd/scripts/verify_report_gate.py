"""The chat route must refuse a candidate-scoped request that carries no trait reports.

Reproduces the reported bug: quick question sent before the batch-report fetch lands, so
trait_reports is empty while candidates_info still names the candidates. Before the gate,
this reached the LLM and came back as a confident, entirely fabricated answer.
"""

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'),
            encoding='utf-8-sig')

import jwt as pyjwt
from api_v2.app import create_app

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def main():
    app = create_app()
    secret = os.getenv('PARTY_A_PLUGIN_SECRET', 'traitty_ai_api')
    token = pyjwt.encode({'sub': 'tester', 'aud': 'traitty',
                          'exp': 4102444800}, secret, algorithm='HS256')
    client = app.test_client()

    def post(body):
        return client.post('/chat/', json=body,
                           headers={'Authorization': f'Bearer {token}'})

    assessed = {'candidate_id': '56', 'name': '王智弘',
                'latest_assessment': {'assessment_id': 900}}
    never_assessed = {'candidate_id': '77', 'name': '林孟德', 'latest_assessment': None}
    base = {'query': '他的溝通風格如何？', 'session_id': 'GATE_TEST',
            'user_id': 'tester@example.com', 'mode': 'expert'}

    print('\n[1] 快速提問 + 報告未到 -> 409，且不呼叫 LLM')
    r = post({**base, 'module_id': 'mgmt_pressure', 'candidate_ids': ['56'],
              'candidates_info': [assessed], 'trait_reports': {}})
    body = r.get_json()
    check('status 409', r.status_code == 409, r.status_code)
    check('code is TRAIT_REPORTS_NOT_READY',
          body.get('error', {}).get('code') == 'TRAIT_REPORTS_NOT_READY', body.get('error'))
    check('the response is not an SSE stream (no answer was generated)',
          'text/event-stream' not in (r.content_type or ''), r.content_type)
    check('message tells the user to wait',
          '尚未載入' in (body.get('error', {}).get('message') or ''),
          body.get('error', {}).get('message'))

    print('\n[2] 部分候選人缺報告 -> 同樣擋下')
    r = post({**base, 'module_id': 'deep_communication', 'candidate_ids': ['56', '77'],
              'candidates_info': [assessed, {'candidate_id': '77', 'name': '林孟德',
                                             'latest_assessment': {'assessment_id': 901}}],
              'trait_reports': {'56': {'project_name_abbreviation': 'CIA', 'traits': []}}})
    check('status 409', r.status_code == 409, r.status_code)

    print('\n[3] 全部從未受測 -> 422，訊息不同（重試永遠不會好）')
    r = post({**base, 'module_id': 'mgmt_pressure', 'candidate_ids': ['77'],
              'candidates_info': [never_assessed], 'trait_reports': {}})
    body = r.get_json()
    check('status 422', r.status_code == 422, r.status_code)
    check('code is NO_ASSESSMENT_DATA',
          body.get('error', {}).get('code') == 'NO_ASSESSMENT_DATA', body.get('error'))
    check('names the candidate', '林孟德' in (body.get('error', {}).get('message') or ''),
          body.get('error', {}).get('message'))

    print('\n[4] 沒選受測者的一般對話 -> 不受影響')
    r = post({**base, 'module_id': None, 'candidate_ids': [], 'candidates_info': [],
              'trait_reports': {}})
    check('not rejected by the gate', r.status_code != 409 and r.status_code != 422,
          r.status_code)

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

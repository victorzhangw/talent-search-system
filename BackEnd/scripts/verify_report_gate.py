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
    # email 是必要欄位——/chat/ 要用它決定打上游時的身分（0905 文件 E-9）。
    token = pyjwt.encode({'sub': 'tester', 'email': 'tester@example.com',
                          'aud': 'traitty', 'exp': 4102444800}, secret, algorithm='HS256')
    client = app.test_client()

    def post(body):
        return client.post('/chat/', json=body,
                           headers={'Authorization': f'Bearer {token}'})

    assessed = {'candidate_id': '56', 'name': '王智弘',
                'latest_assessment': {'assessment_id': 900}}
    never_assessed = {'candidate_id': '77', 'name': '林孟德', 'latest_assessment': None}
    base = {'query': '他的溝通風格如何？', 'session_id': 'GATE_TEST',
            'user_id': 'tester@example.com'}

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

    print('\n[4] 名單上有、candidates_info 沒有 -> 第三種結果，不能說「請稍候」')
    # 2026-09-20 的形狀：前端新增人選時掉了一位的人物件，名單 2 位、資料列 1 位。
    # 舊版守門走訪 candidates_info，這種截短完全看不到，於是放行——打包器把那位丟掉，
    # 使用者拿到一份少一個人、卻毫無提示的回答。
    r = post({**base, 'module_id': 'mgmt_pressure', 'candidate_ids': ['56', '391'],
              'candidates_info': [assessed],
              'trait_reports': {'56': {'project_name_abbreviation': 'CIA', 'traits': []}}})
    body = r.get_json()
    check('status 422（重試永遠不會好，不是 409）', r.status_code == 422, r.status_code)
    check('code is ROSTER_INCOMPLETE',
          body.get('error', {}).get('code') == 'ROSTER_INCOMPLETE', body.get('error'))
    check('沒有產生任何回答', 'text/event-stream' not in (r.content_type or ''), r.content_type)
    msg = body.get('error', {}).get('message') or ''
    check('訊息叫使用者重選，而不是等一下', '重新選擇' in msg and '稍候' not in msg, msg)

    print('\n[5] 名單不完整優先於「報告還沒到」——後者的指示對前者是錯的')
    r = post({**base, 'module_id': 'deep_communication', 'candidate_ids': ['56', '77', '391'],
              'candidates_info': [assessed, {'candidate_id': '77', 'name': '林孟德',
                                             'latest_assessment': {'assessment_id': 901}}],
              'trait_reports': {'56': {'project_name_abbreviation': 'CIA', 'traits': []}}})
    check('兩種缺法同時存在時，先報名單不完整',
          r.get_json().get('error', {}).get('code') == 'ROSTER_INCOMPLETE',
          r.get_json().get('error'))

    print('\n[6] candidates_info 比名單多出來的人不再被誤擋（打包器本來就會丟掉他們）')
    r = post({**base, 'module_id': 'mgmt_pressure', 'candidate_ids': ['56'],
              'candidates_info': [assessed, never_assessed],
              'trait_reports': {'56': {'project_name_abbreviation': 'CIA', 'traits': []}}})
    check('名單內的人報告齊全就放行', r.status_code not in (409, 422), r.status_code)

    print('\n[7] 舊版 widget 只送 candidates_info、不送 candidate_ids -> 行為不變')
    r = post({**base, 'module_id': 'mgmt_pressure', 'candidates_info': [never_assessed],
              'trait_reports': {}})
    check('仍然擋下並回 NO_ASSESSMENT_DATA',
          r.status_code == 422
          and r.get_json().get('error', {}).get('code') == 'NO_ASSESSMENT_DATA',
          (r.status_code, r.get_json().get('error')))

    print('\n[8] 沒選受測者的一般對話 -> 不受影響')
    r = post({**base, 'module_id': None, 'candidate_ids': [], 'candidates_info': [],
              'trait_reports': {}})
    check('not rejected by the gate', r.status_code != 409 and r.status_code != 422,
          r.status_code)

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

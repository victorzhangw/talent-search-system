"""The meta event must carry the typewriter switch, and the switch must actually flip it.

The frontend decides whether to replay a segment character by character purely from this
event, so if the field silently stops being sent the widget falls back to pasting whole
360-char blocks and nothing else in the system notices. That is exactly how the original
`packed_chat` docstring ended up describing a client-side replay that was never built.

No LLM is called: `generate_response` is stubbed, because what is under test is the
transport of a config value, not the model.
"""

import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api_v2', '.env'),
            encoding='utf-8-sig')

import jwt as pyjwt  # noqa: E402
from api_v2.app import create_app  # noqa: E402
from api_v2.routes import chat as chat_route  # noqa: E402

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}"
          f"{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


class _Chunk:
    def __init__(self, content):
        self.usage = None
        self.choices = [type('C', (), {'delta': type('D', (), {'content': content})()})()]


def meta_of(app, **overrides):
    """Drive one request and hand back the parsed meta event."""
    for key, value in overrides.items():
        app.config[key] = value

    secret = os.getenv('PARTY_A_PLUGIN_SECRET', 'traitty_ai_api')
    token = pyjwt.encode({'sub': 'tester', 'aud': 'traitty', 'exp': 4102444800},
                         secret, algorithm='HS256')
    r = app.test_client().post(
        '/chat/',
        json={'query': '你好', 'session_id': 'TYPEWRITER_TEST',
              'user_id': 'tester@example.com', 'mode': 'expert',
              'candidate_ids': [], 'candidates_info': [], 'trait_reports': {}},
        headers={'Authorization': f'Bearer {token}'})
    body = r.get_data(as_text=True)
    for line in body.split('\n\n'):
        if line.startswith('data: '):
            event = json.loads(line[6:])
            if event.get('type') == 'meta':
                return event
    print(body[:800])
    return None


def main():
    app = create_app()

    # Stub the model. The route holds a module-level singleton built in before_request,
    # so patching the class is not enough -- the instance is what gets called.
    chat_route.rag_service = type('Stub', (), {
        'model_name': 'stub',
        'generate_response': lambda self, *a, **k: (iter([_Chunk('嗨')]), 'general_chat'),
        'load_history': lambda self, s: [],
    })()

    print('\n[1] 預設：meta 帶著逐字重播開關')
    m = meta_of(app)
    check('meta 事件存在', m is not None, m)
    check("typewriter is True", m and m.get('typewriter') is True, m)
    check('typewriter_cps 是正整數',
          m and isinstance(m.get('typewriter_cps'), int) and m['typewriter_cps'] > 0,
          m and m.get('typewriter_cps'))
    check('intent 沒有被擠掉', m and 'intent' in m, m)

    print('\n[2] TYPEWRITER_ENABLED=0 -> meta 說 False（前端退回整段貼上）')
    m = meta_of(app, TYPEWRITER_ENABLED=False)
    check("typewriter is False", m and m.get('typewriter') is False, m)

    print('\n[3] 速度可調')
    m = meta_of(app, TYPEWRITER_ENABLED=True, TYPEWRITER_CHARS_PER_SEC=200)
    check('typewriter_cps == 200', m and m.get('typewriter_cps') == 200,
          m and m.get('typewriter_cps'))

    print('\n[4] 值是在 app context 內讀的（生成器裡讀會 RuntimeError）')
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                            'api_v2', 'routes', 'chat.py'), encoding='utf-8').read()
    before = src.index("typewriter = bool(current_app.config")
    check('讀取在 def generate() 之前', before < src.index('def generate():'),
          'config 讀取必須留在請求處理函式內')

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

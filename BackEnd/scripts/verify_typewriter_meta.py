"""The meta event must carry the typewriter switch, and the switch must actually flip it.

The frontend decides whether to replay a segment character by character purely from this
event, so if the field silently stops being sent the widget falls back to pasting whole
360-char blocks and nothing else in the system notices. That is exactly how the original
`packed_chat` docstring ended up describing a client-side replay that was never built.

No LLM is called and no LOG is assembled: `packed_chat.packed_stream` is stubbed,
because what is under test is the transport of a config value, not the model.
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
from api_v2.services import packed_chat  # noqa: E402

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


def meta_of(app, payload_extra=None, **overrides):
    """Drive one request and hand back the parsed meta event.

    `payload_extra` 疊在 payload 上，用來測「舊版 widget 多送的欄位」。
    """
    for key, value in overrides.items():
        app.config[key] = value

    secret = os.getenv('PARTY_A_PLUGIN_SECRET', 'traitty_ai_api')
    # email 是必要欄位——/chat/ 要用它決定打上游時的身分（0905 文件 E-9）。
    token = pyjwt.encode({'sub': 'tester', 'email': 'tester@example.com',
                          'aud': 'traitty', 'exp': 4102444800},
                         secret, algorithm='HS256')
    payload = {'query': '你好', 'session_id': 'TYPEWRITER_TEST',
               'user_id': 'tester@example.com',
               'candidate_ids': [], 'candidates_info': [], 'trait_reports': {}}
    payload.update(payload_extra or {})
    r = app.test_client().post('/chat/', json=payload,
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
        'load_history': lambda self, s: [],
        'packer_stream': lambda self, m: iter([]),
        'packer_followup': lambda self, m, i: '',
    })()

    # 打包器是唯一的生成路徑（U7），而這支腳本要測的是 meta 事件而不是打包。
    # chat.py 是在產生器內部才 import packed_stream 的，所以換掉模組屬性就會生效。
    class _StubPacked:
        def __iter__(self):
            yield _Chunk('嗨')

        def finish(self):
            return {'status': 'ok'}

    packed_chat.packed_stream = lambda *a, **k: _StubPacked()

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

    print('\n[5] 相容性：舊版 widget 仍會送 mode，多的欄位必須被忽略而不是報錯')
    # U4 把 mode 從 payload 移除了，但已經部署出去的 widget build 還會送。
    # 前端不是後端能同步更新的東西，所以「多送一個欄位」必須永遠是安全的。
    m = meta_of(app, payload_extra={'mode': 'expert'},
                TYPEWRITER_ENABLED=True, TYPEWRITER_CHARS_PER_SEC=60)
    check('帶著 mode 的請求照常回 meta', m is not None, m)
    check('行為與不帶 mode 時相同',
          m and m.get('typewriter') is True and m.get('typewriter_cps') == 60, m)
    m2 = meta_of(app, payload_extra={'mode': 'auto', 'some_future_field': 123})
    check('連沒見過的欄位也不影響', m2 is not None and m2.get('typewriter') is True, m2)

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

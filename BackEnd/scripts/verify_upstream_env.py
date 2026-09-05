"""上游環境切換（UAT / PRD）的安全邊界與解析行為。

用法：
    python scripts/verify_upstream_env.py

這支驗的是「切換功能不會變成一個洞」。三條邊界：預設關閉、前端只能送名字不能送網址、
名字跟著簽過名的 token 走。任何一條鬆掉都會讓客戶端有辦法叫我們的後端去打別的地方。

不打網路：全部在 Flask test app 的 request context 裡跑。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'),
            encoding='utf-8-sig')

import jwt                                                            # noqa: E402
from flask import Flask                                               # noqa: E402

from api_v2.utils import upstream_env as ue                           # noqa: E402
from api_v2.utils.token_generator import generate_upstream_token      # noqa: E402

UAT = 'https://uat.example.test'
PRD = 'https://prd.example.test'

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}"
          f"{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def app_with(switch_on, prd_base=PRD, prd_secret=None):
    app = Flask(__name__)
    app.config.update(TRAITTY_API_BASE=UAT,
                      TRAITTY_API_BASE_PRD=prd_base,
                      PARTY_A_PLUGIN_SECRET_PRD=prd_secret,
                      ALLOW_UPSTREAM_ENV_SWITCH=switch_on)
    return app


def token_with(env_value):
    """帶著某個 upstream_env 欄位的 token。故意用別把鑰匙簽——env_from_request 不驗簽，
    所以這裡要證明的是「就算偽造也只能拿到白名單內的值」。"""
    return jwt.encode({'email': 'x@example.com', ue.ENV_CLAIM: env_value},
                      'some-other-secret', algorithm='HS256')


def main():
    print('\n[1] 預設關閉：開關沒開時，送什麼都沒用')
    with app_with(False).test_request_context(
            headers={'Authorization': f'Bearer {token_with("prd")}'}):
        check('switching_allowed() 為 False', ue.switching_allowed() is False)
        check('normalize_env("prd") 收斂回 default',
              ue.normalize_env('prd') == ue.ENV_DEFAULT, ue.normalize_env('prd'))
        check('env_from_request() 回 default（token 說 prd 也一樣）',
              ue.env_from_request() == ue.ENV_DEFAULT, ue.env_from_request())
        check('upstream_base() 仍是 .env 的預設值', ue.upstream_base() == UAT,
              ue.upstream_base())

    print('\n[2] 開關打開之後才生效')
    with app_with(True).test_request_context(
            headers={'Authorization': f'Bearer {token_with("prd")}'}):
        check('env_from_request() 讀得到 prd', ue.env_from_request() == 'prd')
        check('upstream_base(prd) 是 PRD 網址', ue.upstream_base('prd') == PRD,
              ue.upstream_base('prd'))
        check('upstream_base(default) 仍是 UAT', ue.upstream_base('default') == UAT)

    print('\n[3] 前端只能送名字，不能送網址')
    with app_with(True).test_request_context():
        for bad in ('http://evil.example.com', '//evil.example.com', 'PRD; drop',
                    '../prd', 'uat', '', None, 'staging'):
            got = ue.normalize_env(bad)
            check(f'{bad!r} -> {got}', got in ue.KNOWN_ENVS and got != 'prd', got)

    print('\n[4] 偽造的 token 也只能拿到白名單內的值')
    with app_with(True).test_request_context(
            headers={'Authorization': f'Bearer {token_with("http://evil.example.com")}'}):
        check('夾帶網址的 token -> default', ue.env_from_request() == ue.ENV_DEFAULT,
              ue.env_from_request())
    with app_with(True).test_request_context(headers={'Authorization': 'Bearer not-a-jwt'}):
        check('解不開的 token -> default', ue.env_from_request() == ue.ENV_DEFAULT)
    with app_with(True).test_request_context():
        check('完全沒有 Authorization -> default', ue.env_from_request() == ue.ENV_DEFAULT)

    print('\n[5] PRD 沒設定時退回預設，不會指向空字串')
    with app_with(True, prd_base=None).test_request_context():
        check('TRAITTY_API_BASE_PRD 未設定 -> 用 TRAITTY_API_BASE',
              ue.upstream_base('prd') == UAT, ue.upstream_base('prd'))

    print('\n[6] 簽上游 token 的 secret 跟著環境走')
    os.environ['PARTY_A_PLUGIN_SECRET'] = 'main-secret'
    with app_with(True, prd_secret='prd-secret').test_request_context():
        check('default 用主要那把', ue.upstream_secret('default') == 'main-secret')
        check('prd 用 PRD 那把', ue.upstream_secret('prd') == 'prd-secret')
        t = generate_upstream_token('x@example.com', 'prd')
        jwt.decode(t, 'prd-secret', algorithms=['HS256'], audience='traitty')
        check('PRD token 確實是用 PRD secret 簽的', True)
        try:
            jwt.decode(t, 'main-secret', algorithms=['HS256'], audience='traitty')
            check('且主要那把驗不過', False, '主要 secret 竟然驗得過')
        except jwt.InvalidSignatureError:
            check('且主要那把驗不過', True)
    with app_with(True, prd_secret=None).test_request_context():
        check('PRD secret 未設定 -> 沿用主要那把',
              ue.upstream_secret('prd') == 'main-secret')

    print('\n[7] describe() 不外洩 secret')
    with app_with(True).test_request_context():
        d = ue.describe('prd')
        check('只回 env / base_url / switch_enabled',
              set(d) == {'env', 'base_url', 'switch_enabled'}, sorted(d))
        check('內容裡沒有 secret 字樣',
              not any('secret' in str(v).lower() for v in d.values()), d)

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

"""Boundary checks for the deterministic conversation title (services/session_title.py).

Pure function, no DB and no model, so this runs anywhere. What it is guarding:

  * the title never comes back empty -- an empty title is what produced 「新對話」
  * the 20-character ceiling holds for every combination of names and question length
  * the names are dropped, not the question, once the question would be squeezed below
    MIN_QUERY_ROOM: a title that is four names and an ellipsis identifies nothing
  * a quick question's curated label survives intact for realistic respondent counts,
    which is the case the client actually looks at in the history list
"""

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from api_v2.services.session_title import (  # noqa: E402
    ELLIPSIS, LEGACY_PLACEHOLDER, MIN_QUERY_ROOM, TITLE_MAX, clamp_title, fallback_title,
    is_placeholder, title_for_metadata)

failures = []


def check(label, ok, detail=''):
    print(f"  [{'OK' if ok else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not ok:
        failures.append(label)


ONE = ['林孟德']
TWO = ['林孟德', '陳亭羽']
FOUR = ['林孟德', '陳亭羽', '洪宗瑋', '王湘萍']

# Real question labels, exactly as useChatLogic.sendQuickMessage sends them.
QUICK = ['高潛人才識別要點', '培育重點與發展方向', '適合的培訓方式與學習節奏',
         '打造高效會議團隊', '有效的溝通方法／模式', '需注意的管理問題或潛在風險']
FREE_SHORT = '他適合帶新人嗎？'
FREE_LONG = '他在跨部門協作的時候，遇到意見不合會怎麼處理？會不會直接放棄？'


def main():
    print('[1] 一定有值，一定不超過上限')
    cases = []
    for names in ([], ONE, TWO, FOUR):
        for q in QUICK + [FREE_SHORT, FREE_LONG, '', None, '   \n  ']:
            cases.append((names, q))
    for names, q in cases:
        t = fallback_title(names, q)
        if not t or len(t) > TITLE_MAX:
            check(f'names={len(names)} q={str(q)[:12]!r}', False, f'{t!r} len={len(t)}')
            break
    else:
        check(f'{len(cases)} 種組合都非空且 <= {TITLE_MAX} 字', True)
    check('沒有任何組合產生「新對話」',
          all(fallback_title(n, q) != '新對話' for n, q in cases))

    print('\n[2] 快速提問：客戶期待的格式')
    t = fallback_title(TWO, '高潛人才識別要點')
    check('兩人 + 題目標籤完整保留', t == '林孟德, 陳亭羽：高潛人才識別要點', t)
    for q in QUICK:
        t = fallback_title(TWO, q)
        # 標籤本身可能被截，但姓名區段必須完整，否則認不出是誰
        check(f'兩人 {q[:8]}: 姓名段完整', t.startswith('林孟德, 陳亭羽：') or ELLIPSIS in t, t)

    print('\n[3] 自由提問：使用者自己的問句')
    t = fallback_title(ONE, FREE_SHORT)
    check('單人 + 短問句原樣呈現', t == '林孟德：他適合帶新人嗎？', t)
    t = fallback_title(ONE, FREE_LONG)
    check('單人 + 長問句截斷並標記', t.startswith('林孟德：') and t.endswith(ELLIPSIS)
          and len(t) == TITLE_MAX, t)

    print('\n[4] 人數多到擠掉問題時，捨姓名保問題')
    t = fallback_title(FOUR, FREE_SHORT)
    check('四人時不放姓名', not t.startswith('林孟德'), t)
    check('四人時問句完整呈現', t == FREE_SHORT, t)
    # 邊界：名字剛好讓 room 掉到 MIN_QUERY_ROOM 以下就該切換
    just_over = ['A' * (TITLE_MAX - MIN_QUERY_ROOM)]      # prefix 長度 = room 恰好不足
    t = fallback_title(just_over, FREE_SHORT)
    check(f'room < {MIN_QUERY_ROOM} 時切換為純問句', t == FREE_SHORT, t)
    just_under = ['A' * (TITLE_MAX - MIN_QUERY_ROOM - 1)]
    t = fallback_title(just_under, FREE_SHORT)
    check(f'room == {MIN_QUERY_ROOM} 時仍保留姓名', t.startswith('A'), t)

    print('\n[5] 沒有問題可顯示時')
    check('有姓名 -> 姓名 + 分析', fallback_title(TWO, '') == '林孟德, 陳亭羽 分析',
          fallback_title(TWO, ''))
    check('無姓名無問題 -> 未命名對話', fallback_title([], '') == '未命名對話',
          fallback_title([], ''))
    check('姓名過長時仍不超過上限', len(fallback_title(FOUR + ['莊英良'], '')) <= TITLE_MAX,
          fallback_title(FOUR + ['莊英良', '曾莉婷'], ''))
    check('None 也要安全', fallback_title(None, None) == '未命名對話',
          fallback_title(None, None))

    print('\n[6] clamp_title：模型回傳過長時的共用規則')
    check('剛好 20 字不動', clamp_title('A' * TITLE_MAX) == 'A' * TITLE_MAX)
    check('21 字截為 20 並標記',
          clamp_title('A' * (TITLE_MAX + 1)) == 'A' * (TITLE_MAX - 1) + ELLIPSIS)
    check('換行與多餘空白會被收斂', clamp_title('  林孟德\n 分析 ') == '林孟德 分析',
          repr(clamp_title('  林孟德\n 分析 ')))

    print('\n[7] 歷史列表的標題推導（GET /sessions 走的那條）')
    check('metadata 為 None -> 未命名對話', title_for_metadata(None) == '未命名對話',
          title_for_metadata(None))
    check('metadata 為空 dict -> 未命名對話', title_for_metadata({}) == '未命名對話',
          title_for_metadata({}))
    check('存的是舊的「新對話」時視同沒有標題',
          title_for_metadata({'title': LEGACY_PLACEHOLDER}) == '未命名對話',
          title_for_metadata({'title': LEGACY_PLACEHOLDER}))
    check('舊「新對話」但有候選人 -> 用候選人',
          title_for_metadata({'title': LEGACY_PLACEHOLDER,
                              'candidates': [{'name': '林孟德'}, {'name': '陳亭羽'}]})
          == '林孟德, 陳亭羽 分析',
          title_for_metadata({'title': LEGACY_PLACEHOLDER,
                              'candidates': [{'name': '林孟德'}, {'name': '陳亭羽'}]}))
    check('有真標題時原樣回傳',
          title_for_metadata({'title': '林孟德：他適合帶新人嗎？'}) == '林孟德：他適合帶新人嗎？')
    check('candidates 結構壞掉也不會炸',
          title_for_metadata({'candidates': [None, 'x', {'no_name': 1}]}) == '未命名對話',
          title_for_metadata({'candidates': [None, 'x', {'no_name': 1}]}))
    check('is_placeholder 認得空字串與空白', is_placeholder('') and is_placeholder('  '))
    check('is_placeholder 不會誤判正常標題',
          not is_placeholder('林孟德, 陳亭羽：高潛人才識別要點'))
    check('歷史列表永遠不會回傳「新對話」',
          all(title_for_metadata(m) != LEGACY_PLACEHOLDER for m in (
              None, {}, {'title': LEGACY_PLACEHOLDER}, {'title': ''},
              {'title': LEGACY_PLACEHOLDER, 'candidates': [{'name': '王湘萍'}]})))

    verify_flow()

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


# --------------------------------------------------------------------------------------
# [8] The real background_generate_title, with the model and the DB replaced.
#
# Testing the route's own function rather than a copy of its logic: the bug being fixed
# was never in the title text, it was in which flags got written and whether the reasoning
# pass was disabled, and both of those live in that function.
# --------------------------------------------------------------------------------------

class _FakeResp:
    def __init__(self, content, finish_reason='stop'):
        msg = type('M', (), {'content': content})()
        self.choices = [type('C', (), {'message': msg, 'finish_reason': finish_reason})()]
        self.usage = type('U', (), {'total_tokens': 500, 'prompt_tokens': 300,
                                    'completion_tokens': 200})()


class _FakeRag:
    """Stands in for RAGService along the whole `client.chat.completions.create` chain."""

    model_name = 'test-model'

    def __init__(self, content):
        self._content = content
        self.calls = []

    @property
    def client(self):
        return self

    @property
    def chat(self):
        return self

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResp(self._content)

    def _thinking_kwargs(self):
        return {'extra_body': {'thinking': {'type': 'disabled'}}}


class _FakeSessionRow:
    def __init__(self, meta=None):
        self.metadata_ = meta


class _FakeDB:
    def __init__(self, row):
        self._row = row

    def query(self, *a, **k):
        return self

    def filter(self, *a, **k):
        return self

    def first(self):
        return self._row

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class _NoopStore:
    def add_message(self, *a, **k):
        pass


def run_title(content, candidate_names, user_query, existing_meta=None):
    """Drive background_generate_title once; return the metadata it wrote."""
    import api_v2.routes.chat as chat
    import api_v2.services.session_store as store_mod

    row = _FakeSessionRow(existing_meta)
    rag = _FakeRag(content)
    saved = (chat.rag_service, chat.get_db_session, store_mod.SqlSessionStore)
    chat.rag_service = rag
    chat.get_db_session = lambda: _FakeDB(row)
    store_mod.SqlSessionStore = _NoopStore
    try:
        chat.background_generate_title('TEST-SESSION', user_query, candidate_names)
    finally:
        chat.rag_service, chat.get_db_session, store_mod.SqlSessionStore = saved
    return row.metadata_ or {}, rag.calls


def verify_flow():
    print('\n[8] background_generate_title 實際行為（模型與 DB 換成假的）')
    import tempfile
    import api_v2.routes.chat as chat
    # 對話紀錄導到暫存目錄，測試不要污染正式的 conversations.log
    for h in chat.conv_logger.handlers:
        h.base_dir = os.path.join(tempfile.gettempdir(), 'verify_session_title')
        h.current_date = None
        if getattr(h, 'file_output', None):
            h.file_output.close()
            h.file_output = None

    meta, calls = run_title('林孟德, 陳亭羽：高潛人才識別特質分析', TWO, '高潛人才識別要點')
    check('模型呼叫帶上關閉推理的參數',
          calls and calls[0].get('extra_body') == {'thinking': {'type': 'disabled'}},
          calls[0].get('extra_body') if calls else 'no call')
    check('模型成功時採用模型標題',
          meta.get('title') == '林孟德, 陳亭羽：高潛人才識別特質分析', meta.get('title'))
    check('模型成功時 title_provisional 為 False', meta.get('title_provisional') is False,
          meta.get('title_provisional'))
    check('title_tries 記為 1', meta.get('title_tries') == 1, meta.get('title_tries'))

    meta, _ = run_title('', TWO, '高潛人才識別要點')
    check('content 為空時不再寫入「新對話」', meta.get('title') != '新對話', meta.get('title'))
    check('content 為空時採用確定性備援',
          meta.get('title') == fallback_title(TWO, '高潛人才識別要點'), meta.get('title'))
    check('備援標記為 provisional', meta.get('title_provisional') is True,
          meta.get('title_provisional'))

    meta, _ = run_title(None, ONE, FREE_LONG)
    check('content 為 None 也不會炸，且用使用者問句', meta.get('title', '').startswith('林孟德：'),
          meta.get('title'))

    # 重試上限：第二次仍然失敗後，title_tries 應為 2，之後 needs_title_generation 不再成立
    meta, _ = run_title('', TWO, '高潛人才識別要點',
                        existing_meta={'title': '林孟德, 陳亭羽：高潛人才識別要點',
                                       'title_provisional': True, 'title_tries': 1})
    check('第二次失敗後 title_tries 累加為 2', meta.get('title_tries') == 2,
          meta.get('title_tries'))
    retry_allowed = (meta.get('title_provisional')
                     and int(meta.get('title_tries') or 0) < 2)
    check('達上限後不再重試（與 chat.py 的判斷式一致）', not retry_allowed, retry_allowed)

    meta, _ = run_title('模型後來成功了', TWO, '高潛人才識別要點',
                        existing_meta={'title': '林孟德, 陳亭羽：高潛人才識別要點',
                                       'title_provisional': True, 'title_tries': 1})
    check('重試成功會覆蓋備援並解除 provisional',
          meta.get('title') == '模型後來成功了' and meta.get('title_provisional') is False,
          f"{meta.get('title')} provisional={meta.get('title_provisional')}")


if __name__ == '__main__':
    sys.exit(main())

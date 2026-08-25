"""Verify that a swallowed add_message failure actually reaches errors.log.

The defect being guarded is not a wrong value, it is silence. SqlSessionStore.add_message
catches every exception and returns None, so the request still returns 200 and the message
is simply lost. On PRD that happened for a week -- chat_messages_id_seq had fallen behind
max(id), so every INSERT hit a duplicate primary key -- and the only trace was one line in
session_store.log's ordinary INFO stream. Nobody looks there until a client complains.

So what is checked here is that the failure lands in a file that is empty when nothing is
wrong, with enough context to say which message was dropped.

No DB and no network: the failure is injected by making get_db_session raise.
"""

import logging
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import api_v2.services.session_store as store_mod  # noqa: E402
from api_v2.utils.logger import get_error_logger  # noqa: E402

failures = []


def check(label, ok, detail=''):
    print(f"  [{'OK' if ok else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not ok:
        failures.append(label)


class _ExplodingDB:
    """A DB session whose add() fails the way a duplicate primary key does."""

    def add(self, *a, **k):
        raise Exception('duplicate key value violates unique constraint '
                        '"chat_messages_pkey" DETAIL: Key (id)=(927) already exists.')

    def query(self, *a, **k):
        return self

    def filter_by(self, *a, **k):
        return self

    def update(self, *a, **k):
        return 0

    def commit(self):
        pass

    def rollback(self):
        pass

    def refresh(self, *a, **k):
        pass

    def close(self):
        pass


def redirect(logger, base_dir):
    """Point a daily logger's handler at a scratch directory and return the log path."""
    for h in logger.handlers:
        h.base_dir = base_dir
        h.current_date = None
        if getattr(h, 'file_output', None):
            h.file_output.close()
            h.file_output = None
    from datetime import datetime
    return os.path.join(base_dir, datetime.now().strftime('%Y-%m-%d'), h.filename)


def main():
    tmp = tempfile.mkdtemp(prefix='verify_error_log_')
    err_path = redirect(store_mod.error_logger, tmp)
    redirect(store_mod.session_logger, tmp)

    print('[1] errors.log 只收 ERROR，平常應該是空的')
    check('尚未發生錯誤時檔案不存在', not os.path.exists(err_path), err_path)
    store_mod.error_logger.info('這是 INFO，不該進 errors.log')
    store_mod.error_logger.warning('這是 WARNING，不該進 errors.log')
    check('INFO / WARNING 不會建立檔案', not os.path.exists(err_path))
    check('logger 等級為 ERROR', store_mod.error_logger.level == logging.ERROR,
          store_mod.error_logger.level)

    print('\n[2] add_message 吞掉例外時，錯誤必須留在 errors.log')
    saved = store_mod.get_db_session
    store_mod.get_db_session = lambda: _ExplodingDB()
    try:
        result = store_mod.SqlSessionStore().add_message(
            'SESSION-UNDER-TEST', 'assistant', '一段被丟掉的回覆內容',
            token_usage=1234, model_name='deepseek-v4-flash')
    finally:
        store_mod.get_db_session = saved

    check('對呼叫端仍然回傳 None（行為不變）', result is None, result)
    check('errors.log 已建立', os.path.exists(err_path), err_path)

    text = open(err_path, encoding='utf-8').read() if os.path.exists(err_path) else ''
    for needle, why in (('SESSION-UNDER-TEST', 'session_id，才知道是哪一段對話'),
                        ('add_message dropped a message', '一眼看出訊息被丟掉'),
                        ('role=assistant', '角色'),
                        ('chat_messages_pkey', '原始資料庫錯誤'),
                        ('deepseek-v4-flash', '模型名稱'),
                        ('ERROR', '等級')):
        check(f'内容含 {needle}（{why}）', needle in text)
    check('有完整 traceback', 'Traceback (most recent call last)' in text)
    check('沒有 emoji（Windows cp950 會炸）',
          all(ord(c) < 0x2190 or 0x4E00 <= ord(c) <= 0x9FFF or c in '（）「」，。：、'
              for c in text),
          [c for c in text if ord(c) >= 0x2190 and not (0x4E00 <= ord(c) <= 0x9FFF)
           and c not in '（）「」，。：、'][:10])

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

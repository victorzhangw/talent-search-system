"""左側歷史清單（/chat/history?v=2）的分組、游標與單筆格式。

為什麼分組在後端算：資料庫存的是無時區的 UTC（`datetime.utcnow()`），舊介面輸出的
`isoformat()` 也不帶時區，前端拿去 `new Date()` 會當成本地時間，差 8 小時，跨午夜的對話
就分錯組。分組規則只放這一份，用 Asia/Taipei 算好再給前端，前端只負責照 `bucket` 畫標題。

為什麼用游標而不是 page=N：使用者一邊捲一邊聊天時，被聊到的那筆會跳到最上面，偏移量
分頁會因此在下一頁重複或漏掉一筆。游標是上一頁最後一筆的 (last_active_at, session_id)，
跳走的那筆只會從後面消失，不會擠動其他筆。
"""

import base64
import binascii
import json
from datetime import datetime, timedelta, timezone

from .session_title import title_for_metadata

TAIPEI = timezone(timedelta(hours=8))
DEFAULT_LIMIT = 30
MAX_LIMIT = 50


class InvalidCursor(ValueError):
    pass


def to_taipei(dt_utc_naive):
    return dt_utc_naive.replace(tzinfo=timezone.utc).astimezone(TAIPEI)


def bucket_for(last_active_utc, now_utc=None):
    """(key, label)。依台北時間的「日曆日」差距分組，不是依 24 小時。

        0 天        today         今天
        1 天        yesterday     昨天
        2-6 天      last_7_days   過去 7 天
        7-29 天     last_30_days  過去 30 天
        更早        YYYY-MM       2026 年 8 月   （月份帶年份，跨年也不會混）
    """
    now_utc = now_utc or datetime.utcnow()
    active = to_taipei(last_active_utc)
    days = (to_taipei(now_utc).date() - active.date()).days
    if days <= 0:
        return 'today', '今天'
    if days == 1:
        return 'yesterday', '昨天'
    if days <= 6:
        return 'last_7_days', '過去 7 天'
    if days <= 29:
        return 'last_30_days', '過去 30 天'
    return f'{active.year:04d}-{active.month:02d}', f'{active.year} 年 {active.month} 月'


def parse_limit(raw):
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    return max(1, min(MAX_LIMIT, value))


def encode_cursor(last_active_utc, session_id):
    payload = json.dumps({'t': last_active_utc.isoformat(), 's': session_id},
                         separators=(',', ':'))
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip('=')


def decode_cursor(raw):
    """回 (last_active_utc_naive, session_id)；任何格式問題都丟 InvalidCursor。"""
    try:
        padded = raw + '=' * (-len(raw) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        t = datetime.fromisoformat(data['t'])
        s = data['s']
    except (ValueError, KeyError, TypeError, binascii.Error, UnicodeDecodeError) as e:
        raise InvalidCursor(str(e)) from e
    if t.tzinfo is not None or not isinstance(s, str) or not s:
        raise InvalidCursor('malformed cursor')
    return t, s


def _iso_utc(dt):
    """帶 +00:00 的 ISO 字串。舊介面輸出的不帶時區，前端會誤當本地時間。"""
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt else None


def item(session, now_utc=None):
    active = session.last_active_at or session.started_at
    key, label = bucket_for(active, now_utc)
    return {
        'session_id': session.session_id,
        'title': title_for_metadata(session.metadata_),
        'started_at': _iso_utc(session.started_at),
        'last_active_at': _iso_utc(session.last_active_at),
        'status': session.status,
        'bucket': key,
        'bucket_label': label,
    }

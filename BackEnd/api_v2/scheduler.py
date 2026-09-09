"""Daily settlement 補送作業（單元 U3b）。

這是一支 **one-shot 批次作業**，不是常駐服務：跑一輪、寫下結果、離開。週期交給 Windows
工作排程器（見 scripts/install-settlement-task.bat，預設每 15 分鐘）。

用法：
    python api_v2/scheduler.py             # 跑一輪並實際補送
    python api_v2/scheduler.py --dry-run   # 只列出會送什麼，完全不打上游、不寫資料庫
    python api_v2/scheduler.py --limit 5   # 這一輪最多處理 5 筆

離開碼（工作排程器的「上次執行結果」會顯示這個值）：
    0  正常跑完（沒有待處理紀錄也算正常）
    1  有紀錄補送失敗
    2  作業本身出錯（連不到資料庫、設定缺漏等）

為什麼不是常駐迴圈：這是計費補送，不該跟 chat 後端或任何一個常駐行程同生共死。舊版是
`while True: process(); sleep(600)`，而且 `process()` 每一輪都呼叫一次 `create_app()`
——每 10 分鐘重建一整個 Flask app、重跑 `Base.metadata.create_all()`、重新註冊所有
blueprint 與 CORS/limiter。現在 app 只在 `main()` 建一次。

排程器層級還提供一件迴圈給不了的事：**單一執行個體保證**。工作排程器的
MultipleInstancesPolicy 設為 IgnoreNew，上一輪還沒跑完就不會再起一輪。上游雖然靠
external_event_id 去重，但計費不該把去重責任外包給對方。
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta

import httpx

# Ensure we are in the correct path to absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_v2.app import create_app
from api_v2.database.connection import get_db_session
from api_v2.database.models import DailySettlementRecord
from api_v2.utils.logger import get_daily_logger
from api_v2.utils.token_generator import generate_upstream_token
from api_v2.utils.upstream_env import normalize_stored_env, upstream_base_for

# 只掃描最近幾天內、重試次數還沒用完的紀錄。
# 注意：超出視窗的紀錄就再也不會被補送了，這是刻意的（過期的帳補回去意義不大，而且
# 上游的 report_date 也對不上），但它同時表示視窗外的失敗筆數需要有人看——
# 這正是 scripts/uat_db_check.py 之外還需要一份定期盤點的理由。
SCAN_WINDOW_DAYS = 7
MAX_RETRIES = 10
# 連續請求之間的間隔，避免打爆上游的速率限制。
REQUEST_INTERVAL_SEC = 0.5

EXIT_OK = 0
EXIT_SOME_FAILED = 1
EXIT_JOB_ERROR = 2

# 排程執行時沒有主控台可看，所以寫檔。與後端其他元件同一個 logs/<date>/ 慣例。
logger = get_daily_logger('SettlementScheduler', 'settlement_scheduler.log',
                          level=logging.INFO)


def upstream_for_record(record):
    """這筆扣點要補送到哪裡：回傳 (已正規化的環境名, base_url 或 None)。

    補送必須回到當初真的打過的那個上游，不能一律用預設值。`normalize_stored_env()` 與
    `upstream_base_for()` 刻意跳過 ALLOW_UPSTREAM_ENV_SWITCH 閘門——那個開關是用來擋
    客戶端輸入的，若它在 submit 與 retry 之間被關掉，一筆 PRD 的帳會被改寫成 default
    送到 UAT。見 utils/upstream_env.py 的 normalize_stored_env()。

    抽成函式是為了讓 scripts/verify_settlement_env.py 能在不呼叫 create_app()、不連
    PostgreSQL 的情況下驗這段解析。
    """
    env = normalize_stored_env(getattr(record, 'upstream_env', None))
    return env, upstream_base_for(env)


def build_payload(record):
    """上游 /v1/ai/usage/daily-settlement 要的 body。

    欄位全部從資料庫這一列取，不從當下的時間或設定推——補送的是「當初那一筆」，
    report_date 必須是當初的日期，否則上游會把它算到今天的帳上。
    """
    asked_dt = record.created_at or datetime.utcnow()
    event_id = (f"{record.session_id}_{record.message_id}"
                if getattr(record, 'message_id', None) else record.session_id)
    return {
        "provider": "tratty api",
        "report_date": asked_dt.strftime("%Y-%m-%d"),
        "records": [
            {
                "plan_id": record.plan_id,
                "asked_at": asked_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "external_event_id": event_id,
            }
        ],
    }


def pending_records(db, limit=None):
    q = (db.query(DailySettlementRecord)
           .filter(DailySettlementRecord.status.in_(['PENDING', 'FAILED']),
                   DailySettlementRecord.created_at >= datetime.utcnow() - timedelta(days=SCAN_WINDOW_DAYS),
                   DailySettlementRecord.retry_count < MAX_RETRIES)
           .order_by(DailySettlementRecord.created_at))
    return q.limit(limit).all() if limit else q.all()


def sync_one(record, dry_run=False):
    """補送一筆。回傳 True 表示成功。dry_run 時只解析與組裝，不打上游也不改紀錄。"""
    record_env, base_url = upstream_for_record(record)
    if not base_url:
        logger.error(f"record={record.id} env={record_env!r} 找不到上游網址；"
                     f"請檢查 TRAITTY_API_BASE / TRAITTY_API_BASE_PRD。跳過。")
        return False

    url = f"{base_url}/v1/ai/usage/daily-settlement"
    payload = build_payload(record)

    if dry_run:
        logger.info(f"[DRY-RUN] record={record.id} user={record.user_id} "
                    f"env={record_env} -> {url} payload={payload['records'][0]}")
        return True

    logger.info(f"record={record.id} user={record.user_id} env={record_env} -> {url}")
    try:
        headers = {
            "Authorization": f"Bearer {generate_upstream_token(record.user_id, record_env, trusted_env=True)}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        response = httpx.post(url, headers=headers, json=payload, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        if not data.get("status"):
            raise RuntimeError(f"API returned status false: {data}")
        record.status = 'SYNCED'
        record.last_error = ""
        logger.info(f"record={record.id} SYNCED")
        return True
    except Exception as e:
        err_response = getattr(e, 'response', None)
        err_text = err_response.text if err_response is not None else str(e)
        record.status = 'FAILED'
        # 上游失敗時回的是整頁 HTML 的情況實際發生過（id 83/84），整段存進 DB 只會
        # 讓 last_error 沒法讀。截斷後仍足以判斷是哪一類失敗。
        record.last_error = err_text[:500]
        record.retry_count = (record.retry_count or 0) + 1
        logger.error(f"record={record.id} FAILED (retry_count={record.retry_count}): "
                     f"{err_text[:200]}")
        return False


def process_pending_and_failed_records(app, dry_run=False, limit=None):
    """跑一輪。回傳 (處理筆數, 失敗筆數)。"""
    with app.app_context():
        db = get_db_session()
        try:
            records = pending_records(db, limit)
            if not records:
                logger.info("沒有待補送的紀錄。")
                return 0, 0

            logger.info(f"找到 {len(records)} 筆待補送{'（DRY-RUN）' if dry_run else ''}。")
            failed = 0
            for i, record in enumerate(records):
                if i:
                    time.sleep(REQUEST_INTERVAL_SEC)
                if not sync_one(record, dry_run=dry_run):
                    failed += 1

            if dry_run:
                db.rollback()
                logger.info("DRY-RUN：未寫入任何變更。")
            else:
                try:
                    db.commit()
                    logger.info("資料庫已更新。")
                except Exception as e:
                    db.rollback()
                    logger.error(f"寫入補送結果失敗，本輪全部回滾：{e}")
                    return len(records), len(records)
            return len(records), failed
        finally:
            db.close()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Daily settlement 補送作業（跑一輪就離開，週期交給工作排程器）')
    parser.add_argument('--dry-run', action='store_true',
                        help='只列出會送什麼，不打上游、不寫資料庫')
    parser.add_argument('--limit', type=int, default=None,
                        help='這一輪最多處理幾筆')
    args = parser.parse_args(argv)

    started = time.time()
    logger.info(f"=== 補送作業開始 dry_run={args.dry_run} limit={args.limit} ===")
    try:
        app = create_app()          # 一輪一次，不是每筆一次
        total, failed = process_pending_and_failed_records(app, args.dry_run, args.limit)
    except Exception as e:
        logger.error(f"作業本身出錯：{e}", exc_info=True)
        return EXIT_JOB_ERROR

    elapsed = time.time() - started
    logger.info(f"=== 補送作業結束 處理={total} 失敗={failed} 耗時={elapsed:.1f}s ===")
    return EXIT_SOME_FAILED if failed else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

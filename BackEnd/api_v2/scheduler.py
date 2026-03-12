import os
import sys
import time
import logging
from datetime import datetime
import httpx

# Ensure we are in the correct path to absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_v2.app import create_app
from api_v2.database.connection import get_db_session
from api_v2.database.models import DailySettlementRecord
from api_v2.utils.token_generator import generate_upstream_token
from flask import current_app

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SettlementScheduler")

def process_pending_and_failed_records():
    app = create_app()
    with app.app_context():
        db = get_db_session()
        from datetime import datetime, timedelta
        
        # 只掃描最近 7 天內的紀錄，且重試次數小於 10 次的
        time_limit = datetime.utcnow() - timedelta(days=7)
        records = db.query(DailySettlementRecord).filter(
            DailySettlementRecord.status.in_(['PENDING', 'FAILED']),
            DailySettlementRecord.created_at >= time_limit,
            DailySettlementRecord.retry_count < 10
        ).all()
        
        if not records:
            logger.info("No pending or failed records found. Sleeping...")
            return

        logger.info(f"Found {len(records)} records to sync. Processing...")
        
        base_url = os.getenv('TRAITTY_API_BASE') or app.config.get('TRAITTY_API_BASE')
        if not base_url:
            logger.error("Critical Error: TRAITTY_API_BASE is not set in environment or configuration. Aborting sync.")
            return

        url = f"{base_url}/v1/ai/usage/daily-settlement"
        
        for record in records:
            try:
                # Add a brief delay between requests to avoid rate limits
                time.sleep(0.5)
                
                upstream_token = generate_upstream_token(record.user_id)
                headers = {
                    "Authorization": f"Bearer {upstream_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
                
                asked_dt = record.created_at or datetime.utcnow()
                asked_at_str = asked_dt.strftime("%Y-%m-%d %H:%M:%S")
                report_date_str = asked_dt.strftime("%Y-%m-%d")

                # 從資料庫取出乾淨的欄位動態組裝
                event_id_str = f"{record.session_id}_{record.message_id}" if getattr(record, 'message_id', None) else record.session_id

                payload = {
                    "provider": "tratty api", 
                    "report_date": report_date_str,
                    "records": [
                        {
                            "plan_id": record.plan_id,
                            "asked_at": asked_at_str,
                            "external_event_id": event_id_str
                        }
                    ]
                }
                
                logger.info(f"Attempting to sync record ID {record.id} for user {record.user_id}...")
                response = httpx.post(url, headers=headers, json=payload, timeout=15.0)
                response.raise_for_status()
                data = response.json()
                
                if data.get("status"):
                    record.status = 'SYNCED'
                    record.last_error = ""
                    logger.info(f"Record {record.id} sync successful.")
                else:
                    raise Exception(f"API Returned status false: {data}")
                    
            except Exception as e:
                err_content = getattr(e, 'response', None)
                err_text = err_content.text if err_content else str(e)
                logger.error(f"Failed to sync record {record.id}: {err_text}")
                record.status = 'FAILED'
                record.last_error = err_text
                record.retry_count += 1
                
        try:
            db.commit()
            logger.info("Database updated with retry results.")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit database updates: {e}")
        finally:
            db.close()

if __name__ == "__main__":
    logger.info("Starting Daily Settlement Retry Scheduler...")
    # 使用簡單的無窮迴圈執行定期發送，每 5 分鐘掃描一次
    while True:
        try:
            process_pending_and_failed_records()
        except Exception as e:
            logger.error(f"Scheduler encountered an unexpected error: {e}", exc_info=True)
            
        logger.info("Sleeping for 10 minutes before next run...")
        time.sleep(600) # 10 minutes (600 seconds)

import httpx
from datetime import datetime
from flask import current_app
from .token_generator import generate_upstream_token
import logging
import os
from .logger import get_daily_logger

def get_traitty_logger():
    return get_daily_logger("TraittyAPI_Logger", "traitty_api.log", level=logging.INFO)

api_logger = get_traitty_logger()

def fetch_init_data(email: str):
    """
    獲取目前使用者的 Initiation 資料 (包含配額與可用計畫)
    """
    upstream_token = generate_upstream_token(email)
    base_url = current_app.config.get('TRAITTY_API_BASE', 'https://uat.traitty.com')
    url = f"{base_url}/v1/init/"
    
    headers = {
        "Authorization": f"Bearer {upstream_token}",
        "Accept": "application/json"
    }
    
    response = httpx.get(url, headers=headers, timeout=15.0)
    response.raise_for_status()
    return response.json()

def find_active_plan(usable_plans: list):
    """
    透過現在系統時間尋找合適的 plan_id
    """
    if not usable_plans:
        return None
        
    now = datetime.now()
    
    for plan in usable_plans:
        # 日期格式： 2026-02-01 00:00:00
        starts_at = datetime.strptime(plan['starts_at'], "%Y-%m-%d %H:%M:%S")
        ends_at = datetime.strptime(plan['ends_at'], "%Y-%m-%d %H:%M:%S")
        if starts_at <= now <= ends_at:
            return plan['plan_id']
            
    # 若無精準匹配，回傳第一個 plan_id 確保不為空
    return usable_plans[0]['plan_id']

from ..database.connection import get_db_session
from ..database.models import DailySettlementRecord

def submit_daily_settlement(email: str, plan_id: int, session_id: str, message_id: str = None):
    """
    呼叫 daily-settlement 扣抵額度，並先在資料庫記錄狀態以防遺失。
    若帶有 message_id，則組合為 external_event_id，確保同一 session 內的每一次問答都是獨立扣點。
    """
    db = get_db_session()
    
    event_id_str = f"{session_id}_{message_id}" if message_id else session_id

    # 1. 建立 Pending 紀錄到資料庫
    record = DailySettlementRecord(
        user_id=email,
        plan_id=plan_id,
        session_id=event_id_str, # 這裡存入組合後的 key 以便對齊
        status='PENDING'
    )
    try:
        db.add(record)
        db.commit()
    except Exception as dbe:
        db.rollback()
        api_logger.error(f"[Daily Settlement] DB Insert Failed: {dbe}")
        # 如果寫入資料庫失敗，仍然繼續嘗試發送 API (盡量不影響扣抵邏輯)
        pass

    # 2. 準備呼叫 API
    upstream_token = generate_upstream_token(email)
    base_url = current_app.config.get('TRAITTY_API_BASE', 'https://uat.traitty.com')
    url = f"{base_url}/v1/ai/usage/daily-settlement"
    
    headers = {
        "Authorization": f"Bearer {upstream_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # 取得指定格式，例如 "2026-02-28 09:30:00"
    now_dt = datetime.now()
    asked_at_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    report_date_str = now_dt.strftime("%Y-%m-%d")
    
    payload = {
        "provider": "tratty api", 
        "report_date": report_date_str,
        "records": [
            {
                "plan_id": plan_id,
                "asked_at": asked_at_str,
                "external_event_id": event_id_str
            }
        ]
    }
    
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        
        # 驗證回傳格式
        if not data.get("status"):
            api_logger.error(f"[Daily Settlement Error] API Status False. Body: {data}")
            raise Exception(f"API returned status false: {data}")
            
        summary = data.get("summary", {})
        accepted_count = summary.get("accepted", 0)
        
        if accepted_count != 1: # 因為我們每次只發送 1 筆 record
            api_logger.warning(f"[Daily Settlement Warning] Accepted count mismatch! Expected 1, got {accepted_count}. Full Res: {data}")

        # 3. 成功，更新資料庫狀態
        if record.id:
            try:
                record.status = 'SYNCED'
                db.commit()
            except Exception as dbe:
                db.rollback()
                api_logger.error(f"[Daily Settlement] DB Update SYNCED Failed: {dbe}")
            
        return data
        
    except Exception as e:
        # 如果發生 Http Error，盡可能印出錯誤詳細內容
        err_content = getattr(e, 'response', None)
        err_text = err_content.text if err_content else str(e)
        api_logger.error(f"[Daily Settlement Fatal] Request Failed: {err_text}", exc_info=True)
        
        # 4. 失敗，更新資料庫狀態以便日後補送
        if record.id:
            try:
                record.status = 'FAILED'
                record.last_error = err_text
                db.commit()
            except Exception as dbe:
                db.rollback()
                api_logger.error(f"[Daily Settlement] DB Update FAILED Failed: {dbe}")
                
        raise
    finally:
        db.close()


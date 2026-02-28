import httpx
from datetime import datetime
from flask import current_app
from .token_generator import generate_upstream_token

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

def submit_daily_settlement(email: str, plan_id: int, session_id: str):
    """
    呼叫 daily-settlement 扣抵額度
    """
    upstream_token = generate_upstream_token(email)
    base_url = current_app.config.get('TRAITTY_API_BASE', 'https://uat.traitty.com')
    url = f"{base_url}/v1/ai/usage/daily-settlement"
    
    headers = {
        "Authorization": f"Bearer {upstream_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # 取得含時區的 ISO 格式，例如 "2026-03-05T09:30:00+08:00"
    now_dt = datetime.now().astimezone()
    asked_at_str = now_dt.isoformat()
    report_date_str = now_dt.strftime("%Y-%m-%d")
    
    payload = {
        "provider": "tratty api", 
        "report_date": report_date_str,
        "records": [
            {
                "plan_id": plan_id,
                "asked_at": asked_at_str,
                "external_event_id": session_id
            }
        ]
    }
    
    response = httpx.post(url, headers=headers, json=payload, timeout=15.0)
    response.raise_for_status()
    return response.json()

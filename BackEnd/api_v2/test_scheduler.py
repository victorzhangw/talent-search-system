import os
import sys
import uuid
import logging

# Ensure absolute import path works
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_v2.app import create_app
from api_v2.database.connection import get_db_session
from api_v2.database.models import DailySettlementRecord
from api_v2.scheduler import process_pending_and_failed_records

logging.basicConfig(level=logging.WARNING) # 關閉過多 debug 訊息

def test_recording_and_retry():
    app = create_app()
    with app.app_context():
        db = get_db_session()
        
        # 建立一個測試用的隨機 Session ID
        test_session_id = str(uuid.uuid4())
        # 使用一個不存在的 email 或真實 email 測試
        test_email = "test_retry@traitty.com"
        test_plan_id = 999  # 故意寫一個可能錯誤的 plan_id 測試能不能記錄下來
        
        print("\n=== 🛠️ 階段 1: 模擬斷線，直接在資料庫建立 FAILED 紀錄 ===")
        record = DailySettlementRecord(
            user_id=test_email,
            plan_id=test_plan_id,
            session_id=test_session_id,
            status='FAILED',
            last_error="[模擬環境] 網路瞬斷無法連線",
            retry_count=0
        )
        db.add(record)
        db.commit()
        
        saved_record = db.query(DailySettlementRecord).filter_by(session_id=test_session_id).first()
        print(f"✔️ 成功建立紀錄！ ID: {saved_record.id}, 狀態: {saved_record.status}")
        db.close()
        
        print("\n=== 🚀 階段 2: 啟動排程器 (Scheduler) 攔截並重發 ===")
        print("排程器正在掃描所有狀態為 PENDING 與 FAILED 的紀錄並重新打 API...")
        process_pending_and_failed_records()
        
        print("\n=== 📊 階段 3: 驗證重試結果 ===")
        db = get_db_session()
        updated_record = db.query(DailySettlementRecord).filter_by(session_id=test_session_id).first()
        print(f"紀錄 ID: {updated_record.id}")
        print(f"更新後狀態: {updated_record.status}")
        print(f"重試累積次數: {updated_record.retry_count}")
        print(f"最後錯誤訊息: {updated_record.last_error}")
        
        # 如果 API 回傳 400/404/500，這個狀態依然會是 FAILED，但 retry_count 會變成 1
        # 如果恰好這個假資料送過去成功了，狀態會是 SYNCED，retry_count 維持不變
        
        # 清理測試資料以免弄髒資料庫
        print("\n=== 🧹 階段 4: 清理測試資料 ===")
        db.delete(updated_record)
        db.commit()
        db.close()
        print("✔️ 測試資料已清除，測試完畢！")

if __name__ == "__main__":
    test_recording_and_retry()

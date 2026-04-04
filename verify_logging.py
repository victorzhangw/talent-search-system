import sys
import os
import logging

# 加入專案路徑以便匯入
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from BackEnd.api_v2.utils.logger import get_conversation_logger

def test_logging():
    logger = get_conversation_logger()
    session_id = "test-session-123"
    user_id = "test-user@example.com"
    
    print("Writing test logs to conversations.log...")
    logger.info(f"[USER] SessionID: {session_id} | UserID: {user_id} | Content: 這是測試提問")
    logger.info(f"[AI] SessionID: {session_id} | Content: 這是助理測試回覆 | Tokens: 150 (P:50, C:100) | Model: gpt-4o")
    logger.info(f"[SYSTEM] SessionID: {session_id} | Title: 測試對話標題 | Tokens: 30 (P:20, C:10)")
    print("Done.")

if __name__ == "__main__":
    test_logging()

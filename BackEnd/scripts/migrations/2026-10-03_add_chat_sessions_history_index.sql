-- =====================================================================
-- 2026-10-03  chat_sessions 新增歷史清單用的複合索引（歷史清單延長 U1）
--
-- 問題   : /chat/history?v=2 的查詢是
--            WHERE lower(user_id) = :email AND last_active_at >= :cutoff
--            [AND (last_active_at, session_id) < (:cursor_t, :cursor_s)]
--            ORDER BY last_active_at DESC, session_id DESC LIMIT :n
--          既有的 ix_chat_sessions_user_id 是 user_id 單欄，比對 lower(user_id) 時用不上，
--          也無法提供排序。資料量小時看不出差別，天數拉到 180 天以上之後每次翻頁都要掃整張表。
--
-- 影響   : 只在 chat_sessions 新增一個索引；不改任何資料、欄位或既有索引。
-- 目標 DB : PostgreSQL / ai_chatbot_v2（本機、UAT）、ai_chatbot_v2_prd（PRD）
-- 冪等   : IF NOT EXISTS；可重複執行。
-- 鎖     : CONCURRENTLY，建立期間不擋讀寫。CONCURRENTLY 不能放在交易裡，
--          所以本檔沒有 BEGIN/COMMIT，psql 也不要加 -1 / --single-transaction。
-- 回滾   : DROP INDEX CONCURRENTLY IF EXISTS ix_chat_sessions_user_lower_active;
--
-- 與 BackEnd/api_v2/database/models.py 的 Index('ix_chat_sessions_user_lower_active', ...)
-- 同步；全新資料庫由 Base.metadata.create_all() 直接建出相同索引，不需執行本檔。
-- =====================================================================

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_chat_sessions_user_lower_active
    ON chat_sessions (lower(user_id), last_active_at DESC, session_id DESC);

-- CONCURRENTLY 中途失敗會留下 INVALID 的索引，IF NOT EXISTS 之後也不會重建。
-- 驗證（應回 1 列，indisvalid = true）：
--   SELECT c.relname, i.indisvalid FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
--   WHERE c.relname = 'ix_chat_sessions_user_lower_active';
-- 若為 false：先 DROP INDEX CONCURRENTLY，再重跑本檔。

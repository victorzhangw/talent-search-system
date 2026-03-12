-- migration/04_add_message_id_to_daily_settlements.sql

-- 新增 message_id 欄位到 daily_settlements，用於單獨儲存訊息 ID，避免將其與 session_id 混合
ALTER TABLE daily_settlements ADD COLUMN message_id VARCHAR(255) DEFAULT NULL;

-- 可選：如果已有一些舊資料將 message_id 與 session_id 混合在 session_id 中（格式為 uuid_msgid）
-- 下方的 SQL 是一個更新範例，若您使用的是 PostgreSQL，可以利用 substring 或 split_part 拆分
-- UPDATE daily_settlements 
-- SET 
--     message_id = substring(session_id from position('_' in session_id) + 1),
--     session_id = substring(session_id from 1 for position('_' in session_id) - 1)
-- WHERE session_id LIKE '%_%';

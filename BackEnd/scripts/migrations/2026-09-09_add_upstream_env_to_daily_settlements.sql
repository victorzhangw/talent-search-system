-- =====================================================================
-- 2026-09-09  daily_settlements 新增 upstream_env 欄位（單元 U3a）
--
-- 問題   : submit_daily_settlement() 打上游時走 env_from_request()，解得出 'prd'
--          （ALLOW_UPSTREAM_ENV_SWITCH 打開時），會用 TRAITTY_API_BASE_PRD +
--          PARTY_A_PLUGIN_SECRET_PRD 送出。但 daily_settlements 沒有任何欄位記下
--          「這筆打的是哪一個上游」，所以 scheduler.py 補送時只能用預設上游與預設
--          secret——一筆 PRD 的扣點會被重送到 UAT，或用錯的 shared secret 拿到 401。
--
-- 目標   : 把「這筆當初打過哪裡」變成資料，補送照著它回到同一個上游。
--
-- 影響   : 只 ALTER daily_settlements 一張表，新增一個有預設值的欄位。
--          既有列一律 backfill 為 'default'——在這個欄位存在之前，唯一可能被打到的
--          就是 TRAITTY_API_BASE，這不是猜測而是當時程式碼的唯一行為。
--          其他資料表、既有查詢、既有索引皆不受影響。
--
-- 目標 DB : PostgreSQL / ai_chatbot_v2
-- 冪等   : 使用 IF NOT EXISTS；可重複執行。
-- 回滾   : ALTER TABLE daily_settlements DROP COLUMN IF EXISTS upstream_env;
--
-- 與 BackEnd/api_v2/database/models.py 的 DailySettlementRecord 同步；
-- 全新資料庫由 Base.metadata.create_all() 直接建出相同結構，不需執行本檔。
-- =====================================================================

BEGIN;

-- 1. 新增欄位。給 server_default 是為了讓既有列在 ALTER 當下就被填好，
--    不必再跑一次 UPDATE，也避免 NOT NULL 在有資料的表上失敗。
ALTER TABLE daily_settlements
    ADD COLUMN IF NOT EXISTS upstream_env VARCHAR(16) NOT NULL DEFAULT 'default';

-- 2. 保險：若欄位是先前以可為 NULL 的形式建立的，補齊並收緊。
UPDATE daily_settlements SET upstream_env = 'default' WHERE upstream_env IS NULL;

ALTER TABLE daily_settlements
    ALTER COLUMN upstream_env SET DEFAULT 'default';

ALTER TABLE daily_settlements
    ALTER COLUMN upstream_env SET NOT NULL;

COMMIT;

-- 驗證（執行後應為 0 列）：
--   SELECT COUNT(*) FROM daily_settlements WHERE upstream_env IS NULL;
-- 分布：
--   SELECT upstream_env, status, COUNT(*) FROM daily_settlements
--   GROUP BY upstream_env, status ORDER BY 1, 2;

-- =====================================================================
-- 2026-08-05  新增端點資料表（對應 0805 02_08 V6.3 spec_.xlsx 的 09/10 分頁）
--
-- 目標   : 讓「風險端點／作答校準／未來新增的端點型別」及其 LOG 子區塊對應
--          成為資料，新增端點或端點型別不必改程式碼。
-- 影響   : 既有三張表（trait_definitions / trait_bands / trait_interactions）
--          結構完全不變，無 ALTER、無 backfill、無既有查詢受影響。
--          本檔只做 CREATE TABLE + 種子資料。
-- 目標 DB : PostgreSQL 18.3 / ai_chatbot_v2
-- 冪等   : 全部使用 IF NOT EXISTS / ON CONFLICT，可重複執行。
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 1. endpoint_blocks  ←  spec 10_endpoint_blocks 分頁
--    端點型別 → LOG 子區塊的對應。先建，因為 trait_endpoints 會參照它。
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS endpoint_blocks (
    block_key      VARCHAR(32)  PRIMARY KEY,
    question_type  VARCHAR(16)  NOT NULL,
    header_text    TEXT         NOT NULL,
    sort_order     SMALLINT     NOT NULL,
    priority       SMALLINT     NOT NULL,
    footnote_rule  TEXT,
    CONSTRAINT ck_endpoint_blocks_qtype
        CHECK (question_type IN ('scoped', 'whole_person', 'both'))
);

COMMENT ON TABLE  endpoint_blocks IS
    'LOG 交互子區塊定義。header_text 為客戶 a 文件的逐字字串，程式不得改寫或自行命名。';
COMMENT ON COLUMN endpoint_blocks.sort_order IS
    '同一份 LOG 內的輸出順序（小者在前）。';
COMMENT ON COLUMN endpoint_blocks.priority IS
    '衝突裁決（2026-08-05 定案）：一條交互只輸出一次，取其命中型別中 priority 數字最小的區塊。';

-- ---------------------------------------------------------------------
-- 2. trait_endpoints  ←  spec 09_endpoints 分頁
--    一列一個端點。band = '*' 代表特質層級端點（三個 band 皆適用）。
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trait_endpoints (
    id             SERIAL       PRIMARY KEY,
    trait_id       VARCHAR(50)  NOT NULL
                   REFERENCES trait_definitions(trait_id) ON DELETE CASCADE,
    band           VARCHAR(10)  NOT NULL,
    endpoint_type  VARCHAR(32)  NOT NULL,
    endpoint_level VARCHAR(32),
    block_key      VARCHAR(32)  NOT NULL
                   REFERENCES endpoint_blocks(block_key),
    note           TEXT,
    CONSTRAINT uq_trait_endpoints UNIQUE (trait_id, band, endpoint_type),
    CONSTRAINT ck_trait_endpoints_band CHECK (band IN ('A', 'B', 'C', '*'))
);

CREATE INDEX IF NOT EXISTS ix_trait_endpoints_lookup
    ON trait_endpoints (trait_id, band);
CREATE INDEX IF NOT EXISTS ix_trait_endpoints_type
    ON trait_endpoints (endpoint_type);

COMMENT ON TABLE  trait_endpoints IS
    '端點清單，正本＝spec 09_endpoints 分頁。新增端點＝加一列；新增端點型別＝加列並在 endpoint_blocks 補一列。';
COMMENT ON COLUMN trait_endpoints.band IS
    'A/B/C；* ＝特質層級端點（三個 band 皆適用），例如作答校準特質。';
COMMENT ON COLUMN trait_endpoints.endpoint_level IS
    '型別內級別（risk：core/marginal/property_peak）。純紀錄，不參與判定——判定條件是「該列存在」。';

-- ---------------------------------------------------------------------
-- 3. endpoint_blocks 種子資料
--    即現行 b §3 / a 文件規則的原樣紀錄，未改變任何行為。
-- ---------------------------------------------------------------------
INSERT INTO endpoint_blocks (block_key, question_type, header_text, sort_order, priority, footnote_rule)
VALUES
    ('related',    'scoped',       '#### 交互作用——本題相關',         1, 1,
     '1–4 條 → 尾註「本題相關交互較少，判讀以特質區塊為主」；0 條 → 整段不輸出且不加尾註'),
    ('calib_risk', 'both',         '#### 交互作用——作答校準與風險提示', 2, 2,
     '無'),
    ('other',      'whole_person', '#### 交互作用——其他參考',         3, 3,
     '無（全注入，無截斷、無「未注入」尾註）')
ON CONFLICT (block_key) DO UPDATE SET
    question_type = EXCLUDED.question_type,
    header_text   = EXCLUDED.header_text,
    sort_order    = EXCLUDED.sort_order,
    priority      = EXCLUDED.priority,
    footnote_rule = EXCLUDED.footnote_rule;

COMMIT;


-- =====================================================================
-- 驗證（套用後執行，四項都應為 true / 預期值）
-- =====================================================================
-- SELECT count(*) = 3  AS blocks_ok        FROM endpoint_blocks;
-- SELECT count(*) = 71 AS risk_ok          FROM trait_endpoints WHERE endpoint_type = 'risk';
-- SELECT count(*) = 3  AS calibration_ok   FROM trait_endpoints WHERE endpoint_type = 'calibration';
-- SELECT count(*) = 0  AS orphan_block_ok  FROM trait_endpoints e
--   LEFT JOIN endpoint_blocks b USING (block_key) WHERE b.block_key IS NULL;
-- SELECT endpoint_type, endpoint_level, count(*)
--   FROM trait_endpoints GROUP BY 1, 2 ORDER BY 1, 2;
--   -- 預期：risk/core 48、risk/marginal 21、risk/property_peak 2、calibration/NULL 3


-- =====================================================================
-- Runtime 查詢：算出某位受測者命中的端點與其應歸屬的子區塊
-- （:pairs 為該受測者的 (trait_id, band) 陣列）
-- =====================================================================
-- SELECT e.trait_id, e.endpoint_type, b.block_key, b.priority
-- FROM   trait_endpoints e
-- JOIN   endpoint_blocks b USING (block_key)
-- JOIN   unnest(:trait_ids::text[], :bands::text[]) AS p(trait_id, band)
--        ON p.trait_id = e.trait_id
--       AND (e.band = p.band OR e.band = '*');
--
-- 交互歸屬：一條交互取其兩端所命中全部型別中 min(priority) 的 block_key，只輸出一次。


-- =====================================================================
-- 回滾（僅在需要完全撤銷本次變更時使用）
-- =====================================================================
-- BEGIN;
-- DROP TABLE IF EXISTS trait_endpoints;
-- DROP TABLE IF EXISTS endpoint_blocks;
-- COMMIT;


-- =====================================================================
-- ⚠ 套用後必須同步修改匯入程式（scripts/migrate_traits_from_excel.py）
--
-- 1. trait_endpoints 對 trait_definitions 有外鍵，而既有匯入的第一步是
--        TRUNCATE trait_interactions, trait_bands, trait_definitions CASCADE
--    CASCADE 會連帶清空 trait_endpoints。這在「同一次匯入會把 09 分頁重新
--    載入」的前提下是正確行為，但若有人用**舊版 spec 檔（沒有 09 分頁）**
--    執行匯入，端點會被靜默清空且不會有任何錯誤訊息。
--    → 匯入程式必須在找不到 09_endpoints 分頁時**中止並報錯**，不得繼續。
--
-- 2. 匯入順序：definitions → bands → interactions → endpoint_blocks(10 分頁)
--    → trait_endpoints(09 分頁)。endpoint_blocks 無外鍵指向 trait 表，
--    不會被上述 CASCADE 清掉，須以 upsert 方式更新。
--
-- 3. 匯入後應自動比對端點筆數與集合是否符合內容方核可的清單，不符即中止。
-- =====================================================================

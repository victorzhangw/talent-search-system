-- 01_schema.sql
-- Database Schema for Traitty V2

-- Clean up existing tables (Optional)
-- DROP TABLE IF EXISTS trait_interactions CASCADE;
-- DROP TABLE IF EXISTS trait_bands CASCADE;
-- DROP TABLE IF EXISTS trait_definitions CASCADE;
-- DROP TABLE IF EXISTS chat_messages CASCADE;
-- DROP TABLE IF EXISTS chat_sessions CASCADE;
-- DROP TABLE IF EXISTS admin_users CASCADE;

-- 1. Admin Users
CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

-- 2. Chat Sessions
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(50),  -- Email or ID
    workflow_id VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    started_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    last_active_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    metadata JSON DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);

-- 3. Chat Messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- user, assistant, system
    content TEXT NOT NULL,
    token_usage INTEGER DEFAULT 0,
    model_name VARCHAR(50),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);

-- 4. Trait Definitions
CREATE TABLE IF NOT EXISTS trait_definitions (
    trait_id VARCHAR(50) PRIMARY KEY,
    name_zh VARCHAR(100),
    name_en VARCHAR(100),
    dimension VARCHAR(50),
    definition TEXT
);

-- 5. Trait Bands
CREATE TABLE IF NOT EXISTS trait_bands (
    id SERIAL PRIMARY KEY,
    trait_id VARCHAR(50) REFERENCES trait_definitions(trait_id) ON DELETE CASCADE,
    trait_project VARCHAR(50),
    band VARCHAR(10), -- A, B, C
    min_score INTEGER,
    max_score INTEGER,
    semantic_label VARCHAR(50),
    description TEXT,
    management_focus TEXT,
    report_wording TEXT,
    report_wording_friendly TEXT,
    ai_guidance JSON,
    CONSTRAINT uq_trait_bands UNIQUE (trait_id, band)

);
CREATE INDEX IF NOT EXISTS idx_trait_bands_trait_id ON trait_bands(trait_id);

-- 6. Trait Interactions
CREATE TABLE IF NOT EXISTS trait_interactions (
    id SERIAL PRIMARY KEY,
    primary_trait_id VARCHAR(50) REFERENCES trait_definitions(trait_id) ON DELETE CASCADE,
    primary_band VARCHAR(10),
    trigger_trait_id VARCHAR(50), -- No FK to simplify circular refs during load, or add later
    trigger_band VARCHAR(10),
    narrative TEXT,
    CONSTRAINT uq_trait_interactions UNIQUE (primary_trait_id, primary_band, trigger_trait_id, trigger_band)

);

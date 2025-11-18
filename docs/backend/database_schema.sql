-- ============================================================
-- Traitty 人才評鑑系統 - 資料庫 Schema
-- ============================================================
-- 基於現有代碼反推的資料庫結構
-- Email: tank_howard@hotmail.com (Howard)
-- ============================================================

-- ============================================================
-- 1. 用戶相關表
-- ============================================================

-- 核心用戶表
CREATE TABLE core_user (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) NOT NULL UNIQUE,
    email VARCHAR(254) UNIQUE,
    password VARCHAR(128) NOT NULL,
    first_name VARCHAR(150),
    last_name VARCHAR(150),
    is_active BOOLEAN DEFAULT TRUE,
    is_staff BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    date_joined TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE core_user IS '核心用戶表 - 存儲所有用戶的基本資訊';
COMMENT ON COLUMN core_user.username IS '用戶名（唯一）';
COMMENT ON COLUMN core_user.email IS '電子郵件（唯一）';
COMMENT ON COLUMN core_user.date_joined IS '註冊日期';

-- 個人檔案表
CREATE TABLE individual_profile (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES core_user(id) ON DELETE CASCADE,
    phone VARCHAR(20),
    birth_date DATE,
    gender VARCHAR(10),
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),
    bio TEXT,
    avatar_url TEXT,
    linkedin_url TEXT,
    github_url TEXT,
    website_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE individual_profile IS '個人檔案表 - 存儲用戶的詳細個人資訊';
COMMENT ON COLUMN individual_profile.user_id IS '關聯到 core_user 的外鍵';
COMMENT ON COLUMN individual_profile.phone IS '聯絡電話';

-- ============================================================
-- 2. 特質定義表
-- ============================================================

-- 特質表
CREATE TABLE trait (
    id SERIAL PRIMARY KEY,
    chinese_name VARCHAR(100) NOT NULL,
    system_name VARCHAR(100) NOT NULL UNIQUE,
    english_name VARCHAR(100),
    description TEXT,
    category VARCHAR(50),
    subcategory VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE trait IS '特質定義表 - 定義所有可評估的特質';
COMMENT ON COLUMN trait.chinese_name IS '特質中文名稱';
COMMENT ON COLUMN trait.system_name IS '系統內部使用的特質名稱（唯一）';
COMMENT ON COLUMN trait.category IS '特質分類（如：認知能力、人際特質等）';

-- 特質分類表
CREATE TABLE trait_category (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_id INTEGER REFERENCES trait_category(id),
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE trait_category IS '特質分類表 - 組織特質的層級結構';

-- ============================================================
-- 3. 測評結果表
-- ============================================================

-- 個人測評結果表
CREATE TABLE individual_test_result (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES core_user(id) ON DELETE CASCADE,
    test_type VARCHAR(50) DEFAULT 'traitty',
    test_version VARCHAR(20),
    test_completion_date TIMESTAMP WITH TIME ZONE,
    trait_results JSONB NOT NULL,
    overall_score DECIMAL(5,2),
    percentile_rank DECIMAL(5,2),
    test_duration_minutes INTEGER,
    is_valid BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE individual_test_result IS '個人測評結果表 - 存儲用戶的測評結果';
COMMENT ON COLUMN individual_test_result.trait_results IS 'JSONB 格式存儲所有特質分數，結構: {"特質名稱": {"score": 85, "percentile": 75, "description": "..."}}';
COMMENT ON COLUMN individual_test_result.test_completion_date IS '測評完成日期';

-- 測評結果詳細表（可選，用於更細緻的分析）
CREATE TABLE test_result_detail (
    id SERIAL PRIMARY KEY,
    test_result_id INTEGER NOT NULL REFERENCES individual_test_result(id) ON DELETE CASCADE,
    trait_id INTEGER NOT NULL REFERENCES trait(id),
    raw_score DECIMAL(5,2),
    normalized_score DECIMAL(5,2),
    percentile DECIMAL(5,2),
    z_score DECIMAL(5,2),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE test_result_detail IS '測評結果詳細表 - 存儲每個特質的詳細分數';

-- ============================================================
-- 4. 測評問題和答案表
-- ============================================================

-- 測評問卷表
CREATE TABLE test_questionnaire (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    version VARCHAR(20),
    description TEXT,
    total_questions INTEGER,
    estimated_duration_minutes INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE test_questionnaire IS '測評問卷表 - 定義不同版本的測評問卷';

-- 測評題目表
CREATE TABLE test_question (
    id SERIAL PRIMARY KEY,
    questionnaire_id INTEGER REFERENCES test_questionnaire(id),
    question_number INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    question_type VARCHAR(20) DEFAULT 'likert',
    trait_id INTEGER REFERENCES trait(id),
    is_reverse_scored BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE test_question IS '測評題目表 - 存儲測評的具體題目';

-- 用戶答題記錄表
CREATE TABLE user_answer (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES core_user(id) ON DELETE CASCADE,
    test_result_id INTEGER REFERENCES individual_test_result(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES test_question(id),
    answer_value INTEGER,
    answer_text TEXT,
    response_time_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE user_answer IS '用戶答題記錄表 - 記錄用戶對每個題目的回答';

-- ============================================================
-- 5. 報告和分析表
-- ============================================================

-- 評鑑報告表
CREATE TABLE assessment_report (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES core_user(id) ON DELETE CASCADE,
    test_result_id INTEGER REFERENCES individual_test_result(id),
    report_type VARCHAR(50) DEFAULT 'individual',
    report_title VARCHAR(200),
    report_content JSONB,
    pdf_url TEXT,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE assessment_report IS '評鑑報告表 - 存儲生成的評鑑報告';
COMMENT ON COLUMN assessment_report.report_content IS 'JSONB 格式存儲報告內容';

-- 特質建議表
CREATE TABLE trait_recommendation (
    id SERIAL PRIMARY KEY,
    test_result_id INTEGER NOT NULL REFERENCES individual_test_result(id) ON DELETE CASCADE,
    trait_id INTEGER NOT NULL REFERENCES trait(id),
    recommendation_type VARCHAR(50),
    recommendation_text TEXT,
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE trait_recommendation IS '特質建議表 - 基於測評結果提供的改善建議';

-- ============================================================
-- 6. 索引
-- ============================================================

-- 用戶表索引
CREATE INDEX idx_core_user_email ON core_user(email);
CREATE INDEX idx_core_user_username ON core_user(username);
CREATE INDEX idx_core_user_date_joined ON core_user(date_joined);

-- 測評結果表索引
CREATE INDEX idx_test_result_user_id ON individual_test_result(user_id);
CREATE INDEX idx_test_result_completion_date ON individual_test_result(test_completion_date);
CREATE INDEX idx_test_result_trait_results ON individual_test_result USING GIN(trait_results);

-- 個人檔案表索引
CREATE INDEX idx_individual_profile_user_id ON individual_profile(user_id);

-- 特質表索引
CREATE INDEX idx_trait_system_name ON trait(system_name);
CREATE INDEX idx_trait_category ON trait(category);

-- 答題記錄表索引
CREATE INDEX idx_user_answer_user_id ON user_answer(user_id);
CREATE INDEX idx_user_answer_test_result_id ON user_answer(test_result_id);

-- ============================================================
-- 7. 視圖（View）
-- ============================================================

-- 用戶完整資訊視圖
CREATE OR REPLACE VIEW v_user_full_profile AS
SELECT 
    cu.id,
    cu.username,
    cu.email,
    cu.date_joined,
    ip.phone,
    ip.birth_date,
    ip.gender,
    ip.city,
    ip.country
FROM core_user cu
LEFT JOIN individual_profile ip ON cu.id = ip.user_id;

COMMENT ON VIEW v_user_full_profile IS '用戶完整資訊視圖 - 合併用戶和個人檔案資訊';

-- 最新測評結果視圖
CREATE OR REPLACE VIEW v_latest_test_results AS
SELECT DISTINCT ON (user_id)
    user_id,
    id as test_result_id,
    test_completion_date,
    trait_results,
    overall_score,
    percentile_rank
FROM individual_test_result
ORDER BY user_id, test_completion_date DESC NULLS LAST;

COMMENT ON VIEW v_latest_test_results IS '最新測評結果視圖 - 每個用戶的最新測評結果';

-- ============================================================
-- 8. 觸發器（Trigger）
-- ============================================================

-- 更新時間戳觸發器函數
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 為各表添加更新時間戳觸發器
CREATE TRIGGER update_core_user_updated_at
    BEFORE UPDATE ON core_user
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_individual_profile_updated_at
    BEFORE UPDATE ON individual_profile
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trait_updated_at
    BEFORE UPDATE ON trait
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_test_result_updated_at
    BEFORE UPDATE ON individual_test_result
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 9. 範例資料（Sample Data）
-- ============================================================

-- 插入範例用戶（Howard）
-- INSERT INTO core_user (username, email, first_name, last_name)
-- VALUES ('Howard', 'tank_howard@hotmail.com', 'Howard', 'Tank');

-- 插入範例特質
-- INSERT INTO trait (chinese_name, system_name, description, category)
-- VALUES 
--     ('協調溝通', 'Coordination', '協調和溝通的能力', '人際特質'),
--     ('創造性思考', 'Creative Thinking', '創新和創造性思維能力', '認知能力'),
--     ('領導能力', 'Leadership', '領導和管理團隊的能力', '領導特質');

-- ============================================================
-- 10. 權限設定（Permissions）
-- ============================================================

-- 創建應用程式用戶
-- CREATE USER traitty_app WITH PASSWORD 'your_secure_password';

-- 授予權限
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO traitty_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO traitty_app;

-- ============================================================
-- 結束
-- ============================================================

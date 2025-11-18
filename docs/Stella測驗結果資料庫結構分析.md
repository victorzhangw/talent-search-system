# Stella 測驗結果資料庫結構分析

## 受測人員資訊

- **Email**: stella24168@gmail.com
- **姓名**: Stella
- **職務角色**: 專案經理
- **身份別**: 在職
- **測驗項目**: AI 時代人才潛能評鑑 (AI Nexus Insight)
- **邀請時間**: 2025 年 09 月 15 日 18:20
- **結果取得時間**: 2025 年 09 月 17 日 13:41

## 資料庫表結構與關聯

### 1. 核心資料表

#### 1.1 core_user (使用者表)

```sql
SELECT id, email, first_name, last_name, user_type, created_at
FROM core_user
WHERE email = 'stella24168@gmail.com';
```

**欄位說明**:

- `id`: 使用者 ID (主鍵)
- `email`: 電子郵件 (唯一)
- `first_name`: 名字
- `last_name`: 姓氏
- `user_type`: 使用者類型 (candidate/recruiter/admin)
- `created_at`: 建立時間

#### 1.2 test_result (測驗結果主表)

```sql
SELECT id, user_id, test_project_id, status, completed_at, created_at
FROM test_result
WHERE user_id = (SELECT id FROM core_user WHERE email = 'stella24168@gmail.com');
```

**欄位說明**:

- `id`: 測驗結果 ID (主鍵)
- `user_id`: 關聯到 core_user.id
- `test_project_id`: 關聯到 test_project.id
- `status`: 測驗狀態 (pending/in_progress/completed)
- `completed_at`: 完成時間
- `created_at`: 建立時間

#### 1.3 test_result_trait (特質評分結果表)

```sql
SELECT
    trt.id,
    trt.test_result_id,
    trt.trait_id,
    trt.score,
    trt.percentile,
    trt.created_at
FROM test_result_trait trt
WHERE trt.test_result_id = ?;
```

**欄位說明**:

- `id`: 評分記錄 ID (主鍵)
- `test_result_id`: 關聯到 test_result.id
- `trait_id`: 關聯到 trait.id
- `score`: 特質分數 (0-100)
- `percentile`: 百分位數 (0-100)
- `created_at`: 建立時間

### 2. 特質定義表

#### 2.1 trait (特質表)

```sql
SELECT id, chinese_name, system_name, description, category
FROM trait
ORDER BY id;
```

**欄位說明**:

- `id`: 特質 ID (主鍵)
- `chinese_name`: 中文名稱 (如：AI 科技素養、人際溝通、創造性思考)
- `system_name`: 系統名稱 (英文識別碼)
- `description`: 特質描述
- `category`: 特質分類

**常見特質範例**:

- AI 科技素養
- 人際溝通
- 創造性思考
- 協商談判
- 好奇心
- 學習敏捷
- 問題解決
- 批判性思維
- 情緒智商
- 團隊合作
- 領導力
- 適應力
- 責任感
- 誠信
- 自我管理
- 壓力管理
- 時間管理
- 決策能力
- 策略思維
- 數據分析

### 3. 測驗專案與分類

#### 3.1 test_project (測驗專案表)

```sql
SELECT id, name, category_id, description, is_active
FROM test_project;
```

**欄位說明**:

- `id`: 專案 ID (主鍵)
- `name`: 專案名稱 (如：AI Nexus Insight)
- `category_id`: 關聯到 test_project_category.id
- `description`: 專案描述
- `is_active`: 是否啟用

#### 3.2 test_project_category (測驗專案分類表)

```sql
SELECT id, name, description
FROM test_project_category;
```

**欄位說明**:

- `id`: 分類 ID (主鍵)
- `name`: 分類名稱 (如：AI 時代人才潛能評鑑)
- `description`: 分類描述

#### 3.3 test_project_category_trait (分類與特質關聯表)

```sql
SELECT category_id, trait_id
FROM test_project_category_trait
WHERE category_id = ?;
```

**欄位說明**:

- `category_id`: 關聯到 test_project_category.id
- `trait_id`: 關聯到 trait.id
- 定義哪些特質屬於哪個測驗分類

## 資料查詢流程

### 完整查詢範例：取得 Stella 的測驗結果報告

```sql
SELECT
    -- 使用者資訊
    u.id as user_id,
    u.email,
    u.first_name,
    u.last_name,
    u.user_type,

    -- 測驗結果資訊
    tr.id as test_result_id,
    tr.status,
    tr.completed_at,
    tr.created_at as test_created_at,

    -- 測驗專案資訊
    tp.id as project_id,
    tp.name as project_name,

    -- 分類資訊
    tpc.id as category_id,
    tpc.name as category_name,
    tpc.description as category_description,

    -- 特質資訊
    t.id as trait_id,
    t.chinese_name as trait_name,
    t.system_name as trait_system_name,
    t.description as trait_description,

    -- 評分資訊
    trt.score,
    trt.percentile

FROM core_user u

-- 關聯測驗結果
INNER JOIN test_result tr ON u.id = tr.user_id

-- 關聯測驗專案
INNER JOIN test_project tp ON tr.test_project_id = tp.id

-- 關聯專案分類
LEFT JOIN test_project_category tpc ON tp.category_id = tpc.id

-- 關聯特質評分
INNER JOIN test_result_trait trt ON tr.id = trt.test_result_id

-- 關聯特質定義
INNER JOIN trait t ON trt.trait_id = t.id

-- 篩選條件
WHERE u.email = 'stella24168@gmail.com'
  AND tr.status = 'completed'

-- 排序
ORDER BY trt.score DESC;
```

## 報告生成邏輯

### 步驟 1: 識別使用者

```sql
SELECT id FROM core_user WHERE email = 'stella24168@gmail.com';
```

### 步驟 2: 取得最新測驗結果

```sql
SELECT id, test_project_id, completed_at
FROM test_result
WHERE user_id = ? AND status = 'completed'
ORDER BY completed_at DESC
LIMIT 1;
```

### 步驟 3: 取得所有特質分數

```sql
SELECT
    t.chinese_name,
    t.description,
    trt.score,
    trt.percentile
FROM test_result_trait trt
JOIN trait t ON trt.trait_id = t.id
WHERE trt.test_result_id = ?
ORDER BY trt.score DESC;
```

### 步驟 4: 按分類組織特質

```sql
SELECT
    tpc.name as category_name,
    t.chinese_name as trait_name,
    trt.score,
    trt.percentile
FROM test_result_trait trt
JOIN trait t ON trt.trait_id = t.id
JOIN test_project_category_trait tpct ON t.id = tpct.trait_id
JOIN test_project_category tpc ON tpct.category_id = tpc.id
WHERE trt.test_result_id = ?
ORDER BY tpc.name, trt.score DESC;
```

## 資料合併與顯示邏輯

### 報告結構

1. **基本資訊區塊**

   - 從 `core_user` 取得姓名、email
   - 從 `test_result` 取得完成時間
   - 從 `test_project` 取得測驗名稱

2. **特質分數區塊**

   - 從 `test_result_trait` 取得分數和百分位
   - 從 `trait` 取得特質名稱和描述
   - 按分數高低排序顯示

3. **分類統計區塊**

   - 透過 `test_project_category_trait` 將特質分組
   - 計算各分類的平均分數
   - 生成雷達圖或長條圖

4. **詳細分析區塊**
   - 針對高分特質提供正面描述
   - 針對低分特質提供發展建議
   - 從 `trait.description` 取得詳細說明

## 關鍵欄位對應

| 報告顯示項目 | 資料來源              | 欄位                     |
| ------------ | --------------------- | ------------------------ |
| 受測者姓名   | core_user             | first_name, last_name    |
| 電子信箱     | core_user             | email                    |
| 職務角色     | test_result           | 可能存在額外欄位或關聯表 |
| 測驗項目     | test_project          | name                     |
| 完成時間     | test_result           | completed_at             |
| 特質名稱     | trait                 | chinese_name             |
| 特質分數     | test_result_trait     | score                    |
| 百分位數     | test_result_trait     | percentile               |
| 特質描述     | trait                 | description              |
| 分類名稱     | test_project_category | name                     |

## 資料完整性檢查

### 必要的資料表

- ✓ core_user
- ✓ test_result
- ✓ test_result_trait
- ✓ trait
- ✓ test_project
- ✓ test_project_category
- ✓ test_project_category_trait

### 關聯完整性

```sql
-- 檢查是否所有 test_result 都有對應的 user
SELECT COUNT(*) FROM test_result tr
LEFT JOIN core_user u ON tr.user_id = u.id
WHERE u.id IS NULL;

-- 檢查是否所有 test_result_trait 都有對應的 trait
SELECT COUNT(*) FROM test_result_trait trt
LEFT JOIN trait t ON trt.trait_id = t.id
WHERE t.id IS NULL;

-- 檢查是否所有 trait 都有對應的分類
SELECT COUNT(*) FROM trait t
LEFT JOIN test_project_category_trait tpct ON t.id = tpct.trait_id
WHERE tpct.trait_id IS NULL;
```

## 效能優化建議

### 索引建議

```sql
-- core_user 表
CREATE INDEX idx_core_user_email ON core_user(email);

-- test_result 表
CREATE INDEX idx_test_result_user_id ON test_result(user_id);
CREATE INDEX idx_test_result_status ON test_result(status);
CREATE INDEX idx_test_result_completed_at ON test_result(completed_at);

-- test_result_trait 表
CREATE INDEX idx_test_result_trait_result_id ON test_result_trait(test_result_id);
CREATE INDEX idx_test_result_trait_trait_id ON test_result_trait(trait_id);
CREATE INDEX idx_test_result_trait_score ON test_result_trait(score);

-- test_project_category_trait 表
CREATE INDEX idx_tpct_category_id ON test_project_category_trait(category_id);
CREATE INDEX idx_tpct_trait_id ON test_project_category_trait(trait_id);
```

### 查詢優化

- 使用 JOIN 而非子查詢
- 限制返回的欄位數量
- 使用適當的 WHERE 條件過濾
- 考慮使用視圖 (VIEW) 簡化複雜查詢

## 總結

Stella 的測驗結果報告資料來自多個資料表的關聯查詢：

1. **使用者識別**: 透過 email 在 `core_user` 找到使用者
2. **測驗記錄**: 在 `test_result` 找到該使用者的測驗記錄
3. **特質評分**: 在 `test_result_trait` 找到所有特質的分數
4. **特質資訊**: 在 `trait` 找到特質的名稱和描述
5. **分類資訊**: 透過 `test_project_category_trait` 和 `test_project_category` 組織特質分類
6. **報告生成**: 將所有資料合併，按照報告模板格式化輸出

這個結構設計允許：

- 靈活定義新的特質
- 動態組合不同的測驗專案
- 追蹤使用者的多次測驗記錄
- 支援多種報告格式和分析維度

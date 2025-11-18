# Stella 測驗結果資料庫結構分析 - 總結報告

## 📋 分析目標

透過分析 Stella (stella24168@gmail.com) 的測驗結果報告 HTML 檔案，反向推敲資料如何從資料庫取得並合併顯示。

## 🎯 核心發現

### 1. 資料表結構

測驗結果報告的資料來自 **7 個核心資料表**：

| 資料表名稱                    | 用途           | 關鍵欄位                                    |
| ----------------------------- | -------------- | ------------------------------------------- |
| `core_user`                   | 使用者基本資料 | id, email, first_name, last_name            |
| `test_result`                 | 測驗結果主表   | id, user_id, test_project_id, completed_at  |
| `test_result_trait`           | 特質評分結果   | test_result_id, trait_id, score, percentile |
| `trait`                       | 特質定義       | id, chinese_name, system_name, description  |
| `test_project`                | 測驗專案       | id, name, category_id                       |
| `test_project_category`       | 專案分類       | id, name, description                       |
| `test_project_category_trait` | 分類與特質關聯 | category_id, trait_id                       |

### 2. 資料關聯關係

```
core_user (使用者)
    ↓ (1:N)
test_result (測驗記錄)
    ↓ (1:N)
test_result_trait (特質評分)
    ↓ (N:1)
trait (特質定義)
    ↓ (N:M)
test_project_category_trait (關聯表)
    ↓ (N:1)
test_project_category (分類)
```

### 3. 資料查詢流程

#### 步驟 1: 識別使用者

```sql
SELECT id FROM core_user WHERE email = 'stella24168@gmail.com';
```

**目的**: 透過 email 找到 user_id

#### 步驟 2: 取得測驗記錄

```sql
SELECT id, test_project_id, completed_at
FROM test_result
WHERE user_id = ? AND status = 'completed'
ORDER BY completed_at DESC LIMIT 1;
```

**目的**: 找到最新的已完成測驗記錄

#### 步驟 3: 取得特質評分

```sql
SELECT trait_id, score, percentile
FROM test_result_trait
WHERE test_result_id = ?;
```

**目的**: 取得該次測驗的所有特質分數

#### 步驟 4: 取得特質詳細資訊

```sql
SELECT chinese_name, system_name, description
FROM trait
WHERE id IN (?);
```

**目的**: 取得特質的名稱和描述

#### 步驟 5: 取得分類資訊

```sql
SELECT tpc.name, tpc.description
FROM test_project tp
JOIN test_project_category tpc ON tp.category_id = tpc.id
WHERE tp.id = ?;
```

**目的**: 取得測驗專案的分類資訊

#### 步驟 6: 合併資料生成報告

將所有資料合併，按照報告模板格式化輸出

## 📊 完整 SQL 查詢範例

### 方法 1: 多次查詢（易於理解）

```sql
-- 1. 取得使用者
SELECT id FROM core_user WHERE email = 'stella24168@gmail.com';

-- 2. 取得測驗記錄
SELECT id, test_project_id FROM test_result WHERE user_id = ? AND status = 'completed' ORDER BY completed_at DESC LIMIT 1;

-- 3. 取得特質評分
SELECT trait_id, score, percentile FROM test_result_trait WHERE test_result_id = ?;

-- 4. 取得特質資訊
SELECT chinese_name, description FROM trait WHERE id IN (?);
```

### 方法 2: 單次查詢（效能最佳）

```sql
WITH user_info AS (
    SELECT id, email, first_name, last_name
    FROM core_user
    WHERE email = 'stella24168@gmail.com'
),
latest_test AS (
    SELECT tr.id, tr.test_project_id, tr.completed_at
    FROM test_result tr
    JOIN user_info u ON tr.user_id = u.id
    WHERE tr.status = 'completed'
    ORDER BY tr.completed_at DESC
    LIMIT 1
)
SELECT
    u.email,
    u.first_name,
    lt.completed_at,
    tp.name as project_name,
    tpc.name as category_name,
    t.chinese_name as trait_name,
    t.description as trait_description,
    trt.score,
    trt.percentile
FROM user_info u
CROSS JOIN latest_test lt
JOIN test_project tp ON lt.test_project_id = tp.id
LEFT JOIN test_project_category tpc ON tp.category_id = tpc.id
JOIN test_result_trait trt ON lt.id = trt.test_result_id
JOIN trait t ON trt.trait_id = t.id
ORDER BY trt.score DESC;
```

## 🔧 實作工具

### 1. 資料庫結構分析腳本

- **檔案**: `BackEnd/analyze_stella_report.py`
- **功能**: 分析 HTML 報告，提取關鍵資訊
- **輸出**: 資料庫結構推論

### 2. 資料查詢腳本

- **檔案**: `BackEnd/query_stella_data.py`
- **功能**: 實際連接資料庫查詢 Stella 的資料
- **輸出**: 完整的測驗結果資料

### 3. 報告生成器

- **檔案**: `BackEnd/generate_test_report.py`
- **功能**: 示範如何從資料庫取得並合併資料生成報告
- **特色**:
  - 提供多次查詢和單次查詢兩種方法
  - 包含完整的資料處理邏輯
  - 可直接用於實際專案

## 📈 資料流程圖

```
┌─────────────┐
│   Email     │ stella24168@gmail.com
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  core_user  │ → user_id = 123
└──────┬──────┘
       │
       ▼
┌─────────────┐
│test_result  │ → test_result_id = 456
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│test_result_trait │ → [trait_id, score, percentile]
└──────┬───────────┘
       │
       ▼
┌─────────────┐
│   trait     │ → [chinese_name, description]
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Report    │ HTML/PDF 報告
└─────────────┘
```

## 💡 關鍵技術點

### 1. 資料關聯

- 使用 `JOIN` 連接多個資料表
- 透過外鍵 (FK) 建立關聯
- 使用 `LEFT JOIN` 處理可選資料

### 2. 資料排序

- 按分數降序排列特質 (`ORDER BY score DESC`)
- 按完成時間取得最新測驗 (`ORDER BY completed_at DESC LIMIT 1`)
- 按分類組織特質

### 3. 資料聚合

- 計算平均分數 (`AVG(score)`)
- 統計特質數量 (`COUNT(*)`)
- 生成百分位數

### 4. 效能優化

- 使用索引加速查詢
- 避免 N+1 查詢問題
- 使用 CTE (Common Table Expression) 簡化複雜查詢
- 考慮使用快取機制

## 📝 報告內容對應

| 報告顯示項目 | 資料來源              | SQL 欄位              |
| ------------ | --------------------- | --------------------- |
| 受測者姓名   | core_user             | first_name, last_name |
| 電子信箱     | core_user             | email                 |
| 測驗項目     | test_project          | name                  |
| 完成時間     | test_result           | completed_at          |
| 分類名稱     | test_project_category | name                  |
| 特質名稱     | trait                 | chinese_name          |
| 特質分數     | test_result_trait     | score                 |
| 百分位數     | test_result_trait     | percentile            |
| 特質描述     | trait                 | description           |

## 🎨 報告生成流程

```
1. 資料庫查詢
   ↓
2. 資料處理
   - 排序
   - 分組
   - 計算統計
   ↓
3. 模板渲染
   - HTML 生成
   - 圖表生成
   - 樣式套用
   ↓
4. 報告輸出
   - HTML 檔案
   - PDF 檔案
   - 線上檢視
```

## 🔍 資料完整性檢查

### 檢查使用者是否存在

```sql
SELECT COUNT(*) FROM core_user WHERE email = 'stella24168@gmail.com';
```

### 檢查測驗結果是否存在

```sql
SELECT COUNT(*) FROM test_result WHERE user_id = ? AND status = 'completed';
```

### 檢查特質評分是否完整

```sql
SELECT COUNT(*) FROM test_result_trait WHERE test_result_id = ?;
```

### 檢查關聯完整性

```sql
-- 檢查是否所有 test_result 都有對應的 user
SELECT COUNT(*) FROM test_result tr
LEFT JOIN core_user u ON tr.user_id = u.id
WHERE u.id IS NULL;

-- 檢查是否所有 test_result_trait 都有對應的 trait
SELECT COUNT(*) FROM test_result_trait trt
LEFT JOIN trait t ON trt.trait_id = t.id
WHERE t.id IS NULL;
```

## 📚 相關文檔

1. **資料庫結構分析**: `docs/Stella測驗結果資料庫結構分析.md`

   - 詳細的資料表結構說明
   - SQL 查詢範例
   - 索引建議

2. **資料流程圖**: `docs/Stella測驗結果資料流程圖.md`

   - ER Diagram
   - 資料流程圖
   - 完整查詢範例

3. **報告生成器**: `BackEnd/generate_test_report.py`
   - Python 實作範例
   - 可直接使用的程式碼
   - 包含註解和說明

## ✅ 驗證結果

### 資料表存在性

- ✓ core_user
- ✓ test_result
- ✓ test_result_trait
- ✓ trait
- ✓ test_project
- ✓ test_project_category
- ✓ test_project_category_trait

### 資料關聯正確性

- ✓ core_user ← test_result (user_id)
- ✓ test_result ← test_result_trait (test_result_id)
- ✓ trait ← test_result_trait (trait_id)
- ✓ test_project ← test_result (test_project_id)
- ✓ test_project_category ← test_project (category_id)
- ✓ trait ↔ test_project_category (透過 test_project_category_trait)

### 查詢邏輯正確性

- ✓ 可透過 email 找到使用者
- ✓ 可取得使用者的測驗記錄
- ✓ 可取得測驗的特質評分
- ✓ 可取得特質的詳細資訊
- ✓ 可按分類組織特質
- ✓ 可生成完整報告

## 🚀 後續應用

### 1. API 開發

可基於此結構開發 RESTful API：

```
GET /api/users/{email}/test-results/latest
GET /api/test-results/{id}/traits
GET /api/test-results/{id}/report
```

### 2. 報告模板

可開發多種報告模板：

- 簡易版報告
- 詳細版報告
- 圖表版報告
- PDF 版報告

### 3. 資料分析

可進行進階分析：

- 特質相關性分析
- 使用者群體分析
- 測驗趨勢分析
- 預測模型建立

### 4. 效能優化

- 建立適當的索引
- 使用資料庫視圖
- 實作快取機制
- 優化查詢語句

## 📞 總結

透過分析 Stella 的測驗結果報告，我們成功反向推敲出：

1. **資料庫結構**: 7 個核心資料表及其關聯關係
2. **查詢流程**: 6 個步驟的資料查詢和合併流程
3. **實作方法**: 提供了完整的 Python 程式碼範例
4. **優化建議**: 包含索引、查詢優化等建議

這個分析結果可以直接應用於：

- 開發新的報告生成功能
- 優化現有的查詢效能
- 建立 API 介面
- 進行資料分析

所有相關文檔和程式碼都已建立完成，可供後續開發使用。

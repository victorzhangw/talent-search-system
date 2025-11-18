# Stella 測驗結果資料流程圖

## 資料表關聯圖 (ER Diagram)

```
┌─────────────────────┐
│   core_user         │
├─────────────────────┤
│ id (PK)            │◄─────┐
│ email              │      │
│ first_name         │      │
│ last_name          │      │
│ user_type          │      │
│ created_at         │      │
└─────────────────────┘      │
                             │
                             │ user_id (FK)
                             │
┌─────────────────────┐      │
│  test_result        │      │
├─────────────────────┤      │
│ id (PK)            │◄─────┤
│ user_id (FK)       │──────┘
│ test_project_id(FK)│──────┐
│ status             │      │
│ completed_at       │      │
│ created_at         │      │
└─────────────────────┘      │
         │                   │
         │                   │ test_project_id (FK)
         │                   │
         │              ┌─────────────────────┐
         │              │  test_project       │
         │              ├─────────────────────┤
         │              │ id (PK)            │
         │              │ name               │
         │              │ category_id (FK)   │──────┐
         │              │ description        │      │
         │              │ is_active          │      │
         │              └─────────────────────┘      │
         │                                           │
         │ test_result_id (FK)                       │ category_id (FK)
         │                                           │
         ▼                                           ▼
┌─────────────────────┐              ┌─────────────────────────┐
│test_result_trait    │              │test_project_category    │
├─────────────────────┤              ├─────────────────────────┤
│ id (PK)            │              │ id (PK)                │◄────┐
│ test_result_id(FK) │              │ name                   │     │
│ trait_id (FK)      │──────┐       │ description            │     │
│ score              │      │       └─────────────────────────┘     │
│ percentile         │      │                    │                  │
│ created_at         │      │                    │                  │
└─────────────────────┘      │                    │                  │
                             │                    │                  │
                             │ trait_id (FK)      │                  │
                             │                    │                  │
                             ▼                    ▼                  │
                    ┌─────────────────────┐  ┌──────────────────────────┐
                    │      trait          │  │test_project_category_trait│
                    ├─────────────────────┤  ├──────────────────────────┤
                    │ id (PK)            │◄─┤ category_id (FK)         │
                    │ chinese_name       │  │ trait_id (FK)            │──┘
                    │ system_name        │  └──────────────────────────┘
                    │ description        │
                    │ category           │
                    └─────────────────────┘
```

## 資料查詢流程 (Data Flow)

### 流程 1: 取得使用者測驗結果

```
┌──────────────────────────────────────────────────────────────┐
│ 步驟 1: 識別使用者                                            │
│ ─────────────────────────────────────────────────────────── │
│ INPUT: email = 'stella24168@gmail.com'                      │
│                                                              │
│ SELECT id FROM core_user WHERE email = ?                    │
│                                                              │
│ OUTPUT: user_id = 123                                        │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 步驟 2: 取得測驗記錄                                          │
│ ─────────────────────────────────────────────────────────── │
│ INPUT: user_id = 123                                         │
│                                                              │
│ SELECT id, test_project_id, completed_at                     │
│ FROM test_result                                             │
│ WHERE user_id = ? AND status = 'completed'                   │
│ ORDER BY completed_at DESC LIMIT 1                           │
│                                                              │
│ OUTPUT: test_result_id = 456, test_project_id = 789         │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 步驟 3: 取得特質評分                                          │
│ ─────────────────────────────────────────────────────────── │
│ INPUT: test_result_id = 456                                  │
│                                                              │
│ SELECT trait_id, score, percentile                           │
│ FROM test_result_trait                                       │
│ WHERE test_result_id = ?                                     │
│                                                              │
│ OUTPUT: [                                                    │
│   {trait_id: 1, score: 85, percentile: 90},                │
│   {trait_id: 2, score: 73, percentile: 75},                │
│   ...                                                        │
│ ]                                                            │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 步驟 4: 取得特質詳細資訊                                      │
│ ─────────────────────────────────────────────────────────── │
│ INPUT: trait_ids = [1, 2, 3, ...]                           │
│                                                              │
│ SELECT id, chinese_name, system_name, description            │
│ FROM trait                                                   │
│ WHERE id IN (?)                                              │
│                                                              │
│ OUTPUT: [                                                    │
│   {id: 1, name: 'AI科技素養', desc: '...'},                 │
│   {id: 2, name: '人際溝通', desc: '...'},                   │
│   ...                                                        │
│ ]                                                            │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 步驟 5: 取得分類資訊                                          │
│ ─────────────────────────────────────────────────────────── │
│ INPUT: test_project_id = 789                                 │
│                                                              │
│ SELECT tpc.name, tpc.description                             │
│ FROM test_project tp                                         │
│ JOIN test_project_category tpc ON tp.category_id = tpc.id   │
│ WHERE tp.id = ?                                              │
│                                                              │
│ OUTPUT: {                                                    │
│   category_name: 'AI時代人才潛能評鑑',                       │
│   description: '...'                                         │
│ }                                                            │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 步驟 6: 合併資料生成報告                                      │
│ ─────────────────────────────────────────────────────────── │
│ 將所有資料合併：                                              │
│ - 使用者資訊 (姓名、email)                                    │
│ - 測驗資訊 (專案名稱、完成時間)                               │
│ - 特質評分 (名稱、分數、百分位、描述)                         │
│ - 分類資訊 (分類名稱、描述)                                   │
│                                                              │
│ 按照報告模板格式化輸出 HTML/PDF                               │
└──────────────────────────────────────────────────────────────┘
```

## 完整 SQL 查詢範例

### 單一查詢取得所有資料

```sql
WITH user_info AS (
    -- 取得使用者資訊
    SELECT id, email, first_name, last_name
    FROM core_user
    WHERE email = 'stella24168@gmail.com'
),
latest_test AS (
    -- 取得最新測驗記錄
    SELECT tr.id, tr.test_project_id, tr.completed_at
    FROM test_result tr
    JOIN user_info u ON tr.user_id = u.id
    WHERE tr.status = 'completed'
    ORDER BY tr.completed_at DESC
    LIMIT 1
)
-- 取得完整測驗結果
SELECT
    -- 使用者資訊
    u.email,
    u.first_name,
    u.last_name,

    -- 測驗資訊
    lt.completed_at,
    tp.name as project_name,
    tpc.name as category_name,

    -- 特質資訊
    t.chinese_name as trait_name,
    t.description as trait_description,

    -- 評分資訊
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

## 報告生成流程

```
┌─────────────────┐
│  資料庫查詢      │
│  (SQL Query)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  資料處理        │
│  (Data Process) │
│  - 排序          │
│  - 分組          │
│  - 計算統計      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  模板渲染        │
│  (Template)     │
│  - HTML 生成     │
│  - 圖表生成      │
│  - 樣式套用      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  報告輸出        │
│  (Output)       │
│  - HTML 檔案     │
│  - PDF 檔案      │
│  - 線上檢視      │
└─────────────────┘
```

## 資料轉換範例

### 原始資料 (Raw Data)

```json
{
  "user": {
    "email": "stella24168@gmail.com",
    "first_name": "Stella",
    "last_name": ""
  },
  "test_result": {
    "id": 456,
    "completed_at": "2025-09-17T13:41:00Z",
    "project_name": "AI Nexus Insight",
    "category_name": "AI時代人才潛能評鑑"
  },
  "traits": [
    {
      "trait_id": 1,
      "chinese_name": "AI科技素養",
      "score": 85,
      "percentile": 90,
      "description": "..."
    },
    {
      "trait_id": 2,
      "chinese_name": "人際溝通",
      "score": 73,
      "percentile": 75,
      "description": "..."
    }
  ]
}
```

### 報告資料 (Report Data)

```html
<div class="report">
  <div class="header">
    <h1>AI時代人才潛能評鑑</h1>
    <h2>特質分析與多向度洞察報告</h2>
  </div>

  <div class="user-info">
    <p>受測者姓名: Stella</p>
    <p>電子信箱: stella24168@gmail.com</p>
    <p>測驗項目: AI Nexus Insight</p>
    <p>結果取得時間: 2025年09月17日 13:41</p>
  </div>

  <div class="traits">
    <h3>關鍵特質分數</h3>
    <table>
      <tr>
        <td>AI科技素養</td>
        <td>85</td>
        <td>高分者具備...</td>
      </tr>
      <tr>
        <td>人際溝通</td>
        <td>73</td>
        <td>高分者具備...</td>
      </tr>
    </table>
  </div>
</div>
```

## 關鍵技術點

### 1. 資料關聯

- 使用 JOIN 連接多個資料表
- 透過外鍵 (FK) 建立關聯
- 使用 LEFT JOIN 處理可選資料

### 2. 資料排序

- 按分數降序排列特質
- 按完成時間取得最新測驗
- 按分類組織特質

### 3. 資料聚合

- 計算平均分數
- 統計特質數量
- 生成百分位數

### 4. 效能優化

- 使用索引加速查詢
- 避免 N+1 查詢問題
- 使用 CTE 簡化複雜查詢
- 考慮使用快取機制

## 總結

Stella 的測驗結果報告資料流程：

1. **輸入**: 使用者 email
2. **查詢**: 多表關聯查詢
3. **處理**: 資料排序、分組、計算
4. **輸出**: 格式化的 HTML 報告

關鍵資料表：

- `core_user`: 使用者身份
- `test_result`: 測驗記錄
- `test_result_trait`: 特質評分
- `trait`: 特質定義
- `test_project`: 測驗專案
- `test_project_category`: 專案分類

這個架構支援：

- 多使用者多次測驗
- 靈活的特質定義
- 動態的分類組合
- 可擴展的報告格式

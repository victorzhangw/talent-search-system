# JSONB 存儲方案總結

**日期**: 2025-11-15

## 快速回答

**是的！測試數據是以 JSONB 格式存放在 PostgreSQL 資料表中。**

---

## 為什麼使用 JSONB？

### 核心原因

1. **靈活性** 🔄

   - 測評系統的特質可能經常變化
   - 不同版本的測評可能有不同的特質集合
   - 無需修改表結構即可添加新特質

2. **完整性** 📦

   - 保留原始測評數據的完整結構
   - 避免數據在多表之間分散
   - 便於數據備份和遷移

3. **性能** ⚡

   - JSONB 是二進制格式，查詢速度快
   - 支持 GIN 索引，查詢效率高
   - 減少 JOIN 操作，提升查詢性能

4. **可擴展性** 📈
   - 輕鬆添加新的數據欄位
   - 支持嵌套結構
   - 適合快速迭代的產品

---

## 核心 JSONB 欄位

### 1. trait_results (特質結果)

**表**: `individual_test_result`  
**類型**: `JSONB`

```json
{
  "communication": {
    "chinese_name": "溝通能力",
    "score": 82.5,
    "percentile": 75,
    "level": "高"
  },
  "leadership": {
    "chinese_name": "領導力",
    "score": 78.0,
    "percentile": 68,
    "level": "中等"
  }
}
```

**用途**:

- 存儲所有特質的評分結果
- 支持靈活的特質組合
- 便於前端展示和分析

### 2. category_results (分類結果)

**表**: `individual_test_result`  
**類型**: `JSONB`

```json
{
  "銷售角色": {
    "score": 85.0,
    "role_index": 88.5,
    "traits": [...]
  },
  "管理角色": {
    "score": 78.0,
    "role_index": 75.5,
    "traits": [...]
  }
}
```

**用途**:

- 存儲角色分類的評分
- 支持多維度分析
- 用於職位匹配

### 3. raw_data (原始數據)

**表**: `test_project_result`  
**類型**: `JSONB`

```json
{
  "performance_metrics": {...},
  "trait_scores": {...},
  "test_metadata": {...}
}
```

**用途**:

- 保留爬蟲獲取的原始數據
- 用於數據審計和驗證
- 支持後續的數據重新處理

---

## 查詢方式

### 基本查詢

```sql
-- 查詢特定特質的分數
SELECT
    username,
    (trait_results->>'communication')::jsonb->>'score' as score
FROM core_user cu
JOIN individual_test_result itr ON cu.id = itr.user_id;
```

### 條件查詢

```sql
-- 查詢分數 >= 80 的候選人
SELECT username
FROM core_user cu
JOIN individual_test_result itr ON cu.id = itr.user_id
WHERE ((trait_results->>'communication')::jsonb->>'score')::float >= 80;
```

### 模糊查詢

```sql
-- 通過中文名稱查詢
SELECT username
FROM core_user cu
JOIN individual_test_result itr ON cu.id = itr.user_id,
     jsonb_each(itr.trait_results)
WHERE value->>'chinese_name' = '溝通能力'
  AND (value->>'score')::float >= 80;
```

---

## 性能優化

### 創建索引

```sql
-- GIN 索引（推薦）
CREATE INDEX idx_trait_results_gin
ON individual_test_result USING GIN (trait_results);

-- 特定路徑索引
CREATE INDEX idx_trait_results_communication
ON individual_test_result USING GIN ((trait_results->'communication'));
```

### 查詢優化建議

1. ✅ **使用索引**: 為常用查詢路徑創建索引
2. ✅ **避免全表掃描**: 使用 WHERE 條件過濾
3. ✅ **限制結果數量**: 使用 LIMIT
4. ✅ **緩存結果**: 對於頻繁查詢的數據使用緩存
5. ❌ **避免複雜嵌套**: 過深的 JSONB 嵌套會影響性能

---

## 優缺點對比

### 優點 ✅

| 優點     | 說明                         |
| -------- | ---------------------------- |
| 靈活性   | 無需修改表結構即可添加新欄位 |
| 完整性   | 保留原始數據結構             |
| 查詢能力 | 支持複雜的 JSON 查詢         |
| 性能     | 有索引的情況下性能良好       |
| 可擴展性 | 易於擴展新功能               |

### 缺點 ❌

| 缺點     | 說明                     | 解決方案             |
| -------- | ------------------------ | -------------------- |
| 查詢複雜 | SQL 語法較複雜           | 封裝常用查詢函數     |
| 數據驗證 | 需要應用層驗證           | 使用 Pydantic 等工具 |
| 遷移困難 | 結構變更需要更新所有記錄 | 使用版本控制         |
| 調試困難 | JSON 結構不直觀          | 提供查詢工具         |

---

## 替代方案對比

### 方案 1: 關聯表（傳統方式）

```sql
CREATE TABLE trait_score (
    id SERIAL PRIMARY KEY,
    test_result_id INTEGER,
    trait_id INTEGER,
    score FLOAT,
    percentile FLOAT
);
```

**優點**:

- 結構清晰
- 易於查詢和統計
- 數據完整性約束

**缺點**:

- 需要多次 JOIN
- 表結構固定
- 難以保留原始數據

### 方案 2: JSONB（當前方案）

```sql
CREATE TABLE individual_test_result (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    trait_results JSONB
);
```

**優點**:

- 靈活性高
- 查詢簡單（單表）
- 保留完整數據

**缺點**:

- SQL 語法複雜
- 需要應用層驗證

### 方案 3: 混合方案

```sql
-- 主表使用 JSONB
CREATE TABLE individual_test_result (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    trait_results JSONB
);

-- 關鍵特質使用獨立欄位
ALTER TABLE individual_test_result
ADD COLUMN communication_score FLOAT,
ADD COLUMN leadership_score FLOAT;
```

**優點**:

- 兼顧靈活性和查詢效率
- 關鍵欄位查詢快速

**缺點**:

- 數據冗餘
- 維護複雜

---

## 實際應用

### 在 BackEnd 中的使用

```python
# talent_search_engine_fixed.py

def search_candidates(self, parsed_query: Dict) -> List[Dict]:
    """搜索候選人 - 使用 JSONB 查詢"""

    sql = """
        SELECT
            cu.id,
            cu.username,
            itr.trait_results
        FROM core_user cu
        JOIN individual_test_result itr ON cu.id = itr.user_id
        WHERE ((trait_results->>'communication')::jsonb->>'score')::float >= 80
    """

    cursor.execute(sql)
    results = cursor.fetchall()

    candidates = []
    for row in results:
        candidates.append({
            'id': row[0],
            'name': row[1],
            'trait_results': row[2]  # 直接獲取 JSONB 數據
        })

    return candidates
```

### 在 Python 中處理 JSONB

```python
# 讀取 JSONB 數據
trait_results = candidate['trait_results']

# 獲取特質分數
communication_score = trait_results.get('communication', {}).get('score', 0)

# 遍歷所有特質
for trait_name, trait_data in trait_results.items():
    if isinstance(trait_data, dict):
        score = trait_data.get('score', 0)
        chinese_name = trait_data.get('chinese_name', trait_name)
        print(f"{chinese_name}: {score} 分")
```

---

## 測試工具

### 1. 查看數據結構

```bash
cd tests
python test_jsonb_queries.py
```

### 2. 測試查詢功能

```python
# 測試 1: 查看 JSONB 結構
# 測試 2: 查詢特定特質
# 測試 3: 按分數閾值查詢
# 測試 4: 通過中文名稱查詢
# 測試 5: 多特質組合查詢
# 測試 6: 統計所有特質
# 測試 7: 高分特質統計
# 測試 8: 模糊搜索
# 測試 9: 導出數據
```

---

## 最佳實踐

### 1. 數據驗證

```python
from pydantic import BaseModel, Field

class TraitData(BaseModel):
    chinese_name: str
    score: float = Field(ge=0, le=100)
    percentile: float = Field(None, ge=0, le=100)
    level: str = None
```

### 2. 查詢封裝

```python
def get_trait_score(trait_results: dict, trait_name: str) -> float:
    """獲取特質分數"""
    trait_data = trait_results.get(trait_name, {})
    if isinstance(trait_data, dict):
        return float(trait_data.get('score', 0))
    return 0.0
```

### 3. 索引策略

```sql
-- 為常用查詢創建索引
CREATE INDEX idx_trait_results_gin
ON individual_test_result USING GIN (trait_results);

-- 為特定特質創建索引
CREATE INDEX idx_communication_score
ON individual_test_result
USING BTREE (((trait_results->'communication'->>'score')::float));
```

### 4. 錯誤處理

```python
try:
    score = float(trait_results['communication']['score'])
except (KeyError, TypeError, ValueError):
    score = 0.0  # 默認值
```

---

## 常見問題

### Q: JSONB 和 JSON 有什麼區別？

**A**:

- **JSON**: 文本格式，存儲原始 JSON 字符串
- **JSONB**: 二進制格式，解析後存儲，查詢更快
- **建議**: 使用 JSONB（當前方案）

### Q: 如何遷移 JSONB 數據結構？

**A**:

```sql
-- 添加新欄位
UPDATE individual_test_result
SET trait_results = trait_results || '{"new_field": "value"}'::jsonb;

-- 重命名欄位
UPDATE individual_test_result
SET trait_results = trait_results - 'old_name' ||
                    jsonb_build_object('new_name', trait_results->'old_name');
```

### Q: JSONB 查詢性能如何？

**A**:

- 有 GIN 索引: 接近普通欄位
- 無索引: 需要全表掃描，較慢
- **建議**: 為常用查詢創建索引

### Q: 如何備份 JSONB 數據？

**A**:

```bash
# 導出
pg_dump -d projectdb -t individual_test_result > backup.sql

# 或導出為 JSON
psql -d projectdb -c "COPY (
    SELECT row_to_json(t) FROM individual_test_result t
) TO STDOUT" > backup.json
```

---

## 相關文檔

1. [JSON 數據結構說明](./JSON數據結構說明.md) - 詳細的數據結構文檔
2. [數據庫修正說明](./數據庫修正說明.md) - 數據庫結構修正
3. [搜索功能修正總結](./搜索功能修正總結-2025-11-15.md) - 搜索功能修正

---

## 總結

✅ **JSONB 是當前系統的核心存儲方案**

- 提供了靈活性和性能的良好平衡
- 適合快速迭代的測評系統
- 有完善的查詢和索引支持
- 已在生產環境中驗證

**建議**:

1. 繼續使用 JSONB 存儲測評數據
2. 為常用查詢創建適當的索引
3. 在應用層做好數據驗證
4. 保持 JSON 結構的文檔更新

---

**文檔版本**: 1.0  
**最後更新**: 2025-11-15  
**維護者**: AI Development Team

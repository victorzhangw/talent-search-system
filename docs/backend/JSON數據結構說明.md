# JSON 數據結構說明

**日期**: 2025-11-15

## 概述

是的！測試數據是以 **JSONB** 格式存放在 PostgreSQL 資料表中。這種設計提供了極大的靈活性，可以存儲複雜的嵌套數據結構，同時保持查詢效率。

---

## 為什麼使用 JSONB？

### 優點

1. **靈活性**: 可以存儲任意結構的數據，不需要預先定義所有欄位
2. **擴展性**: 新增特質或數據欄位不需要修改表結構
3. **查詢能力**: PostgreSQL 的 JSONB 支持強大的查詢和索引
4. **性能**: JSONB 是二進制格式，比純文本 JSON 更快
5. **完整性**: 保留了原始測評數據的完整結構

### 缺點

1. **查詢複雜度**: SQL 查詢語法較複雜
2. **數據驗證**: 需要應用層驗證數據結構
3. **遷移困難**: 如果需要改變數據結構，需要更新所有記錄

---

## 核心 JSONB 欄位

### 1. individual_test_result.trait_results

**表**: `individual_test_result`  
**欄位**: `trait_results`  
**類型**: `JSONB`

#### 數據結構

```json
{
  "communication": {
    "chinese_name": "溝通能力",
    "score": 82.5,
    "percentile": 75,
    "level": "高",
    "description": "具備良好的口語和書面溝通能力"
  },
  "leadership": {
    "chinese_name": "領導力",
    "score": 78.0,
    "percentile": 68,
    "level": "中等",
    "description": "能夠帶領團隊完成目標"
  },
  "analytical_thinking": {
    "chinese_name": "分析思考",
    "score": 85.5,
    "percentile": 82,
    "level": "高",
    "description": "擅長邏輯分析和問題解決"
  },
  "creativity": {
    "chinese_name": "創造力",
    "score": 72.0,
    "percentile": 60,
    "level": "中等",
    "description": "具備一定的創新思維能力"
  }
}
```

#### 欄位說明

| 欄位           | 類型   | 說明             | 範例               |
| -------------- | ------ | ---------------- | ------------------ |
| `chinese_name` | String | 特質的中文名稱   | "溝通能力"         |
| `score`        | Float  | 特質分數 (0-100) | 82.5               |
| `percentile`   | Float  | 百分位數 (0-100) | 75                 |
| `level`        | String | 等級描述         | "高", "中等", "低" |
| `description`  | String | 特質描述         | "具備良好的..."    |

#### SQL 查詢範例

```sql
-- 1. 查詢特定特質的分數
SELECT
    cu.username,
    (trait_results->>'communication')::jsonb->>'score' as communication_score
FROM core_user cu
JOIN individual_test_result itr ON cu.id = itr.user_id
WHERE (trait_results->>'communication') IS NOT NULL;

-- 2. 查詢分數大於 80 的候選人
SELECT cu.username
FROM core_user cu
JOIN individual_test_result itr ON cu.id = itr.user_id
WHERE ((trait_results->>'communication')::jsonb->>'score')::float >= 80;

-- 3. 查詢包含特定中文名稱的特質
SELECT cu.username
FROM core_user cu
JOIN individual_test_result itr ON cu.id = itr.user_id
WHERE EXISTS (
    SELECT 1
    FROM jsonb_each(trait_results)
    WHERE value->>'chinese_name' = '溝通能力'
      AND (value->>'score')::float >= 80
);

-- 4. 統計所有特質的平均分數
SELECT
    key as trait_name,
    AVG((value->>'score')::float) as avg_score
FROM individual_test_result,
     jsonb_each(trait_results)
GROUP BY key
ORDER BY avg_score DESC;

-- 5. 查詢擁有多個高分特質的候選人
SELECT
    cu.username,
    COUNT(*) as high_score_traits
FROM core_user cu
JOIN individual_test_result itr ON cu.id = itr.user_id,
     jsonb_each(itr.trait_results)
WHERE (value->>'score')::float >= 80
GROUP BY cu.username
HAVING COUNT(*) >= 3;
```

---

### 2. individual_test_result.category_results

**表**: `individual_test_result`  
**欄位**: `category_results`  
**類型**: `JSONB`

#### 數據結構

```json
{
  "銷售角色": {
    "score": 85.0,
    "role_index": 88.5,
    "contrast_index": 92.0,
    "traits": [
      {
        "name": "溝通能力",
        "score": 82.0,
        "weight": 1.0
      },
      {
        "name": "說服力",
        "score": 88.0,
        "weight": 1.2
      }
    ],
    "description": "非常適合銷售相關職位"
  },
  "管理角色": {
    "score": 78.0,
    "role_index": 75.5,
    "contrast_index": 68.0,
    "traits": [
      {
        "name": "領導力",
        "score": 78.0,
        "weight": 1.5
      },
      {
        "name": "決策能力",
        "score": 75.0,
        "weight": 1.0
      }
    ],
    "description": "具備管理潛力"
  }
}
```

#### 欄位說明

| 欄位             | 類型   | 說明                 |
| ---------------- | ------ | -------------------- |
| `score`          | Float  | 分類總分             |
| `role_index`     | Float  | 角色指數             |
| `contrast_index` | Float  | 對比指數             |
| `traits`         | Array  | 該分類包含的特質列表 |
| `description`    | String | 分類描述             |

---

### 3. test_project_result.raw_data

**表**: `test_project_result`  
**欄位**: `raw_data`  
**類型**: `JSONB`

#### 數據結構

```json
{
  "performance_metrics": {
    "CI_Raw_Value": 85.5,
    "Prediction_Score": 78.2,
    "Composite_Index": 82.0
  },
  "trait_scores": {
    "communication": {
      "chinese_name": "溝通能力",
      "score": 82.0,
      "raw_score": 164,
      "max_score": 200
    },
    "leadership": {
      "chinese_name": "領導力",
      "score": 75.5,
      "raw_score": 151,
      "max_score": 200
    }
  },
  "test_metadata": {
    "test_date": "2024-11-15T10:30:00Z",
    "test_duration_minutes": 45,
    "test_version": "v2.1",
    "completion_rate": 100
  },
  "demographic_info": {
    "age_group": "25-34",
    "education_level": "bachelor",
    "work_experience_years": 5
  }
}
```

---

### 4. assessment_report.report_content

**表**: `assessment_report`  
**欄位**: `report_content`  
**類型**: `JSONB`

#### 數據結構

```json
{
  "summary": {
    "overall_score": 82.5,
    "strengths": ["溝通能力優秀", "分析思考能力強"],
    "weaknesses": ["時間管理需要改進"],
    "recommendations": ["適合從事需要溝通協調的工作", "建議加強時間管理技能"]
  },
  "trait_analysis": {
    "communication": {
      "score": 82.5,
      "interpretation": "您的溝通能力處於優秀水平...",
      "development_suggestions": [
        "可以嘗試更多公開演講機會",
        "練習書面溝通技巧"
      ]
    }
  },
  "career_suggestions": {
    "suitable_roles": ["銷售經理", "客戶關係經理", "專案經理"],
    "development_paths": [
      "短期：提升領導力",
      "中期：發展策略思維",
      "長期：培養創新能力"
    ]
  }
}
```

---

## Python 操作 JSONB

### 使用 Django ORM

```python
from project.core.models import IndividualTestResult

# 1. 查詢特定特質分數
results = IndividualTestResult.objects.filter(
    trait_results__communication__score__gte=80
)

# 2. 獲取特質數據
result = IndividualTestResult.objects.first()
communication_score = result.trait_results.get('communication', {}).get('score', 0)

# 3. 更新特質數據
result.trait_results['communication']['score'] = 85.0
result.save()

# 4. 添加新特質
result.trait_results['new_trait'] = {
    'chinese_name': '新特質',
    'score': 75.0,
    'percentile': 60
}
result.save()

# 5. 查詢包含特定中文名稱的特質
from django.db.models import Q
from django.contrib.postgres.fields import JSONField

results = IndividualTestResult.objects.filter(
    trait_results__contains={'communication': {'chinese_name': '溝通能力'}}
)
```

### 使用 psycopg2

```python
import psycopg2
import json

conn = psycopg2.connect(...)
cursor = conn.cursor()

# 1. 查詢 JSONB 數據
cursor.execute("""
    SELECT trait_results
    FROM individual_test_result
    WHERE user_id = %s
""", (user_id,))

trait_results = cursor.fetchone()[0]
print(json.dumps(trait_results, indent=2, ensure_ascii=False))

# 2. 更新 JSONB 數據
cursor.execute("""
    UPDATE individual_test_result
    SET trait_results = trait_results || %s::jsonb
    WHERE user_id = %s
""", (json.dumps({'new_trait': {'score': 80}}), user_id))

# 3. 查詢特定路徑的值
cursor.execute("""
    SELECT
        user_id,
        trait_results->'communication'->>'score' as comm_score
    FROM individual_test_result
    WHERE (trait_results->'communication'->>'score')::float > 80
""")
```

---

## JSONB 索引優化

### 創建 GIN 索引

```sql
-- 1. 為整個 JSONB 欄位創建索引
CREATE INDEX idx_trait_results_gin
ON individual_test_result USING GIN (trait_results);

-- 2. 為特定路徑創建索引
CREATE INDEX idx_trait_results_communication
ON individual_test_result USING GIN ((trait_results->'communication'));

-- 3. 為特定操作創建索引
CREATE INDEX idx_trait_results_jsonb_path_ops
ON individual_test_result USING GIN (trait_results jsonb_path_ops);
```

### 索引使用建議

1. **GIN 索引**: 適合包含查詢 (`@>`, `?`, `?&`, `?|`)
2. **jsonb_path_ops**: 更小的索引，但只支持 `@>` 操作
3. **表達式索引**: 為常用的查詢路徑創建專門的索引

---

## 數據驗證

### Python 驗證範例

```python
from typing import Dict, Any
from pydantic import BaseModel, Field, validator

class TraitData(BaseModel):
    """特質數據模型"""
    chinese_name: str = Field(..., description="特質中文名稱")
    score: float = Field(..., ge=0, le=100, description="特質分數")
    percentile: float = Field(None, ge=0, le=100, description="百分位數")
    level: str = Field(None, description="等級")
    description: str = Field(None, description="描述")

    @validator('score')
    def validate_score(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('分數必須在 0-100 之間')
        return v

class TraitResults(BaseModel):
    """特質結果集合"""
    __root__: Dict[str, TraitData]

    def get_trait_score(self, trait_name: str) -> float:
        """獲取特質分數"""
        trait = self.__root__.get(trait_name)
        return trait.score if trait else 0.0

    def get_high_score_traits(self, threshold: float = 80) -> list:
        """獲取高分特質"""
        return [
            (name, data.score)
            for name, data in self.__root__.items()
            if data.score >= threshold
        ]

# 使用範例
trait_results_json = {
    "communication": {
        "chinese_name": "溝通能力",
        "score": 82.5,
        "percentile": 75
    }
}

trait_results = TraitResults(__root__=trait_results_json)
print(trait_results.get_trait_score('communication'))  # 82.5
print(trait_results.get_high_score_traits())  # [('communication', 82.5)]
```

---

## 常見問題

### Q1: 為什麼不使用關聯表？

**A**: 使用 JSONB 的原因：

- 測評系統的特質可能經常變化
- 不同測評版本可能有不同的特質集合
- 需要保留原始測評數據的完整性
- 查詢性能在有索引的情況下很好

### Q2: JSONB 的查詢性能如何？

**A**:

- 有 GIN 索引的情況下，查詢性能接近普通欄位
- 對於複雜查詢，可能需要優化 SQL
- 建議為常用查詢路徑創建專門的索引

### Q3: 如何遷移 JSONB 數據結構？

**A**:

```sql
-- 範例：為所有記錄添加新欄位
UPDATE individual_test_result
SET trait_results = trait_results || '{"new_field": "default_value"}'::jsonb
WHERE trait_results IS NOT NULL;

-- 範例：重命名欄位
UPDATE individual_test_result
SET trait_results = trait_results - 'old_name' ||
                    jsonb_build_object('new_name', trait_results->'old_name')
WHERE trait_results ? 'old_name';
```

### Q4: 如何備份 JSONB 數據？

**A**:

```bash
# 導出為 JSON 文件
psql -d projectdb -c "COPY (
    SELECT row_to_json(t)
    FROM individual_test_result t
) TO STDOUT" > backup.json

# 導入
psql -d projectdb -c "COPY individual_test_result FROM STDIN" < backup.json
```

---

## 最佳實踐

1. **數據驗證**: 在應用層驗證 JSON 結構
2. **索引策略**: 為常用查詢創建適當的索引
3. **數據遷移**: 使用事務確保數據一致性
4. **查詢優化**: 避免在 WHERE 子句中使用複雜的 JSONB 操作
5. **文檔維護**: 保持 JSON 結構的文檔更新

---

## 相關資源

- [PostgreSQL JSONB 文檔](https://www.postgresql.org/docs/current/datatype-json.html)
- [Django JSONField 文檔](https://docs.djangoproject.com/en/stable/ref/models/fields/#jsonfield)
- [JSONB 性能優化](https://www.postgresql.org/docs/current/indexes-types.html#INDEXES-TYPES-GIN)

---

**文檔版本**: 1.0  
**最後更新**: 2025-11-15

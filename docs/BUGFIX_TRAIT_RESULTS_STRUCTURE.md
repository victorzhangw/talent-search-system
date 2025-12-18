# Bug 修復：trait_results 資料結構不匹配

## 問題描述

代碼預期的 `trait_results` JSONB 結構與實際資料庫中的結構不一致，導致：

- 日誌顯示「特質數: 0」
- 無法正確解析特質資料
- HR 諮詢功能無法獲取完整的測評資訊

## 實際資料結構

### 資料庫中的實際結構（test_project_result.trait_results）

```json
{
  "Empathy": {
    "score": 59.0,
    "raw_text": "59%",
    "trait_id": "143b",
    "headsupflag": 0,
    "chinese_name": "Empathy",
    "selector_used": "#lbl_bizform_143b + .val-aptitudes .kp-per-value"
  },
  "Resilience": {
    "score": 81.0,
    "raw_text": "81%",
    "trait_id": "294b",
    "headsupflag": 0,
    "chinese_name": "Resilience",
    "selector_used": "#lbl_bizform_294b + .val-aptitudes .kp-per-value"
  },
  "Achievement Motivation": {
    "score": 89.0,
    "raw_text": "89%",
    "trait_id": "195b",
    "headsupflag": 0,
    "chinese_name": "Achievement Motivation",
    "selector_used": "#lbl_bizform_195b + .val-aptitudes .kp-per-value"
  }
}
```

**特點**：

- ✅ 使用**英文特質名稱**作為 key
- ✅ 每個特質是一個 dict，包含 `score`、`trait_id`、`headsupflag` 等
- ❌ **沒有** `traits` 陣列包裝
- ❌ `chinese_name` 欄位實際存的是**英文**，不是中文
- ❌ **沒有** `weight`、`is_primary`、`display_order`、`level`、`percentile` 等欄位

### 代碼原本預期的結構

```json
{
  "traits": [
    {
      "system_name": "leadership",
      "chinese_name": "領導力",
      "score": 85.5,
      "weight": 1.5,
      "is_primary": true,
      "display_order": 1,
      "level": "優秀",
      "percentile": 90
    }
  ]
}
```

## 修復內容

### 1. 修復特質數量計算

**修改前**：

```python
len(test_data.get('trait_results', {}).get('traits', []))
```

**修改後**：

```python
trait_results = test_data.get('trait_results', {})
trait_count = len([k for k in trait_results.keys()
                   if isinstance(trait_results[k], dict) and 'score' in trait_results[k]])
```

### 2. 修復優劣勢分析

**修改前**：

```python
traits_list = trait_results.get('traits', [])
for trait in traits_list:
    score = trait.get('score', 0)
    chinese_name = trait.get('chinese_name')
```

**修改後**：

```python
for trait_name, trait_data in trait_results.items():
    if not isinstance(trait_data, dict):
        continue
    score = trait_data.get('score', 0)
    display_name = trait_name  # 使用英文名稱
```

### 3. 修復特質列表格式化

**修改前**：

```python
traits_list = trait_results.get('traits', [])
primary_traits = [t for t in traits_list if t.get('is_primary')]
```

**修改後**：

```python
traits_list = []
for trait_name, trait_data in trait_results.items():
    if isinstance(trait_data, dict) and 'score' in trait_data:
        traits_list.append({
            'name': trait_name,
            'score': trait_data.get('score', 0),
            'trait_id': trait_data.get('trait_id'),
            'headsupflag': trait_data.get('headsupflag', 0)
        })

# headsupflag=1 表示需要特別關注的特質
primary_traits = [t for t in traits_list if t.get('headsupflag') == 1]
```

### 4. 欄位映射

| 原預期欄位       | 實際欄位           | 說明                                 |
| ---------------- | ------------------ | ------------------------------------ |
| `traits` (array) | 無                 | 直接使用 dict 的 keys                |
| `chinese_name`   | `trait_name` (key) | 使用英文特質名稱作為 key             |
| `is_primary`     | `headsupflag`      | 1=需要關注，0=正常                   |
| `weight`         | 無                 | 移除權重顯示                         |
| `display_order`  | 無                 | 改用分數排序                         |
| `level`          | 無                 | 根據分數計算（≥80 優秀，<60 待提升） |
| `percentile`     | 無                 | 移除百分位顯示                       |

## 測試驗證

修復後應該能看到：

- ✅ 日誌顯示正確的特質數量（如「特質數: 28」）
- ✅ 優勢特質列表正確顯示（分數 ≥ 80）
- ✅ 待提升特質列表正確顯示（分數 < 60）
- ✅ Prompt 包含完整的特質資訊
- ✅ LLM 能基於實際測評數據給出建議

## 影響範圍

- `BackEnd/hr_consultation_service.py`
  - `_analyze_strengths_weaknesses()` - 優劣勢分析
  - `_build_hr_system_prompt()` - Prompt 構建
  - `_generate_consultation()` - 諮詢生成
  - `_extract_mentioned_traits()` - 特質提取

## 後續改進建議

1. ✅ **中文名稱映射**：已實現從 `trait` 表獲取中文名稱和說明
2. **權重配置**：從 `test_project_trait` 表獲取權重和優先級配置
3. **資料驗證**：添加 trait_results 結構驗證，確保資料完整性
4. **錯誤處理**：增強對異常資料結構的容錯處理

## 第二次修復：添加中文名稱和說明映射

### 新增功能

1. **`_get_trait_name_mapping()` 方法**

   - 從 `trait` 表載入所有特質的中文名稱和說明
   - 建立 `system_name` 到中文資訊的映射
   - 返回格式：`{"Empathy": {"chinese_name": "同理心", "description": "...", ...}}`

2. **優劣勢分析增強**

   - 使用真正的中文名稱（從 trait 表）
   - 包含特質說明
   - 格式：`同理心: 59.0 分 - 待提升\n    說明: 衡量一個人...`

3. **Prompt 增強**
   - 所有特質列表包含中文名稱和說明
   - 優勢/劣勢特質包含完整說明
   - 需要關注的特質包含說明

### 範例輸出

**特質列表**：

```
  1. 成就追求     (Achievement Motivation):  89.0 分
      說明: 衡量一個人對待工作認真的程度、提高工作表現的意願，以及努力達成目標的程度。
  2. 韌性         (Resilience):  81.0 分
      說明: 衡量一個人面對挫折和壓力時的恢復能力...
```

**優勢特質**：

```
  • 成就追求: 89.0 分 - 優秀
    說明: 衡量一個人對待工作認真的程度、提高工作表現的意願，以及努力達成目標的程度。
  • 韌性: 81.0 分 - 優秀
    說明: 衡量一個人面對挫折和壓力時的恢復能力...
```

### trait 表結構

```sql
CREATE TABLE trait (
    id SERIAL PRIMARY KEY,
    chinese_name VARCHAR(100),      -- 中文名稱，如「成就追求」
    system_name VARCHAR(100),       -- 系統名稱，如「Desire To Compete」
    english_name VARCHAR(100),      -- 英文名稱
    description TEXT,               -- 特質說明
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 資料流程

1. 從 `test_project_result.trait_results` 獲取測評分數（英文 key）
2. 從 `trait` 表獲取中文名稱和說明的映射
3. 合併資料，生成包含中文和說明的完整特質資訊
4. 傳遞給 LLM 生成專業建議

## 修復日期

- 第一次修復：2025-12-18（修正資料結構解析）
- 第二次修復：2025-12-18（添加中文名稱和說明映射）

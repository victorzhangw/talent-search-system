# 測試腳本說明

## 概述

本目錄包含系統的測試腳本，用於驗證配置和功能是否正常工作。

## 測試腳本列表

### 1. test_env_config.py

**用途**: 測試環境變數配置是否正確

**測試內容**:

- 通用 HR 諮詢功能
- 候選人特定諮詢功能
- LLM API 連接
- 環境變數載入

**運行方式**:

```bash
cd docs/tests
python test_env_config.py
```

**預期輸出**:

```
🔍 測試環境變數配置

============================================================
測試通用 HR 諮詢（驗證環境變數配置）
============================================================
Status Code: 200
✅ 成功
✅ 環境變數配置正確，LLM API 正常工作

============================================================
測試候選人特定諮詢（驗證環境變數配置）
============================================================
Status Code: 200
✅ 成功
✅ 環境變數配置正確，候選人諮詢正常工作

✅ 所有測試完成！
```

### 2. test_consecutive_calls.py

**用途**: 測試連續 API 調用是否正常

**測試內容**:

- 第一次 API 調用
- 第二次 API 調用
- 資料庫連接狀態管理
- 會話保持

**運行方式**:

```bash
cd docs/tests
python test_consecutive_calls.py
```

**預期輸出**:

```
============================================================
第一次 API 調用
============================================================
Status Code: 200
✅ 成功

等待 2 秒...

============================================================
第二次 API 調用
============================================================
Status Code: 200
✅ 成功

============================================================
測試完成
============================================================
```

### 3. test_candidate_79.py

**用途**: 測試特定候選人的資料查詢

**測試內容**:

- 直接資料庫連接
- 候選人資料查詢
- 測評結果查詢

**注意**: 此測試需要直接資料庫連接（SSH 隧道）

**運行方式**:

```bash
cd docs/tests
python test_candidate_79.py
```

### 4. test_prompt_modification.py

**用途**: 測試 Prompt 動態修改功能

**測試內容**:

- Prompt 文件備份
- Prompt 修改
- 動態重新載入
- Prompt 恢復

**運行方式**:

```bash
cd docs/tests
python test_prompt_modification.py
```

**預期輸出**:

```
============================================================
測試 Prompt 動態修改功能
============================================================

步驟 1: 備份原始 Prompt 文件
✅ 已備份

步驟 2: 獲取 Prompt 管理器
✅ Prompt 管理器已初始化

步驟 3: 測試原始 Prompt
原始 System Prompt 開頭: 你是一位資深的人力資源專家...

步驟 4: 修改 Prompt 文件
✅ Prompt 文件已修改

步驟 5: 重新載入 Prompt
✅ Prompt 已重新載入

步驟 6: 測試修改後的 Prompt
修改後 System Prompt 開頭: 【測試修改】你是一位資深的人力資源專家...

步驟 7: 驗證修改
✅ Prompt 修改成功！
✅ 動態重新載入功能正常工作

步驟 8: 恢復原始 Prompt 文件
✅ 已恢復原始 Prompt 文件

步驟 9: 重新載入原始 Prompt
✅ 已重新載入原始 Prompt

============================================================
測試完成
============================================================
```

## 運行所有測試

### 方法 1: 逐個運行

```bash
cd docs/tests

# 測試 1
python test_env_config.py

# 測試 2
python test_consecutive_calls.py

# 測試 3
python test_prompt_modification.py
```

### 方法 2: 使用測試腳本

創建 `run_all_tests.bat` (Windows):

```batch
@echo off
echo Running all tests...
echo.

echo Test 1: Environment Configuration
python test_env_config.py
echo.

echo Test 2: Consecutive API Calls
python test_consecutive_calls.py
echo.

echo Test 3: Prompt Modification
python test_prompt_modification.py
echo.

echo All tests completed!
pause
```

創建 `run_all_tests.sh` (Linux/Mac):

```bash
#!/bin/bash
echo "Running all tests..."
echo

echo "Test 1: Environment Configuration"
python test_env_config.py
echo

echo "Test 2: Consecutive API Calls"
python test_consecutive_calls.py
echo

echo "Test 3: Prompt Modification"
python test_prompt_modification.py
echo

echo "All tests completed!"
```

## 測試前提條件

### 1. 後端服務運行

確保後端服務正在運行：

```bash
# 檢查後端健康狀態
curl http://localhost:8000/health
```

如果未運行，啟動後端：

```bash
cd BackEnd
python main_api.py
```

### 2. 環境變數配置

確保 `BackEnd/.env.local` 已正確配置：

- `LLM_API_KEY`
- `LLM_API_HOST`
- `DB_*` 配置

### 3. 資料庫連接

確保資料庫可訪問（對於需要資料庫的測試）。

### 4. Python 依賴

確保已安裝所有依賴：

```bash
cd BackEnd
pip install -r requirements.txt
```

## 測試失敗處理

### 測試失敗常見原因

1. **後端未運行**

   - 解決: 啟動後端服務

2. **環境變數未配置**

   - 解決: 檢查 `.env.local` 文件

3. **API Key 無效**

   - 解決: 更新 `LLM_API_KEY`

4. **資料庫連接失敗**

   - 解決: 檢查資料庫配置和 SSH 隧道

5. **端口被佔用**
   - 解決: 更改端口或終止佔用進程

### 查看詳細錯誤

如果測試失敗，查看：

1. 測試腳本輸出的錯誤訊息
2. 後端日誌
3. 瀏覽器開發者工具（如果是前端相關）

## 添加新測試

### 測試腳本模板

```python
"""
測試腳本描述
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"

def test_feature():
    """測試功能描述"""

    print("=" * 60)
    print("測試名稱")
    print("=" * 60)

    # 準備測試數據
    payload = {
        "key": "value"
    }

    try:
        # 發送請求
        response = requests.post(
            f"{API_BASE_URL}/api/endpoint",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        # 檢查結果
        if response.status_code == 200:
            result = response.json()
            print("✅ 測試通過")
            print(f"結果: {result}")
        else:
            print("❌ 測試失敗")
            print(f"錯誤: {response.text}")

    except Exception as e:
        print(f"❌ 測試異常: {e}")

    print("=" * 60)

if __name__ == "__main__":
    test_feature()
```

## 持續集成

### GitHub Actions 配置範例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: |
          cd BackEnd
          pip install -r requirements.txt

      - name: Run tests
        run: |
          cd docs/tests
          python test_env_config.py
          python test_consecutive_calls.py
          python test_prompt_modification.py
```

## 相關資源

- [快速開始指南](../guides/GETTING_STARTED.md)
- [故障排除指南](../guides/TROUBLESHOOTING.md)
- [環境變數配置](../configuration/README_ENV.md)

## 獲取幫助

如果測試遇到問題：

1. 查看 [故障排除指南](../guides/TROUBLESHOOTING.md)
2. 檢查後端日誌
3. 聯繫開發團隊

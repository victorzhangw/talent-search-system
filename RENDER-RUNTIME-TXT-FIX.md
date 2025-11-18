# 🎯 Render runtime.txt 修復 - 最終解決方案

## 問題根源

### 為什麼 PYTHON_VERSION 環境變數不起作用？

Render 的 Python 版本選擇優先級：

1. **runtime.txt** (最高優先級) ← 我們現在使用這個
2. `.python-version` 文件
3. `PYTHON_VERSION` 環境變數 (最低優先級)

我們之前只設定了環境變數，但 Render 可能有默認的 runtime.txt 或其他配置導致使用 Python 3.13。

---

## ✅ 最終解決方案：runtime.txt

### 創建 runtime.txt

在專案根目錄創建 `runtime.txt`：

```txt
python-3.11.9
```

這是 Render 識別 Python 版本的**標準方法**。

### 為什麼選擇 3.11.9？

- ✅ Python 3.11 系列的最新穩定版
- ✅ 所有依賴完全支援
- ✅ psycopg2-binary 完全兼容
- ✅ 性能優秀
- ✅ 生產環境廣泛使用

---

## 📦 完整配置

### 1. runtime.txt (新增)

```txt
python-3.11.9
```

### 2. render.yaml (已更新)

```yaml
services:
  - type: web
    name: talent-search-api
    runtime: python
    region: oregon
    plan: free
    buildCommand: |
      echo "Checking Python version..."
      python --version
      echo "Upgrading pip..."
      pip install --upgrade pip
      echo "Installing dependencies..."
      pip install -r requirements.txt
      echo "Build complete!"
    startCommand: cd BackEnd && python start_fixed_api.py
    envVars:
      # 移除了 PYTHON_VERSION（不需要了）
      - key: DB_SSH_HOST
        sync: false
      ...
```

### 3. requirements.txt (保持不變)

```txt
fastapi==0.115.0
uvicorn[standard]==0.32.0
pydantic==2.10.0
psycopg2-binary>=2.9.9,<3.0
sshtunnel==0.4.0
paramiko==3.4.0
httpx==0.25.1
python-multipart==0.0.6
```

---

## 🚀 已推送到 Git

### Commit 資訊

- **Commit**: bb5385e
- **訊息**: "Fix: Add runtime.txt to force Python 3.11.9 - Render standard method"
- **推送到**: GitHub ✅ 和 Bitbucket ✅

### 更新內容

- 新增 `runtime.txt`
- 更新 `render.yaml`（移除 PYTHON_VERSION，添加詳細日誌）

---

## 🔍 預期的部署結果

### Build Log 應該顯示

```bash
==> Checking Python version...
Python 3.11.9  # ✅ 關鍵：應該是 3.11.9，不是 3.13

==> Upgrading pip...
Successfully installed pip-24.x

==> Installing dependencies...
Collecting fastapi==0.115.0
  Downloading fastapi-0.115.0-py3-none-any.whl (94 kB)
Collecting uvicorn[standard]==0.32.0
  Downloading uvicorn-0.32.0-py3-none-any.whl (63 kB)
Collecting pydantic==2.10.0
  Downloading pydantic-2.10.0-py3-none-any.whl (456 kB)
Collecting pydantic-core==2.27.0
  Downloading pydantic_core-2.27.0-cp311-cp311-manylinux_2_17_x86_64.whl
  # ✅ cp311 = Python 3.11
Collecting psycopg2-binary>=2.9.9,<3.0
  Downloading psycopg2_binary-2.9.10-cp311-cp311-manylinux_2_17_x86_64.whl
  # ✅ cp311 = Python 3.11，不會有 undefined symbol 錯誤
...
Successfully installed:
  fastapi-0.115.0
  uvicorn-0.32.0
  pydantic-2.10.0
  pydantic-core-2.27.0
  psycopg2-binary-2.9.10
  ...

==> Build complete!
==> Build successful 🎉

==> Running 'cd BackEnd && python start_fixed_api.py'
正在初始化資料庫連接...
✓ 資料庫連接完成！
✓ 特質定義載入完成！
✓ LLM 智能搜索已啟用！
✓ 初始化完成！
INFO:     Uvicorn running on http://0.0.0.0:10000
```

### 關鍵差異

**之前（失敗）**：

```
Python 3.13.x  # ❌ 錯誤版本
psycopg2/_psycopg.cpython-313-x86_64-linux-gnu.so
ImportError: undefined symbol: _PyInterpreterState_Get
```

**現在（成功）**：

```
Python 3.11.9  # ✅ 正確版本
psycopg2/_psycopg.cpython-311-x86_64-linux-gnu.so
✓ 資料庫連接完成！
```

---

## ✅ 驗證部署成功

### 1. 檢查 Build Log 中的 Python 版本

**最重要的檢查**：

```
Checking Python version...
Python 3.11.9  # 必須是 3.11.9
```

如果還是顯示 3.13.x，說明 runtime.txt 沒有生效。

### 2. 檢查 psycopg2 安裝

應該看到：

```
Downloading psycopg2_binary-2.9.10-cp311-cp311-manylinux_2_17_x86_64.whl
```

注意 `cp311` 表示 Python 3.11。

### 3. 測試 API

```bash
curl https://your-app.onrender.com/health
```

預期回應：

```json
{
  "status": "healthy",
  "database": "connected",
  "traits_loaded": 50,
  "llm_enabled": true,
  "version": "2.1.0"
}
```

---

## ⚠️ 如果還是使用 Python 3.13

### 可能的原因

1. **runtime.txt 格式錯誤**

   - 確保文件名是 `runtime.txt`（不是 `Runtime.txt`）
   - 確保內容是 `python-3.11.9`（不是 `Python-3.11.9`）
   - 確保沒有多餘的空格或換行

2. **Render 緩存問題**

   - 在 Dashboard 清除 build cache
   - 手動觸發 "Clear build cache & deploy"

3. **文件位置錯誤**
   - runtime.txt 必須在**專案根目錄**
   - 不能在 BackEnd/ 子目錄中

### 解決步驟

1. 確認 runtime.txt 在根目錄：

   ```
   project/
   ├── runtime.txt  ← 必須在這裡
   ├── requirements.txt
   ├── render.yaml
   └── BackEnd/
       └── ...
   ```

2. 確認文件內容：

   ```bash
   cat runtime.txt
   # 應該只顯示：python-3.11.9
   ```

3. 在 Render Dashboard 清除緩存：
   - Settings → Build & Deploy → Clear build cache
   - Manual Deploy → Clear build cache & deploy

---

## 📊 文件結構確認

```
project/
├── runtime.txt              ← 新增（指定 Python 3.11.9）
├── requirements.txt         ← 已更新（所有依賴）
├── render.yaml             ← 已更新（移除 PYTHON_VERSION）
├── BackEnd/
│   ├── requirements.txt    ← 已更新（與根目錄相同）
│   ├── start_fixed_api.py
│   └── ...
└── frontend/
    └── ...
```

---

## 🎯 Render Python 版本選擇機制

### 優先級（從高到低）

1. **runtime.txt** ← 我們使用這個

   ```txt
   python-3.11.9
   ```

2. **.python-version**

   ```txt
   3.11.9
   ```

3. **PYTHON_VERSION 環境變數**

   ```yaml
   envVars:
     - key: PYTHON_VERSION
       value: "3.11"
   ```

4. **Render 默認版本**（通常是最新版，如 3.13）

### 推薦方式

✅ **使用 runtime.txt**

- 標準方法
- 明確且可靠
- 版本控制友好
- Render 官方推薦

---

## 🎉 成功標誌

當你看到以下所有項目時，表示部署成功：

1. ✅ Build Log 第一行顯示 `Python 3.11.9`
2. ✅ psycopg2 安裝顯示 `cp311`
3. ✅ 沒有 `undefined symbol` 錯誤
4. ✅ Runtime Log 顯示 `Uvicorn running on...`
5. ✅ 服務狀態顯示 "Live" (綠色)
6. ✅ `/health` 返回 `"status": "healthy"`

---

## 📝 經驗總結

### 關鍵學習

1. **runtime.txt 是標準方法** - 不要依賴環境變數
2. **Python 3.13 太新** - 生產環境使用 3.11
3. **明確指定版本** - 避免使用默認版本
4. **檢查 Build Log** - 第一步就確認 Python 版本

### 最佳實踐

對於 Render 部署：

- ✅ 使用 runtime.txt 指定 Python 版本
- ✅ 選擇穩定版本（3.11.x）
- ✅ 明確列出所有依賴
- ✅ 在 buildCommand 中添加版本檢查

---

## 🚀 下一步

1. 等待 Render 自動部署（約 3-5 分鐘）
2. **立即檢查 Build Log 第一行** - 必須是 `Python 3.11.9`
3. 如果還是 3.13，清除緩存並重新部署
4. 驗證所有 API 端點
5. 開始使用！

這次使用 runtime.txt 是 Render 的標準方法，應該會成功！🎉

---

## 📞 需要幫助？

如果 Build Log 還是顯示 Python 3.13，請提供：

1. runtime.txt 的完整內容
2. runtime.txt 的文件位置
3. Build Log 的前 20 行

我們會進一步診斷問題。

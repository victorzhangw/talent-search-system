# 故障排除報告：HR 諮詢 404 錯誤

## 問題描述
用戶在前端進行 HR 諮詢交互時，收到 `POST /api/hr-consult 404 Not Found` 錯誤。

## 原因分析
經過檢查啟動腳本 (`start-backend.bat` 和 `BackEnd/start-local.bat`)，發現它們仍然指向舊的 `talent_search_api.py` 入口文件。
`talent_search_api.py` 僅包含人才搜索相關的路由，未包含重構後新增的 HR 諮詢路由 (`/api/hr-consult`)。

新的統一入口文件是 `main_api.py`，它整合了：
- `/api/talent` (人才搜索)
- `/api/hr-consult` (HR 諮詢)

## 修復內容
已更新以下啟動腳本，將目標文件改為 `main_api.py`：
1.  `start-backend.bat`
2.  `start-all-services.bat` (同時修復了未指定 venv python 的問題)
3.  `BackEnd/start-local.bat`

## 解決方案
**請重啟後端服務**。
關閉當前運行的後端命令提示字元窗口，然後重新運行 `start-backend.bat` 或 `start-all-services.bat`。

啟動後，您應該能在控制台看到類似以下的輸出：
```
INFO:     ✅ HR 諮詢模組載入成功
...
INFO:     📍 HR 諮詢: http://localhost:8000/api/hr-consult
```
這表示路由已正確加載。

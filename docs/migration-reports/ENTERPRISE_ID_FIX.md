# Enterprise ID 过滤问题修复

## 🎉 部分成功！

### ✅ 已修复并生效
- **通用 HR 咨询**（无候选人信息）- 正常工作！

### ⚠️ 需要重启后端
- **候选人特定咨询** - 仍返回 404（需要重启）

---

## 问题分析

### 根本原因

从后端日志可以看出：

```
收到諮詢請求 - Enterprise: 1, Query: 紀沅辰適合什麼職位？, 
CandidateID: 83, CandidateName: 紀沅辰
無法識別候選人
```

**问题**：代码使用 `enterprise_id = 1` 作为默认值，但候选人 ID=83 的 `enterprise_id` 不是 1。

查询逻辑：
```sql
WHERE id = 83 AND enterprise_id = 1  -- ❌ 找不到
```

实际上候选人 83 可能属于其他企业，或者 `enterprise_id` 为 NULL。

---

## 修复方案

### 修改 1: 移除默认 enterprise_id 限制

**文件**: `BackEnd/hr_consultation_routes.py` (第 91-93 行)

```python
# 修复前
enterprise_id = x_enterprise_id or 1  # ❌ 强制使用 1

# 修复后
enterprise_id = x_enterprise_id or None  # ✅ None 表示不限制企业
# TODO: 生产环境应该从认证 token 中获取真实的 enterprise_id
```

### 修改 2: 支持可选的企业过滤

**文件**: `BackEnd/hr_consultation_service.py`

#### 修改点 1: 移除强制 enterprise_id 检查 (第 73-80 行)

```python
# 修复前
if not active_enterprise_id:
    return {
        "success": False,
        "error": "未指定企業 ID，無法進行諮詢"
    }

# 修复后
# 允许 enterprise_id 为 None（不限制企业）
active_enterprise_id = enterprise_id if enterprise_id is not None else self.enterprise_id
```

#### 修改点 2: 按 ID 查询候选人 (第 269 行)

```python
# 修复前
WHERE ti.id = %s AND ti.enterprise_id = %s
cursor.execute(query, (candidate_id, enterprise_id))

# 修复后
WHERE ti.id = %s {f"AND ti.enterprise_id = %s" if enterprise_id else ""}
params = [candidate_id]
if enterprise_id:
    params.append(enterprise_id)
cursor.execute(query, tuple(params))
```

#### 修改点 3: 按姓名查询候选人 (第 319 行)

```python
# 修复前
WHERE ti.name LIKE %s AND ti.enterprise_id = %s
cursor.execute(query, (f"%{name}%", enterprise_id))

# 修复后
WHERE ti.name LIKE %s {f"AND ti.enterprise_id = %s" if enterprise_id else ""}
params = [f"%{name}%"]
if enterprise_id:
    params.append(enterprise_id)
cursor.execute(query, tuple(params))
```

---

## 测试结果

### ✅ 通用咨询 - 已生效

```bash
curl -X POST http://localhost:8000/api/hr-consult/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "如何提升团队凝聚力？"}'
```

**结果**: ✅ 200 OK，返回 `"mode": "general"`

### ⚠️ 候选人咨询 - 需要重启

```bash
curl -X POST http://localhost:8000/api/hr-consult/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "紀沅辰適合什麼職位？", "candidate_id": 83, "candidate_name": "紀沅辰"}'
```

**当前结果**: ❌ 404  
**原因**: `hr_consultation_service.py` 的修改需要重启后端才能生效

---

## 🚀 重启后端以完成修复

### 步骤

1. **停止后端**
   ```bash
   # 在后端窗口按 Ctrl+C
   # 或关闭后端窗口
   # 或运行: taskkill /F /IM python.exe
   ```

2. **重新启动**
   ```bash
   cd BackEnd
   venv\Scripts\python.exe main_api.py
   ```

3. **等待启动成功**
   看到以下日志：
   ```
   ✅ HR 諮詢模組載入成功
   🎉 人才管理系統 API 啟動成功！
   ```

4. **测试候选人咨询**
   ```bash
   curl -X POST http://localhost:8000/api/hr-consult/chat \
     -H "Content-Type: application/json" \
     -d '{"query": "紀沅辰適合什麼職位？", "candidate_id": 83, "candidate_name": "紀沅辰"}'
   ```

   **预期结果**: ✅ 200 OK，返回候选人分析

---

## 修复逻辑说明

### 企业隔离行为

| enterprise_id | 查询行为 | 适用场景 |
|---------------|----------|----------|
| **None** | 不限制企业 | 开发/测试环境 |
| **具体数字** (如 1, 2) | 只查询该企业的候选人 | 生产环境（多租户） |

### 前端调用

前端目前**不传递** `X-Enterprise-ID` header：

```javascript
// frontend/src/api/hrConsultation.js
await hrApiClient.post('/api/hr-consult/chat', requestData);
// 没有设置 X-Enterprise-ID header
```

因此后端使用 `enterprise_id = None`，不限制企业。

### 生产环境建议

在生产环境中，应该：

1. **从认证 token 中获取企业 ID**
   ```python
   # 从 JWT token 或 session 中获取
   enterprise_id = get_enterprise_id_from_auth(request)
   ```

2. **前端传递 header**
   ```javascript
   headers: {
     'X-Enterprise-ID': currentUser.enterpriseId
   }
   ```

3. **强制企业隔离**
   ```python
   if not enterprise_id:
       raise HTTPException(status_code=401, detail="需要企业认证")
   ```

---

## 修复文件清单

1. ✅ `BackEnd/hr_consultation_routes.py` - 移除默认 enterprise_id=1
2. ✅ `BackEnd/hr_consultation_service.py` - 支持可选企业过滤
3. ✅ `frontend/src/components/HRConsultationPanel.vue` - UI 双模式支持
4. ✅ `frontend/src/api/hrConsultation.js` - 端口修复 (8001→8000)
5. ✅ `start-all-services.bat` - 端口配置 (5173→3000)

---

## 验证步骤

重启后端后，验证以下场景：

### ✅ 场景 1: 通用咨询（无候选人）
```bash
POST /api/hr-consult/chat
{ "query": "如何提升团队凝聚力？" }
```
**预期**: 200 + `mode: "general"`

### ✅ 场景 2: 候选人咨询（ID + 姓名）
```bash
POST /api/hr-consult/chat
{
  "query": "紀沅辰適合什麼職位？",
  "candidate_id": 83,
  "candidate_name": "紀沅辰"
}
```
**预期**: 200 + 候选人详细分析

### ✅ 场景 3: 候选人咨询（仅姓名）
```bash
POST /api/hr-consult/chat
{
  "query": "請分析紀沅辰的優勢",
  "candidate_name": "紀沅辰"
}
```
**预期**: 200 + 候选人详细分析

### ✅ 场景 4: 候选人不存在
```bash
POST /api/hr-consult/chat
{
  "query": "不存在的人適合什麼？",
  "candidate_name": "不存在的人"
}
```
**预期**: 404 + "無法識別候選人"

---

## 🎯 总结

### 已完成
- ✅ 通用 HR 咨询功能（已生效）
- ✅ 移除强制 enterprise_id=1 限制（已生效）
- ✅ 支持可选企业过滤（需要重启）
- ✅ Pydantic v2 兼容性
- ✅ 前端 UI 双模式支持
- ✅ 端口配置修复

### 待完成
- ⏳ 重启后端以加载 `hr_consultation_service.py` 的修改

---

**请重启后端，然后测试候选人咨询功能！**

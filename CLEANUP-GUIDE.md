# 🧹 Cleanup Guide - Remove Old and Outdated Files

## 📋 Overview

This guide helps you clean up old, outdated, and test files from the project after upgrading to Vue 3 + Vite.

## 🎯 Quick Start

### Step 1: Review Files to be Deleted

```bash
# Run this to see what will be deleted
list-old-files.bat
```

### Step 2: Clean Up

```bash
# Run this to delete old files
cleanup-old-files.bat
```

## 📁 Files to be Removed

### Root Directory - Old BAT Files (13 files)

These are replaced by `start-all.bat`, `stop-all.bat`, and `setup-first-time.bat`

- ❌ `重啟API服務.bat`
- ❌ `停止所有服務.bat`
- ❌ `停止服務.bat`
- ❌ `探索資料庫結構.bat`
- ❌ `啟動人才搜索服務.bat`
- ❌ `啟動完整系統-Vite版.bat`
- ❌ `啟動完整系統.bat`
- ❌ `啟動並測試.bat`
- ❌ `啟動新版API.bat`
- ❌ `診斷資料庫.bat`
- ❌ `GStart.bat`
- ❌ `start_all.bat` (old version)
- ❌ `stop_all.bat` (old version)

### Root Directory - Old HTML Files (4 files)

These are replaced by the new Vue 3 frontend

- ❌ `talent-chat-frontend-backup.html`
- ❌ `talent-chat-frontend.html` (optional - keep if needed)
- ❌ `test_api.html`
- ❌ `測試修正-tooltip.html`
- ❌ `index.html` (old CDN version)

### Root Directory - Old Documentation (30+ files)

These are outdated progress reports and temporary documentation

- ❌ `✅中文特質名稱修正完成.md`
- ❌ `✅完成-立即使用.md`
- ❌ `✅商業級UI設計完成.md`
- ❌ `✅問題修正完成-測試指南.md`
- ❌ `✅新功能完成總結.md`
- ❌ `✅UI修正完成-v3.md`
- ❌ `升級完成說明.md`
- ❌ `方案總結-待確認.md`
- ❌ `正確的測評表分析.md`
- ❌ `如何使用聊天界面.md`
- ❌ `快速啟動指南.md`
- ❌ `快速測試新功能.md`
- ❌ `系統更新總結-2025-11-16.md`
- ❌ `使用說明-圖解.txt`
- ❌ `使用說明.txt`
- ❌ `前後端整合說明.md`
- ❌ `問題修正說明-2025-11-16-v2.md`
- ❌ `問題修正總結-2025-11-16.md`
- ❌ `問題診斷-下一步.md`
- ❌ `問題診斷指南.md`
- ❌ `啟動測試說明.md`
- ❌ `啟動腳本說明.txt`
- ❌ `測試智能搜索.md`
- ❌ `測試API.ps1`
- ❌ `無外鍵處理方案-總結.md`
- ❌ `無外鍵資料庫處理指南.md`
- ❌ `新功能說明-面試問題生成.md`
- ❌ `資料庫逆向工程方案.md`
- ❌ `資料庫探索結果分析.md`
- ❌ `API_v2修正說明.md`
- ❌ `README-快速開始.md`
- ❌ `README-資料庫逆向工程.md`
- ❌ `Test測評表完整說明.md`
- ❌ `UI更新說明.md`
- ❌ `database_schema_report.json`
- ❌ `database_schema_report.md`
- ❌ `connections.xml`
- ❌ `LLMHost.txt`

### BackEnd Directory - Test Files (16 files)

These are debug and test scripts no longer needed

- ❌ `BackEnd/check_db.bat`
- ❌ `BackEnd/check_trait_mapping.py`
- ❌ `BackEnd/debug_trait_results.py`
- ❌ `BackEnd/diagnose_database.py`
- ❌ `BackEnd/explore_database_schema.py`
- ❌ `BackEnd/query_traits.py`
- ❌ `BackEnd/test_enrich.py`
- ❌ `BackEnd/test_full_flow.py`
- ❌ `BackEnd/test_hybrid.bat`
- ❌ `BackEnd/test_ssh_connection.py`
- ❌ `BackEnd/conversation_enhanced_search.py`
- ❌ `BackEnd/conversation_manager.py`
- ❌ `BackEnd/convert_ppk_to_openssh.py`
- ❌ `BackEnd/database_schema.json`
- ❌ `BackEnd/intent_definitions.example.json`
- ❌ `BackEnd/intent_definitions.json`

### BackEnd Directory - Old API Versions (6 files)

These are replaced by `talent_search_api_v2.py`

- ❌ `BackEnd/setup_and_run.bat`
- ❌ `BackEnd/start_api.bat`
- ❌ `BackEnd/start_fixed_api.py`
- ❌ `BackEnd/talent_search_api.py` (v1)
- ❌ `BackEnd/talent_search_api_fixed.py` (old)
- ❌ `BackEnd/talent_search_engine_fixed.py` (old)
- ❌ `BackEnd/requirements_api.txt` (duplicate)

### Tests Directory (2 files)

Old test files

- ❌ `tests/test_jsonb_queries.py`
- ❌ `tests/test_fixed_search.py`

### Assets Directory (Optional)

If using new Vue 3 frontend, the old assets directory can be removed

- ❌ `assets/` (entire directory - optional)

---

## ✅ Files to KEEP (Important)

### Root Directory

- ✅ `start-all.bat` - **NEW** - Start all services
- ✅ `stop-all.bat` - **NEW** - Stop all services
- ✅ `setup-first-time.bat` - **NEW** - First time setup
- ✅ `README-QUICKSTART.md` - **NEW** - Quick start guide
- ✅ `README.md` - Main documentation
- ✅ `PROJECT_STRUCTURE.md` - Project structure
- ✅ `logo.svg` - Logo file

### BackEnd Directory

- ✅ `BackEnd/talent_search_api_v2.py` - **CURRENT** API version
- ✅ `BackEnd/interview_api.py` - **CURRENT** Interview API
- ✅ `BackEnd/requirements.txt` - Python dependencies
- ✅ `BackEnd/private-key-openssh.pem` - SSH key (if needed)
- ✅ `BackEnd/security/` - Security module

### Frontend Directory

- ✅ `frontend/` - **NEW** Vue 3 + Vite frontend (entire directory)

### Docs Directory

- ✅ `docs/` - Keep all documentation

### Project Directory

- ✅ `project/` - Keep if contains important files

### .kiro Directory

- ✅ `.kiro/` - Kiro IDE configuration

---

## 📊 Summary

| Category           | Files to Remove | Disk Space  |
| ------------------ | --------------- | ----------- |
| Old BAT files      | 13              | ~50 KB      |
| Old HTML files     | 4               | ~200 KB     |
| Old documentation  | 30+             | ~500 KB     |
| BackEnd test files | 16              | ~300 KB     |
| Old API versions   | 6               | ~400 KB     |
| Test directory     | 2               | ~50 KB      |
| **Total**          | **70+**         | **~1.5 MB** |

---

## 🚀 After Cleanup

Your project structure will be clean and organized:

```
AI-Talent-Search/
├── BackEnd/
│   ├── talent_search_api_v2.py  ✅ Current API
│   ├── interview_api.py         ✅ Current API
│   └── requirements.txt         ✅ Dependencies
├── frontend/                    ✅ Vue 3 + Vite
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── docs/                        ✅ Documentation
├── start-all.bat               ✅ Start everything
├── stop-all.bat                ✅ Stop everything
├── setup-first-time.bat        ✅ First time setup
├── README-QUICKSTART.md        ✅ Quick start
└── README.md                   ✅ Main docs
```

---

## ⚠️ Safety Notes

1. **Backup First**: The cleanup script will ask for confirmation
2. **Review List**: Run `list-old-files.bat` first to see what will be deleted
3. **Optional Items**: Some items (like `assets/` and `talent-chat-frontend.html`) are optional
4. **No Undo**: Deleted files cannot be recovered (unless you have Git history)

---

## 🔄 Git Users

If using Git, you can safely delete these files as they're in your history:

```bash
# After cleanup, commit the changes
git add .
git commit -m "Clean up old and outdated files after Vue 3 upgrade"
```

---

## 📝 Manual Cleanup (Alternative)

If you prefer manual cleanup, delete files in this order:

1. Old BAT files (safe to delete)
2. Old documentation (safe to delete)
3. Test files (safe to delete)
4. Old API versions (keep one backup just in case)
5. Old HTML files (keep one backup just in case)
6. Assets directory (only if new frontend works perfectly)

---

## ✅ Verification

After cleanup, verify everything works:

```bash
# Run setup (if needed)
setup-first-time.bat

# Start all services
start-all.bat

# Test in browser
# Open http://localhost:3000
```

If everything works, cleanup was successful! 🎉

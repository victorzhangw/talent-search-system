# 🚀 START HERE - Quick Setup Guide

## ⚡ First Time Setup (Required)

Before you can start the application, you MUST run the setup script once:

```bash
# Double-click this file:
setup-first-time.bat
```

This will:

1. ✅ Check Python and Node.js installation
2. ✅ Create Python virtual environment (venv)
3. ✅ Install Python dependencies in venv
4. ✅ Install Frontend dependencies (npm)
5. ✅ Create configuration files

**Time required:** 3-5 minutes

---

## 🎯 Start the Application

After setup is complete, start the application:

```bash
# Double-click this file:
start-all.bat
```

This will:

1. ✅ Check virtual environment exists
2. ✅ Start Backend API (Port 8000) using venv
3. ✅ Start Frontend (Port 3000)
4. ✅ Automatically open browser

---

## 🛑 Stop the Application

```bash
# Double-click this file:
stop-all.bat
```

Or simply close the terminal windows.

---

## ❓ Why Virtual Environment?

The backend uses a Python virtual environment (`BackEnd/venv/`) to:

- ✅ Isolate project dependencies
- ✅ Avoid conflicts with system Python
- ✅ Ensure consistent package versions

**Important:** `start-all.bat` now uses `venv\Scripts\python.exe` instead of system Python.

---

## 🔧 Troubleshooting

### Problem: "Backend virtual environment not found"

**Solution:** Run `setup-first-time.bat` first!

### Problem: "ModuleNotFoundError: No module named 'psycopg2'"

**Solution:**

1. Delete `BackEnd\venv` folder
2. Run `setup-first-time.bat` again

### Problem: Frontend won't start

**Solution:**

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Problem: Port 8000 already in use

**Solution:**

```powershell
# Find and kill the process
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
Stop-Process -Id <PID> -Force
```

---

## 📂 File Structure

```
AI-Talent-Search/
├── BackEnd/
│   ├── venv/                    ← Python virtual environment
│   ├── talent_search_api_v2.py  ← Main API
│   └── requirements.txt         ← Python dependencies
├── frontend/
│   ├── node_modules/            ← NPM packages
│   ├── src/                     ← Vue source code
│   └── package.json             ← NPM dependencies
├── setup-first-time.bat         ← 1️⃣ Run this FIRST
├── start-all.bat                ← 2️⃣ Then run this
└── stop-all.bat                 ← 3️⃣ Stop services
```

---

## ✅ Verification

After running `start-all.bat`, you should see:

**Terminal 1 (Backend):**

```
✓ 資料庫連接完成！
✓ 特質定義載入完成！
INFO: Uvicorn running on http://0.0.0.0:8000
```

**Terminal 2 (Frontend):**

```
VITE v5.4.21 ready in 398 ms
➜ Local: http://localhost:3000/
```

**Browser:**

- Opens automatically to http://localhost:3000
- Shows the AI Talent Search interface

---

## 🎉 Success!

If you see the application in your browser, everything is working correctly!

---

## 📚 More Help

- **Quick Start:** `README-QUICKSTART.md`
- **How to Start:** `HOW-TO-START.md`
- **Frontend Docs:** `frontend/README.md`
- **Backend Docs:** `docs/backend/README.md`

---

**Last Updated:** After fixing venv issue

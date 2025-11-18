# 🚀 How to Start the Application

## ⚠️ IMPORTANT - Use the Correct Files!

### ✅ CORRECT Files to Use (NEW)

| File                   | Purpose                 |
| ---------------------- | ----------------------- |
| `setup-first-time.bat` | First time installation |
| `start-all.bat`        | Start all services      |
| `stop-all.bat`         | Stop all services       |

### ❌ OLD Files (DELETED)

These files have been removed:

- ~~啟動完整系統.bat~~ ❌ (Opens old HTML)
- ~~GStart.bat~~ ❌
- ~~start_all.bat~~ ❌ (underscore version)
- ~~啟動並測試.bat~~ ❌
- ~~啟動新版 API.bat~~ ❌
- ~~停止所有服務.bat~~ ❌
- And many more...

---

## 📝 Quick Start Guide

### First Time Setup

1. **Run Setup**
   ```
   Double-click: setup-first-time.bat
   ```
   This will:
   - Check Python and Node.js
   - Install Python dependencies
   - Install Frontend dependencies

### Daily Use

2. **Start All Services**

   ```
   Double-click: start-all.bat
   ```

   This will:

   - Start Backend on http://localhost:8000
   - Start Frontend on http://localhost:3000
   - Automatically open browser to http://localhost:3000

3. **Stop All Services**
   ```
   Double-click: stop-all.bat
   ```
   Or simply close the terminal windows

---

## 🌐 Access Points

After running `start-all.bat`:

- **Frontend (Vue 3):** http://localhost:3000 ✅
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs

---

## ❓ Troubleshooting

### Problem: Browser opens old HTML file

**Solution:** You're running an old BAT file!

1. Make sure you're running `start-all.bat` (NOT any other bat file)
2. Clear browser cache
3. Manually navigate to http://localhost:3000

### Problem: Port already in use

**Backend (8000):**

```bash
# Stop the process using port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Frontend (3000):**

```bash
# Stop the process using port 3000
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

### Problem: Frontend dependencies not installed

```bash
cd frontend
npm install
```

---

## 📂 Project Structure

```
AI-Talent-Search/
├── BackEnd/
│   ├── talent_search_api_v2.py  ← Current API
│   └── interview_api.py         ← Interview API
├── frontend/                    ← Vue 3 + Vite
│   ├── src/
│   └── package.json
├── setup-first-time.bat        ← First time setup
├── start-all.bat               ← Start everything ✅
├── stop-all.bat                ← Stop everything
└── README-QUICKSTART.md        ← Detailed guide
```

---

## 🎯 Remember

- **ALWAYS use `start-all.bat`** to start the application
- **Frontend runs on port 3000** (Vue 3 + Vite)
- **Backend runs on port 8000** (FastAPI)
- Old HTML file (`talent-chat-frontend.html`) is deprecated

---

## 📚 More Information

- Full documentation: `README-QUICKSTART.md`
- Frontend docs: `frontend/README.md`
- Backend docs: `docs/backend/README.md`

---

**Last Updated:** After Vue 3 + Vite upgrade

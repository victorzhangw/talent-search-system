# 🚀 AI Talent Search System - Quick Start Guide

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+** - [Download](https://www.python.org/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Git** (optional) - [Download](https://git-scm.com/)

## 🎯 Quick Start (3 Steps)

### Step 1: First Time Setup

Run the setup script to install all dependencies:

```bash
# Double-click or run:
setup-first-time.bat
```

This will:

- ✅ Check Python and Node.js installation
- ✅ Install Python dependencies (FastAPI, psycopg2, etc.)
- ✅ Install Frontend dependencies (Vue, Vite, etc.)
- ✅ Create configuration files

**Time required:** 3-5 minutes

---

### Step 2: Start All Services

Run the launcher to start both backend and frontend:

```bash
# Double-click or run:
start-all.bat
```

This will:

- ✅ Start Backend API on `http://localhost:8000`
- ✅ Start Frontend on `http://localhost:3000`
- ✅ Automatically open browser

**Services will run in separate windows**

---

### Step 3: Use the Application

The browser will automatically open to `http://localhost:3000`

If not, manually open:

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

---

## 🛑 Stop Services

To stop all services:

```bash
# Double-click or run:
stop-all.bat
```

Or simply close the terminal windows.

---

## 📁 Project Structure

```
AI-Talent-Search/
├── BackEnd/                 # Python FastAPI Backend
│   ├── talent_search_api_v2.py
│   └── requirements.txt
├── frontend/                # Vue 3 + Vite Frontend
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── start-all.bat           # 🚀 Start everything
├── stop-all.bat            # 🛑 Stop everything
└── setup-first-time.bat    # ⚙️ First time setup
```

---

## 🔧 Manual Start (Alternative)

If you prefer to start services manually:

### Backend

```bash
cd BackEnd
python talent_search_api_v2.py
```

### Frontend

```bash
cd frontend
npm run dev
```

---

## 🐛 Troubleshooting

### Port Already in Use

**Backend (8000):**

- Stop other services using port 8000
- Or modify port in `BackEnd/talent_search_api_v2.py`

**Frontend (3000):**

- Stop other services using port 3000
- Or modify port in `frontend/vite.config.js`

### Dependencies Installation Failed

**Python:**

```bash
cd BackEnd
pip install -r requirements.txt --upgrade
```

**Frontend:**

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Backend Connection Failed

1. Ensure backend is running on port 8000
2. Check `frontend/src/config/index.js` for correct API URL
3. Check firewall settings

---

## 📚 Additional Resources

- **Frontend Documentation:** `frontend/README.md`
- **Backend Documentation:** `BackEnd/README.md`
- **Upgrade Guide:** `升級完成說明.md`

---

## 🎉 Features

- 🤖 **AI-Powered Search** - Natural language talent search
- 💬 **Chat Interface** - Conversational UI
- 📊 **Smart Matching** - Trait-based candidate matching
- 📝 **Interview Questions** - Auto-generate interview questions
- 🎨 **Modern UI** - Beautiful gradient design
- ⚡ **Fast** - Vite-powered frontend

---

## 🆘 Need Help?

1. Check the troubleshooting section above
2. Review the detailed documentation in each folder
3. Check the API documentation at http://localhost:8000/docs

---

## 📝 Development

### Frontend Development

```bash
cd frontend
npm run dev          # Start dev server
npm run build        # Build for production
npm run preview      # Preview production build
```

### Backend Development

```bash
cd BackEnd
python talent_search_api_v2.py  # Start API server
```

---

## 🔒 Security Notes

- This is a development setup
- For production, configure proper security settings
- Update API keys and database credentials
- Enable HTTPS
- Configure CORS properly

---

## 📄 License

MIT License - See LICENSE file for details

---

**Happy Coding! 🚀**

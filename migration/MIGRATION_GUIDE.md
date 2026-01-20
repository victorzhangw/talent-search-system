# Traitty UAT Migration Guide

## 1. Environment Setup (UAT)

### Server Requirements
- OS: Windows Server or Linux (Ubuntu 20.04+ recommended)
- Python: 3.9+
- PostgreSQL: 14+
- Node.js: 18+ (for frontend build)

### Database Setup
1. Create a new database (e.g., `traitty_uat`).
2. Run the migration scripts in order:

```bash
# Example using psql
psql -U postgres -d traitty_uat -f 01_schema.sql
psql -U postgres -d traitty_uat -f 02_seed_data.sql
```

## 2. Backend Deployment

1. Copy the `BackEnd` folder to the server root (e.g. `C:\inetpub\wwwroot\TalentChatAPI\BackEnd`). 
   **IMPORTANT**: Do not flatten the folder structure. The server root should contain `asgi.py` and the `BackEnd` folder.
2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
# Activate venv
# Windows: .venv\Scripts\activate
# Linux: source .venv/bin/activate
pip install -r requirements.txt
```

3. Configure `.env` file in the project root:
   - Set `DATABASE_URL` to your database connection string.
   - Set `DEEPSEEK_API_KEY` and other secrets.
   - **Important**: Configure the upstream data source:
     ```ini
     # To fetch data from UAT Environment
     TRAITTY_API_BASE=https://uat.traitty.com
     
     # To fetch data from Production Environment
     # TRAITTY_API_BASE=https://app.traitty.com
     ```
   - Set `FLASK_ENV=production`

4. Run the backend (Production Mode):

> We use **Uvicorn** (ASGI) for better performance and streaming support.

```bash
# Windows / Linux
# Ensure you are in the project root (where asgi.py is located)
uvicorn asgi:app --host 0.0.0.0 --port 5000 --workers 4

# Alternatively, if you must use Waitress (Windows only, WSGI):
# waitress-serve --host=0.0.0.0 --port=5000 asgi:app
```

## 3. Frontend Deployment & API Configuration

### API Endpoint Configuration
**Crucial Step**: You must update the API base URL in the frontend configuration before building.

1. Locate the configuration mechanism.
   - **Method A (Build-time)**: If hardcoded, check `.env.production` in frontend.
   - **Method B (Runtime Config - Recommended)**:
     The application uses a `window.TRAITTY_WIDGET_CONFIG` object usually injected by the embedding client page. However, for the standalone UAT site, check `frontend/chat-widget/index.html` or the specific entry point.

   **To switch from Dev to UAT (`uat.traitty.com`):**

   Create or update a `config.js` in the public folder or modify the embedding code on the client's UAT website HTML:

   ```html
   <script>
     window.TRAITTY_WIDGET_CONFIG = {
       apiBaseUrl: "https://uat.traitty.com/api/v2", // CHANGE THIS
       userEmail: "uat-tester@client.com"
     };
   </script>
   ```

   *If using the Admin Panel:*
   Update `frontend/admin-panel/.env.production` (or create it):
   ```
   VITE_API_BASE_URL=https://uat.traitty.com/api/v2
   ```

2. Build the Frontend:

```bash
cd frontend/chat-widget
npm install
npm run build
# Output is in dist/

cd ../admin-panel
npm install
npm run build
# Output is in dist/
```

3. Deploy the `dist` folders to your web server (Nginx/IIS).

## 4. Verification

1. Access the Admin Panel at `https://uat.traitty.com/admin` (or your configured path).
2. Login with the default admin credentials (from seed data).
3. Test the Chat Widget. It should connect to `https://uat.traitty.com/api/v2/chat`.

## 5. Client Integration (For their UAT Site)

Provide the client with the following snippet to embed on their UAT environment:

```html
<!-- Widget Container -->
<div id="talent-rag-widget"></div>

<!-- Config -->
<script>
  window.TRAITTY_WIDGET_CONFIG = {
    apiBaseUrl: "https://uat.traitty.com/api/v2", // Client UAT Endpoint
    userEmail: "{CURRENT_USER_EMAIL}" // Client needs to inject dynamic email here
  };
</script>

<!-- Styles and Script -->
<link rel="stylesheet" href="https://uat.traitty.com/widget/style.css">
<script type="module" src="https://uat.traitty.com/widget/main.js"></script>
```

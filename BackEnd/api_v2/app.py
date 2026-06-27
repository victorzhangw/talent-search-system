import os
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from .config.settings import Config
from .database import init_db
from .extensions import limiter

_LOCALHOST = {'127.0.0.1', '::1', 'localhost'}
_PROTECTED_PREFIXES = ('/chat', '/api/v2')

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize CORS — restrict to allowed origins from env
    _raw = os.getenv('ALLOWED_ORIGINS', '')
    _origins = [o.strip() for o in _raw.split(',') if o.strip()]
    # Always include localhost for local development (safe: prod browsers never originate from localhost)
    _dev_origins = ['http://localhost:5300', 'http://localhost:5000', 'http://127.0.0.1:5300']
    _final_origins = list(set(_origins + _dev_origins)) if _origins else '*'
    CORS(app, origins=_final_origins, supports_credentials=True)

    # Initialize Rate Limiter
    limiter.init_app(app)

    # IP allowlist middleware — applies to /chat/ and /api/v2/* only
    allowed_ips = app.config.get('ALLOWED_IPS', [])

    @app.before_request
    def check_ip():
        if not allowed_ips:
            return  # Disabled when ALLOWED_IPS is not set

        # Only enforce on protected paths
        if not request.path.startswith(_PROTECTED_PREFIXES):
            return

        # Resolve real client IP:
        # X-Forwarded-For may contain a chain; take the first (original client).
        # Note: only trust X-Forwarded-For if the server is behind a known proxy.
        xff = request.headers.get('X-Forwarded-For', '')
        client_ip = xff.split(',')[0].strip() if xff else request.remote_addr

        if client_ip in _LOCALHOST:
            return  # Always allow local development

        if client_ip not in allowed_ips:
            app.logger.warning(f'[IP Block] {client_ip} -> {request.path}')
            resp = jsonify({'success': False, 'code': 'FORBIDDEN', 'message': 'Access denied'})
            resp.status_code = 403
            return resp

    # Initialize Database
    init_db(app)

    @app.errorhandler(500)
    def internal_error(error):
        import traceback
        traceback.print_exc()
        from .utils.response_helpers import err
        return err('INTERNAL_SERVER_ERROR', '伺服器發生未預期錯誤，請聯絡管理員', 500)

    # Register Blueprints
    from .routes import chat, auth, candidates, reports, init_proxy, modules, docs
    from .admin import router as admin_router

    app.register_blueprint(chat.bp) # Default /chat
    app.register_blueprint(auth.bp, url_prefix='/auth')
    app.register_blueprint(candidates.bp, url_prefix='/api/v2/candidates') # Explicit path
    app.register_blueprint(reports.bp, url_prefix='/api/v2/reports') # NEW: Batch reports endpoint
    app.register_blueprint(init_proxy.bp, url_prefix='/api/v2/init') # Proxy to upstream /v1/init
    app.register_blueprint(admin_router.bp) # /api/admin as defined in blueprint url_prefix
    app.register_blueprint(modules.bp, url_prefix='/api/v2/modules') # 快速提問模組清單 API
    app.register_blueprint(docs.bp) # /api/docs — Swagger UI


    @app.route('/health')
    def health_check():
        return {'status': 'ok', 'service': 'Talent Search API v2', 'mode': app.config['INTEGRATION_MODE']}

    @app.route('/widget/<path:filename>')
    def widget_static(filename):
        widget_dir = os.path.join(app.static_folder, 'widget')
        return send_from_directory(widget_dir, filename)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

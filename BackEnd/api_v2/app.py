import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from .config.settings import Config
from .database import init_db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize CORS
    CORS(app)

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

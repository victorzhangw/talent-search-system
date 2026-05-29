"""
Swagger UI + OpenAPI 3.0 規格服務
  GET /api/docs/          → Swagger UI（CDN）
  GET /api/docs/openapi.json → OpenAPI 規格（JSON）
"""
from flask import Blueprint, jsonify, make_response
import os
import yaml

bp = Blueprint("docs", __name__, url_prefix="/api/docs")

_SPEC_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "openapi.yaml"
)


def _load_spec():
    with open(_SPEC_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@bp.route("/openapi.json")
def openapi_json():
    spec = _load_spec()
    resp = jsonify(spec)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@bp.route("/", strict_slashes=False)
def swagger_ui():
    html = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Talent Chat API v2 — Docs</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
  <style>
    body { margin: 0; }
    .swagger-ui .topbar { background: #1e293b; }
    .swagger-ui .topbar .download-url-wrapper { display: none; }
    .swagger-ui .info .title { color: #1e293b; }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = function () {
      SwaggerUIBundle({
        url: "/api/docs/openapi.json",
        dom_id: "#swagger-ui",
        deepLinking: true,
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
        plugins: [SwaggerUIBundle.plugins.DownloadUrl],
        layout: "StandaloneLayout",
        tryItOutEnabled: true,
        requestInterceptor: function(req) {
          // 保留 Authorization header（讓 Try it out 可以帶 JWT）
          return req;
        }
      });
    };
  </script>
</body>
</html>"""
    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp

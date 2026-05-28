from flask import jsonify


def ok(data=None, meta=None, status=200):
    """Standard success envelope."""
    return jsonify({
        "success": True,
        "data": data,
        "error": None,
        "meta": meta
    }), status


def err(code, message, status=400, details=None, field=None):
    """Standard error envelope."""
    error_obj = {"code": code, "message": message}
    if details is not None:
        error_obj["details"] = details
    if field is not None:
        error_obj["field"] = field
    return jsonify({
        "success": False,
        "data": None,
        "error": error_obj,
        "meta": None
    }), status

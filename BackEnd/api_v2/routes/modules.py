"""
模組清單 API — 提供前端動態拉取快速提問模組清單（單一資料源）
"""
from flask import Blueprint, jsonify
import json
import os

bp = Blueprint('modules', __name__, url_prefix='/modules')


@bp.route('/', methods=['GET', 'OPTIONS'])
def get_modules():
    """回傳快速提問模組清單，供前端動態渲染。"""
    if __import__('flask').request.method == 'OPTIONS':
        return '', 200

    modules_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'config', 'quick_modules.json'
    )

    try:
        with open(modules_path, 'r', encoding='utf-8') as f:
            modules = json.load(f)
    except Exception as e:
        return jsonify({'error': f'Failed to load modules config: {e}'}), 500

    # 組裝前端所需格式：依分類分組，保持分類順序
    category_order = ['招募', '管理', '團隊合作', '留才', '培育發展', '深度分析']
    categories = {}

    for mod_id, mod in modules.items():
        cat = mod['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            'id': mod_id,
            'label': mod['display_name'],
            'mode': mod['candidate_mode']
        })

    # 依照預設順序排列（若有未知分類則往後排）
    ordered = {}
    for cat in category_order:
        if cat in categories:
            ordered[cat] = categories[cat]
    for cat in categories:
        if cat not in ordered:
            ordered[cat] = categories[cat]

    return jsonify({'categories': ordered})

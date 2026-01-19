
from flask import Blueprint, request, jsonify
from sqlalchemy import func
from datetime import datetime, timedelta
import datetime as dt

from ..database.connection import get_db_session
from ..database.models import ChatSession, ChatMessage, AdminUser
from .auth import create_access_token, verify_password, get_password_hash, token_required

bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
         return jsonify({'detail': 'Username and password required'}), 400
         
    db = get_db_session()
    try:
        user = db.query(AdminUser).filter(AdminUser.username == data['username']).first()
        if not user:
            return jsonify({'detail': 'Incorrect username or password'}), 401
            
        if not verify_password(data['password'], user.password_hash):
            return jsonify({'detail': 'Incorrect username or password'}), 401
        
        access_token = create_access_token(data={"sub": user.username})
        return jsonify({"access_token": access_token, "token_type": "bearer"})
    finally:
        db.close()

@bp.route('/me', methods=['GET'])
@token_required
def read_users_me(current_user):
    return jsonify({"username": current_user})

@bp.route('/register-dev', methods=['POST'])
def register():
    # REMOVE IN PROD
    data = request.get_json()
    db = get_db_session()
    try:
        if db.query(AdminUser).count() > 0:
             return jsonify({'detail': 'Admins already exist.'}), 400
             
        hashed_password = get_password_hash(data['password'])
        new_user = AdminUser(username=data['username'], password_hash=hashed_password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return jsonify({"username": new_user.username})
    finally:
        db.close()

# --- Dashboard APIs ---

@bp.route('/sessions', methods=['GET'])
@token_required
def list_sessions(current_user):
    skip = request.args.get('skip', 0, type=int)
    limit = request.args.get('limit', 20, type=int)
    user_id = request.args.get('user_id')
    
    db = get_db_session()
    try:
        query = db.query(ChatSession)
        if user_id:
            query = query.filter(ChatSession.user_id == user_id)
            
        sessions = query.order_by(ChatSession.last_active_at.desc()).offset(skip).limit(limit).all()
        
        results = []
        for s in sessions:
            msg_count = len(s.messages)
            total_tokens = sum([m.token_usage for m in s.messages if m.token_usage])
            
            # Serialize
            results.append({
                "session_id": s.session_id,
                "user_id": s.user_id,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
                "message_count": msg_count,
                "total_tokens": total_tokens
            })
        return jsonify(results)
    except Exception as e:
        print(f"[Admin] Error listing sessions: {e}")
        return jsonify({'detail': str(e)}), 500
    finally:
        db.close()

@bp.route('/sessions/<session_id>', methods=['GET'])
@token_required
def get_session_details(current_user, session_id):
    db = get_db_session()
    try:
        session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if not session:
            return jsonify({'detail': 'Session not found'}), 404
            
        messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
        
        return jsonify({
            "session": {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "status": session.status,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "metadata": session.metadata_
            },
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "token_usage": m.token_usage,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                } for m in messages
            ]
        })
    finally:
        db.close()

@bp.route('/stats', methods=['GET'])
@token_required
def get_dashboard_stats(current_user):
    db = get_db_session()
    try:
        total_sessions = db.query(func.count(ChatSession.session_id)).scalar()
        total_tokens = db.query(func.sum(ChatMessage.token_usage)).scalar() or 0
        
        one_day_ago = datetime.datetime.utcnow() - dt.timedelta(days=1)
        active_24h = db.query(func.count(ChatSession.session_id)).filter(ChatSession.last_active_at >= one_day_ago).scalar()
        
        total_messages = db.query(func.count(ChatMessage.id)).scalar()
        
        return jsonify({
            "total_sessions": total_sessions,
            "total_tokens": total_tokens,
            "active_sessions_24h": active_24h,
            "total_messages": total_messages
        })
    finally:
        db.close()

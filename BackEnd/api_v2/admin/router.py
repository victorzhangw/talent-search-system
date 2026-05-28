
from flask import Blueprint, request
from sqlalchemy import func
from datetime import datetime, timedelta
import datetime as dt

from ..database.connection import get_db_session
from ..database.models import ChatSession, ChatMessage, AdminUser
from .auth import create_access_token, verify_password, get_password_hash, token_required
from ..utils.response_helpers import ok, err

bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return err('MISSING_FIELD', 'Username and password required', 400)

    db = get_db_session()
    try:
        user = db.query(AdminUser).filter(AdminUser.username == data['username']).first()
        if not user or not verify_password(data['password'], user.password_hash):
            return err('INVALID_CREDENTIALS', 'Incorrect username or password', 401)

        access_token = create_access_token(data={"sub": user.username})
        return ok({"access_token": access_token, "token_type": "bearer"})
    finally:
        db.close()

@bp.route('/me', methods=['GET'])
@token_required
def read_users_me(current_user):
    return ok({"username": current_user})

@bp.route('/users', methods=['POST'])
@token_required
def create_user(current_user):
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return err('MISSING_FIELD', 'Username and password required', 400)

    db = get_db_session()
    try:
        if db.query(AdminUser).filter(AdminUser.username == data['username']).first():
            return err('CONFLICT', 'Username already exists', 400)

        hashed_password = get_password_hash(data['password'])
        new_user = AdminUser(username=data['username'], password_hash=hashed_password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return ok({"username": new_user.username, "id": new_user.id}, status=201)
    finally:
        db.close()

@bp.route('/users/<int:user_id>/password', methods=['PUT'])
@token_required
def update_user_password(current_user, user_id):
    data = request.get_json()
    if not data or not data.get('password'):
        return err('MISSING_FIELD', 'New password required', 400, field='password')

    db = get_db_session()
    try:
        user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
        if not user:
            return err('NOT_FOUND', 'User not found', 404)

        user.password_hash = get_password_hash(data['password'])
        db.commit()
        return ok({"message": "Password updated successfully"})
    finally:
        db.close()

@bp.route('/users', methods=['GET'])
@token_required
def list_users(current_user):
    db = get_db_session()
    try:
        users = db.query(AdminUser).all()
        return ok([{"id": u.id, "username": u.username, "created_at": u.created_at.isoformat()} for u in users])
    finally:
        db.close()

# --- Dashboard APIs ---

@bp.route('/sessions', methods=['GET'])
@token_required
def list_sessions(current_user):
    skip = request.args.get('skip', 0, type=int)
    limit = request.args.get('limit', 20, type=int)
    user_id = request.args.get('user_id')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    db = get_db_session()
    try:
        query = db.query(ChatSession)
        if user_id:
            query = query.filter(ChatSession.user_id == user_id)
            
        if start_date_str:
            # Assume local input (UTC+8) -> Convert to UTC
            # E.g. User selects 2026-01-20. This means 2026-01-20 00:00:00 Local -> 2026-01-19 16:00:00 UTC
            start_date_local = datetime.strptime(start_date_str, '%Y-%m-%d')
            start_date_utc = start_date_local - timedelta(hours=8)
            query = query.filter(ChatSession.started_at >= start_date_utc)
            
        if end_date_str:
            # End Date Inclusive (End of Day Local)
            # E.g. User selects 2026-01-20. This means 2026-01-21 00:00:00 Local -> 2026-01-20 16:00:00 UTC
            end_date_local = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
            end_date_utc = end_date_local - timedelta(hours=8)
            query = query.filter(ChatSession.started_at < end_date_utc)
            
        total = query.count()
        sessions = query.order_by(ChatSession.last_active_at.desc()).offset(skip).limit(limit).all()

        results = []
        for s in sessions:
            msg_count = len(s.messages)
            total_tokens = sum([m.token_usage for m in s.messages if m.token_usage])
            results.append({
                "session_id": s.session_id,
                "user_id": s.user_id,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "last_active_at": s.last_active_at.isoformat() if s.last_active_at else None,
                "message_count": msg_count,
                "total_tokens": total_tokens
            })
        return ok(results, meta={"skip": skip, "limit": limit, "total": total})
    except Exception as e:
        print(f"[Admin] Error listing sessions: {e}")
        return err('QUERY_FAILED', str(e), 500)
    finally:
        db.close()

@bp.route('/sessions/<session_id>', methods=['GET'])
@token_required
def get_session_details(current_user, session_id):
    db = get_db_session()
    try:
        session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if not session:
            return err('NOT_FOUND', 'Session not found', 404)

        messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()

        return ok({
            "session": {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "status": session.status,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "metadata": session.metadata_
            },
            "messages": [{
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "token_usage": m.token_usage,
                "created_at": m.created_at.isoformat() if m.created_at else None
            } for m in messages]
        })
    finally:
        db.close()

@bp.route('/stats', methods=['GET'])
@token_required
def get_dashboard_stats(current_user):
    db = get_db_session()
    try:
        # Timezone Handling (Taiwan is UTC+8)
        now_utc = datetime.utcnow()
        now_tw = now_utc + timedelta(hours=8)
        
        # 1. Start of Month (TW) -> UTC
        start_of_month_tw = now_tw.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_month_utc = start_of_month_tw - timedelta(hours=8)
        
        # 2. Yesterday Range (TW) -> UTC
        yesterday_date_tw = (now_tw - timedelta(days=1)).date()
        start_of_yesterday_tw = datetime.combine(yesterday_date_tw, datetime.min.time())
        end_of_yesterday_tw = start_of_yesterday_tw + timedelta(days=1)
        
        start_of_yesterday_utc = start_of_yesterday_tw - timedelta(hours=8)
        end_of_yesterday_utc = end_of_yesterday_tw - timedelta(hours=8)
        
        # --- Stats Queries (Monthly Cumulative) ---
        total_sessions = db.query(func.count(ChatSession.session_id))\
            .filter(ChatSession.started_at >= start_of_month_utc).scalar() or 0
            
        total_tokens = db.query(func.sum(ChatMessage.token_usage))\
            .filter(ChatMessage.created_at >= start_of_month_utc).scalar() or 0
            
        total_messages = db.query(func.count(ChatMessage.id))\
            .filter(ChatMessage.created_at >= start_of_month_utc).scalar() or 0
            
        # --- Active Users Yesterday ---
        active_users_yesterday = db.query(func.count(func.distinct(ChatSession.user_id)))\
            .filter(ChatSession.last_active_at >= start_of_yesterday_utc)\
            .filter(ChatSession.last_active_at < end_of_yesterday_utc).scalar() or 0
        
        # --- Token Trend (Last 7 Days) ---
        # We query per day (UTC for simplicity, or approximate shift)
        # Using Python adjustment for simplified SQL
        days_to_fetch = 7
        trend_start_utc = now_utc - timedelta(days=days_to_fetch)
        
        # Truncate to day
        date_col = func.date_trunc('day', ChatMessage.created_at).label('day_date')
        
        trend_results = db.query(
            date_col,
            func.sum(ChatMessage.token_usage)
        ).filter(ChatMessage.created_at >= trend_start_utc)\
         .group_by(date_col)\
         .order_by(date_col).all()
        
        token_trend = []
        for r in trend_results:
            # Format date as MM-DD
            d_str = r[0].strftime('%m-%d')
            token_trend.append({"date": d_str, "tokens": r[1] or 0})
            
        return ok({
            "total_sessions": total_sessions,
            "total_tokens": total_tokens,
            "total_messages": total_messages,
            "active_users_yesterday": active_users_yesterday,
            "token_trend": token_trend
        })
    finally:
        db.close()

# --- Reports & Analytics ---

@bp.route('/reports/users-usage', methods=['GET'])
@token_required
def users_usage_report(current_user):
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    db = get_db_session()
    try:
        # Base query: Join Session and Message to get token usage per user
        # We group by user_id
        
        query = db.query(
            ChatSession.user_id,
            func.count(func.distinct(ChatSession.session_id)).label('session_count'),
            func.sum(ChatMessage.token_usage).label('total_tokens'),
            func.max(ChatSession.last_active_at).label('last_active_at')
        ).join(ChatMessage, ChatSession.session_id == ChatMessage.session_id)
        
        # Filter Date Range (on Message creation for accurate token usage in period)
        if start_date_str:
            start_date_local = datetime.strptime(start_date_str, '%Y-%m-%d')
            start_date_utc = start_date_local - timedelta(hours=8)
            query = query.filter(ChatMessage.created_at >= start_date_utc)
            
        if end_date_str:
            end_date_local = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
            end_date_utc = end_date_local - timedelta(hours=8)
            query = query.filter(ChatMessage.created_at < end_date_utc)
            
        results = query.group_by(ChatSession.user_id).all()
        
        data = []
        for r in results:
            user_id = r.user_id or "Anonymous"
            data.append({
                "user_id": user_id,
                "session_count": r.session_count,
                "total_tokens": r.total_tokens or 0,
                "last_active_at": r.last_active_at.isoformat() if r.last_active_at else None
            })
            
        return ok(data)
    except Exception as e:
        print(f"[Admin] Report Error: {e}")
        return err('QUERY_FAILED', str(e), 500)
    finally:
        db.close()

@bp.route('/reports/daily-usage', methods=['GET'])
@token_required
def daily_usage_report(current_user):
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    user_id = request.args.get('user_id')
    
    db = get_db_session()
    try:
        # Postgres date_trunc
        date_col = func.date_trunc('day', ChatMessage.created_at).label('date')
        
        query = db.query(
            date_col,
            func.sum(ChatMessage.token_usage).label('tokens'),
            func.count(func.distinct(ChatSession.session_id)).label('sessions')
        ).join(ChatSession, ChatSession.session_id == ChatMessage.session_id)
        
        if user_id:
            query = query.filter(ChatSession.user_id == user_id)
            
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            query = query.filter(ChatMessage.created_at >= start_date)
            
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(ChatMessage.created_at < end_date)
            
        results = query.group_by(date_col).order_by(date_col).all()
        
        data = []
        for r in results:
            data.append({
                "date": r.date.strftime('%Y-%m-%d'),
                "tokens": r.tokens or 0,
                "sessions": r.sessions
            })
            
        return ok(data)
    except Exception as e:
        print(f"[Admin] Daily Report Error: {e}")
        return err('QUERY_FAILED', str(e), 500)
    finally:
        db.close()



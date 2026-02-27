
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
from ..database.connection import get_db_session
from ..database.models import ChatSession, ChatMessage

class SqlSessionStore:
    def __init__(self):
        # We use a fresh session per operation or manage it carefully
        pass

    def create_session(self, session_id: str, user_id: str = None, workflow_id: str = "default"):
        db = get_db_session()
        try:
            session = ChatSession(
                session_id=session_id,
                user_id=user_id,
                workflow_id=workflow_id,
                status='active',
                started_at=datetime.utcnow(),
                last_active_at=datetime.utcnow()
            )
            db.add(session)
            db.commit()
            return session
        except Exception as e:
            db.rollback()
            print(f"[SessionStore] Create Session Failed: {e}")
            raise
        finally:
            db.close()

    def add_message(self, session_id: str, role: str, content: str, token_usage: int = 0, model_name: str = None):
        db = get_db_session()
        try:
            # Verify session exists
            # session = db.query(ChatSession).filter_by(session_id=session_id).first()
            # If not exists, maybe create? Or fail? 
            # Chat flow: Frontend sends session_id. If new, we create it.
            
            msg = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                token_usage=token_usage,
                model_name=model_name,
                created_at=datetime.utcnow()
            )
            db.add(msg)
            
            # Update parent session last_active
            db.query(ChatSession).filter_by(session_id=session_id).update(
                {"last_active_at": datetime.utcnow()}
            )
            
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[SessionStore] Add Message Failed: {e}")
        finally:
            db.close()

    def get_session(self, session_id: str):
        db = get_db_session()
        try:
            return db.query(ChatSession).filter_by(session_id=session_id).first()
        finally:
            db.close()

    def get_user_sessions(self, user_id: str, days: int = 30):
        db = get_db_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            sessions = db.query(ChatSession).filter(
                ChatSession.user_id == user_id,
                ChatSession.started_at >= cutoff_date
            ).order_by(ChatSession.started_at.desc()).all()
            return sessions
        finally:
            db.close()

    def get_messages(self, session_id: str):
        db = get_db_session()
        try:
            return db.query(ChatMessage).filter_by(session_id=session_id).order_by(ChatMessage.created_at).all()
        finally:
            db.close()
            
    def update_session_metadata(self, session_id: str, metadata: dict):
        db = get_db_session()
        try:
            session = db.query(ChatSession).filter_by(session_id=session_id).first()
            if session:
                if session.metadata_ is None:
                    session.metadata_ = {}
                # Merge or replace? Let's merge shallowly
                current = dict(session.metadata_) if session.metadata_ else {}
                current.update(metadata)
                session.metadata_ = current
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"[SessionStore] Update Metadata Failed: {e}")
        finally:
            db.close()

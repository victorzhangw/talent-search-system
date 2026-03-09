from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import logging
import os
from ..database.connection import get_db_session
from ..database.models import ChatSession, ChatMessage
from ..utils.logger import get_daily_logger

def get_session_logger():
    return get_daily_logger("SessionStore_Logger", "session_store.log", level=logging.INFO)

session_logger = get_session_logger()

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
            session_logger.error(f"Create Session Failed: {e}", exc_info=True)
            raise
        finally:
            db.close()

    def add_message(self, session_id: str, role: str, content: str, token_usage: int = 0, model_name: str = None):
        db = get_db_session()
        try:
            msg = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                token_usage=token_usage,
                model_name=model_name,
                created_at=datetime.utcnow()
            )
            db.add(msg)
            
            db.query(ChatSession).filter_by(session_id=session_id).update(
                {"last_active_at": datetime.utcnow()}
            )
            
            db.commit()
            db.refresh(msg)
            return msg.id
        except Exception as e:
            db.rollback()
            session_logger.error(f"Add Message Failed: {e}", exc_info=True)
            return None
        finally:
            db.close()

    def update_message_rating(self, message_id: int, rating: int):
        db = get_db_session()
        try:
            msg = db.query(ChatMessage).filter_by(id=message_id).first()
            if msg:
                msg.rating = rating
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            session_logger.error(f"Update Rating Failed: {e}", exc_info=True)
            return False
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
                ChatSession.last_active_at >= cutoff_date
            ).order_by(ChatSession.last_active_at.desc()).all()
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
                current = dict(session.metadata_) if session.metadata_ else {}
                current.update(metadata)
                session.metadata_ = current
                db.commit()
        except Exception as e:
            db.rollback()
            session_logger.error(f"Update Metadata Failed: {e}", exc_info=True)
        finally:
            db.close()

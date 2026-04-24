
import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from contextlib import contextmanager
from .models import Base

# Global instances
engine = None
db_session = None

def get_db_url():
    """Construct DB URL from env or default to localhost."""
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD', 'postgres') # Common default, user might need to change
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    dbname = os.getenv('DB_NAME', 'ai_chatbot_v2')
    
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

def get_db_engine():
    global engine
    if engine:
        return engine
        
    db_url = get_db_url()
    try:
        # pool_pre_ping helps recover from connection drops
        engine = create_engine(db_url, pool_pre_ping=True)
    except Exception as e:
        print(f"Error creating engine: {e}")
        raise
    return engine

def get_db_session_factory():
    engine = get_db_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Global scoped session
db_session = scoped_session(lambda: get_db_session_factory()())

def get_db_session():
    return db_session()

def init_db(app):
    """Initialize DB connection and tables."""
    global engine
    
    # Force engine creation to test connection
    engine = get_db_engine()
    
    # Create Tables (Idempotent)
    try:
        Base.metadata.create_all(bind=engine)
        print("[SUCCESS] Database tables created/verified in PostgreSQL.")
    except Exception as e:
        print(f"[ERROR] Failed to connect/create tables in PostgreSQL: {e}")
        print("   Please check your .env DB_USER / DB_PASSWORD / DB_NAME")
    
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

@contextmanager
def get_db_cursor():
    """Raw cursor for direct SQL if needed."""
    session = get_db_session()
    # Access raw connection from SQLAlchemy session
    connection = session.connection().connection
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()

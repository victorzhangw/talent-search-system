
import os
import sys
import sqlite3
import psycopg2
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base, relationship
from datetime import datetime
from contextlib import contextmanager

# ---------------------------------------------------------
# 1. Models Definition (Copied from models.py)
# ---------------------------------------------------------
Base = declarative_base()

class AdminUser(Base):
    __tablename__ = 'admin_users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    session_id = Column(String(64), primary_key=True)
    user_id = Column(String(50), index=True)
    workflow_id = Column(String(50))
    started_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(20), default='active')
    metadata_ = Column('metadata', JSON, default={})
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey('chat_sessions.session_id'), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    token_usage = Column(Integer, default=0)
    model_name = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("ChatSession", back_populates="messages")

class TraitDefinition(Base):
    __tablename__ = 'trait_definitions'
    trait_id = Column(String(50), primary_key=True)
    name_zh = Column(String(100))
    name_en = Column(String(100))
    dimension = Column(String(50))
    definition = Column(Text)

class TraitBand(Base):
    __tablename__ = 'trait_bands'
    id = Column(Integer, primary_key=True, autoincrement=True)
    trait_id = Column(String(50), ForeignKey('trait_definitions.trait_id'))
    band = Column(String(10))
    min_score = Column(Integer)
    max_score = Column(Integer)
    semantic_label = Column(String(50))
    description = Column(Text)
    management_focus = Column(Text)
    report_wording = Column(Text)
    ai_guidance = Column(JSON)

class TraitInteraction(Base):
    __tablename__ = 'trait_interactions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    primary_trait_id = Column(String(50), ForeignKey('trait_definitions.trait_id'))
    primary_band = Column(String(10))
    trigger_trait_id = Column(String(50))
    trigger_band = Column(String(10))
    narrative = Column(Text)

# ---------------------------------------------------------
# 2. Connection Logic (Simplified)
# ---------------------------------------------------------
def get_db_url():
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD', 'postgres')
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    dbname = os.getenv('DB_NAME', 'ai_chatbot_v2')
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

# ---------------------------------------------------------
# 3. Auth Helper (from argon2)
# ---------------------------------------------------------
from argon2 import PasswordHasher
ph = PasswordHasher()
def get_password_hash(password):
    return ph.hash(password)

# ---------------------------------------------------------
# 4. Migration Logic
# ---------------------------------------------------------
def run():
    print("🚀 Starting Standalone Migration...")
    
    # Connect PG
    db_url = get_db_url()
    try:
        pg_engine = create_engine(db_url)
        Session = sessionmaker(bind=pg_engine)
        pg_session = Session()
        print("   ✅ Connected to PostgreSQL")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return

    # Create Tables
    print("   Creating Tables...")
    Base.metadata.create_all(bind=pg_engine)

    # Seed Admin
    print("   Seeding Admin...")
    admin = pg_session.query(AdminUser).filter_by(username='admin').first()
    if not admin:
        new_admin = AdminUser(username='admin', password_hash=get_password_hash('admin123'))
        pg_session.add(new_admin)
        print("   ✅ Created admin/admin123")
    else:
        print("   ℹ️ Admin exists")

    # Connect SQLite
    # Try different paths
    possible_paths = [
        'backend/api_v2/app.db',
        'backend/app.db',
        'app.db'
    ]
    sqlite_path = None
    for p in possible_paths:
        if os.path.exists(p):
            sqlite_path = p
            break
            
    if not sqlite_path:
        print("   ⚠️ app.db not found. Checked: " + ", ".join(possible_paths))
        pg_session.commit()
        return
        
    print(f"   Reading from {sqlite_path}...")
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Migrate Traits
    if pg_session.query(TraitDefinition).count() == 0:
        print("   Migrating Traits...")
        rows = cursor.execute("SELECT * FROM trait_definitions").fetchall()
        for row in rows:
            pg_session.merge(TraitDefinition(
                trait_id=row['trait_id'],
                name_zh=row['name_zh'],
                name_en=row['name_en'],
                dimension=row['dimension'],
                definition=row['definition']
            ))
            
        rows = cursor.execute("SELECT * FROM trait_bands").fetchall()
        for row in rows:
            try:
                pg_session.add(TraitBand(
                    trait_id=row['trait_id'],
                    band=row['band'],
                    min_score=row['min_score'],
                    max_score=row['max_score'],
                    semantic_label=row['semantic_label'],
                    description=row['description'],
                    management_focus=row['management_focus'],
                    report_wording=row['report_wording'],
                    ai_guidance=row['ai_guidance']
                ))
                pg_session.flush() # Force SQL execution to catch integrity errors here
            except Exception as e:
                print(f"   ⚠️ Error adding Band {row['trait_id']} - {row['band']}: {e}")
                pg_session.rollback() # Rollback the failed statement transaction


            
        rows = cursor.execute("SELECT * FROM trait_interactions").fetchall()
        for row in rows:
            pg_session.add(TraitInteraction(
                primary_trait_id=row['primary_trait_id'],
                primary_band=row['primary_band'],
                trigger_trait_id=row['trigger_trait_id'],
                trigger_band=row['trigger_band'],
                narrative=row['narrative']
            ))
        print("   ✅ Traits migrated")
    else:
        print("   ℹ️ Traits already in PG")

    # Migrate Logs
    # (Simplified: Skip logic here as primary goal is Traits/Admin)
    
    pg_session.commit()
    pg_session.close()
    conn.close()
    print("✅ Migration Done.")

if __name__ == "__main__":
    run()

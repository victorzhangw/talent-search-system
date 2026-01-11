from flask import Flask
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
# from sqlalchemy.ext.declarative import declarative_base # Deprecated in 2.0
from datetime import datetime

Base = declarative_base()
engine = None
db_session = None

def init_db(app: Flask):
    global engine, db_session
    database_uri = app.config.get('DATABASE_URI', 'sqlite:///app.db')
    
    # Ensure correct path for SQLite if relative
    if database_uri.startswith('sqlite:///'):
        import os
        db_path = database_uri.replace('sqlite:///', '')
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    engine = create_engine(database_uri)
    db_session = scoped_session(sessionmaker(autocommit=False,
                                             autoflush=False,
                                             bind=engine))
    
    Base.query = db_session.query_property()
    
    # Import models here to ensure they are registered
    # from .models import Log
    
    Base.metadata.create_all(bind=engine)
    
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

# --- Models ---

class ChatLog(Base):
    __tablename__ = 'chat_logs'
    id = Column(Integer, primary_key=True)
    session_id = Column(String(50), index=True)
    meta_info = Column(JSON, default={})
    timestamp = Column(DateTime, default=datetime.utcnow)

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
    band = Column(String(10)) # A, B, C
    min_score = Column(Integer)
    max_score = Column(Integer)
    semantic_label = Column(String(50))
    description = Column(Text)
    management_focus = Column(Text)
    report_wording = Column(Text)
    ai_guidance = Column(JSON) # Stores {do: [], dont: []}

class TraitInteraction(Base):
    __tablename__ = 'trait_interactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    primary_trait_id = Column(String(50), ForeignKey('trait_definitions.trait_id'))
    primary_band = Column(String(10)) # A, B, C
    trigger_trait_id = Column(String(50)) # Triggering trait ID
    trigger_band = Column(String(10)) # A, B, C (mapped from high/low)
    narrative = Column(Text)

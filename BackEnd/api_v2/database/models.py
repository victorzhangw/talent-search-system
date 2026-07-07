
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

# --- Admin & Auth ---
class AdminUser(Base):
    __tablename__ = 'admin_users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- Chat & Sessions ---
class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    
    session_id = Column(String(64), primary_key=True) # UUID
    user_id = Column(String(50), index=True) # Optional link to user
    workflow_id = Column(String(50))
    
    started_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(20), default='active') # active, ended, archival
    
    metadata_ = Column('metadata', JSON, default={}) # 'metadata' is reserved in SQLAlchemy sometimes, safer naming? No, JSON is fine.

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey('chat_sessions.session_id'), nullable=False)
    
    role = Column(String(20), nullable=False) # user, assistant, system
    content = Column(Text, nullable=False)
    
    # New requirement: Token Usage
    token_usage = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    model_name = Column(String(50))
    rating = Column(Integer, default=0) # 1 for Good, -1 for Bad, 0 for None
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("ChatSession", back_populates="messages")

# --- Trait System (Migrated from SQLite) ---
class TraitDefinition(Base):
    __tablename__ = 'trait_definitions'

    trait_id = Column(String(50), primary_key=True) # system_name e.g. "Achievement"
    name_zh = Column(String(100))
    name_en = Column(String(100))
    dimension = Column(String(50))
    definition = Column(Text)
    definition_en = Column(Text)
    hidden_anchor = Column(Text)

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
    usage_note = Column(Text)
    trait_interaction_guide = Column(Text)
    report_wording = Column(Text)
    report_wording_friendly = Column(Text)
    trait_project = Column(String(50))
    ai_guidance = Column(JSON) # {do: [], dont: []}
    version = Column(String(20))

class TraitInteraction(Base):
    __tablename__ = 'trait_interactions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    primary_trait_id = Column(String(50), ForeignKey('trait_definitions.trait_id'))
    primary_band = Column(String(10)) 
    trigger_trait_id = Column(String(50))
    trigger_band = Column(String(10))
    narrative = Column(Text)

# --- API Usage & Settlement ---
class DailySettlementRecord(Base):
    __tablename__ = 'daily_settlements'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), index=True, nullable=False) # e.g. email
    plan_id = Column(Integer, nullable=False)
    session_id = Column(String(64), nullable=False) # external_event_id mapping base
    message_id = Column(String(255), nullable=True) # Optional message_id for deduplication
    status = Column(String(20), default='PENDING', index=True) # PENDING, SYNCED, FAILED
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



import os
import sys
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

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
    report_wording = Column(Text)
    report_wording_friendly = Column(Text)
    trait_project = Column(String(50))
    ai_guidance = Column(JSON)

class TraitInteraction(Base):
    __tablename__ = 'trait_interactions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    primary_trait_id = Column(String(50), ForeignKey('trait_definitions.trait_id'))
    primary_band = Column(String(10)) 
    trigger_trait_id = Column(String(50))
    trigger_band = Column(String(10))
    narrative = Column(Text)

# Setup in-memory DB
engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db_session = Session()

# Seed data
# ANI: Self-Leadership (mapped to ANI_05 in previous check, but let's use ANI_300b for test if that's what's passed)
# Wait, let's seed BOTH variations to see which one works.
db_session.add_all([
    TraitDefinition(trait_id='ANI_05', name_en='Self-Leadership', name_zh='自我領導'),
    TraitBand(trait_id='ANI_05', band='A', min_score=70, max_score=100, description='ANI Excellent'),
    
    TraitDefinition(trait_id='CIA_10', name_en='Efficacy', name_zh='自我效能'),
    TraitBand(trait_id='CIA_10', band='A', min_score=70, max_score=100, description='CIA Excellent')
])
db_session.commit()

# Mock the module import for ContextBuilder if possible, or just re-implement build() for debug
# Since I want to find the core factor in the EXISTING code, I'll use the existing file.
sys.path.append(r"d:\python\AI-Character-Chatbot")
import BackEnd.api_v2.services.context_builder as cb_mod
cb_mod.db_session = db_session # REPLACEMENT

from BackEnd.api_v2.services.context_builder import ContextBuilder

def run_debug():
    cb = ContextBuilder({})
    
    # Candidates
    cand_ani = {
        "candidate_id": 36,
        "name": "Julie",
        "assessment": {
            "assessment_id": 36,
            "project_name_abbreviation": "ANI",
            "trait_results": {
                "Self-Leadership": {"score": 79, "trait_id": "300b", "chinese_name": "Self-Leadership"}
            }
        }
    }
    
    cand_cia = {
        "candidate_id": 84,
        "name": "Teacher Liu",
        "assessment": {
            "assessment_id": 88,
            "project_name_abbreviation": "CIA",
            "trait_results": {
                "Efficacy": {"score": 89, "trait_id": "215f", "chinese_name": "Efficacy"}
            }
        }
    }
    
    print("\n--- TEST: BOTH CANDIDATES ---")
    res = cb.build({}, [cand_ani, cand_cia])
    print("Result Analysis Chunk:")
    print(res['base_analysis'])

if __name__ == "__main__":
    run_debug()

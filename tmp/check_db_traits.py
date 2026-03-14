
from BackEnd.api_v2.database.models import TraitDefinition
from BackEnd.api_v2.database.session import db_session
from sqlalchemy import func

def check_traits():
    print("Checking ANI traits...")
    ani_traits = db_session.query(TraitDefinition).filter(TraitDefinition.trait_id.like('ANI_%')).all()
    print(f"Found {len(ani_traits)} ANI traits.")
    for t in ani_traits[:5]:
        print(f"  ID: {t.trait_id}, Name EN: '{t.name_en}', Name ZH: '{t.name_zh}'")

    print("\nChecking CIA traits...")
    cia_traits = db_session.query(TraitDefinition).filter(TraitDefinition.trait_id.like('CIA_%')).all()
    print(f"Found {len(cia_traits)} CIA traits.")
    for t in cia_traits[:5]:
        print(f"  ID: {t.trait_id}, Name EN: '{t.name_en}', Name ZH: '{t.name_zh}'")

    # Specifically check for one from the user's list
    target_id = "ANI_300b"
    t = db_session.query(TraitDefinition).filter_by(trait_id=target_id).first()
    if t:
        print(f"\n✅ Found {target_id}: '{t.name_en}'")
    else:
        print(f"\n❌ {target_id} NOT found in database.")

    target_id_cia = "CIA_215f"
    t = db_session.query(TraitDefinition).filter_by(trait_id=target_id_cia).first()
    if t:
        print(f"\n✅ Found {target_id_cia}: '{t.name_en}'")
    else:
        print(f"\n❌ {target_id_cia} NOT found in database.")

if __name__ == "__main__":
    check_traits()

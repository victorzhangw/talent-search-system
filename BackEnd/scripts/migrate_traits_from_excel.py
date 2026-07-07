"""
Migrate trait definitions from Excel spec to PostgreSQL.

Usage:
    python scripts/migrate_traits_from_excel.py --excel path/to/file.xlsx [--dry-run]

Steps:
    1. Parse Excel (sheets: 02_TraitSemanticBands, 08 interaction_narrative)
    2. Backup existing DB data to SQL file under scripts/backups/
    3. TRUNCATE and re-insert all three trait tables
"""

import sys
import os
import argparse
import json
import re
from datetime import datetime

# Allow importing from api_v2 package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import openpyxl
except ImportError:
    print("[ERROR] openpyxl not installed. Run: pip install openpyxl")
    sys.exit(1)

# Load .env before importing DB modules
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env')
load_dotenv(env_path, encoding='utf-8-sig')

from api_v2.database.connection import get_db_engine


# ---------------------------------------------------------------------------
# Excel parsing
# ---------------------------------------------------------------------------

BAND_SHEET = '02_TraitSemanticBands'
INTERACTION_SHEET = '08 interaction_narrative'

# Expected column indices (0-based) for Sheet 2
COL = {
    'trait_id':                0,
    'trait_name_zh':           1,
    'trait_name_en':           2,
    'dimension_group':         3,
    'definition_zh':           4,
    'definition_en':           5,
    'hidden_anchor':           6,
    'band':                    7,
    'band_range':              8,
    'semantic_label':          9,
    'semantic_description':    10,
    'management_focus':        11,
    'usage_note':              12,
    'trait_interaction_guide': 13,
    'report_wording_zh':       14,
    'report_wording_friendly': 15,
    'ai_do':                   16,
    'ai_dont':                 17,
    'version':                 18,
}


def _cell(row, idx):
    """Safe cell value access."""
    try:
        v = row[idx]
        if v is None:
            return None
        return str(v).strip() if not isinstance(v, str) else v.strip()
    except IndexError:
        return None


def _parse_band_range(band_range_str):
    """Parse '76-100' → (76, 100). Returns (None, None) on failure."""
    if not band_range_str:
        return None, None
    m = re.match(r'(\d+)\s*[-~]\s*(\d+)', str(band_range_str).strip())
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def _extract_project(trait_id):
    """'CIA_01' → 'CIA'"""
    if trait_id and '_' in trait_id:
        return trait_id.split('_')[0]
    return None


def parse_band_sheet(ws):
    """
    Returns:
        definitions: dict[trait_id] → dict  (one per unique trait)
        bands:       list of dict            (one per trait × band)
    """
    definitions = {}
    bands = []

    rows = list(ws.iter_rows(values_only=True))
    header = rows[0] if rows else []

    for row in rows[1:]:
        trait_id = _cell(row, COL['trait_id'])
        if not trait_id:
            continue

        band = _cell(row, COL['band'])
        if not band:
            continue

        # Accumulate one definition per trait_id (first occurrence wins)
        if trait_id not in definitions:
            definitions[trait_id] = {
                'trait_id':     trait_id,
                'name_zh':      _cell(row, COL['trait_name_zh']),
                'name_en':      _cell(row, COL['trait_name_en']),
                'dimension':    _cell(row, COL['dimension_group']),
                'definition':   _cell(row, COL['definition_zh']),
                'definition_en': _cell(row, COL['definition_en']),
                'hidden_anchor': _cell(row, COL['hidden_anchor']),
            }

        min_score, max_score = _parse_band_range(_cell(row, COL['band_range']))

        ai_do_raw = _cell(row, COL['ai_do']) or ''
        ai_dont_raw = _cell(row, COL['ai_dont']) or ''
        ai_do_list = [s.strip() for s in re.split(r'[;\n]+', ai_do_raw) if s.strip()]
        ai_dont_list = [s.strip() for s in re.split(r'[;\n]+', ai_dont_raw) if s.strip()]

        bands.append({
            'trait_id':               trait_id,
            'band':                   band,
            'min_score':              min_score,
            'max_score':              max_score,
            'semantic_label':         _cell(row, COL['semantic_label']),
            'description':            _cell(row, COL['semantic_description']),
            'management_focus':       _cell(row, COL['management_focus']),
            'usage_note':             _cell(row, COL['usage_note']),
            'trait_interaction_guide': _cell(row, COL['trait_interaction_guide']),
            'report_wording':         _cell(row, COL['report_wording_zh']),
            'report_wording_friendly': _cell(row, COL['report_wording_friendly']),
            'ai_guidance':            {'do': ai_do_list, 'dont': ai_dont_list},
            'version':                _cell(row, COL['version']),
            'trait_project':          _extract_project(trait_id),
        })

    return list(definitions.values()), bands


def parse_interaction_sheet(ws):
    """Returns list of interaction dicts."""
    interactions = []
    rows = list(ws.iter_rows(values_only=True))

    for row in rows[1:]:
        primary_trait_id = _cell(row, 0)
        if not primary_trait_id:
            continue
        primary_band = _cell(row, 2)
        interaction_json_str = _cell(row, 4)
        narrative = _cell(row, 5)

        trigger_trait_id = None
        trigger_band = None
        if interaction_json_str:
            try:
                data = json.loads(interaction_json_str)
                triggers = data.get('trigger', [])
                if triggers:
                    trigger_trait_id = triggers[0].get('id')
                    trigger_band = triggers[0].get('band')
            except (json.JSONDecodeError, AttributeError):
                pass

        interactions.append({
            'primary_trait_id': primary_trait_id,
            'primary_band':     primary_band,
            'trigger_trait_id': trigger_trait_id,
            'trigger_band':     trigger_band,
            'narrative':        narrative,
        })

    return interactions


def parse_excel(excel_path):
    print(f"[Parse] Opening: {excel_path}")
    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    sheets = wb.sheetnames
    print(f"[Parse] Sheets found: {sheets}")

    if BAND_SHEET not in sheets:
        raise ValueError(f"Sheet '{BAND_SHEET}' not found in Excel. Available: {sheets}")
    if INTERACTION_SHEET not in sheets:
        raise ValueError(f"Sheet '{INTERACTION_SHEET}' not found in Excel. Available: {sheets}")

    definitions, bands = parse_band_sheet(wb[BAND_SHEET])
    interactions = parse_interaction_sheet(wb[INTERACTION_SHEET])
    wb.close()

    print(f"[Parse] trait_definitions: {len(definitions)} records")
    print(f"[Parse] trait_bands:       {len(bands)} records")
    print(f"[Parse] trait_interactions:{len(interactions)} records")

    return definitions, bands, interactions


# ---------------------------------------------------------------------------
# DB backup
# ---------------------------------------------------------------------------

def _escape_sql_value(v):
    if v is None:
        return 'NULL'
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, dict):
        s = json.dumps(v, ensure_ascii=False).replace("'", "''")
        return f"'{s}'"
    s = str(v).replace("'", "''")
    return f"'{s}'"


def backup_table(conn, table_name, f):
    result = conn.execute(f"SELECT * FROM {table_name}")
    cols = list(result.keys())
    rows = result.fetchall()
    f.write(f"\n-- ========== {table_name} ({len(rows)} rows) ==========\n")
    f.write(f"DELETE FROM {table_name};\n")
    for row in rows:
        values = ', '.join(_escape_sql_value(row[c]) for c in cols)
        col_list = ', '.join(cols)
        f.write(f"INSERT INTO {table_name} ({col_list}) VALUES ({values});\n")
    print(f"[Backup] {table_name}: {len(rows)} rows written")


def create_backup(engine, backup_dir):
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(backup_dir, f'trait_backup_{ts}.sql')

    with engine.connect() as conn:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"-- Trait tables backup generated {ts}\n")
            f.write("BEGIN;\n")
            # Backup in FK-safe restore order
            backup_table(conn, 'trait_definitions', f)
            backup_table(conn, 'trait_bands', f)
            backup_table(conn, 'trait_interactions', f)
            f.write("\nCOMMIT;\n")

    print(f"[Backup] Written to: {path}")
    return path


# ---------------------------------------------------------------------------
# DB write
# ---------------------------------------------------------------------------

def apply_schema_migration(engine):
    """Add new columns if they don't exist yet (idempotent)."""
    from sqlalchemy import text as sa_text
    migrations = [
        "ALTER TABLE trait_definitions ADD COLUMN IF NOT EXISTS definition_en TEXT",
        "ALTER TABLE trait_definitions ADD COLUMN IF NOT EXISTS hidden_anchor TEXT",
        "ALTER TABLE trait_bands ADD COLUMN IF NOT EXISTS usage_note TEXT",
        "ALTER TABLE trait_bands ADD COLUMN IF NOT EXISTS trait_interaction_guide TEXT",
        "ALTER TABLE trait_bands ADD COLUMN IF NOT EXISTS version VARCHAR(20)",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            conn.execute(sa_text(sql))
        conn.commit()
    print("[Schema] Column migrations applied.")


def write_to_db(engine, definitions, bands, interactions):
    from sqlalchemy import text

    with engine.begin() as conn:
        # Truncate in FK-dependency order
        conn.execute(text("TRUNCATE trait_interactions, trait_bands, trait_definitions CASCADE"))
        print("[Write] Tables truncated.")

        # Insert trait_definitions
        for d in definitions:
            conn.execute(text("""
                INSERT INTO trait_definitions
                    (trait_id, name_zh, name_en, dimension, definition, definition_en, hidden_anchor)
                VALUES
                    (:trait_id, :name_zh, :name_en, :dimension, :definition, :definition_en, :hidden_anchor)
            """), d)
        print(f"[Write] trait_definitions: {len(definitions)} rows inserted")

        # Insert trait_bands
        for b in bands:
            b_copy = dict(b)
            b_copy['ai_guidance'] = json.dumps(b_copy['ai_guidance'], ensure_ascii=False)
            conn.execute(text("""
                INSERT INTO trait_bands
                    (trait_id, band, min_score, max_score, semantic_label, description,
                     management_focus, usage_note, trait_interaction_guide,
                     report_wording, report_wording_friendly, trait_project, ai_guidance, version)
                VALUES
                    (:trait_id, :band, :min_score, :max_score, :semantic_label, :description,
                     :management_focus, :usage_note, :trait_interaction_guide,
                     :report_wording, :report_wording_friendly, :trait_project,
                     CAST(:ai_guidance AS jsonb), :version)
            """), b_copy)
        print(f"[Write] trait_bands: {len(bands)} rows inserted")

        # Insert trait_interactions
        for i in interactions:
            conn.execute(text("""
                INSERT INTO trait_interactions
                    (primary_trait_id, primary_band, trigger_trait_id, trigger_band, narrative)
                VALUES
                    (:primary_trait_id, :primary_band, :trigger_trait_id, :trigger_band, :narrative)
            """), i)
        print(f"[Write] trait_interactions: {len(interactions)} rows inserted")

    print("[Write] Commit successful.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Migrate trait data from Excel to PostgreSQL')
    parser.add_argument('--excel', required=True, help='Path to Traitty_RAG_SpeC Excel file')
    parser.add_argument('--dry-run', action='store_true', help='Parse only, do not write to DB')
    args = parser.parse_args()

    excel_path = os.path.abspath(args.excel)
    if not os.path.exists(excel_path):
        print(f"[ERROR] File not found: {excel_path}")
        sys.exit(1)

    definitions, bands, interactions = parse_excel(excel_path)

    if args.dry_run:
        print("\n[DRY RUN] Parsed counts:")
        print(f"  trait_definitions : {len(definitions)}")
        print(f"  trait_bands       : {len(bands)}")
        print(f"  trait_interactions: {len(interactions)}")
        if definitions:
            print(f"\nSample definition: {definitions[0]}")
        if bands:
            b = dict(bands[0])
            b['ai_guidance'] = str(b['ai_guidance'])[:80]
            print(f"Sample band      : {b}")
        if interactions:
            print(f"Sample interaction: {interactions[0]}")
        print("\n[DRY RUN] Done. No data written.")
        return

    engine = get_db_engine()

    backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
    print("\n[Step 1] Creating SQL backup...")
    backup_path = create_backup(engine, backup_dir)

    print("\n[Step 2] Applying schema migration...")
    apply_schema_migration(engine)

    print("\n[Step 3] Writing new data...")
    write_to_db(engine, definitions, bands, interactions)

    print(f"\n✓ Migration complete. Backup saved at: {backup_path}")


if __name__ == '__main__':
    main()

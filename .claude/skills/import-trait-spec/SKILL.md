---
name: import-trait-spec
description: >
  Compare a new Traitty trait spec Excel file (e.g. "Traitty_RAG_SpeC_vX.X.xlsx"
  or "*spec*.xlsx" under docs/) against the previous version, and — if the
  sheet/column format is unchanged — import it into the trait_definitions /
  trait_bands / trait_interactions PostgreSQL tables using the existing
  migration code. Use when the user provides a new trait spec Excel file and
  asks to compare it with the old one and/or import it into the database.
user-invokable: true
argument-hint: "[path to new spec .xlsx]"
metadata:
  category: data-migration
---

# Import Trait Spec Excel into Database

This project stores character-trait data (definitions, score bands, cross-trait
interaction narratives) in three PostgreSQL tables, sourced from a client-provided
Excel spec file. This skill formalizes the process of taking a new spec file,
verifying it matches the expected format, and importing it safely.

## Existing code (do not duplicate — reuse it)

- `BackEnd/scripts/migrate_traits_from_excel.py` — CLI script: parses Excel,
  backs up current DB tables to `BackEnd/scripts/backups/trait_backup_<ts>.sql`,
  applies idempotent schema migrations, truncates and re-inserts the three
  trait tables. Supports `--dry-run` (parse only, no DB write, no backup).
- `BackEnd/api_v2/admin/trait_importer.py` — shared parsing/import library used
  by both the CLI script and the `/api/admin/traits/upload` endpoint. Has a
  stricter `parse_excel_bytes()` that reports skipped/malformed rows
  (`mismatch` dict) instead of silently dropping them — use this to double-check
  format compatibility before trusting the CLI dry-run.
- DB connection comes from `BackEnd/api_v2/database/connection.py` /
  `BackEnd/api_v2/.env` (`DB_HOST`, `DB_NAME`, etc. — currently local Postgres
  `ai_chatbot_v2`). Always confirm this file before assuming which DB is targeted.

Expected workbook shape (both scripts look up sheets by substring match, so
sheet order/other sheets don't matter):

- A sheet whose name contains `TraitSemanticBands` — one row per
  trait × band (A/B/C), trait_id format `[A-Z]{2,6}_\d{2,3}` (e.g. `CIA_01`).
  19 columns: trait_id, trait_name_zh, trait_name_en, dimension_group,
  definition (zh), definition (en), hidden_anchor, band, band_range,
  semantic_label, semantic_description, management_focus, usage_note,
  trait_interaction_guide, report_wording_zh, report_wording_friendly,
  ai_do, ai_dont, version.
- A sheet whose name contains `interaction_narrative` — one row per trait ×
  interaction: trait_id, trait_name_zh, band, interaction_summary,
  interaction_json (`{"trigger":[{"id":...,"band":...}]}`), interaction_narrative.

## Procedure

1. **Locate the files.** New file is usually dropped in `docs/` (e.g.
   `docs/0722 02_08 V6.2 spec_.xlsx`). Find the previous version to diff
   against — look for the most recent `docs/Traitty_RAG_SpeC_v*.xlsx` or
   similarly named prior spec.

2. **Compare structure, not just filenames.** Using `openpyxl` (already a
   project dependency), for both old and new files check:
   - Sheet names (substring-matched against `TraitSemanticBands` and
     `interaction_narrative`).
   - Header row (row 1) of each matched sheet — must match column-for-column.
   - Row counts, as a sanity signal (not a hard requirement — content can
     legitimately grow, e.g. more traits or interactions).

   Example one-off check:
   ```python
   import openpyxl
   def sheets_and_header(path, key):
       wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
       name = next(n for n in wb.sheetnames if key.lower() in n.lower())
       header = next(wb[name].iter_rows(values_only=True))
       wb.close()
       return name, header
   ```
   If headers differ (columns added/removed/reordered), **stop** — the
   fixed-index `COL` mapping in both import scripts will silently misalign
   data. That requires updating `COL` in both `migrate_traits_from_excel.py`
   and `trait_importer.py` before importing, not a plain re-run of this skill.

3. **Dry-run parse the new file** (no DB writes):
   ```
   python BackEnd/scripts/migrate_traits_from_excel.py --excel "docs/<new file>.xlsx" --dry-run
   ```
   Confirms it opens, finds both sheets, and reports parsed counts for
   trait_definitions / trait_bands / trait_interactions.

4. **Cross-check with the stricter validator** to catch rows the dry-run
   would silently skip (invalid trait_id, invalid band, template rows):
   ```python
   import sys; sys.path.insert(0, 'BackEnd')
   from api_v2.admin.trait_importer import parse_excel_bytes
   data = open('docs/<new file>.xlsx', 'rb').read()
   definitions, bands, interactions, error, mismatch = parse_excel_bytes(data)
   ```
   `error` should be `None` and `mismatch` should be `None`. If `mismatch` is
   set, it lists exactly which Excel rows were skipped and why — surface that
   to the user rather than importing partial data.

5. **If format matches (no error, no mismatch): run the real import.** This
   auto-creates a pre-import SQL backup of the three tables before truncating:
   ```
   python BackEnd/scripts/migrate_traits_from_excel.py --excel "docs/<new file>.xlsx"
   ```
   Since this is a destructive write (TRUNCATE + re-insert) against the live
   DB, treat it like any other destructive operation: confirm with the user
   first unless they already explicitly asked for the import in this request.

6. **Verify post-import.** Query row counts and spot-check a known trait/band:
   ```python
   from sqlalchemy import text
   from api_v2.database.connection import get_db_engine
   with get_db_engine().connect() as conn:
       for t in ('trait_definitions', 'trait_bands', 'trait_interactions'):
           print(t, conn.execute(text(f'SELECT COUNT(*) FROM {t}')).scalar())
   ```
   Counts should equal the parsed counts from step 3/4.

7. **If format does NOT match**, do not import. Report the specific diff
   (missing/renamed sheet, changed header columns) so the user can decide
   whether to update the parser or ask the client to fix the file.

## Notes

- If the import fails partway or produces wrong data, restore from the
  auto-generated backup at `BackEnd/scripts/backups/trait_backup_<timestamp>.sql`
  — it's a plain SQL file (`DELETE FROM ...; INSERT INTO ...;` per table)
  that can be run directly, or via `restore_from_backup()` in
  `trait_importer.py`.
- Windows console encoding (cp950) will garble printed Chinese sheet names/text
  in terminal output — this is cosmetic only, not a parse error. Don't add
  emoji to any print/log line in these scripts (project convention, see
  `CLAUDE.md`) — it will crash on Windows with `UnicodeEncodeError`.

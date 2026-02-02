---
description: Workflow to update trait definitions and seed data from new specification versions
---

# Update Trait Data from Specification

This workflow outlines the steps to update the `trait_definitions`, `trait_bands`, and `trait_interactions` data from a new Markdown specification file.

## Prerequisites
- Python environment.
- New specification Markdown file (e.g., `Traitty_RAG_SpeC_v4.xlsx.md`).
- **Database Schema**: Ensure the `trait_bands` table has the `trait_project` column. (If updating an existing DB, ensure `migration/03_add_trait_project.sql` or equivalent has been applied).

## Steps

1.  **Place the new specification file**
    Copy the new Markdown specification file to `Reference-Docs/Extracted/`.

2.  **Run the generation script**
    Execute the Python script to parse the Markdown and generate the SQL seed file.
    Update the `--input` path to point to your new version.

    ```bash
    python scripts/generate_seed_sql.py --input "Reference-Docs/Extracted/Traitty_RAG_SpeC_v3.xlsx.md"
    ```

3.  **Review the generated SQL**
    Check `migration/02_seed_data.sql`.
    - Verify `trait_project` column is populated (e.g., 'ANI', 'CIA').
    - Verify `INSERT ... ON CONFLICT` statements are present.

4.  **Apply Migration**
    Apply the generate SQL to your database.
    
    > [!IMPORTANT]
    > This script uses `INSERT ... ON CONFLICT DO UPDATE`. It will update existing traits/bands/interactions in place. It DOES NOT delete records that are removed from the spec (unless you manually TRUNCATE first, but be careful with Foreign Keys).

    > [!NOTE]
    > If you encounter JSON parsing warnings, check the source Markdown file for malformed JSON strings in the Interaction Sheet.

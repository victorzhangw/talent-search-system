
import sys
import os

# Explicitly add project root to path
project_root = r"d:\python\AI-Character-Chatbot"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"SYS PATH: {sys.path}")

try:
    from backend.api_v2.scripts.migrate_sqlite_to_pg import migrate_sqlite_to_pg
    print("Module found, running migration...")
    migrate_sqlite_to_pg()
except ImportError as e:
    print(f"Import Error: {e}")
except Exception as e:
    print(f"Execution Error: {e}")

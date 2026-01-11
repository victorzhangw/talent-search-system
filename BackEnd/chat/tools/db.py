from __future__ import annotations

import os
from typing import Optional

import psycopg2


class DBConfigError(RuntimeError):
    pass


def get_pg_connection_from_env():
    """Create a direct PostgreSQL connection from env.

    This intentionally avoids importing `talent_search_api.py` (which has FastAPI app side-effects).

    Required env vars:
    - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

    NOTE: This does NOT create an SSH tunnel. If your DB requires SSH tunneling,
    keep using the legacy talent_search module for now or extend this connector in a later milestone.
    """

    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    name = os.getenv("DB_NAME")
    user = os.getenv("DB_USER")
    pwd = os.getenv("DB_PASSWORD")

    missing = [k for k, v in [("DB_HOST", host), ("DB_PORT", port), ("DB_NAME", name), ("DB_USER", user), ("DB_PASSWORD", pwd)] if not v]
    if missing:
        raise DBConfigError(f"DB env vars missing for direct connection: {', '.join(missing)}")

    return psycopg2.connect(host=host, port=int(port), database=name, user=user, password=pwd)

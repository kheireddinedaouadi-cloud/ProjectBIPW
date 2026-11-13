"""SQLite connection helper (standard library only, no server and no credentials needed)."""
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("ABC_DB_PATH", ROOT / "data" / "abc_retail.db"))


def connect(read_only=True):
    """Open a new connection. Read-only for the dashboard, read-write for the ETL."""
    if read_only:
        conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def database_ready():
    """True when the database file exists and contains the star schema."""
    if not DB_PATH.exists():
        return False
    try:
        with connect() as conn:
            conn.execute("SELECT 1 FROM vw_clean_sales LIMIT 1")
        return True
    except sqlite3.Error:
        return False

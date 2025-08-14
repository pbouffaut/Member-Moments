import sqlite3
from typing import Dict, Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  published_at TEXT,
  company_name TEXT NOT NULL,
  company_location TEXT,
  title TEXT,
  url TEXT UNIQUE,
  source TEXT,
  event_type TEXT,
  severity REAL,
  confidence REAL,
  evidence TEXT,
  is_verified INTEGER DEFAULT 1,
  verification_note TEXT,
  tone TEXT DEFAULT 'NEUTRAL',
  tone_confidence REAL DEFAULT 0.5
);
"""

def get_conn(db_path="events.db"):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(SCHEMA)
    return conn

def seen_url(conn, url: str) -> bool:
    cur = conn.execute("SELECT 1 FROM events WHERE url = ?", (url,))
    return cur.fetchone() is not None

def save_event(conn, row: Dict[str, Any]):
    cols = ",".join(row.keys())
    qs = ",".join(["?"]*len(row))
    conn.execute(f"INSERT OR IGNORE INTO events ({cols}) VALUES ({qs})", tuple(row.values()))
    conn.commit()

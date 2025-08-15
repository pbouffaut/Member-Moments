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
  verification_confidence REAL DEFAULT 1.0,
  wikidata_id TEXT,
  entity_types TEXT,
  tone TEXT DEFAULT 'NEUTRAL',
  tone_confidence REAL DEFAULT 0.5
);
"""

def get_conn(db_path="events.db"):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(SCHEMA)
    
    # Migrate existing database to add new columns if they don't exist
    migrate_database(conn)
    
    return conn

def migrate_database(conn):
    """Add new columns to existing database if they don't exist"""
    try:
        # Check if new columns exist
        cursor = conn.execute("PRAGMA table_info(events)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add missing columns
        if 'is_verified' not in columns:
            conn.execute("ALTER TABLE events ADD COLUMN is_verified INTEGER DEFAULT 1")
        if 'verification_note' not in columns:
            conn.execute("ALTER TABLE events ADD COLUMN verification_note TEXT")
        if 'verification_confidence' not in columns:
            conn.execute("ALTER TABLE events ADD COLUMN verification_confidence REAL DEFAULT 1.0")
        if 'wikidata_id' not in columns:
            conn.execute("ALTER TABLE events ADD COLUMN wikidata_id TEXT")
        if 'entity_types' not in columns:
            conn.execute("ALTER TABLE events ADD COLUMN entity_types TEXT")
        if 'tone' not in columns:
            conn.execute("ALTER TABLE events ADD COLUMN tone TEXT DEFAULT 'NEUTRAL'")
        if 'tone_confidence' not in columns:
            conn.execute("ALTER TABLE events ADD COLUMN tone_confidence REAL DEFAULT 0.5")
        
        conn.commit()
    except Exception as e:
        print(f"Migration warning: {e}")
        # Continue even if migration fails

def seen_url(conn, url: str) -> bool:
    cur = conn.execute("SELECT 1 FROM events WHERE url = ?", (url,))
    return cur.fetchone() is not None

def save_event(conn, row: Dict[str, Any]):
    cols = ",".join(row.keys())
    qs = ",".join(["?"]*len(row))
    conn.execute(f"INSERT OR IGNORE INTO events ({cols}) VALUES ({qs})", tuple(row.values()))
    conn.commit()

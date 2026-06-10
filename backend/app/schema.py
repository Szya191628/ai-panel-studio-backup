"""Database schema and migration management.

Uses PRAGMA user_version for version gating.
"""

from __future__ import annotations

import sqlite3

# Schema version
SCHEMA_VERSION = 1

# Initial schema SQL
INITIAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS discussions (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    status TEXT DEFAULT 'assembling',
    max_rounds INTEGER DEFAULT 5,
    current_round INTEGER DEFAULT 0,
    host_profile TEXT,  -- JSON
    created_at INTEGER,
    concluded_at INTEGER,
    conclusion TEXT,
    convergence_score REAL
);

CREATE TABLE IF NOT EXISTS participants (
    id TEXT PRIMARY KEY,
    discussion_id TEXT NOT NULL,
    name TEXT NOT NULL,
    job_title TEXT,
    title TEXT,
    stance TEXT,
    color TEXT DEFAULT '#4A90D9',
    avatar_seed TEXT,
    status TEXT DEFAULT 'standby',
    thinking_summary TEXT,
    is_host INTEGER DEFAULT 0,
    FOREIGN KEY (discussion_id) REFERENCES discussions(id)
);

CREATE TABLE IF NOT EXISTS speeches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discussion_id TEXT NOT NULL,
    participant_id TEXT NOT NULL,
    round INTEGER NOT NULL,
    content TEXT NOT NULL,
    speech_type TEXT DEFAULT 'statement',
    reply_to INTEGER,
    created_at INTEGER,
    FOREIGN KEY (discussion_id) REFERENCES discussions(id),
    FOREIGN KEY (participant_id) REFERENCES participants(id)
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discussion_id TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('consensus', 'disagreement', 'new_point')),
    content TEXT NOT NULL,
    round INTEGER NOT NULL,
    related_speeches TEXT,  -- JSON array of speech IDs
    FOREIGN KEY (discussion_id) REFERENCES discussions(id)
);

CREATE TABLE IF NOT EXISTS convergence_history (
    discussion_id TEXT NOT NULL,
    round INTEGER NOT NULL,
    score REAL,
    consensus_count INTEGER DEFAULT 0,
    disagreement_count INTEGER DEFAULT 0,
    PRIMARY KEY (discussion_id, round),
    FOREIGN KEY (discussion_id) REFERENCES discussions(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_participants_discussion ON participants(discussion_id);
CREATE INDEX IF NOT EXISTS idx_speeches_discussion ON speeches(discussion_id);
CREATE INDEX IF NOT EXISTS idx_speeches_round ON speeches(discussion_id, round);
CREATE INDEX IF NOT EXISTS idx_findings_discussion ON findings(discussion_id);
CREATE INDEX IF NOT EXISTS idx_findings_type ON findings(discussion_id, type);
"""


def apply_schema(conn: sqlite3.Connection) -> None:
    """Apply schema to connection, idempotent."""
    current_version = conn.execute("PRAGMA user_version").fetchone()[0]

    if current_version < SCHEMA_VERSION:
        conn.executescript(INITIAL_SCHEMA)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()


def get_connection(db_path: str) -> sqlite3.Connection:
    """Get a new connection with proper pragmas."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    apply_schema(conn)
    return conn

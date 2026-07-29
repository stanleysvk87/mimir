import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("MIMIR_DB_PATH", "./data/mimir.db")).resolve()

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'live',
    key_paths TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'product',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_name ON projects(name);

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    machine TEXT NOT NULL DEFAULT '',
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    title TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL DEFAULT 'manual_pwa',
    source_ref TEXT NOT NULL DEFAULT '',
    commit_ref TEXT NOT NULL DEFAULT '',
    sindri_script_id INTEGER,
    is_sensitive INTEGER NOT NULL DEFAULT 0,
    follow_up_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entries_timestamp ON entries(timestamp);
CREATE INDEX IF NOT EXISTS idx_entries_project_id ON entries(project_id);
CREATE INDEX IF NOT EXISTS idx_entries_source_ref ON entries(source_ref);
CREATE INDEX IF NOT EXISTS idx_entries_machine ON entries(machine);

-- Fulltext index over entries(title, body, tags), external-content mode
-- (no separate copy of the text, just the tokenized index -- entries
-- stays the single source of truth). tokenize=unicode61 remove_diacritics 2
-- makes MATCH accent- and case-insensitive, which plain SQL LIKE never
-- was for Slovak text (LIKE only case-folds ASCII, diacritics are exact-
-- match only) -- added 2026-07-25 after an audit session repeatedly had
-- to guess exact accented substrings.
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
    title, body, tags,
    content='entries', content_rowid='id',
    tokenize="unicode61 remove_diacritics 2"
);

CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts(rowid, title, body, tags)
    VALUES (new.id, new.title, new.body, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, title, body, tags)
    VALUES ('delete', old.id, old.title, old.body, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, title, body, tags)
    VALUES ('delete', old.id, old.title, old.body, old.tags);
    INSERT INTO entries_fts(rowid, title, body, tags)
    VALUES (new.id, new.title, new.body, new.tags);
END;

-- Read-only window into the FTS5 inverted index, used only to detect
-- (in _backfill_fts) whether entries_fts actually has terms indexed yet.
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts_vocab USING fts5vocab('entries_fts', 'row');

CREATE TABLE IF NOT EXISTS checklist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    resolved_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_checklist_project_id ON checklist_items(project_id);

CREATE TABLE IF NOT EXISTS threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS thread_entries (
    thread_id INTEGER NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    PRIMARY KEY (thread_id, entry_id)
);

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    mime_type TEXT NOT NULL DEFAULT '',
    ocr_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attachments_entry_id ON attachments(entry_id);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

-- Failed login attempts, per source IP -- see auth.py's is_locked_out().
CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT NOT NULL,
    attempted_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts(ip);

-- Generic key/value overrides editable from Settings later (AI provider
-- mode/API key, app password). Takes priority over the env var default
-- when present -- same pattern as Sindri's settings_store.
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _backfill_project_columns(conn)
        _backfill_fts(conn)


def _backfill_project_columns(conn):
    """CREATE TABLE IF NOT EXISTS never adds columns to an already-existing
    table, so a DB created before `notes`/`category` existed needs them
    added by hand, once, on startup."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(projects)")}
    if "notes" not in existing:
        conn.execute("ALTER TABLE projects ADD COLUMN notes TEXT NOT NULL DEFAULT ''")
    if "category" not in existing:
        conn.execute("ALTER TABLE projects ADD COLUMN category TEXT NOT NULL DEFAULT 'product'")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_category ON projects(category)")


def _backfill_fts(conn):
    """One-time population of entries_fts for rows that existed before the
    FTS5 index was added. The AFTER INSERT/UPDATE/DELETE triggers only
    cover writes from this point forward, so anything already in `entries`
    needs to be indexed once.

    Must use the FTS5 'rebuild' special command, not a manual
    `INSERT INTO entries_fts(rowid, ...) SELECT ... FROM entries` --
    confirmed by testing that the manual multi-row insert registers rows
    (count(*) matches) but leaves the actual inverted index (fts5vocab)
    empty, so MATCH silently returns nothing. 'rebuild' is the documented
    way to (re)populate an external-content FTS5 table from its source
    table and was verified to build a real, searchable index."""
    (entries_count,) = conn.execute("SELECT count(*) FROM entries").fetchone()
    (fts_terms,) = conn.execute("SELECT count(*) FROM entries_fts_vocab").fetchone()
    if entries_count > 0 and fts_terms == 0:
        conn.execute("INSERT INTO entries_fts(entries_fts) VALUES('rebuild')")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

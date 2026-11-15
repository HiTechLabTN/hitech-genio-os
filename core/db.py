"""SQLite store and migrations — Plan v1 §4.1 / §5.

Local-first by design: one file, no server. The database lives with the memory
files and stays out of git. ``GENIO_DATA_DIR`` (or ``GENIO_DB``) overrides the
location so tests and dev instances never touch real data.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Migrations: append-only. ``PRAGMA user_version`` tracks what was applied.
# The full table list from Plan v1 §5 is created up-front so later phases only
# add columns, never whole schemas.
# ---------------------------------------------------------------------------
MIGRATION_1 = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    display_name  TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'member',
    workspace_slug TEXT NOT NULL UNIQUE,
    created_at    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    csrf       TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS profiles (
    user_id          INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    locale           TEXT NOT NULL DEFAULT 'ar-TN',
    register         TEXT NOT NULL DEFAULT 'derja',
    technical_level  TEXT NOT NULL DEFAULT 'intermediate',
    occupation       TEXT NOT NULL DEFAULT '',
    persona_pack     TEXT NOT NULL DEFAULT 'chat_general',
    mode             TEXT NOT NULL DEFAULT 'chat',
    env              TEXT NOT NULL DEFAULT 'local',
    data_sensitivity TEXT NOT NULL DEFAULT 'medium',
    goals            TEXT NOT NULL DEFAULT '[]',
    sectors          TEXT NOT NULL DEFAULT '[]',
    tools            TEXT NOT NULL DEFAULT '[]',
    safety           TEXT NOT NULL DEFAULT '{}',
    onboarding_done  INTEGER NOT NULL DEFAULT 0,
    updated_at       REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS orgs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    owner_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS org_members (
    org_id  INTEGER NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role    TEXT NOT NULL DEFAULT 'member',
    PRIMARY KEY (org_id, user_id)
);

CREATE TABLE IF NOT EXISTS conversations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      TEXT NOT NULL DEFAULT '',
    agent      TEXT NOT NULL DEFAULT 'Genio-Rayes',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    created_at      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS tool_grants (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tool    TEXT NOT NULL,
    granted INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, tool)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,
    actor      TEXT NOT NULL DEFAULT '',
    tool       TEXT NOT NULL DEFAULT '',
    action     TEXT NOT NULL,
    target     TEXT NOT NULL DEFAULT '',
    status     TEXT NOT NULL DEFAULT 'ok',
    detail     TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,
    kind       TEXT NOT NULL,
    model      TEXT NOT NULL DEFAULT '',
    tokens     INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS rag_sources (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,
    name       TEXT NOT NULL,
    license    TEXT NOT NULL DEFAULT 'unknown',
    url        TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS rag_chunks (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES rag_sources(id) ON DELETE CASCADE,
    heading   TEXT NOT NULL DEFAULT '',
    body      TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,
    message_id INTEGER,
    rating     INTEGER NOT NULL DEFAULT 0,
    note       TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_packs (
    name       TEXT PRIMARY KEY,
    version    TEXT NOT NULL DEFAULT '1.0',
    manifest   TEXT NOT NULL DEFAULT '{}',
    enabled    INTEGER NOT NULL DEFAULT 1,
    updated_at REAL NOT NULL
);
"""

MIGRATION_2 = """
CREATE TABLE IF NOT EXISTS approvals (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tool       TEXT NOT NULL,
    params     TEXT NOT NULL DEFAULT '{}',
    status     TEXT NOT NULL DEFAULT 'pending',
    created_at REAL NOT NULL,
    decided_at REAL,
    decided_by INTEGER
);
"""

MIGRATION_3 = """
CREATE TABLE IF NOT EXISTS projects (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    template   TEXT NOT NULL,
    slug       TEXT NOT NULL,
    idea       TEXT NOT NULL DEFAULT '',
    tasks      TEXT NOT NULL DEFAULT '[]',
    created_at REAL NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS projects_user_slug ON projects (user_id, slug);
"""

MIGRATIONS: List[str] = [MIGRATION_1, MIGRATION_2, MIGRATION_3]


def data_dir() -> Path:
    configured = os.environ.get("GENIO_DATA_DIR")
    return Path(configured).expanduser() if configured else BASE_DIR


def db_path() -> Path:
    configured = os.environ.get("GENIO_DB")
    if configured:
        return Path(configured).expanduser()
    return data_dir() / "memory" / "genio.db"


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    target = Path(path) if path else db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version >= len(MIGRATIONS):
        return
    for index in range(version, len(MIGRATIONS)):
        conn.executescript(MIGRATIONS[index])
        conn.execute(f"PRAGMA user_version = {index + 1}")
    conn.commit()


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """Short-lived connection per request/task (SQLite is cheap to open)."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> Path:
    """Create the schema if needed; returns the database path."""
    conn = connect()
    conn.close()
    return db_path()


def row_to_dict(row: sqlite3.Row | None) -> dict:
    return dict(row) if row is not None else {}

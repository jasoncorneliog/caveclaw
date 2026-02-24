"""SQLite for scheduled tasks and key-value state."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from caveclaw.config import CONFIG_DIR

DB_PATH = CONFIG_DIR / "caveclaw.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cron TEXT NOT NULL,
            command TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at REAL DEFAULT (unixepoch())
        );
        CREATE TABLE IF NOT EXISTS task_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER REFERENCES scheduled_tasks(id),
            started_at REAL,
            finished_at REAL,
            result TEXT
        );
        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at REAL
        );
        """
    )
    conn.close()


def add_task(name: str, cron: str, command: str) -> int:
    """Insert a scheduled task, return its id."""
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO scheduled_tasks (name, cron, command) VALUES (?, ?, ?)",
        (name, cron, command),
    )
    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return task_id


def get_due_tasks() -> list[dict]:
    """Return all enabled scheduled tasks (caller handles cron matching)."""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM scheduled_tasks WHERE enabled = 1"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_state(key: str, default: str | None = None) -> str | None:
    """Get a value from the key-value state store."""
    conn = _connect()
    row = conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row:
        return row["value"]
    return default


def set_state(key: str, value: str) -> None:
    """Set a value in the key-value state store."""
    conn = _connect()
    conn.execute(
        "INSERT INTO state (key, value, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (key, value, time.time()),
    )
    conn.commit()
    conn.close()

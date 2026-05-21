"""SQLite snapshot for session recovery after refresh."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "jobs.sqlite"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(DB_PATH))


def init_db() -> None:
    c = _conn()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            session_id TEXT PRIMARY KEY,
            snapshot_json TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )
    c.commit()
    c.close()


def save_snapshot(session_id: str, snapshot: dict[str, Any]) -> None:
    init_db()
    c = _conn()
    c.execute(
        """
        INSERT INTO jobs (session_id, snapshot_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            snapshot_json = excluded.snapshot_json,
            updated_at = excluded.updated_at
        """,
        (session_id, json.dumps(snapshot, ensure_ascii=False), time.time()),
    )
    c.commit()
    c.close()


def load_snapshot(session_id: str) -> dict[str, Any] | None:
    if not DB_PATH.exists():
        return None
    c = _conn()
    row = c.execute(
        "SELECT snapshot_json FROM jobs WHERE session_id = ?", (session_id,)
    ).fetchone()
    c.close()
    if not row:
        return None
    return json.loads(row[0])

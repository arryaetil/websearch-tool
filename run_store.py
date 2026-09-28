"""Short-lived storage for evaluation reports. Never persist provider credentials."""

import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

RETENTION_SECONDS = 7 * 24 * 60 * 60
MAX_RUNS = 100


def _database_path() -> Path:
    return Path(os.environ.get("KYCX_RUN_DB", "./data/research_runs.sqlite3"))


@contextmanager
def _connect():
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch(mode=0o600)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("""CREATE TABLE IF NOT EXISTS research_runs (
        id TEXT PRIMARY KEY,
        created_at INTEGER NOT NULL,
        expires_at INTEGER NOT NULL,
        name TEXT NOT NULL,
        city TEXT NOT NULL,
        employer TEXT NOT NULL,
        report_json TEXT NOT NULL
    )""")
    connection.execute("CREATE INDEX IF NOT EXISTS research_runs_expiry ON research_runs(expires_at)")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _prune(connection: sqlite3.Connection, now: int) -> None:
    connection.execute("DELETE FROM research_runs WHERE expires_at <= ?", (now,))
    connection.execute("""DELETE FROM research_runs WHERE id IN (
        SELECT id FROM research_runs ORDER BY created_at DESC, id DESC LIMIT -1 OFFSET ?
    )""", (MAX_RUNS,))


def prune_runs() -> None:
    with _connect() as connection:
        _prune(connection, int(time.time()))


def save_run(report: dict) -> dict:
    now = int(time.time())
    run_id = str(uuid.uuid4())
    subject = report.get("subject") or {}
    expires_at = now + RETENTION_SECONDS
    with _connect() as connection:
        _prune(connection, now)
        connection.execute(
            "INSERT INTO research_runs VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, now, expires_at, subject.get("name", ""),
             subject.get("city", ""), subject.get("employer", ""),
             json.dumps(report, ensure_ascii=False)),
        )
        _prune(connection, now)
    return {"id": run_id, "created_at": now, "expires_at": expires_at}


def list_runs() -> list[dict]:
    with _connect() as connection:
        _prune(connection, int(time.time()))
        rows = connection.execute("""SELECT id, created_at, expires_at, name, city, employer
            FROM research_runs ORDER BY created_at DESC, id DESC""").fetchall()
    return [dict(row) for row in rows]


def get_run(run_id: str) -> dict | None:
    with _connect() as connection:
        _prune(connection, int(time.time()))
        row = connection.execute(
            "SELECT report_json FROM research_runs WHERE id = ?", (run_id,)
        ).fetchone()
    return json.loads(row["report_json"]) if row else None


def delete_run(run_id: str) -> bool:
    with _connect() as connection:
        cursor = connection.execute("DELETE FROM research_runs WHERE id = ?", (run_id,))
    return cursor.rowcount > 0


def delete_all_runs() -> int:
    with _connect() as connection:
        cursor = connection.execute("DELETE FROM research_runs")
    return cursor.rowcount

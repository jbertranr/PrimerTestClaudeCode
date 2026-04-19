import os
import sqlite3
from datetime import datetime
from typing import Dict

STATUS_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "status.db")

VALID_STATUSES = {"new", "interested", "applied", "discarded"}


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(STATUS_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(STATUS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_status_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS status (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'new',
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()


def get_status(job_id: str) -> str:
    with _connect() as conn:
        row = conn.execute(
            "SELECT status FROM status WHERE job_id = ?", (job_id,)
        ).fetchone()
        return row["status"] if row else "new"


def set_status(job_id: str, status: str) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO status (job_id, status, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at
            """,
            (job_id, status, datetime.utcnow().isoformat()),
        )
        conn.commit()


def get_all_statuses() -> Dict[str, str]:
    with _connect() as conn:
        rows = conn.execute("SELECT job_id, status FROM status").fetchall()
        return {row["job_id"]: row["status"] for row in rows}

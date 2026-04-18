import sqlite3
import os
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scrapers.base import Job

DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                url TEXT,
                source TEXT,
                category TEXT,
                posted_at TEXT,
                first_seen_at TEXT NOT NULL,
                cover_letter_generated INTEGER DEFAULT 0
            )
        """)
        conn.commit()


def is_new(job_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM seen_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return row is None


def mark_seen(job: "Job") -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO seen_jobs
                (id, title, company, location, url, source, category, posted_at, first_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                job.title,
                job.company,
                job.location,
                job.url,
                job.source,
                job.category,
                job.posted_at,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()


def mark_cover_letter_done(job_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE seen_jobs SET cover_letter_generated = 1 WHERE id = ?",
            (job_id,),
        )
        conn.commit()


def count_today_jobs() -> int:
    today = datetime.utcnow().date().isoformat()
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM seen_jobs WHERE first_seen_at LIKE ?",
            (f"{today}%",),
        ).fetchone()
        return row[0] if row else 0

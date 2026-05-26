import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "scraper.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                id      TEXT PRIMARY KEY,
                url     TEXT,
                seen_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        # Migrate: add url column if it doesn't exist yet
        cols = [r[1] for r in conn.execute("PRAGMA table_info(seen_jobs)")]
        if "url" not in cols:
            conn.execute("ALTER TABLE seen_jobs ADD COLUMN url TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_seen_url ON seen_jobs(url)")


def is_seen(job_id: str, url: str = "") -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT 1 FROM seen_jobs WHERE id = ? OR (url != '' AND url = ?)",
            (job_id, url)
        ).fetchone()
    return row is not None


def mark_seen(job_id: str, url: str = "") -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen_jobs (id, url) VALUES (?, ?)",
            (job_id, url)
        )

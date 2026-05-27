import sqlite3
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "jobs.db")

STATUSES = ["watchlist", "applied", "phone_screen", "interview", "offer", "rejected", "ghosted"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company     TEXT NOT NULL,
    role        TEXT NOT NULL,
    url         TEXT,
    source      TEXT,
    contact     TEXT,
    status      TEXT NOT NULL DEFAULT 'applied',
    date_applied TEXT,
    follow_up_date TEXT,
    notes       TEXT,
    date_created TEXT NOT NULL,
    date_updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scraped_jobs (
    external_id TEXT PRIMARY KEY,
    role        TEXT NOT NULL,
    company     TEXT,
    location    TEXT,
    url         TEXT,
    source      TEXT,
    scraped_at  TEXT NOT NULL,
    tracker_id  INTEGER
);
CREATE TABLE IF NOT EXISTS scraper_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ran_at      DATETIME NOT NULL DEFAULT (datetime('now')),
    query_count INTEGER NOT NULL DEFAULT 0,
    jobs_found  INTEGER NOT NULL DEFAULT 0
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        try:
            conn.execute("ALTER TABLE scraped_jobs ADD COLUMN dismissed INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass  # column already exists


def _now():
    return datetime.utcnow().isoformat()


def _row_to_dict(row):
    return dict(row) if row else None


def get_all_jobs(status=None, order_by="date_updated", order_dir="desc"):
    _COLS = {"company", "role", "status", "date_applied", "date_updated", "follow_up_date"}
    if order_by not in _COLS:
        order_by = "date_updated"
    if order_dir not in ("asc", "desc"):
        order_dir = "desc"
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                f"SELECT * FROM jobs WHERE status = ? ORDER BY {order_by} {order_dir}", (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM jobs ORDER BY {order_by} {order_dir}"
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_job(job_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_dict(row)


def create_job(data):
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO jobs (company, role, url, source, contact, status,
               date_applied, follow_up_date, notes, date_created, date_updated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("company"),
                data.get("role"),
                data.get("url", ""),
                data.get("source", ""),
                data.get("contact", ""),
                data.get("status", "applied"),
                data.get("date_applied", date.today().isoformat()),
                data.get("follow_up_date", ""),
                data.get("notes", ""),
                now,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_dict(row)


def update_job(job_id, data):
    now = _now()
    fields = []
    values = []
    allowed = ["company", "role", "url", "source", "contact", "status",
               "date_applied", "follow_up_date", "notes"]
    for key in allowed:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if not fields:
        return get_job(job_id)
    fields.append("date_updated = ?")
    values.append(now)
    values.append(job_id)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE jobs SET {', '.join(fields)} WHERE id = ?", values
        )
    return get_job(job_id)


def delete_job(job_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))


def get_summary():
    """Return count per status + overdue follow-up count."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status"
        ).fetchall()
        today = date.today().isoformat()
        overdue = conn.execute(
            "SELECT COUNT(*) as cnt FROM jobs WHERE follow_up_date != '' AND follow_up_date < ? AND status NOT IN ('offer','rejected','ghosted')",
            (today,)
        ).fetchone()
    counts = {s: 0 for s in STATUSES}
    for row in rows:
        counts[row["status"]] = row["cnt"]
    return {"by_status": counts, "overdue_followups": overdue["cnt"]}


def upsert_scraped_job(data):
    """Insert a scraped job; silently skip if already exists."""
    now = _now()
    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO scraped_jobs
               (external_id, role, company, location, url, source, scraped_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                data["external_id"], data["role"],
                data.get("company", ""), data.get("location", ""),
                data.get("url", ""), data.get("source", ""),
                now,
            ),
        )
    return get_scraped_job(data["external_id"])


def get_scraped_job(external_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM scraped_jobs WHERE external_id = ?", (external_id,)
        ).fetchone()
    return _row_to_dict(row)


def get_scraped_jobs(order_by="scraped_at", order_dir="desc"):
    _COLS = {"company", "role", "scraped_at"}
    if order_by not in _COLS:
        order_by = "scraped_at"
    if order_dir not in ("asc", "desc"):
        order_dir = "desc"
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM scraped_jobs WHERE dismissed = 0 ORDER BY {order_by} {order_dir}"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def dismiss_scraped_job(external_id):
    with get_conn() as conn:
        conn.execute(
            "UPDATE scraped_jobs SET dismissed = 1 WHERE external_id = ?", (external_id,)
        )


def mark_scraped_added(external_id, tracker_id):
    with get_conn() as conn:
        conn.execute(
            "UPDATE scraped_jobs SET tracker_id = ? WHERE external_id = ?",
            (tracker_id, external_id),
        )


def get_overdue_followups():
    """Return jobs with a past follow_up_date that aren't closed."""
    today = date.today().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM jobs
               WHERE follow_up_date != '' AND follow_up_date < ?
               AND status NOT IN ('offer','rejected','ghosted')
               ORDER BY follow_up_date ASC""",
            (today,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def log_scraper_run(query_count: int, jobs_found: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO scraper_runs (query_count, jobs_found) VALUES (?, ?)",
            (query_count, jobs_found),
        )


def get_scraper_run_stats() -> dict:
    """Return total runs and query count for the current calendar month."""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT COUNT(*) as runs, COALESCE(SUM(query_count), 0) as api_calls
               FROM scraper_runs
               WHERE strftime('%Y-%m', ran_at) = strftime('%Y-%m', 'now')"""
        ).fetchone()
        return {
            "runs_this_month": row[0],
            "api_calls_this_month": row[1],
            "api_call_limit": 200,
        }

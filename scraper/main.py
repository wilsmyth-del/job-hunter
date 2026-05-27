#!/usr/bin/env python3
"""
Job finder — fetches new job listings from LinkedIn and JSearch (RapidAPI),
scores them against your configured keywords and location preferences, and sends
top matches to Telegram. Runs via cron once daily.
"""

import json
import logging
import os
import re
import requests
import smtplib
import time
import urllib.parse
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

from config import (
    AUTO_ADD_THRESHOLD,
    BLOCKED_DOMAINS,
    BLOCKED_SOURCES,
    KEYWORDS,
    LINKEDIN_LOCATION,
    LOCATION_SCORES,
    MAX_JOBS_PER_NOTIFICATION,
    MIN_KEYWORD_SCORE,
    SEARCH_QUERIES,
)
from db import init_db, is_seen, mark_seen

load_dotenv(Path(__file__).parent.parent / ".env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("ALLOWED_CHAT_ID")
JOB_TRACKER_URL = os.getenv("JOB_TRACKER_URL", "http://localhost:5002")

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "")
EMAIL_RECIPIENTS = [e.strip() for e in os.getenv("EMAIL_RECIPIENTS", "").split(",") if e.strip()]
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-CA,en;q=0.9",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


# ── Sources ───────────────────────────────────────────────────────────────────

def fetch_linkedin(query: str, location: str = "") -> list[dict]:
    """
    Fetch jobs from LinkedIn's public guest job search API.
    Returns up to 20 results per query (2 pages of 10).
    """
    jobs = []
    seen_ids: set[str] = set()

    for start in (0, 10):
        params = urllib.parse.urlencode({
            "keywords": query,
            "location": location,
            "start": str(start),
        })
        url = (
            "https://www.linkedin.com/jobs-guest/jobs/api/"
            f"seeMoreJobPostings/search?{params}"
        )
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                html = r.read().decode("utf-8", errors="ignore")

            # Parse job cards from HTML
            cards = re.findall(
                r'data-entity-urn="urn:li:jobPosting:(\d+)".*?'
                r'base-card__full-link[^>]+href="([^"]+)".*?'
                r'base-search-card__title[^>]*>\s*(.*?)\s*</h3>.*?'
                r'hidden-nested-link[^>]*>\s*(.*?)\s*</a>.*?'
                r'job-search-card__location[^>]*>\s*(.*?)\s*</span>',
                html, re.DOTALL
            )

            for job_id, link, title, company, location_text in cards:
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                # Clean up HTML entities
                title = re.sub(r'<[^>]+>', '', title).strip()
                company = re.sub(r'<[^>]+>', '', company).strip()
                link_clean = link.split("?")[0]  # strip tracking params
                jobs.append({
                    "id": f"linkedin_{job_id}",
                    "role": title,
                    "company": company,
                    "location": location_text.strip(),
                    "url": link_clean,
                    "description": f"{title} {company}",
                    "source": "LinkedIn",
                })

            if len(cards) < 10:
                break  # no more pages
            time.sleep(1)  # be polite between pages

        except Exception as e:
            log.warning(f"LinkedIn fetch failed for '{query}' (start={start}): {e}")
            break

    return jobs


def fetch_jsearch(query: str) -> list[dict]:
    """Fetch jobs from JSearch (RapidAPI) — aggregates Indeed, LinkedIn, Glassdoor, Google for Jobs."""
    if not JSEARCH_API_KEY:
        log.warning("JSEARCH_API_KEY not set — skipping JSearch")
        return []
    try:
        response = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={
                "x-rapidapi-key": JSEARCH_API_KEY,
                "x-rapidapi-host": "jsearch.p.rapidapi.com",
            },
            params={
                "query": query,
                "num_pages": "1",
                "date_posted": "3days",
                "employment_types": "FULLTIME,CONTRACTOR",
                "country": "ca",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json().get("data") or []
        jobs = []
        for item in data:
            job_id = item.get("job_id", "")
            title = item.get("job_title", "")
            company = item.get("employer_name", "")
            city = item.get("job_city", "")
            state = item.get("job_state", "")
            location = f"{city}, {state}".strip(", ")
            url = item.get("job_apply_link") or item.get("job_google_link", "")
            description = item.get("job_description", "")[:500]
            if not url:
                continue
            jobs.append({
                "id": f"jsearch_{job_id}",
                "role": title,
                "company": company,
                "location": location,
                "url": url,
                "description": f"{title} {company} {description}",
                "source": item.get("job_publisher", "JSearch"),
            })
        log.info(f"JSearch returned {len(jobs)} jobs for '{query}'")
        return jobs
    except Exception as e:
        log.warning(f"JSearch fetch failed for '{query}': {e}")
        return []



# ── Filtering ─────────────────────────────────────────────────────────────────

def _load_blocked_domains() -> set:
    """Merge hardcoded BLOCKED_DOMAINS with runtime blocked_domains.txt."""
    domains = set(BLOCKED_DOMAINS)
    blocklist = Path(__file__).parent.parent / "filters" / "blocked_domains.txt"
    if blocklist.exists():
        for line in blocklist.read_text().splitlines():
            line = line.strip()
            if line:
                domains.add(line)
    return domains


def _load_negative_keywords() -> list:
    path = Path(__file__).parent.parent / "filters" / "negative_keywords.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return []


def is_title_blocked(job: dict) -> bool:
    import re
    title = job.get("role", "").lower()
    for kw in _load_negative_keywords():
        if re.search(r'\b' + re.escape(kw.strip().lower()) + r'\b', title):
            return True
    return False


def is_blocked(job: dict) -> bool:
    """Return True if the job URL or publisher is on the blocklist."""
    url = job.get("url", "").lower()
    for domain in _load_blocked_domains():
        if domain in url:
            return True
    source = job.get("source", "").lower()
    for name in BLOCKED_SOURCES:
        if name in source:
            return True
    return False


# ── Scoring ───────────────────────────────────────────────────────────────────

def score_job(job: dict) -> int:
    """
    Score 0–80: keyword relevance (0–60) + location preference (0–20).
    """
    text = f"{job['role']} {job['description']} {job['company']}".lower()
    loc = f"{job['location']}".lower()

    kw_score = 0
    for kw, weight in KEYWORDS.items():
        if kw.lower() in text:
            kw_score += weight
    kw_score = min(kw_score, 60)

    # Location bonus only applies if the job is already keyword-relevant.
    # Prevents location bonus from inflating scores for completely unrelated roles.
    loc_score = 0
    if kw_score >= MIN_KEYWORD_SCORE:
        for place, weight in LOCATION_SCORES.items():
            if place in loc:
                loc_score = max(loc_score, weight)
        if not loc_score and ("bc" in loc or "british columbia" in loc or "canada" in loc):
            loc_score = 6

    return kw_score + loc_score


# ── Actions ───────────────────────────────────────────────────────────────────

def ingest_to_tracker(job: dict, score: int) -> bool:
    """Send a scraped job to the job tracker's Sources tab.
    High-scoring jobs (score >= AUTO_ADD_THRESHOLD) are also auto-added to
    the pipeline as Watchlist entries."""
    try:
        data = json.dumps({
            "external_id": job["id"],
            "role": job["role"],
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "url": job["url"],
            "source": job["source"],
            "score": score,
            "auto_add": score >= AUTO_ADD_THRESHOLD,
        }).encode()
        req = urllib.request.Request(
            f"{JOB_TRACKER_URL}/api/scraped",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
        return resp.get("auto_added", False)
    except Exception as e:
        log.warning(f"Failed to ingest to tracker: {e}")
        return False


def send_telegram(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.info("Telegram not configured — skipping notification")
        return
    data = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10)


def send_email(scored_top: list, new_count: int, auto_added: int) -> None:
    if not GMAIL_USER or not GMAIL_APP_PASSWORD or not EMAIL_RECIPIENTS:
        log.info("Email not configured or no recipients — skipping")
        return

    now = datetime.now().strftime("%B %d, %Y – %I:%M %p")
    subject = f"Job Digest – {datetime.now().strftime('%b %d')} ({new_count} new listings)"

    lines = [
        f"Job Digest — {now}",
        f"{new_count} new listing{'s' if new_count != 1 else ''}, top {len(scored_top)} shown",
        "",
    ]
    for job, score in scored_top:
        icon = "🔥" if score >= 50 else "⭐" if score >= 30 else "📌"
        company = f" @ {job['company']}" if job["company"] else ""
        loc = f" · {job['location']}" if job["location"] else ""
        lines.append(f"{icon} {job['role']}{company}{loc}  [score: {score}]")
        lines.append(f"   {job['url']}")
        lines.append("")

    if auto_added:
        lines.append(f"✅ {auto_added} high-match job{'s' if auto_added != 1 else ''} auto-added to the tracker")
        lines.append("")

    lines.append("—")
    lines.append(f"Sent by Octo · Job Finder · {GMAIL_USER}")

    body = "\n".join(lines)
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = f"Octo Job Finder <{GMAIL_USER}>"
    msg["To"] = ", ".join(EMAIL_RECIPIENTS)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.sendmail(GMAIL_USER, EMAIL_RECIPIENTS, msg.as_string())
        log.info(f"Email sent to {len(EMAIL_RECIPIENTS)} recipient(s)")
    except Exception as e:
        log.error(f"Email send failed: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    init_db()

    # Load search queries and LinkedIn location from JSON config; fall back to config.py
    _config_path = Path(__file__).parent.parent / "filters" / "scraper_config.json"
    active_queries = SEARCH_QUERIES
    active_linkedin_location = LINKEDIN_LOCATION
    if _config_path.exists():
        try:
            _cfg = json.loads(_config_path.read_text())
            _loaded = _cfg.get("search_queries")
            if isinstance(_loaded, list) and _loaded:
                active_queries = _loaded
                log.info("Loaded %d queries from scraper_config.json", len(active_queries))
            else:
                log.warning("scraper_config.json has no valid search_queries — using config.py fallback")
            _loc = _cfg.get("linkedin_location", "").strip()
            if _loc:
                active_linkedin_location = _loc
                log.info("Loaded LinkedIn location from scraper_config.json: %s", _loc)
        except Exception as _e:
            log.warning("Could not parse scraper_config.json (%s) — using config.py fallback", _e)
    else:
        log.info("scraper_config.json not found — using config.py fallback")

    # Cap at 8 queries
    if len(active_queries) > 8:
        log.info("Capping query list from %d to 8", len(active_queries))
        active_queries = active_queries[:8]

    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    blocked_count = 0
    title_blocked_count = 0
    for query in active_queries:
        for job in fetch_linkedin(query, active_linkedin_location) + fetch_jsearch(query):
            if job["url"] in seen_urls:
                continue
            if is_blocked(job):
                blocked_count += 1
                log.info(f"Blocked (paygated domain): {job['url']}")
                continue
            if is_title_blocked(job):
                title_blocked_count += 1
                log.info(f"Blocked (title filter): {job['role']}")
                continue
            seen_urls.add(job["url"])
            all_jobs.append(job)
        time.sleep(0.5)  # polite gap between queries

    log.info(f"Fetched {len(all_jobs)} listings ({blocked_count} domain-blocked, {title_blocked_count} title-blocked)")

    new_jobs = [j for j in all_jobs if not is_seen(j["id"], j.get("url", ""))]
    log.info(f"{len(new_jobs)} new listings")

    if not new_jobs:
        log.info("Nothing new — exiting")
        return

    scored = sorted(
        [(j, score_job(j)) for j in new_jobs],
        key=lambda x: x[1],
        reverse=True,
    )

    added = 0
    for job, score in scored:
        mark_seen(job["id"], job.get("url", ""))
        if ingest_to_tracker(job, score):
            added += 1

    top = scored[:MAX_JOBS_PER_NOTIFICATION]
    now = datetime.now().strftime("%b %d, %I:%M %p")
    lines = [
        f"💼 *Job Digest — {now}*",
        f"_{len(new_jobs)} new listing{'s' if len(new_jobs) != 1 else ''}, "
        f"top {len(top)} shown_\n",
    ]

    for job, score in top:
        icon = "🔥" if score >= 50 else "⭐" if score >= 30 else "📌"
        company = f" @ {job['company']}" if job["company"] else ""
        loc = f" · {job['location']}" if job["location"] else ""
        lines.append(f"{icon} *{job['role']}*{company}{loc}")
        lines.append(f"  [{job['source']}]({job['url']})\n")

    if added:
        lines.append(
            f"_✅ {added} high-match job{'s' if added != 1 else ''} "
            f"added to your tracker_"
        )

    send_telegram("\n".join(lines))
    send_email(scored, len(new_jobs), added)
    log.info(f"Sent digest: {len(top)} shown, {added} auto-added to tracker")

    # Log this run to tracker.db (best-effort — do not crash if table absent)
    import sqlite3 as _sqlite3
    _db_path = Path(__file__).parent.parent / "data" / "tracker.db"
    if _db_path.exists():
        try:
            with _sqlite3.connect(str(_db_path)) as _conn:
                _conn.execute(
                    "INSERT OR IGNORE INTO scraper_runs (query_count, jobs_found) VALUES (?, ?)",
                    (len(active_queries), len(all_jobs)),
                )
        except Exception as _e:
            log.warning("Could not log scraper run: %s", _e)


if __name__ == "__main__":
    main()

# job-hunter — Vision & North Star

_Last updated: 2026-02-20_

---

## What It Is

**job-hunter** is a self-hostable job hunting toolkit. It scrapes job listings from multiple sources, scores them against your background and location, filters out the noise, and tracks your pipeline from first look to offer.

It runs on your own hardware. Your data stays on your machine. It gets smarter the more you use it.

---

## Who It's For

Individuals running a targeted job search — especially people with a specific skill set in a specific city who are tired of wading through irrelevant listings. It's built for the person who wants automation without paying for a SaaS and without handing their job search data to a third party.

You supply your own API keys. You tune your own keywords. You own the results.

---

## Core Principles

1. **Privacy-first** — no cloud database, no third-party tracking, runs entirely on your own server
2. **Self-hostable** — one config file, one command, running
3. **Learns from feedback** — the more you dismiss and flag, the less noise you see
4. **Transparent** — nothing is silently dropped; filtered jobs are always logged for review
5. **Composable** — scraper, tracker, and filter are independent layers; use what you need

---

## Current Capabilities

- **Scraping**: LinkedIn (guest API) + JSearch/RapidAPI (aggregates Indeed, ZipRecruiter, Glassdoor, Google for Jobs)
- **Scoring**: keyword relevance (role titles, skills) + location preference (commute-weighted)
- **Notifications**: Telegram digest (top N) + email digest (all scored results) sent daily at 6am
- **Pipeline tracker**: web UI — Watchlist → Applied → Phone Screen → Interview → Offer
- **Sources tab**: review all scraped jobs, manually add to pipeline, dismiss irrelevant ones
- **Auto-add**: high-scoring jobs automatically added to Watchlist in the tracker

---

## Near-Term Roadmap

### Phase 1 — Smart Filtering (next)
- Negative keyword list (`filters/negative_keywords.json`) — hard-exclude irrelevant professions
- Dismissed roles feedback loop — "Not Relevant" button in tracker writes to `filters/dismissed_roles.json`
- Positive keyword override — if a job matches both negative and positive keywords, it passes ("tie goes to the runner")
- All filtered jobs logged to `filters/filtered.jsonl` for false positive review

### Phase 2 — AI Pre-filter
- Optional AI pass (Jez / Gemini Flash) over incoming batch
- Uses dismissed roles + negative keywords as context
- Flags additional irrelevant listings before notifications go out
- Cost decreases over time as the keyword lists mature

### Phase 3 — Packaging
- Single `docker-compose.yml` — one command to run everything
- Clean `.env.example` with all required keys documented
- Pluggable sources — add/remove scrapers without touching core logic
- Configurable notification targets (Telegram, email, both, neither)

### Phase 4 — Multi-user / Distribution
- Per-user keyword profiles
- Shareable config templates (e.g. "Vancouver IT support" starter config)
- Proper install/setup docs for non-technical users

---

## What It Is NOT

- Not a job board
- Not a recruiter tool
- Not a SaaS — there is no hosted version
- Not a replacement for actually applying — it finds and tracks, you do the work
- Not a one-size-fits-all tool — it's built to be tuned for your specific search

---

## Architecture

```
scraper/        — fetch, score, filter, notify (runs via cron)
tracker/        — Flask web app: pipeline management + sources review
data/           — SQLite databases (scraper.db, jobs.db)
filters/        — feedback data (negative_keywords.json, dismissed_roles.json, filtered.jsonl)
logs/           — execution logs
```

Scraper and tracker communicate over a local HTTP API. The filter layer sits between scoring and notification — jobs are filtered before they reach your inbox.

---

## The Bigger Picture

Most job hunters use a spreadsheet and a lot of browser tabs. job-hunter replaces both — automated discovery on one end, structured pipeline on the other, with a feedback loop that makes the signal better over time.

If it works well for one person, it can work for anyone running a targeted search. The goal is eventually a clean, documented package that someone can clone, fill in their `.env`, and have running in under 10 minutes.

That's the north star.

# job-hunter

Self-hostable job hunting toolkit. Scrapes listings, scores them, filters the noise, tracks your pipeline.

---

## Quick Start

**With Docker (recommended):**
```bash
git clone <repo> job-hunter
cd job-hunter
cp .env.example .env
# Fill in your keys — see Environment Variables below
docker compose up -d
# Tracker available at http://localhost:5002
```

**Without Docker:**
```bash
git clone <repo> job-hunter
cd job-hunter
cp .env.example .env
pip install -r scraper/requirements.txt
pip install -r tracker/requirements.txt
python tracker/app.py &        # starts tracker at http://localhost:5002
# Add scraper to cron (see Cron Setup below)
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values.

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_TOKEN` | Yes | Telegram bot token from @BotFather |
| `ALLOWED_CHAT_ID` | Yes | Your Telegram chat ID |
| `GMAIL_USER` | Yes | Gmail address used to send digests |
| `GMAIL_APP_PASSWORD` | Yes | Gmail app-specific password (not your account password) |
| `EMAIL_RECIPIENTS` | Yes | Comma-separated list of email addresses to receive digests |
| `JSEARCH_API_KEY` | Optional | RapidAPI key for JSearch (aggregates Indeed, ZipRecruiter, etc.) |

---

## How It Works

```
[cron @ 6am]
     │
     ▼
scraper/main.py
  ├── fetch_linkedin()    — LinkedIn guest API
  ├── fetch_jsearch()     — JSearch / RapidAPI
  ├── score_job()         — keyword + location scoring
  ├── filter_job()        — negative keywords + dismissed roles
  ├── ingest_to_tracker() — POST to tracker API
  ├── send_telegram()     — top N results to Telegram
  └── send_email()        — all scored results to email list

[always running]
     │
     ▼
tracker/app.py  →  http://localhost:5002
  ├── Pipeline tab   — Watchlist → Applied → Interview → Offer
  └── Sources tab    — Review scraped jobs, add to pipeline, dismiss irrelevant
```

---

## Tuning Your Search

### Search Queries (`scraper/config.py`)

Edit `SEARCH_QUERIES` to match your target roles and location:

```python
SEARCH_QUERIES = [
    "IT support technician [Your City]",
    "help desk [Your City]",
]
```

Keep queries targeted. Each query = 1 JSearch API request per day.

### Keyword Scoring (`scraper/config.py`)

`KEYWORDS` — role titles and skills from your background, with weights (higher = more relevant).
`LOCATION_SCORES` — locations weighted by commute preference.
`AUTO_ADD_THRESHOLD` — jobs scoring above this are auto-added to your Watchlist.

### Filtering (`filters/`)

`negative_keywords.json` — list of terms that disqualify a job (e.g. "accountant", "physician").
`dismissed_roles.json` — populated automatically when you dismiss jobs in the Sources tab.

Positive keyword override: if a job matches a negative keyword but *also* matches a keyword in your `KEYWORDS` list, it passes through and is flagged for manual review. Tie goes to the runner.

---

## Cron Setup

Add to crontab (`crontab -e`):

```
0 6 * * * /home/<you>/dev/job-hunter/scraper/venv/bin/python /home/<you>/dev/job-hunter/scraper/main.py >> /home/<you>/dev/job-hunter/logs/finder.log 2>&1
```

---

## Tracker Service (systemd)

To run the tracker as a persistent service, see your system's service configuration.
The tracker runs on port `5002` by default.

---

## Data

All data lives in `data/`:

| File | Contents |
|---|---|
| `data/scraper.db` | Seen job IDs (prevents duplicate notifications) |
| `data/jobs.db` | Full pipeline + scraped sources |

Both are SQLite databases. Back them up periodically.

CSV exports are triggered from the tracker UI and download directly to your browser.

---

## Project Structure

```
job-hunter/
├── VISION.md              — What this is and where it's going
├── README.md              — This file
├── .env                   — Your secrets (gitignored)
├── .env.example           — Template
├── scraper/               — Job fetching, scoring, filtering, notifications
├── tracker/               — Web UI for pipeline management
├── data/                  — SQLite databases
├── filters/               — Feedback data for smart filtering
└── logs/                  — Scraper execution logs
```

---

## Docker

`docker compose up -d` starts both services:
- **tracker** — web UI on port 5002
- **scheduler** — runs the scraper on the cron schedule defined in `scheduler/crontab`

Both containers share the `data/` and `filters/` directories via volume mounts, so the scraper and tracker stay in sync.

---

## Acknowledgements

Built for a personal job search. Designed to be reusable — swap in your own roles, city, and keywords.

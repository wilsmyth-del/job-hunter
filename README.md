# job-hunter

Self-hostable job hunting toolkit. Scrapes listings, filters the noise, and tracks your pipeline.

> **Status:** This original single-user toolkit is retained as a reference. Active hosted development moved to [job-hunter-portal](https://github.com/wilsmyth-del/job-hunter-portal).

---

## Quick Start

**With Docker (recommended):**
```bash
git clone https://github.com/wilsmyth-del/job-hunter.git
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
| `JSEARCH_API_KEY` | Optional | RapidAPI key for JSearch — see below |
| `TELEGRAM_TOKEN` | Optional | Telegram bot token from @BotFather |
| `ALLOWED_CHAT_ID` | Optional | Your Telegram chat ID |
| `GMAIL_USER` | Optional | Gmail address used to send digests |
| `GMAIL_APP_PASSWORD` | Optional | Gmail app-specific password (Settings → Security → App passwords) |
| `EMAIL_RECIPIENTS` | Optional | Comma-separated list of email addresses to receive digests |

Notifications are optional — the scraper and tracker work without any of them. Skip what you don't need.

---

## Getting a JSearch API Key

JSearch aggregates listings from Indeed, ZipRecruiter, Glassdoor, and others. Without it, the scraper falls back to LinkedIn only.

1. Go to [rapidapi.com](https://rapidapi.com) and create a free account
2. Search for **JSearch** and subscribe to the free plan — **200 requests/month** at no cost
3. Copy your RapidAPI key — paste it into the **Settings tab** in the tracker, or add it to `.env` as `JSEARCH_API_KEY`

200 requests = 200 daily scraper runs, which is more than enough for a job search. Each search query counts as one request per day, so keep your query list to 5–6 targeted searches.

---

## Notifications

Both notification methods are optional. You can use one, both, or neither.

### Telegram (optional)

Sends your top job matches to a Telegram chat each morning.

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts — you'll get a bot token
3. Message your new bot, then visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` to find your chat ID
4. Add both to `.env` as `TELEGRAM_TOKEN` and `ALLOWED_CHAT_ID`

### Email digest (optional)

Sends a daily digest of all scored jobs to one or more email addresses.

1. Use a Gmail account (or create one for job search use)
2. Enable 2FA, then go to **Settings → Security → App passwords** and generate one
3. Add to `.env` as `GMAIL_USER`, `GMAIL_APP_PASSWORD`, and `EMAIL_RECIPIENTS`

> Slack support is not currently built in. PRs welcome.

---

## How It Works

```
[cron @ 6am]
     │
     ▼
scraper/main.py
  ├── fetch_linkedin()    — LinkedIn guest API
  ├── fetch_jsearch()     — JSearch / RapidAPI
  ├── filter_job()        — negative keywords + dismissed roles
  ├── ingest_to_tracker() — POST to tracker API
  ├── send_telegram()     — top N results to Telegram
  └── send_email()        — daily digest to email list

[always running]
     │
     ▼
tracker/app.py  →  http://localhost:5002
  ├── Pipeline tab   — Watchlist → Applied → Interview → Offer
  ├── Sources tab    — Review scraped jobs, add to pipeline, dismiss irrelevant
  └── Settings tab   — Configure queries, API key, run scraper on demand
```

---

## Tuning Your Search

### Search Queries

The easiest way to configure queries is through the **Settings tab** in the tracker UI — no file editing needed. You can set your search terms, LinkedIn location, and JSearch API key there, and trigger a manual run with the **Run Now** button.

Alternatively, edit `scraper/config.py` directly:

```python
SEARCH_QUERIES = [
    "IT support technician [Your City]",
    "help desk [Your City]",
]
LINKEDIN_LOCATION = "Your City, Province/State"
```

Keep queries targeted. Each query = 1 JSearch API request per day (free tier: 200/month).

### Filtering (`filters/`)

`negative_keywords.json` — list of terms that disqualify a job (e.g. "accountant", "physician").
`dismissed_roles.json` — populated automatically when you dismiss jobs in the Sources tab.

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

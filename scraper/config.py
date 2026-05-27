# Search queries — customize these to match your target roles and location.
# Each query costs 1 JSearch API call per day, so keep the list focused.
SEARCH_QUERIES = [
    "IT support specialist OR help desk analyst [Your City, Province/State]",
    "desktop support analyst OR service desk analyst [Your City, Province/State]",
    "IT manager OR infrastructure manager [Your City, Province/State]",
]

# Location passed to the LinkedIn guest API — set to your city and region.
# Example: "Vancouver, BC" or "Toronto, ON" or "Seattle, WA"
LINKEDIN_LOCATION = "Your City, Province/State"

# Keyword scoring — matched against job title + description.
# Add terms from your target roles and resume. Higher score = more relevant.
KEYWORDS = {
    # Target role titles
    "IT support": 15,
    "help desk": 15,
    "helpdesk": 15,
    "service desk": 15,
    "technical support": 12,
    "desktop support": 12,
    "IT specialist": 12,
    "IT analyst": 10,
    "IT technician": 12,
    "systems administrator": 8,
    "sysadmin": 8,
    "IT manager": 15,
    "IT operations manager": 15,
    "infrastructure manager": 15,
    # Skills from your resume — customize these
    "ITSM": 6,
    "incident management": 6,
    "ITIL": 6,
    "Jira": 5,
    "ticketing": 5,
    "Windows": 4,
    "troubleshooting": 3,
    # Availability match
    "contract": 3,
    "temporary": 3,
    "remote": 5,
    "hybrid": 4,
}

# Location scoring — boost jobs close to you, down-weight long commutes.
# Score is added on top of keyword score. Cap at 20.
# Replace these with your own city, neighbourhoods, and commute preferences.
LOCATION_SCORES = {
    # Home area — highest priority
    "your city": 20,
    # Nearby — good commute
    "nearby city": 14,
    # Remote / hybrid — always welcome
    "remote": 15,
    "work from home": 15,
    "wfh": 15,
    "hybrid": 12,
    # Further out — deprioritise
    "far city": 4,
}

# Minimum keyword score before location bonus is added.
# Prevents location inflating scores for completely irrelevant roles.
MIN_KEYWORD_SCORE = 8

# Publisher names returned by JSearch that should be dropped.
# These slip through the URL domain check because JSearch proxies their links.
BLOCKED_SOURCES = {
    "bebee",
    "jobrapido",
    "jooble",
    "talent.com",
    "neuvoo",
    "careerjet",
    "joblist",
    "snagajob",
    "simplyhired",
    "adzuna",
    "learn4good",
    "recruit.net",
    "trabajo.org",
    "talentify",
    "whatjobs",
    "hiring.zycto",
    "jobleads",
}

# Paygated / low-quality aggregators — jobs from these domains are dropped
# before they reach the tracker or email. Add new offenders here as needed.
BLOCKED_DOMAINS = {
    "bebee.com",
    "rapidojob.com",
    "jooble.org",
    "talent.com",
    "neuvoo.com",
    "jobrapido.com",
    "careerjet.ca",
    "careerjet.com",
    "joblist.com",
    "snagajob.com",
    "simplyhired.com",
    "simplyhired.ca",
    "adzuna.com",
    "adzuna.ca",
    "jobomas.com",
    "jobleads.com",
    "learn4good.com",
    "recruit.net",
}

# Jobs scoring this or above get auto-added to job tracker as Watchlist
AUTO_ADD_THRESHOLD = 35

# Max jobs shown per Telegram notification
MAX_JOBS_PER_NOTIFICATION = 8

# How many days back to search (1 = today only, 2 = safety buffer for weekends)
SEARCH_DAYS_BACK = 2

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

# Max jobs shown per Telegram notification
MAX_JOBS_PER_NOTIFICATION = 8

# How many days back to search (1 = today only, 2 = safety buffer for weekends)
SEARCH_DAYS_BACK = 2

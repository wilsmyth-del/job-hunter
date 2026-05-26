FROM python:3.11-slim

# supercronic — a cron replacement built for Docker containers.
# Unlike regular cron, it runs in the foreground, respects environment
# variables, and logs cleanly. Exactly what you want in a container.
ARG SUPERCRONIC_VERSION=v0.2.29
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64 \
    -o /usr/local/bin/supercronic && \
    chmod +x /usr/local/bin/supercronic && \
    apt-get purge -y curl && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install scraper dependencies
COPY scraper/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt requests

# Copy scraper code and crontab
COPY scraper/ scraper/
COPY filters/ filters/
COPY scheduler/crontab crontab

CMD ["supercronic", "/app/crontab"]

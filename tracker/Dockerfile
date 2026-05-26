FROM python:3.11-slim

WORKDIR /app/tracker

# Install dependencies
COPY tracker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy tracker source
COPY tracker/ .

EXPOSE 5002

CMD ["gunicorn", "-w", "2", "--timeout", "120", "-b", "0.0.0.0:5002", "app:create_app()"]

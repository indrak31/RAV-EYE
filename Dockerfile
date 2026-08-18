# Dockerfile — Traffic Violation backend API
#
# Build: docker build -t tv-backend .
# Run:   docker run -p 8000:8000 -e DATABASE_URL=... tv-backend

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (for psycopg2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install psycopg for Postgres support
RUN pip install --no-cache-dir "psycopg[binary]"

# Copy application code
COPY app ./app
COPY .env.example .env

# Create media directory
RUN mkdir -p /app/media

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
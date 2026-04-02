FROM python:3.11-slim

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.2

# Copy dependency files first (layer caching)
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main

# Copy source
COPY services/betting/ ./betting/

# Persistent data directories — mount these as volumes
RUN mkdir -p /data/db /data/csv_cache

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "betting"]

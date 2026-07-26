FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static files at build time (no db needed for this)
RUN python manage.py collectstatic --noinput

# Create appuser but do NOT switch to it here —
# entrypoint.sh needs root to chown the mounted volume first
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
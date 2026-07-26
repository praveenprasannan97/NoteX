#!/bin/sh
set -e

# Ensure the db directory exists and is writable by appuser
# This runs as root before we drop privileges
mkdir -p /app/db
chown -R appuser:appuser /app/db

echo "Running migrations..."
# Run migrate as appuser
su -s /bin/sh appuser -c "python manage.py migrate --noinput"

echo "Starting Gunicorn..."
exec su -s /bin/sh appuser -c "
    gunicorn notex.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 1 \
        --threads 1 \
        --timeout 60 \
        --access-logfile - \
        --error-logfile -
"
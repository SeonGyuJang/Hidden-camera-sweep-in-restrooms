#!/bin/sh
set -e

echo "Running DB migrations..."
flask db upgrade 2>/dev/null || flask db init && flask db migrate && flask db upgrade

echo "Seeding buildings..."
flask init-db 2>/dev/null || true

echo "Starting gunicorn..."
exec gunicorn app:app \
  --bind 0.0.0.0:8080 \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -

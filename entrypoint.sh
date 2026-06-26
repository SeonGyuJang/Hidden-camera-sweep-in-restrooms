#!/bin/sh
set -e

# Volume 마운트 디렉토리 확인
mkdir -p "${DATA_DIR:-/data}/photos"

echo "Running DB migrations..."
if flask db upgrade; then
  echo "Migrations applied."
else
  echo "Migration failed or no versions — falling back to create_all..."
  flask init-db
fi

echo "Seeding buildings..."
flask init-db 2>/dev/null || true

echo "Starting gunicorn..."
exec gunicorn app:app \
  --bind 0.0.0.0:8080 \
  --workers 1 \
  --timeout 120 \
  --limit-request-body 209715200 \
  --access-logfile - \
  --error-logfile -

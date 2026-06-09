#!/bin/sh
set -e

PORT="${PORT:-8000}"

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Running Alembic migrations..."
  alembic upgrade head
fi

echo "Starting uvicorn on 0.0.0.0:${PORT} ..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --workers "${UVICORN_WORKERS:-1}"

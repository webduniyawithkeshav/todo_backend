#!/bin/sh
set -e

# Wait for Postgres to be available using a small Python helper, then exec the passed command.
PYWAIT=/app/app/wait_for_db.py
if [ -f "$PYWAIT" ]; then
  echo "Waiting for database to be ready..."
  /usr/bin/env python3 "$PYWAIT"
else
  echo "wait_for_db helper not found, continuing without wait"
fi

if [ "$1" = 'pytest' ]; then
  exec pytest -q
else
  exec "$@"
fi

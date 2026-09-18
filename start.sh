#!/usr/bin/env bash
set -e

echo "--- Seeding database ---"
python database/seed_db.py

echo "--- Starting server ---"
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"

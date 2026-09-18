#!/usr/bin/env bash
set -e
echo "--- Starting Forensier backend ---"
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"

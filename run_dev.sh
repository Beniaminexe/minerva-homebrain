#!/usr/bin/env bash
set -e

# Activate venv if present
if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
EOF
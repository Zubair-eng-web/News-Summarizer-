#!/usr/bin/env bash
# One-command setup (Linux/Mac). Docker ki zaroorat nahi.
set -e
cd "$(dirname "$0")/.."
[ -d venv ] || python3 -m venv venv
venv/bin/python -m pip install --upgrade pip
venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env ban gayi: ab usme GEMINI_API_KEY waghera bharein"
fi
venv/bin/python -m app.core.migrate
venv/bin/python -m pytest tests -q
echo "Setup mukammal. API: uvicorn app.main:app --reload"
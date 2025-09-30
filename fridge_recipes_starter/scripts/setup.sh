#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements_mongo.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ">> Created .env – fill in MONGODB_URI then run: ./scripts/seed.sh ./test.xlsx"
else
  echo ">> .env already exists."
fi

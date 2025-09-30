#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
EXCEL_PATH="${1:-./test.xlsx}"
if [ ! -f "$EXCEL_PATH" ]; then
  echo "File not found: $EXCEL_PATH"
  exit 1
fi
python -m etl.load_recipes_mongo "$EXCEL_PATH"

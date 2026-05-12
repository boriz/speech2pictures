#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--fix" ]]; then
  source ./activate_venv.sh
  python3 -m ruff check --fix .
  python3 -m ruff format .
  python3 -m ruff check .
  exit 0
fi

source ./activate_venv.sh
python3 -m ruff check .

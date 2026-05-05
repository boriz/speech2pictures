#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "--fix" ]]; then
  npm run lint:js:fix
  npm run lint:js
  exit 0
fi

npm run lint:js

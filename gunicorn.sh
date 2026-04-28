#!/usr/bin/env bash
set -euo pipefail

repo_root="$(
    cd "$(dirname "$0")" && pwd
)"

echo "gunicorn.sh is deprecated."
echo "Use ./run_app.sh after 'source ./activate_venv.sh'."
echo "Launching the canonical app startup path now."

exec "${repo_root}/run_app.sh" "$@"

#!/usr/bin/env bash
set -euo pipefail

repo_root="$(
    cd "$(dirname "$0")" && pwd
)"
activate_script="${repo_root}/activate_venv.sh"

if [[ ! -f "${activate_script}" ]]; then
    echo "Activation script not found at ${activate_script}" >&2
    exit 1
fi

cd "${repo_root}"

# shellcheck disable=SC1090
source "${activate_script}"

host="${FLASK_RUN_HOST:-0.0.0.0}"
port="${FLASK_RUN_PORT:-5000}"

exec python3 -m flask --app app run \
    --host "${host}" \
    --port "${port}" \
    "$@"

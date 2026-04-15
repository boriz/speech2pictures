#!/usr/bin/env bash
set -euo pipefail

repo_root="$(
    cd "$(dirname "$0")" && pwd
)"
venv_python="${repo_root}/venv/bin/python3"

if [[ ! -x "${venv_python}" ]]; then
    echo "Python executable not found in ${repo_root}/venv" >&2
    exit 1
fi

cd "${repo_root}"

host="${FLASK_RUN_HOST:-0.0.0.0}"
port="${FLASK_RUN_PORT:-5000}"

exec "${venv_python}" -m flask --app app run \
    --host "${host}" \
    --port "${port}" \
    "$@"

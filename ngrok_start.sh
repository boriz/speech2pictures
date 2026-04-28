#!/usr/bin/env bash
set -euo pipefail

repo_root="$(
    cd "$(dirname "$0")" && pwd
)"

cat <<'EOF'
ngrok_start.sh is deprecated.
Use ./run_app.sh to start the app.
If you need ngrok, start it manually in another shell after the app is up.
EOF

echo "Repo root: ${repo_root}"
echo "Example:"
echo "  source ./activate_venv.sh"
echo "  ./run_app.sh"
echo "  ngrok http 5000"

exit 1

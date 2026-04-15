#!/usr/bin/env bash

# Source this file from bash to activate the repo-local virtualenv.

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Use: source ./activate_venv.sh"
    exit 1
fi

_speech2pictures_root="$(
    cd "$(dirname "${BASH_SOURCE[0]}")" && pwd
)"
_speech2pictures_venv="${_speech2pictures_root}/venv"

if [[ ! -x "${_speech2pictures_venv}/bin/python3" ]]; then
    echo "Virtualenv not found at ${_speech2pictures_venv}" >&2
    return 1
fi

export VIRTUAL_ENV="${_speech2pictures_venv}"
export PATH="${VIRTUAL_ENV}/bin:${PATH}"
unset PYTHONHOME

hash -r 2>/dev/null || true

echo "Activated virtualenv: ${VIRTUAL_ENV}"

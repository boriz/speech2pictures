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

if [[ ! -f "${_speech2pictures_venv}/bin/activate" ]]; then
    echo "Virtualenv not found at ${_speech2pictures_venv}" >&2
    return 1
fi

_speech2pictures_original_path="${PATH}"

# shellcheck disable=SC1090
source "${_speech2pictures_venv}/bin/activate"

# The generated venv activator contains an absolute path from when the
# environment was created. Force the current repo-local path here so the
# wrapper still activates the right environment if the repo directory was
# renamed.
export VIRTUAL_ENV="${_speech2pictures_venv}"
export PATH="${VIRTUAL_ENV}/bin:${_speech2pictures_original_path}"
unset PYTHONHOME

if [[ -d "/usr/lib/wsl/drivers" ]]; then
    _speech2pictures_cuda_driver_lib="$(
        ls -1dt /usr/lib/wsl/drivers/*/libcuda.so.1.1 2>/dev/null | head -n 1
    )"
    _speech2pictures_cuda_driver_dir=""
    if [[ -n "${_speech2pictures_cuda_driver_lib}" ]]; then
        _speech2pictures_cuda_driver_dir="$(
            dirname "${_speech2pictures_cuda_driver_lib}"
        )"
    fi
    _speech2pictures_cuda_lib_path="/usr/lib/wsl/lib"
    if [[ -n "${_speech2pictures_cuda_driver_dir}" ]]; then
        export LD_LIBRARY_PATH="${_speech2pictures_cuda_lib_path}:${_speech2pictures_cuda_driver_dir}:${LD_LIBRARY_PATH:-}"
    elif [[ -d "${_speech2pictures_cuda_lib_path}" ]]; then
        export LD_LIBRARY_PATH="${_speech2pictures_cuda_lib_path}:${LD_LIBRARY_PATH:-}"
    fi
fi

hash -r 2>/dev/null || true

echo "Activated virtualenv: ${VIRTUAL_ENV}"

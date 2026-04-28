#!/usr/bin/env bash
set -euo pipefail

cuda_lib_dir="/usr/lib/wsl/lib"
driver_lib_glob="/usr/lib/wsl/drivers/*/libcuda.so.1.1"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run with sudo: sudo ./fix_cuda.sh" >&2
    exit 1
fi

if [[ ! -d "${cuda_lib_dir}" ]]; then
    echo "WSL CUDA library directory not found: ${cuda_lib_dir}" >&2
    exit 1
fi

mapfile -t driver_lib_candidates < <(
    ls -1t ${driver_lib_glob} 2>/dev/null || true
)

if [[ "${#driver_lib_candidates[@]}" -eq 0 ]]; then
    echo "No driver CUDA libraries found matching ${driver_lib_glob}" >&2
    exit 1
fi

target_lib="${driver_lib_candidates[0]}"

cd "${cuda_lib_dir}"

rm -f libcuda.so libcuda.so.1 libcuda.so.1.1
ln -s "${target_lib}" libcuda.so.1.1
ln -s libcuda.so.1.1 libcuda.so.1
ln -s libcuda.so.1.1 libcuda.so
ldconfig

echo "Updated WSL CUDA symlinks in ${cuda_lib_dir}"
echo "libcuda.so.1.1 -> ${target_lib}"
echo "libcuda.so.1 -> libcuda.so.1.1"
echo "libcuda.so -> libcuda.so.1.1"

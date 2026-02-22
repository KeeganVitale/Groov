#!/usr/bin/env bash
set -euo pipefail

if ! command -v appimage-builder >/dev/null 2>&1; then
  echo "appimage-builder is required. Install it first:"
  echo "  python3 -m pip install --user appimage-builder"
  exit 1
fi

host_arch="$(uname -m)"
if [[ "$host_arch" != "aarch64" && "${GROOV_SKIP_ARCH_CHECK:-0}" != "1" ]]; then
  echo "This recipe targets aarch64 and should be run on an aarch64 host (Raspberry Pi 64-bit)."
  echo "Current host architecture: $host_arch"
  echo "If you intentionally set up full emulation, rerun with GROOV_SKIP_ARCH_CHECK=1."
  exit 1
fi

cd "$(dirname "$0")/.."
export PATH="$PWD/appimage/bin:$PATH"
appimage-builder --recipe appimage/AppImageBuilder.aarch64.yml --skip-test

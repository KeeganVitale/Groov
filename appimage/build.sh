#!/usr/bin/env bash
set -euo pipefail

if ! command -v appimage-builder >/dev/null 2>&1; then
  echo "appimage-builder is required. Install it first:"
  echo "  python3 -m pip install --user appimage-builder"
  exit 1
fi

cd "$(dirname "$0")/.."
export PATH="$PWD/appimage/bin:$PATH"
appimage-builder --recipe appimage/AppImageBuilder.yml --skip-test

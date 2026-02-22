#!/usr/bin/env bash
set -euo pipefail

APPDIR="${APPDIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

PYTHON_BIN="$APPDIR/usr/bin/python3"
SITE_DIR="$APPDIR/usr/lib/python3/dist-packages"
APP_ROOT="$APPDIR/usr/share/groov"
PYSIDE_ROOT="$SITE_DIR/PySide6/Qt"

export PYTHONNOUSERSITE=1
export PYTHONPATH="$SITE_DIR:$APP_ROOT"
export GI_TYPELIB_PATH="$APPDIR/usr/lib/x86_64-linux-gnu/girepository-1.0:$APPDIR/usr/lib/girepository-1.0:${GI_TYPELIB_PATH:-}"
export GST_PLUGIN_PATH="$APPDIR/usr/lib/x86_64-linux-gnu/gstreamer-1.0:$APPDIR/usr/lib/gstreamer-1.0"
export GST_PLUGIN_SYSTEM_PATH_1_0="$GST_PLUGIN_PATH"
export LD_LIBRARY_PATH="$APPDIR/usr/lib/x86_64-linux-gnu:$APPDIR/usr/lib:${LD_LIBRARY_PATH:-}"
export QT_PLUGIN_PATH="$PYSIDE_ROOT/plugins"
export QML2_IMPORT_PATH="$PYSIDE_ROOT/qml"

exec "$PYTHON_BIN" -m package.main "$@"

#!/bin/bash
# Installs a self-contained Python environment inside the packaged
# app bundle, so the double-clickable app has its backend without any
# npm/venv business. Run after `npm run package` (the make:app script
# does both).
#
# The venv is built with this machine's python3 and absolute paths,
# so the resulting .app is tied to machines with a compatible Python
# at the same location — fine for personal installs. True
# re-distributable builds would want PyInstaller instead.
set -euo pipefail

cd "$(dirname "$0")/.."

APP_DIR=$(find out -maxdepth 2 -name "*.app" -type d | head -1)
if [ -z "$APP_DIR" ]; then
  echo "No packaged .app found under out/ — run 'npm run package' first." >&2
  exit 1
fi

RESOURCES="$APP_DIR/Contents/Resources/app"
if [ ! -f "$RESOURCES/requirements.txt" ]; then
  echo "Unexpected bundle layout: $RESOURCES/requirements.txt missing." >&2
  exit 1
fi

echo "Installing Python environment into $APP_DIR ..."
python3 -m venv "$RESOURCES/.venv"
"$RESOURCES/.venv/bin/pip" install --quiet --upgrade pip
"$RESOURCES/.venv/bin/pip" install --quiet -r "$RESOURCES/requirements.txt"

echo "Verifying the bundled backend can boot ..."
RES="$RESOURCES" "$RESOURCES/.venv/bin/python3" -c "
import sys, os
sys.path.insert(0, os.environ['RES'])
os.chdir(os.environ['RES'])
from backend.app import create_app  # imports the whole dependency tree
print('backend imports OK')
"

echo "Done: $APP_DIR"

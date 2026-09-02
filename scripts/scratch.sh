#!/bin/bash
# Launch the app against a THROWAWAY database — fresh on every run —
# on its own port (5679), so it can run right alongside the real app.
# For testing first-run behavior (onboarding) and risk-free
# experiments; nothing here can touch the real data in
# ~/Library/Application Support/TarotJournal.
#
# Usage:  npm run scratch
# Keep the scratch data between runs instead:  KEEP_SCRATCH=1 npm run scratch
set -euo pipefail

cd "$(dirname "$0")/.."

SCRATCH="$HOME/.tarot-journal-scratch"
if [ "${KEEP_SCRATCH:-}" != "1" ]; then
  rm -rf "$SCRATCH"
fi
mkdir -p "$SCRATCH"

npm run build:frontend

echo "Scratch instance: data in $SCRATCH, port 5679"
FLASK_PORT=5679 TAROT_JOURNAL_DATA_DIR="$SCRATCH" npx electron .

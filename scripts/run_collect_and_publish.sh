#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TOKEN_FILE="$HOME/.agri-info-hub/github.env"

cd "$ROOT_DIR"

/usr/bin/python3 collector.py --once

if [[ -f "$TOKEN_FILE" ]]; then
  /usr/bin/python3 publisher.py --token-file "$TOKEN_FILE" --message "Update agriculture data"
else
  echo "Skipping GitHub publish: missing $TOKEN_FILE"
fi

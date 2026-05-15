#!/bin/zsh
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$HOME/Library/Application Support/AgriInfoHub"
PORT="${1:-4173}"

if [[ -d "$APP_DIR/web" && -d "$APP_DIR/data" ]]; then
  cd "$APP_DIR"
else
  cd "$SOURCE_DIR"
fi

/usr/bin/python3 -m http.server "$PORT"

#!/bin/zsh
set -euo pipefail

LABEL="com.agri-info-hub.collector"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
USER_DOMAIN="gui/$(id -u)"

if launchctl print "${USER_DOMAIN}/${LABEL}" >/dev/null 2>&1; then
  launchctl bootout "$USER_DOMAIN" "$PLIST_PATH" >/dev/null 2>&1 || true
fi

rm -f "$PLIST_PATH"

echo "Uninstalled ${LABEL}"

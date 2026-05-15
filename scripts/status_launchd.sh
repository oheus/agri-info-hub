#!/bin/zsh
set -euo pipefail

APP_DIR="$HOME/Library/Application Support/AgriInfoHub"
LABEL="com.agri-info-hub.collector"
USER_DOMAIN="gui/$(id -u)"

echo "LaunchAgent status: ${USER_DOMAIN}/${LABEL}"
if launchctl print "${USER_DOMAIN}/${LABEL}" >/dev/null 2>&1; then
  launchctl print "${USER_DOMAIN}/${LABEL}" | sed -n '1,80p'
else
  echo "Not installed or not loaded."
fi

echo ""
echo "Latest collector output:"
if [[ -f "$APP_DIR/logs/collector.out.log" ]]; then
  tail -n 20 "$APP_DIR/logs/collector.out.log"
else
  echo "No stdout log yet."
fi

echo ""
echo "Latest collector errors:"
if [[ -f "$APP_DIR/logs/collector.err.log" ]]; then
  tail -n 20 "$APP_DIR/logs/collector.err.log"
else
  echo "No stderr log yet."
fi

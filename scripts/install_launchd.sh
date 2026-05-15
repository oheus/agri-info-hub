#!/bin/zsh
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$HOME/Library/Application Support/AgriInfoHub"
LABEL="com.agri-info-hub.collector"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
USER_DOMAIN="gui/$(id -u)"

INTERVAL_SECONDS="$(cd "$SOURCE_DIR" && /usr/bin/python3 -c 'import json; print(int(json.load(open("config.json", encoding="utf-8"))["collection_interval_minutes"]) * 60)')"

mkdir -p "$APP_DIR/data" "$APP_DIR/web" "$APP_DIR/logs"
mkdir -p "$HOME/Library/LaunchAgents"

/bin/cp "$SOURCE_DIR/collector.py" "$APP_DIR/collector.py"
/bin/cp "$SOURCE_DIR/config.json" "$APP_DIR/config.json"
/usr/bin/ditto "$SOURCE_DIR/web" "$APP_DIR/web"

if [[ ! -f "$APP_DIR/data/agri_items.sqlite3" && -f "$SOURCE_DIR/data/agri_items.sqlite3" ]]; then
  /bin/cp "$SOURCE_DIR/data/agri_items.sqlite3" "$APP_DIR/data/agri_items.sqlite3"
fi

if [[ ! -f "$APP_DIR/data/items.json" && -f "$SOURCE_DIR/data/items.json" ]]; then
  /bin/cp "$SOURCE_DIR/data/items.json" "$APP_DIR/data/items.json"
fi

if [[ ! -f "$APP_DIR/data/summary.json" && -f "$SOURCE_DIR/data/summary.json" ]]; then
  /bin/cp "$SOURCE_DIR/data/summary.json" "$APP_DIR/data/summary.json"
fi

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${LABEL}</string>

    <key>ProgramArguments</key>
    <array>
      <string>/usr/bin/python3</string>
      <string>${APP_DIR}/collector.py</string>
      <string>--once</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${APP_DIR}</string>

    <key>RunAtLoad</key>
    <true/>

    <key>StartInterval</key>
    <integer>${INTERVAL_SECONDS}</integer>

    <key>StandardOutPath</key>
    <string>${APP_DIR}/logs/collector.out.log</string>

    <key>StandardErrorPath</key>
    <string>${APP_DIR}/logs/collector.err.log</string>
  </dict>
</plist>
PLIST

if launchctl print "${USER_DOMAIN}/${LABEL}" >/dev/null 2>&1; then
  launchctl bootout "$USER_DOMAIN" "$PLIST_PATH" >/dev/null 2>&1 || true
fi

launchctl bootstrap "$USER_DOMAIN" "$PLIST_PATH"
launchctl enable "${USER_DOMAIN}/${LABEL}"
launchctl kickstart -k "${USER_DOMAIN}/${LABEL}"

echo "Installed ${LABEL}"
echo "Interval: ${INTERVAL_SECONDS}s"
echo "Runtime: ${APP_DIR}"
echo "Plist: ${PLIST_PATH}"
echo "Logs: ${APP_DIR}/logs"

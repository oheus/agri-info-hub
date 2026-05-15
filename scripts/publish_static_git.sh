#!/bin/zsh
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MESSAGE="${1:-Update public agriculture data}"

cd "$SOURCE_DIR"

if [[ ! -d .git ]]; then
  git init
fi

./scripts/build_static_site.sh

git add \
  .gitignore \
  README.md \
  collector.py \
  config.json \
  launchd \
  scripts \
  web \
  public \
  data/items.json \
  data/summary.json

if git diff --cached --quiet; then
  echo "No changes to commit."
else
  git commit -m "$MESSAGE"
fi

echo "Ready to push. Add a remote once, then run:"
echo "  git push -u origin main"

#!/bin/zsh
set -euo pipefail

CONFIG_DIR="$HOME/.agri-info-hub"
TOKEN_FILE="$CONFIG_DIR/github.env"

mkdir -p "$CONFIG_DIR"
chmod 700 "$CONFIG_DIR"

echo "Paste a GitHub fine-grained token with Contents: Read and write for oheus/agri-info-hub."
echo "Input is hidden. Press Enter after pasting."
printf "GITHUB_TOKEN: "
stty -echo
read -r TOKEN
stty echo
printf "\n"

if [[ -z "$TOKEN" ]]; then
  echo "No token entered."
  exit 1
fi

cat > "$TOKEN_FILE" <<EOF
GITHUB_TOKEN=$TOKEN
GITHUB_REPOSITORY=oheus/agri-info-hub
GITHUB_BRANCH=main
EOF

chmod 600 "$TOKEN_FILE"
echo "Saved token config to $TOKEN_FILE"

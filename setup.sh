#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

python_cmd=""
if need_cmd python3; then
  python_cmd="python3"
elif need_cmd python; then
  python_cmd="python"
else
  echo "Python is required but was not found on PATH."
  exit 1
fi

if ! need_cmd node; then
  echo "Node.js is required but was not found on PATH."
  exit 1
fi

if ! need_cmd npm; then
  echo "npm is required but was not found on PATH."
  exit 1
fi

echo "Installing Python dependencies..."
"$python_cmd" -m pip install -r "$ROOT_DIR/services/downloader/requirements.txt"

node_modules_path="$ROOT_DIR/apps/desktop/node_modules"
if [[ -d "$node_modules_path" ]]; then
  read -r -p "Remove existing node_modules to reduce size? (y/N) " clean_answer
  if [[ "$clean_answer" == "y" || "$clean_answer" == "Y" ]]; then
    rm -rf "$node_modules_path"
  fi
fi

echo "Installing desktop dependencies..."
(
  cd "$ROOT_DIR/apps/desktop"
  npm install
)

if ! need_cmd ffmpeg; then
  echo "Warning: FFmpeg not found. MP3 extraction will fail without it."
fi

read -r -p "Start the app now? (y/N) " answer
if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
  (
    cd "$ROOT_DIR/apps/desktop"
    npm run dev
  )
else
  echo "Setup complete. Run the app later with: cd apps/desktop && npm run dev"
fi

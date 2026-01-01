#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="4545"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
COMPOSE_COOKIES_FILE="$ROOT_DIR/docker-compose.cookies.yml"

compose_args=(-f "$COMPOSE_FILE")

default_cookies_candidates=(
  "$ROOT_DIR/cookies.txt"
  "$ROOT_DIR/cookies"
)

read -r -p "Path to cookies.txt (leave blank to use ./cookies.txt or skip): " cookies_path
if [[ -z "$cookies_path" ]]; then
  for candidate in "${default_cookies_candidates[@]}"; do
    if [[ -f "$candidate" ]]; then
      cookies_path="$candidate"
      echo "Using default cookies at: $cookies_path"
      break
    fi
  done
fi
if [[ -n "$cookies_path" ]]; then
  if [[ ! -f "$cookies_path" ]]; then
    echo "cookies.txt not found at: $cookies_path"
    exit 1
  fi
  export YT_DLP_COOKIES_PATH="$cookies_path"
  compose_args+=(-f "$COMPOSE_COOKIES_FILE")
fi

echo "Stopping any previous Compose stack..."
docker compose "${compose_args[@]}" down --remove-orphans >/dev/null 2>&1 || true
docker rm -f yt-downloader-test >/dev/null 2>&1 || true

echo "Starting services with Docker Compose..."
docker compose "${compose_args[@]}" up -d --build

echo "Checking health endpoint..."
for i in {1..20}; do
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    echo "Health check OK."
    break
  fi
  sleep 0.5
done

if ! curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
  echo "Health check failed. Container logs:"
  docker compose "${compose_args[@]}" logs downloader
  exit 1
fi

read -r -p "Start the Electron app now? (y/N) " start_answer
if [[ "$start_answer" == "y" || "$start_answer" == "Y" ]]; then
  (
    cd "$ROOT_DIR/apps/desktop"
    YT_DOWNLOADER_API_URL="http://127.0.0.1:${PORT}" npm run dev
  )
fi

read -r -p "Stop and remove the containers now? (y/N) " answer
if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
  docker compose "${compose_args[@]}" down
  echo "Containers removed."
else
  echo "Containers left running."
fi

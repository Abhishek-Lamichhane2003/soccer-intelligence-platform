#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
if [ ! -f frontend/package-lock.json ]; then
  echo "Generating frontend/package-lock.json for reproducible installs..."
  docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$ROOT/frontend:/app" -w /app node:22-alpine npm install --package-lock-only --ignore-scripts --no-audit --no-fund
fi
exec docker compose up --build

#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend/pluto_duck_frontend"

pnpm --dir "$FRONTEND_DIR" dev --hostname 127.0.0.1 --port 3100


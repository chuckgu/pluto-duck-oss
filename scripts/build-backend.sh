#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "pyinstaller is not available in PATH" >&2
  exit 1
fi

pyinstaller pluto-duck-backend.spec --distpath dist --workpath build --clean


#!/bin/zsh
set -euo pipefail

echo "========================================="
echo "Pluto Duck - Local Build Script"
echo "========================================="
echo ""

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Activate virtual environment
if [ -f "$ROOT_DIR/.venv/bin/activate" ]; then
  echo "Activating Python virtual environment..."
  source "$ROOT_DIR/.venv/bin/activate"
fi

# Step 1: Build Backend
echo "Step 1/3: Building backend with PyInstaller..."
echo "-----------------------------------------"
./scripts/build-backend.sh
echo "✓ Backend build complete"
echo ""

# Step 2: Build Frontend
echo "Step 2/3: Building frontend with Next.js..."
echo "-----------------------------------------"
cd "$ROOT_DIR/frontend/pluto_duck_frontend"
pnpm install
pnpm build
echo "✓ Frontend build complete"
echo ""

# Step 3: Build Tauri App
echo "Step 3/3: Building Tauri app..."
echo "-----------------------------------------"
cd "$ROOT_DIR/tauri-shell"
cargo tauri build
echo "✓ Tauri build complete"
echo ""

echo "========================================="
echo "Build Complete!"
echo "========================================="
echo ""
echo "Your .app file is located at:"
echo "$ROOT_DIR/tauri-shell/src-tauri/target/release/bundle/macos/Pluto Duck.app"
echo ""
echo "To run it:"
echo "  open '$ROOT_DIR/tauri-shell/src-tauri/target/release/bundle/macos/Pluto Duck.app'"
echo ""


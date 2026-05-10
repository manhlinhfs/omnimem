#!/bin/bash
set -euo pipefail

# Resolve the repo root (this script lives at <repo>/scripts/setup.sh).
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
cd "$REPO_DIR"

VERSION=$(cat VERSION)
echo "=== OMNIMEM v$VERSION: The Universal RAG Core for CLI ==="
echo "Installing dependencies for Linux/macOS..."

# 1. Create Python Virtual Environment
echo "[1/4] Creating Python Virtual Environment (venv)..."
python3 -m venv venv
source venv/bin/activate

# 2. Install Dependencies
echo "[2/4] Installing dependencies (Kreuzberg, ChromaDB)..."
pip install -r requirements.txt > /dev/null 2>&1
pip install -e . > /dev/null 2>&1

echo "[3/4] Bootstrapping the local embedding model..."
if [ "${OMNIMEM_SKIP_MODEL_BOOTSTRAP:-0}" = "1" ]; then
  echo "Skipping model bootstrap because OMNIMEM_SKIP_MODEL_BOOTSTRAP=1"
else
  ./venv/bin/python3 -m omnimem.bootstrap || exit 1
fi

echo "[4/4] SETUP COMPLETE!"
echo ""
echo "OmniMem is ready. Wire it into your agent CLIs:"
echo "  ./scripts/omnimem quickstart"
echo ""
echo "Manual usage examples:"
echo "  ./scripts/omnimem import /path/to/document.pdf"
echo "  ./scripts/omnimem doctor"
echo "  ./scripts/omnimem update --check"
echo "  ./scripts/omnimem search \"my query\" --full"
echo ""
echo "After install, the 'omnimem' console script is also available at:"
echo "  ./venv/bin/omnimem"

#!/bin/bash

echo "=== OMNIMEM: The Universal RAG Core for CLI ==="
echo "Installing dependencies for Linux/macOS..."

# 1. Create Python Virtual Environment
echo "[1/4] Creating Python Virtual Environment (venv)..."
python3 -m venv venv
source venv/bin/activate

# 2. Install Dependencies
echo "[2/4] Installing dependencies (Kreuzberg, ChromaDB)..."
pip install -r requirements.txt > /dev/null 2>&1

echo "[3/4] Bootstrapping the local embedding model..."
if [ "${OMNIMEM_SKIP_MODEL_BOOTSTRAP:-0}" = "1" ]; then
  echo "Skipping model bootstrap because OMNIMEM_SKIP_MODEL_BOOTSTRAP=1"
else
  ./venv/bin/python3 omni_bootstrap.py || exit 1
fi

echo "[4/4] SETUP COMPLETE!"
echo ""
echo "🔥 OmniMem is ready. To use it with your CLI AI (Claude, Gemini, Cursor):"
echo "Copy the 'System Prompt' from the README and paste it into your AI's custom instructions."
echo "Example usage manually:"
echo "./venv/bin/python3 omni_import.py /path/to/document.pdf"
echo "./venv/bin/python3 omni_bootstrap.py"
echo "./venv/bin/python3 omni_search.py "my query" --full"

#!/bin/bash

echo "=== OMNIMEM: The Universal RAG Core for CLI ==="
echo "Installing dependencies for Linux/macOS..."

# 1. Create Python Virtual Environment
echo "[1/3] Creating Python Virtual Environment (venv)..."
python3 -m venv venv
source venv/bin/activate

# 2. Install Dependencies
echo "[2/3] Installing dependencies (Kreuzberg, ChromaDB)..."
pip install -r requirements.txt > /dev/null 2>&1

echo "[3/3] SETUP COMPLETE!"
echo ""
echo "🔥 OmniMem is ready. To use it with your CLI AI (Claude, Gemini, Cursor):"
echo "Copy the 'System Prompt' from the README and paste it into your AI's custom instructions."
echo "Example usage manually:"
echo "./venv/bin/python3 omni_import.py /path/to/document.pdf"
echo "./venv/bin/python3 omni_search.py "my query" --full"

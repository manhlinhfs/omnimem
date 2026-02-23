Write-Host "=== OMNIMEM: The Universal RAG Core for CLI ===" -ForegroundColor Cyan
Write-Host "Installing dependencies for Windows PowerShell..."

Write-Host "[1/3] Creating Python Virtual Environment (venv)..."
python -m venv venv
.\venv\Scripts\Activate.ps1

Write-Host "[2/3] Installing dependencies (Kreuzberg, ChromaDB)..."
pip install -r requirements.txt | Out-Null

Write-Host "[3/3] SETUP COMPLETE!" -ForegroundColor Green
Write-Host ""
Write-Host "🔥 OmniMem is ready. To use it with your CLI AI (Claude, Gemini, Cursor):"
Write-Host "Copy the 'System Prompt' from the README and paste it into your AI's custom instructions."
Write-Host "Example usage manually:"
Write-Host ".\venv\Scripts\python.exe omni_import.py C:\path	o\document.pdf" -ForegroundColor Yellow
Write-Host ".\venv\Scripts\python.exe omni_search.py `"my query`" --full" -ForegroundColor Yellow

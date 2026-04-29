$version = Get-Content VERSION | Select-Object -First 1
Write-Host "=== OMNIMEM v$version: The Universal RAG Core for CLI ===" -ForegroundColor Cyan
Write-Host "Installing dependencies for Windows PowerShell..."

Write-Host "[1/4] Creating Python Virtual Environment (venv)..."
python -m venv venv
.\venv\Scripts\Activate.ps1

Write-Host "[2/4] Installing dependencies (Kreuzberg, ChromaDB)..."
pip install -r requirements.txt | Out-Null

Write-Host "[3/4] Bootstrapping the local embedding model..."
if ($env:OMNIMEM_SKIP_MODEL_BOOTSTRAP -eq "1") {
    Write-Host "Skipping model bootstrap because OMNIMEM_SKIP_MODEL_BOOTSTRAP=1" -ForegroundColor Yellow
} else {
    .\venv\Scripts\python.exe omni_bootstrap.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[4/4] SETUP COMPLETE!" -ForegroundColor Green
Write-Host ""
Write-Host "🔥 OmniMem is ready. To use it with your CLI AI (Claude, Gemini, Cursor):"
Write-Host "Copy the 'System Prompt' from the README and paste it into your AI's custom instructions."
Write-Host "Example usage manually:"
Write-Host ".\omnimem.ps1 import C:\path\to\document.pdf" -ForegroundColor Yellow
Write-Host ".\omnimem.ps1 bootstrap" -ForegroundColor Yellow
Write-Host ".\omnimem.ps1 doctor" -ForegroundColor Yellow
Write-Host ".\omnimem.ps1 update --check" -ForegroundColor Yellow
Write-Host ".\omnimem.ps1 update" -ForegroundColor Yellow
Write-Host ".\omnimem.ps1 search `"my query`" --full" -ForegroundColor Yellow
Write-Host "Legacy scripts still work under .\venv\Scripts\python.exe as before." -ForegroundColor DarkYellow

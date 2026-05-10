$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoDir = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoDir

$version = Get-Content VERSION | Select-Object -First 1
Write-Host "=== OMNIMEM v${version}: The Universal RAG Core for CLI ===" -ForegroundColor Cyan
Write-Host "Installing dependencies for Windows PowerShell..."

Write-Host "[1/4] Creating Python Virtual Environment (venv)..."
python -m venv venv
.\venv\Scripts\Activate.ps1

Write-Host "[2/4] Installing dependencies (Kreuzberg, ChromaDB)..."
pip install -r requirements.txt | Out-Null
pip install -e . | Out-Null

Write-Host "[3/4] Bootstrapping the local embedding model..."
if ($env:OMNIMEM_SKIP_MODEL_BOOTSTRAP -eq "1") {
    Write-Host "Skipping model bootstrap because OMNIMEM_SKIP_MODEL_BOOTSTRAP=1" -ForegroundColor Yellow
} else {
    .\venv\Scripts\python.exe -m omnimem.bootstrap
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "[4/4] SETUP COMPLETE!" -ForegroundColor Green
Write-Host ""
Write-Host "OmniMem is ready. Wire it into your agent CLIs:"
Write-Host "  .\scripts\omnimem.ps1 quickstart" -ForegroundColor Yellow
Write-Host ""
Write-Host "Manual usage examples:"
Write-Host "  .\scripts\omnimem.ps1 import C:\path\to\document.pdf" -ForegroundColor Yellow
Write-Host "  .\scripts\omnimem.ps1 doctor" -ForegroundColor Yellow
Write-Host "  .\scripts\omnimem.ps1 update --check" -ForegroundColor Yellow
Write-Host "  .\scripts\omnimem.ps1 search `"my query`" --full" -ForegroundColor Yellow
Write-Host ""
Write-Host "After install, the 'omnimem' console script is also available at:"
Write-Host "  .\venv\Scripts\omnimem.exe" -ForegroundColor Yellow

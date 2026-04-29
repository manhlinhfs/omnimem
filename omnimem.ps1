$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoPython = Join-Path $scriptDir "venv\Scripts\python.exe"
$cliScript = Join-Path $scriptDir "omnimem.py"

if (Test-Path $repoPython) {
    & $repoPython $cliScript @args
} else {
    & python $cliScript @args
}

exit $LASTEXITCODE

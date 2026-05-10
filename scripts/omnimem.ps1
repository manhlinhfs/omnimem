$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoDir = Resolve-Path (Join-Path $scriptDir "..")
$repoPython = Join-Path $repoDir "venv\Scripts\python.exe"

if (Test-Path $repoPython) {
    & $repoPython -m omnimem @args
} else {
    $env:PYTHONPATH = "$repoDir;$env:PYTHONPATH"
    & python -m omnimem @args
}

exit $LASTEXITCODE

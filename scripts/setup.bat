@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."

set /p OMNIMEM_VERSION=<VERSION
echo === OMNIMEM v%OMNIMEM_VERSION%: The Universal RAG Core for CLI ===
echo Installing dependencies for Windows...

echo [1/4] Creating Python Virtual Environment (venv)...
python -m venv venv
call venv\Scripts\activate.bat

echo [2/4] Installing dependencies (Kreuzberg, ChromaDB)...
pip install -r requirements.txt >nul 2>&1
pip install -e . >nul 2>&1

echo [3/4] Bootstrapping the local embedding model...
if "%OMNIMEM_SKIP_MODEL_BOOTSTRAP%"=="1" (
  echo Skipping model bootstrap because OMNIMEM_SKIP_MODEL_BOOTSTRAP=1
) else (
  .\venv\Scripts\python.exe -m omnimem.bootstrap
  if errorlevel 1 (popd & exit /b 1)
)

echo [4/4] SETUP COMPLETE!
echo.
echo OmniMem is ready. Wire it into your agent CLIs:
echo   .\scripts\omnimem.bat quickstart
echo.
echo Manual usage examples:
echo   .\scripts\omnimem.bat import C:\path\to\document.pdf
echo   .\scripts\omnimem.bat doctor
echo   .\scripts\omnimem.bat update --check
echo   .\scripts\omnimem.bat search "my query" --full
echo.
echo After install, the 'omnimem' console script is also available at:
echo   .\venv\Scripts\omnimem.exe

popd
pause

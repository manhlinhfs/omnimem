@echo off
set /p OMNIMEM_VERSION=<VERSION
echo === OMNIMEM v%OMNIMEM_VERSION%: The Universal RAG Core for CLI ===
echo Installing dependencies for Windows...

echo [1/4] Creating Python Virtual Environment (venv)...
python -m venv venv
call venv\Scripts\activate.bat

echo [2/4] Installing dependencies (Kreuzberg, ChromaDB)...
pip install -r requirements.txt >nul 2>&1

echo [3/4] Bootstrapping the local embedding model...
if "%OMNIMEM_SKIP_MODEL_BOOTSTRAP%"=="1" (
  echo Skipping model bootstrap because OMNIMEM_SKIP_MODEL_BOOTSTRAP=1
) else (
  .\venv\Scripts\python.exe omni_bootstrap.py
  if errorlevel 1 exit /b 1
)

echo [4/4] SETUP COMPLETE!
echo.
echo 🔥 OmniMem is ready. To use it with your CLI AI (Claude, Gemini, Cursor):
echo Copy the 'System Prompt' from the README and paste it into your AI's custom instructions.
echo Example usage manually:
echo .\venv\Scripts\python.exe omni_import.py C:\path\to\document.pdf
echo .\venv\Scripts\python.exe omni_bootstrap.py
echo .\venv\Scripts\python.exe omni_doctor.py
echo .\venv\Scripts\python.exe omni_update.py --check
echo .\venv\Scripts\python.exe omni_update.py
echo .\venv\Scripts\python.exe omni_search.py "my query" --full
pause

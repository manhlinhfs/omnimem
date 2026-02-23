@echo off
echo === OMNIMEM: The Universal RAG Core for CLI ===
echo Installing dependencies for Windows...

echo [1/3] Creating Python Virtual Environment (venv)...
python -m venv venv
call venv\Scripts\activate.bat

echo [2/3] Installing dependencies (Kreuzberg, ChromaDB)...
pip install -r requirements.txt >nul 2>&1

echo [3/3] SETUP COMPLETE!
echo.
echo 🔥 OmniMem is ready. To use it with your CLI AI (Claude, Gemini, Cursor):
echo Copy the 'System Prompt' from the README and paste it into your AI's custom instructions.
echo Example usage manually:
echo .\venv\Scripts\python.exe omni_import.py C:\path	o\document.pdf
echo .\venv\Scripts\python.exe omni_search.py "my query" --full
pause

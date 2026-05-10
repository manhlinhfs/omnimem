@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "REPO_DIR=%SCRIPT_DIR%.."
set "REPO_PYTHON=%REPO_DIR%\venv\Scripts\python.exe"

if exist "%REPO_PYTHON%" (
  "%REPO_PYTHON%" -m omnimem %*
) else (
  set "PYTHONPATH=%REPO_DIR%;%PYTHONPATH%"
  python -m omnimem %*
)

exit /b %ERRORLEVEL%

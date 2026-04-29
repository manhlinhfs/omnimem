@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "REPO_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"
set "CLI_SCRIPT=%SCRIPT_DIR%omnimem.py"

if exist "%REPO_PYTHON%" (
  "%REPO_PYTHON%" "%CLI_SCRIPT%" %*
) else (
  python "%CLI_SCRIPT%" %*
)

exit /b %ERRORLEVEL%

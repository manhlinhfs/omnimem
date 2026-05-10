#!/usr/bin/env bash
# OmniMem one-line installer for Linux / macOS.
#
# Usage:
#     curl -fsSL https://raw.githubusercontent.com/manhlinhfs/omnimem/main/install.sh | bash
#
# Or to install into a specific directory:
#     curl -fsSL https://raw.githubusercontent.com/manhlinhfs/omnimem/main/install.sh | OMNIMEM_INSTALL_DIR=$HOME/tools/omnimem bash
#
# This script clones the repo, runs the standard setup, and prints next steps.
# It does NOT modify your shell rc files. See QUICKSTART.md to wire OmniMem
# into your agent CLI.

set -euo pipefail

REPO_URL="${OMNIMEM_REPO_URL:-https://github.com/manhlinhfs/omnimem.git}"
INSTALL_DIR="${OMNIMEM_INSTALL_DIR:-$HOME/.omnimem-cli}"
BRANCH="${OMNIMEM_BRANCH:-main}"

log() { printf "\033[1;34m[omnimem]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[omnimem]\033[0m %s\n" "$*" >&2; exit 1; }

require() {
    command -v "$1" >/dev/null 2>&1 || err "$1 is required but not on PATH. Install it and re-run."
}

require git
require python3

if [[ -e "$INSTALL_DIR" ]]; then
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        log "Existing OmniMem checkout at $INSTALL_DIR. Pulling latest."
        git -C "$INSTALL_DIR" fetch origin
        git -C "$INSTALL_DIR" checkout "$BRANCH"
        git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"
    else
        err "$INSTALL_DIR exists but is not a git checkout. Move or delete it and re-run."
    fi
else
    log "Cloning $REPO_URL into $INSTALL_DIR (branch $BRANCH)..."
    git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

if [[ -x "./scripts/setup.sh" ]]; then
    log "Running scripts/setup.sh (this bootstraps the embedding model on first run)."
    ./scripts/setup.sh
else
    err "scripts/setup.sh not found or not executable in $INSTALL_DIR."
fi

LAUNCHER="$INSTALL_DIR/omnimem"
if [[ ! -x "$LAUNCHER" ]]; then
    err "Launcher $LAUNCHER is missing or not executable. Setup may have failed."
fi

log "Install complete."
echo
echo "Run the interactive wizard to wire OmniMem into your agent CLIs:"
echo "    $LAUNCHER quickstart"
echo
echo "Or jump straight in:"
echo "    $LAUNCHER init --agent all"
echo "    $LAUNCHER hook install --agent all"
echo
echo "Add this directory to PATH if you want a plain 'omnimem' command:"
echo "    export PATH=\"$INSTALL_DIR:\$PATH\""
echo
echo "Docs: $INSTALL_DIR/QUICKSTART.md"

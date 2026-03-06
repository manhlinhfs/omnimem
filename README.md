# OmniMem v1.4.0 - The Universal CLI Brain 🧠

[Tiếng Việt](README_vi.md) | [Русский](README_ru.md) | [English](README.md)

OmniMem is an LLM-agnostic, multimodal Retrieval-Augmented Generation (RAG) system running purely in the terminal. It acts as a "Second Brain" for any AI coding agent (Claude Code, Gemini CLI, Cursor, Cline, OpenClaw) by allowing them to read, store, and recall knowledge from complex documents like PDFs, Word files, source code, and OCR images.

## Core Architecture
- **Kreuzberg (Rust Core):** Ingests and extracts clean Markdown and metadata from 56+ file formats.
- **ChromaDB:** A persistent, local Vector Database running entirely offline on your hard drive.
- **SentenceTransformers:** Uses a bootstrapped local copy of `all-MiniLM-L6-v2` for generating embeddings at runtime.

## Installation

### Linux / macOS
```bash
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
chmod +x setup.sh
./setup.sh
```
`setup.sh` now installs dependencies and downloads the embedding model into `.omnimem_models/` so runtime stays offline-safe.

### Windows (PowerShell)
```powershell
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
.\setup.ps1
```
`setup.ps1` performs the same bootstrap step for Windows users.

### Bootstrap the embedding model manually
```bash
python3 omni_bootstrap.py
```
Use `--offline-only` to restore from the local Hugging Face cache without hitting the network.

### Inspect runtime health
```bash
python3 omni_doctor.py
python3 omni_doctor.py --deep
python3 omni_doctor.py --json
```

### Update an existing clone
```bash
python3 omni_update.py --check
python3 omni_update.py
```
`omni_update.py` updates the current tracked branch with fast-forward only semantics, refuses to overwrite a dirty worktree, reinstalls dependencies when `requirements.txt` changes, and refreshes the local model bootstrap state.

## Offline-safe runtime
- Runtime commands (`omni_add.py`, `omni_search.py`, `omni_import.py`) now load embeddings from `.omnimem_models/` by default.
- If the local model directory is missing, OmniMem first tries to restore it from the local Hugging Face cache.
- If the model is still missing, OmniMem fails with a direct instruction to run `python3 omni_bootstrap.py` instead of crashing in the middle of a request.
- Set `OMNIMEM_ALLOW_MODEL_DOWNLOAD=1` only if you explicitly want runtime to download the model on demand.

## How to integrate with AI Agents (Crucial Step)

To give your AI Agent the ability to use OmniMem, you MUST inject the following rules into their **Custom Instructions** or **System Prompt** (e.g., in `.gemini/GEMINI.md`, or Claude's `.claude/settings.json`, or Cursor's Rules for AI):

```markdown
## OmniMem Protocol (Second Brain)
1. **ALWAYS Search First:** Before answering complex project questions, you MUST run the command: `[OMNIMEM_PATH]/venv/bin/python3 [OMNIMEM_PATH]/omni_search.py "your query" --full` to fetch context. Use `--full` to read the entire text without truncation. You can also use `--json` for structured data parsing.
2. **ALWAYS Import Docs:** When the user asks you to read or remember a complex file (PDF, DOCX, Image, Code), run: `[OMNIMEM_PATH]/venv/bin/python3 [OMNIMEM_PATH]/omni_import.py <file_path>` to ingest it via Kreuzberg.
3. **Save Milestones:** After resolving a major issue, run: `[OMNIMEM_PATH]/venv/bin/python3 [OMNIMEM_PATH]/omni_add.py "brief summary"` to save the context for your future sessions.
```
*(Note: Replace `[OMNIMEM_PATH]` with the absolute path to your cloned omnimem directory, e.g., `/root/omnimem` or `C:\omnimem`)*

## Unified CLI Usage
Use the repo launchers for normal operation because they prefer the local `venv` automatically. On Windows, use `.\omnimem.ps1` or `.\omnimem.bat` from the repo root.

- **Show version:** `python3 omnimem.py --version`
- **Show version via launcher:** `./omnimem --version`
- **Doctor:** `./omnimem doctor`
- **Check for updates:** `./omnimem update --check`
- **Update this clone:** `./omnimem update`
- **Bootstrap model:** `./omnimem bootstrap`
- **Add text:** `./omnimem add "Server password is 123"`
- **Import file:** `./omnimem import my_design.pdf`
- **Search:** `./omnimem search "password" --full`
- **Delete:** `./omnimem delete --wipe-all`

## Legacy standalone scripts
- `python3 omni_add.py "Server password is 123"`
- `python3 omni_import.py my_design.pdf`
- `python3 omni_search.py "password" --full`
- `python3 omni_del.py --wipe-all`
- `python3 omni_doctor.py`
- `python3 omni_update.py --check`

## Development
- **Run tests:** `python3 -m unittest discover -s tests -v`
- **Read release notes:** `CHANGELOG.md`
- **Follow release gates:** `docs/release-checklist.md`

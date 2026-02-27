# OmniMem - The Universal CLI Brain 🧠

[Tiếng Việt](README_vi.md) | [Русский](README_ru.md) | [English](README.md)

OmniMem is an LLM-agnostic, multimodal Retrieval-Augmented Generation (RAG) system running purely in the terminal. It acts as a "Second Brain" for any AI coding agent (Claude Code, Gemini CLI, Cursor, Cline, OpenClaw) by allowing them to read, store, and recall knowledge from complex documents like PDFs, Word files, source code, and OCR images.

## Core Architecture
- **Kreuzberg (Rust Core):** Ingests and extracts clean Markdown and metadata from 56+ file formats.
- **ChromaDB:** A persistent, local Vector Database running entirely offline on your hard drive.
- **SentenceTransformers:** Uses open-source `all-MiniLM-L6-v2` for generating embeddings.

## Installation

### Linux / macOS
```bash
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
chmod +x setup.sh
./setup.sh
```

### Windows (PowerShell)
```powershell
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
.\setup.ps1
```

## How to integrate with AI Agents (Crucial Step)

To give your AI Agent the ability to use OmniMem, you MUST inject the following rules into their **Custom Instructions** or **System Prompt** (e.g., in `.gemini/GEMINI.md`, or Claude's `.claude/settings.json`, or Cursor's Rules for AI):

```markdown
## OmniMem Protocol (Second Brain)
1. **ALWAYS Search First:** Before answering complex project questions, you MUST run the command: `[OMNIMEM_PATH]/venv/bin/python3 [OMNIMEM_PATH]/omni_search.py "your query" --full` to fetch context. Use `--full` to read the entire text without truncation. You can also use `--json` for structured data parsing.
2. **ALWAYS Import Docs:** When the user asks you to read or remember a complex file (PDF, DOCX, Image, Code), run: `[OMNIMEM_PATH]/venv/bin/python3 [OMNIMEM_PATH]/omni_import.py <file_path>` to ingest it via Kreuzberg.
3. **Save Milestones:** After resolving a major issue, run: `[OMNIMEM_PATH]/venv/bin/python3 [OMNIMEM_PATH]/omni_add.py "brief summary"` to save the context for your future sessions.
```
*(Note: Replace `[OMNIMEM_PATH]` with the absolute path to your cloned omnimem directory, e.g., `/root/omnimem` or `C:\omnimem`)*

## Manual CLI Usage
- **Add text:** `python3 omni_add.py "Server password is 123"`
- **Import file:** `python3 omni_import.py my_design.pdf`
- **Search:** `python3 omni_search.py "password" --full`
- **Delete:** `python3 omni_del.py --wipe-all`

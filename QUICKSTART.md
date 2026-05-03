# OmniMem Quickstart

Get OmniMem wired into your AI coding agent in **under 60 seconds**.

## TL;DR

```bash
git clone https://github.com/manhlinhfs/omnimem.git && cd omnimem
./setup.sh
./omnimem quickstart
```

`omnimem quickstart` detects whichever agent CLIs you have (Claude Code, Codex CLI, Gemini CLI, Cursor), installs the integration rule, registers the MCP server, and seeds a welcome note. Restart your agent CLI and you're done.

## Per-CLI cheat sheet

If you'd rather wire one specific CLI by hand:

### Claude Code

```bash
./omnimem init --agent claude
./omnimem hook install --agent claude
# Restart Claude Code. The omnimem_* tools should appear in `/mcp`.
```

### Codex CLI

```bash
./omnimem init --agent codex
./omnimem hook install --agent codex
# Restart Codex. AGENTS.md is read on session start.
```

### Gemini CLI

```bash
./omnimem init --agent gemini
# Restart Gemini. settings.json is re-read on launch.
```

### Cursor

```bash
./omnimem init --agent cursor
# Reload the Cursor window.
```

### All of them at once

```bash
./omnimem init --agent all
./omnimem hook install --agent all
```

The installer is **idempotent and reversible**:

```bash
./omnimem init --status                       # see what's wired up
./omnimem init --uninstall --agent claude     # remove cleanly
```

## First useful command

Once an agent CLI is wired, ask it any project-specific question. The agent will call `note_search` / `search_all` first, then save a note when it's done. You can also drive OmniMem directly:

```bash
./omnimem note new "Why we chose FastAPI" --type decision --tags auth,backend
./omnimem note search "fastapi"
./omnimem import path/to/spec.pdf
./omnimem search "rate limit" --all
./omnimem codemap build .
./omnimem codemap query "TokenManager"
```

## Where things live

```
$OMNIMEM_HOME/
├── .omnimem_db/            # ChromaDB vector store (offline)
├── .omnimem_models/        # bootstrapped embedding model
└── vault/
    ├── notes/              # zettelkasten markdown — Obsidian-friendly
    ├── conversations/      # imported transcripts
    ├── attachments/        # binary side-files
    └── codemap/<repo>/     # source structural maps
```

`OMNIMEM_HOME` defaults to `~/.omnimem/` on every OS (Linux, macOS, Windows). Override with the `OMNIMEM_HOME` environment variable or in `omnimem.json`.

## What next

- Read [`docs/notes.md`](docs/notes.md) for the full note CLI surface.
- Read [`docs/codemap.md`](docs/codemap.md) for codemap usage.
- Read [`docs/integrations/`](docs/integrations/) for CLI-specific tweaks.
- Read [`docs/faq.md`](docs/faq.md) for "is this offline?", "how is this different from Mem0?", and friends.
- Hit a snag? See [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md).

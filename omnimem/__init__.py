"""OmniMem — local terminal-first second brain for AI coding agents.

Public entry point: `main()` (CLI dispatcher). The console-script `omnimem`
declared in pyproject.toml resolves here.

Submodule layout (each module retains its own argparse `--version` flag and
can be invoked as `python -m omnimem.<module>`):

- ``omnimem.cli``        — the unified argparse dispatcher (`omnimem` console script)
- ``omnimem.add``        — `omnimem add` (insert memory rows)
- ``omnimem.search``     — `omnimem search` (federated search across documents/notes/codemap)
- ``omnimem.import_``    — `omnimem import` (Kreuzberg-backed file ingest); module
                           is `import_` because `import` is a keyword
- ``omnimem.del_``       — `omnimem del` (delete memory); module is `del_` for the same reason
- ``omnimem.note``       — `omnimem note` (Zettelkasten note CRUD)
- ``omnimem.note_index`` — note-vault embedding index
- ``omnimem.codemap``    — `omnimem codemap` (per-source structural map)
- ``omnimem.canvas``     — Obsidian Canvas export
- ``omnimem.redact``     — `omnimem redact` (secret scanner)
- ``omnimem.hooks``      — `omnimem hook` (Claude/Codex lifecycle hook installer)
- ``omnimem.init``       — `omnimem init` (per-agent CLI integration installer)
- ``omnimem.mcp``        — `omnimem mcp serve` (stdio MCP server)
- ``omnimem.quickstart`` — `omnimem quickstart` (interactive bootstrap wizard)
- ``omnimem.config``     — runtime configuration loader
- ``omnimem.paths``      — XDG-style path resolution + install-mode detection
- ``omnimem.vault``      — vault tree management
- ``omnimem.metadata``   — chroma metadata helpers
- ``omnimem.embeddings`` — sentence-transformers embedding factory
- ``omnimem.search_core``— ChromaDB-backed search runtime
- ``omnimem.service``    — long-lived warm search runtime IPC
- ``omnimem.ops``        — backup / export / restore
- ``omnimem.reindex``    — bulk reindex
- ``omnimem.bootstrap``  — embedding model bootstrap
- ``omnimem.update``     — git-based self-update
- ``omnimem.doctor``     — install diagnostic
- ``omnimem.version``    — `--version` argparse helper
"""

from omnimem.cli import main, _force_utf8_streams, _print

__all__ = ["main", "_force_utf8_streams", "_print"]

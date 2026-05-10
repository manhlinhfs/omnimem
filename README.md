# OmniMem v1.2.7 - The CLI Second Brain 🧠

[Tiếng Việt](README_vi.md) | [Русский](README_ru.md) | [English](README.md)

> **Quickstart in 60 seconds.** [`QUICKSTART.md`](QUICKSTART.md) shows the fastest path for Claude Code / Codex CLI / Gemini CLI / Cursor users.
>
> ```bash
> git clone https://github.com/manhlinhfs/omnimem.git && cd omnimem
> ./setup.sh
> ./omnimem quickstart        # interactive: detect agents, install, seed welcome note
> ```

OmniMem is an LLM-agnostic, multimodal second brain running purely in the terminal. It gives any AI coding agent (Claude Code, Codex CLI, Gemini CLI, Cursor, Cline, OpenClaw) six things in one CLI:

1. **Document RAG** — ingest PDFs, Word files, source code, and OCR images via Kreuzberg + ChromaDB.
2. **Structured notes** — Zettelkasten-style notes in a portable Markdown vault with bi-directional wikilinks.
3. **Codemap** — `omnimem codemap build` walks a repo and writes a structural map per source file. Supports Python (stdlib `ast`), JavaScript, TypeScript, Go, and Rust via the parser registry, with per-symbol records in ChromaDB.
4. **One-command integration** — `omnimem init --agent claude|codex|gemini|cursor|all` wires OmniMem into each agent's instructions file and MCP config; `omnimem hook --agent claude|codex|all` adds lifecycle hooks for both Claude Code and Codex CLI.
5. **Federated search + temporal queries** — `omnimem search --all` ranks results from imported documents, structured notes, and codemap symbols together. `--at-date YYYY-MM-DD` reconstructs the state of the vault as of a given day.
6. **Canvas export + secret redaction** — `omnimem note canvas` exports the note graph as Obsidian Canvas JSON. `omnimem redact` scans text for AWS / GitHub / OpenAI / Anthropic tokens, PEM blocks, JWTs, and the obvious credential shapes.

## Core Architecture
- **Kreuzberg (Rust Core):** Ingests and extracts clean Markdown and metadata from 56+ file formats.
- **ChromaDB:** A persistent, local Vector Database running entirely offline on your hard drive (collections: `omnimem_core` for documents, `omnimem_notes` for structured notes, `omnimem_codemap` for source maps).
- **SentenceTransformers:** Uses a bootstrapped local copy of `all-MiniLM-L6-v2` for generating embeddings at runtime.
- **MCP server:** Stdio Model Context Protocol server with six introspectable tools.
- **Markdown vault:** A portable `vault/` tree under `OMNIMEM_HOME` that any human can read/edit (Obsidian-friendly).

## Installation

For the fastest path see the Quickstart block at the top of this README. Below are the four supported install modes.

### One-line installer (Linux / macOS)
```bash
curl -fsSL https://raw.githubusercontent.com/manhlinhfs/omnimem/main/install.sh | bash
~/.omnimem-cli/omnimem quickstart
```
Clones into `~/.omnimem-cli` (override with `OMNIMEM_INSTALL_DIR=...`), runs `setup.sh`, then leaves you at the interactive wizard.

### Linux / macOS (manual clone)
```bash
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
chmod +x setup.sh
./setup.sh
./omnimem quickstart
```
`setup.sh` installs dependencies and downloads the embedding model. The model lives at `<OMNIMEM_HOME>/.omnimem_models/` (default `~/.omnimem/.omnimem_models/`) — **not inside the repo**.

### Windows (PowerShell)
```powershell
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
.\setup.ps1
.\omnimem quickstart
```
`setup.ps1` performs the same bootstrap on Windows. Runtime data lives at `~/.omnimem/` by default (same as Linux/macOS). The launcher `.\omnimem.bat` works from `cmd.exe` too.

### Package install mode
```bash
python3 -m pip install .
omnimem --version
omnimem quickstart
```
Package installs place runtime data in the OS user data directory (instead of inside `site-packages`) and expose `omnimem` directly on your `PATH`.

### Install directly from GitHub
```bash
python3 -m pip install "git+https://github.com/manhlinhfs/omnimem.git@main"
omnimem --version
omnimem quickstart
```

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

### Configure runtime paths and behavior
```bash
cp omnimem.example.json omnimem.json
./omnimem doctor
```
Edit `omnimem.json` to move the DB/model directories or change operational settings without editing code.

### Update an existing clone
```bash
python3 omni_update.py --check
python3 omni_update.py
```
`omni_update.py` updates the current tracked branch with fast-forward only semantics, refuses to overwrite a dirty worktree, reinstalls dependencies when `requirements.txt` changes, and refreshes the local model bootstrap state.

Package installs do not support `omnimem update`; reinstall or upgrade them with `pip` instead.

### Backup, export, and restore
```bash
./omnimem backup
./omnimem export
./omnimem restore /path/to/omnimem-backup.tar.gz
./omnimem restore /path/to/omnimem-export.json --force
```

### Reindex older imports with the new chunker
```bash
./omnimem reindex --dry-run
./omnimem reindex
```
This is intended for users who imported files on older OmniMem releases and want to rebuild their DB with the current chunking strategy.

### Warm local search service
```bash
./omnimem serve --status
./omnimem search "release notes" --full
./omnimem search "release notes" --direct
```
`search`, `add`, `import`, and `reindex` now prefer a local service that keeps the embedding model and Chroma client warm across repeated commands. The first service-backed command still warms the model once; subsequent commands reuse it and avoid most of the previous startup cost.

## Offline-safe runtime
- Every runtime command (the unified `omnimem` CLI and the legacy `omni_*.py` scripts) loads embeddings from `<OMNIMEM_HOME>/.omnimem_models/` by default. This is in your OS user data directory, **not** inside the repo.
- If the local model directory is missing, OmniMem first tries to restore it from your Hugging Face cache (typically `~/.cache/huggingface/hub/`).
- If the model is still missing, OmniMem fails with a direct instruction to run `omnimem bootstrap` (or `python3 omni_bootstrap.py`) instead of crashing in the middle of a request.
- Set `OMNIMEM_ALLOW_MODEL_DOWNLOAD=1` only if you explicitly want runtime to fetch the model from Hugging Face on demand. By default OmniMem refuses to reach the network.

## How to wire OmniMem into your agent CLI

**Prefer the one-command install** — `omnimem init` writes the rule block, registers the MCP server, and (with `omnimem hook`) sets up lifecycle hooks. No manual prompt editing required.

### Recommended: interactive wizard

```bash
./omnimem quickstart           # detect installed agents, install everything, seed a welcome note
./omnimem quickstart --yes     # non-interactive (accept all defaults)
```

### Explicit per-agent install

| Agent | Command |
|---|---|
| Claude Code | `./omnimem init --agent claude && ./omnimem hook --agent claude` |
| Codex CLI | `./omnimem init --agent codex && ./omnimem hook --agent codex` |
| Gemini CLI | `./omnimem init --agent gemini` |
| Cursor | `./omnimem init --agent cursor` |
| All four | `./omnimem init --agent all && ./omnimem hook --agent all` |

What `init` does:
- Writes a marked rule block (`<!-- OMNIMEM:START v1.2 -->` ... `<!-- OMNIMEM:END -->`) into the agent's instructions file (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, or `.cursor/rules/omnimem.mdc`). Existing content is preserved.
- Registers the OmniMem MCP server in the agent's MCP config (`mcp.json` for Claude Code / Cursor, `settings.json` for Gemini, `config.toml` for Codex).
- Idempotent: re-running replaces only the marked block. Reversible: `./omnimem init --uninstall --agent <agent>` strips it cleanly.

What `omnimem hook` does (Claude Code + Codex CLI only):
- `SessionStart` → injects the most recent notes so the agent has fresh project context.
- `Stop` → lists today's notes so the agent reflects on what was just completed.
- `PostToolUse` (Edit / Write / MultiEdit) → triggers `omnimem note reindex` so any edited markdown re-syncs into ChromaDB.

Each entry is tagged `omnimem-v1` so the installer can coexist with any hand-authored hooks you already have. Hook commands launch the `omnimem` console script (no `python -m omnimem`, fix in v1.2.7) and quote Windows paths with POSIX forward slashes for `bash -c` (fix in v1.2.4). v1.2.7+ also auto-rewrites stale `<python> -m omnimem ...` entries from earlier installs on the next `omnimem hook` / `omnimem init` invocation.

### What the agent sees after install

The injected protocol tells your agent to:
1. **Prefer the MCP tools** when registered (`note_search`, `note_new`, `note_show`, `note_link`, `search_all`, `import_file`).
2. **Fall back to the OmniMem CLI** otherwise (`./omnimem note search "..."`, `./omnimem search "..." --full`, `./omnimem note new "..." --type decision`, `./omnimem import <path>`).
3. **Search OmniMem before answering** project-specific questions; **save a note after** non-trivial tasks with `[[wikilinks]]` to related notes.

Restart the agent CLI session after install so the MCP server and rule block are picked up. Detailed per-CLI tweaks live in [`docs/integrations/`](docs/integrations/).

### Verifying

```bash
./omnimem init --status        # which agents have the marked block + MCP entry
./omnimem hook --status        # which lifecycle hooks are active per scope
./omnimem doctor               # whole-runtime health, including vault and integrations
./omnimem mcp tools            # 6 MCP tools the server exposes
```

### Uninstalling

```bash
./omnimem init --uninstall --agent <agent>      # remove rule block + MCP entry (only the marked region)
./omnimem hook --uninstall --agent <agent>      # remove only OmniMem-tagged hooks
```

Hand-authored content outside the marker block is preserved in both cases.

## Unified CLI Usage

Use the repo launchers (`./omnimem`, `.\omnimem.ps1`, `.\omnimem.bat`) for clone mode — they activate the local `venv` automatically. In package mode, the installed `omnimem` command works the same way.

```bash
./omnimem --help               # full subcommand list
```

20 subcommands, grouped below by topic.

### Setup and diagnostics

```bash
./omnimem --version                          # OmniMem version
./omnimem quickstart [--yes] [--skip-hooks] [--skip-seed]
./omnimem doctor [--deep] [--json]           # runtime health, vault, integrations
./omnimem bootstrap [--offline-only] [--force]  # download / restore the embedding model
./omnimem update [--check]                   # self-update on git clones
```

### Documents (RAG via Kreuzberg + ChromaDB)

```bash
./omnimem add "FastAPI is the chosen auth framework" --tags arch,decision
./omnimem add "Note text" --direct                          # skip the warm service
./omnimem import path/to/spec.pdf
./omnimem import path/to/spec.pdf --direct
./omnimem search "auth flow" --full
./omnimem search "release" --source path/to/spec.pdf --since 2026-03-06
./omnimem search "invoice" --mime-type application/pdf
./omnimem search "rate limit" --all                         # federated: documents + notes + codemap
./omnimem search "decisions" --at-date 2026-04-15           # vault state at a given date
./omnimem search "auth" --direct                            # bypass warm service for debugging
./omnimem reindex [--dry-run] [--direct]                    # rebuild imports with the current chunker
./omnimem delete --wipe-all --force                         # nuke the documents collection
```

### Structured notes (Zettelkasten in a Markdown vault)

```bash
./omnimem note new "Why we chose FastAPI" --type decision --tags auth,backend
echo "Body via stdin" | ./omnimem note new "Title" --body -
./omnimem note show <slug-or-id>
./omnimem note update <slug-or-id> --title "New title" --add-tag urgent --rm-tag draft
./omnimem note rm <slug-or-id>
./omnimem note list --type decision --tag auth --since 2026-04-01 --limit 20
./omnimem note list --at-date 2026-04-15
./omnimem note search "fastapi" --full --limit 5 [--at-date YYYY-MM-DD]
./omnimem note link source-slug target-slug
./omnimem note unlink source-slug target-slug
./omnimem note backlinks <slug-or-id>
./omnimem note graph [--root <slug>]
./omnimem note canvas vault.canvas [--root <slug>] [--depth 2]   # Obsidian Canvas export
./omnimem note reindex [--dry-run]
```

### Codemap (source code structural maps)

```bash
./omnimem codemap build /path/to/repo --repo-name myproject
./omnimem codemap build . --language python --language go         # restrict to subset
./omnimem codemap update path/to/file.py --repo-path /path/to/repo
./omnimem codemap query "TokenManager" --limit 10
./omnimem codemap rm myproject
```

Languages supported in v1.2.x: Python (stdlib `ast`), JavaScript, TypeScript, Go, Rust.

### Multi-CLI integration

```bash
./omnimem init --agent claude|codex|gemini|cursor|all [--scope user|project] [--no-mcp]
./omnimem init --status
./omnimem init --uninstall --agent <agent>
./omnimem init --dry-run --agent claude
```

### Lifecycle hooks (Claude Code + Codex CLI)

```bash
./omnimem hook --agent claude|codex|all [--event SessionStart|Stop|PostToolUse]
./omnimem hook --status
./omnimem hook --uninstall --agent <agent>
./omnimem hook --dry-run --agent claude
```

### MCP server

```bash
./omnimem mcp serve            # stdio JSON-RPC 2.0 (this is what agent CLIs spawn)
./omnimem mcp tools [--json]   # introspect the 6 published tools
```

### Safety: secret redaction

```bash
echo "Token: ghp_aBcDeFgHiJkL... AKIA..." | ./omnimem redact -
./omnimem redact - --detect-only --json    # report findings without modifying
```

Patterns covered: AWS, GitHub PAT/OAuth, OpenAI, Anthropic, Slack, Google, Stripe tokens, PEM private key blocks, JWTs, generic `password=` / `api_key=` shapes. Pipe input with `redact -` (or pass a literal string).

### Vault round-trip and warm service

```bash
./omnimem backup [--output snapshot.tar.gz] [--no-models] [--no-config]
./omnimem export [--output snapshot.json]
./omnimem restore /path/to/snapshot.tar.gz [--force]
./omnimem restore /path/to/snapshot.json --force
./omnimem serve [--status]                    # warm local search service
```

`add`, `import`, `search`, `reindex` prefer the warm service automatically — pass `--direct` to bypass it.

### Configure runtime paths

```bash
cp omnimem.example.json omnimem.json
./omnimem doctor                              # confirms the new paths are loaded
```

`omnimem.json` keys: `home`, `db_dir`, `models_dir`, `allow_model_download`, chunker tuning, `search_service_*`. Override per-process with env vars `OMNIMEM_HOME`, `OMNIMEM_CONFIG`, or `OMNIMEM_ALLOW_MODEL_DOWNLOAD`.

## Legacy standalone scripts

The unified `omnimem` CLI is the canonical entry point in v1.2.x. The older `omni_*.py` scripts are kept around for backward compatibility and for users who want to vendor a single file:

```bash
python3 omni_add.py "Project uses FastAPI for the auth service"
python3 omni_add.py "..." --direct
python3 omni_import.py my_design.pdf
python3 omni_import.py my_design.pdf --direct
python3 omni_search.py "auth" --full
python3 omni_search.py "auth" --direct
python3 omni_del.py --wipe-all --force
python3 omni_doctor.py [--deep] [--json]
python3 omni_ops.py backup
python3 omni_ops.py export
python3 omni_ops.py restore /path/to/file
python3 omni_reindex.py [--dry-run] [--direct]
python3 omni_update.py [--check]
python3 omni_bootstrap.py [--offline-only] [--force]
```

The note / codemap / init / hook / mcp / quickstart / redact subcommands are **only** available through the unified `omnimem` CLI.

## Documentation

For users:

- [`QUICKSTART.md`](QUICKSTART.md) — 60-second adoption path with per-CLI cheat sheet
- [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) — common failures with concrete fixes
- [`docs/faq.md`](docs/faq.md) — offline?, vs Mem0 / Basic Memory / MemPalace?, note vs document?, etc.
- [`docs/notes.md`](docs/notes.md) — full note CLI reference and frontmatter schema
- [`docs/codemap.md`](docs/codemap.md) — codemap usage, parser registry, language matrix
- [`docs/hooks.md`](docs/hooks.md) — Claude Code + Codex CLI lifecycle hooks
- [`docs/redact.md`](docs/redact.md) — secret pattern matrix and library use
- [`docs/benchmarks.md`](docs/benchmarks.md) — retrieval / latency / parser accuracy numbers
- [`docs/integrations/`](docs/integrations/) — per-CLI deep dives (Claude Code, Codex CLI, Gemini CLI, Cursor, MCP)

For contributors:

- [`CONTRIBUTING.md`](CONTRIBUTING.md) — dev setup, coding standards (stdlib-first), PR checklist, recipe for adding a codemap language or redaction pattern
- [`CHANGELOG.md`](CHANGELOG.md) — release history
- [`ROADMAP.md`](ROADMAP.md) — what's planned for v1.3+

## Development

```bash
python3 -m unittest discover -s tests -v          # run tests (stdlib + pyyaml)
python3 -m benchmarks.run_all                     # run the benchmark suite
python3 -m build                                  # build the wheel
```

Reference docs for the underlying machinery:

- [`docs/install-modes.md`](docs/install-modes.md) — git clone vs package vs source tree
- [`docs/configuration.md`](docs/configuration.md) — `omnimem.json` precedence rules
- [`docs/operations.md`](docs/operations.md) — backup / export / restore semantics
- [`docs/chunking.md`](docs/chunking.md) — chunker profiles and overrides
- [`docs/reindexing.md`](docs/reindexing.md) — when and how to rebuild collections
- [`docs/search-filters.md`](docs/search-filters.md) — `--source`, `--since`, `--until`, `--mime-type`
- [`docs/search-service.md`](docs/search-service.md) — warm local service architecture
- [`docs/release-checklist.md`](docs/release-checklist.md) — release gate

## License

MIT.

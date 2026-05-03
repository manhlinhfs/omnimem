# FAQ

## Is this really offline?

Yes. After `setup.sh` bootstraps the embedding model, every command (`add`, `import`, `note`, `search`, `codemap`, `mcp serve`, `init`, `hook`) runs without network access. ChromaDB lives on your disk, the embedding model lives in `$OMNIMEM_HOME/.omnimem_models/`, and Kreuzberg parses files locally.

The only network step is the initial model download (~22MB for `all-MiniLM-L6-v2`). After that, you can `unplug` the network and OmniMem still works.

## Does my data leave my machine?

No data leaves your machine. There is no cloud sync, no telemetry, no analytics. The only network egress is the optional model download during `bootstrap` (controlled by `OMNIMEM_ALLOW_MODEL_DOWNLOAD`).

If you opt to use a cloud reranker (planned for v1.4.0), that will be opt-in and clearly labeled.

## How is OmniMem different from Mem0 / Basic Memory / MemPalace?

| | OmniMem | Mem0 | Basic Memory | MemPalace |
|---|---|---|---|---|
| Multi-CLI agent agnostic via shell | ✅ | SDK only | MCP only | MCP only |
| Document RAG (PDF/DOCX/code) | ✅ | ❌ | ❌ | ❌ |
| Codemap multi-language | ✅ | ❌ | ❌ | ❌ |
| Markdown vault Obsidian-readable | ✅ | ❌ | ✅ | ❌ |
| Lifecycle hooks for Claude/Codex | ✅ | ❌ | ❌ | ❌ |
| One-command multi-CLI install | ✅ | ❌ | ❌ | ❌ |
| LLM-driven note consolidation | ❌ | ✅ | ❌ | ❌ |
| Public benchmark | ✅ | ✅ LOCOMO | ❌ | ✅ LOCOMO |

OmniMem owns the "second brain for coding agents" niche — document RAG + structured notes + codemap + multi-CLI integration in one CLI. Mem0 wins for conversational memory with auto-consolidation. Basic Memory wins for pure markdown knowledge graph editing. MemPalace wins for spatial-recall benchmarks.

## When should I use a note vs. an imported document?

- **Use `omnimem add` / `omnimem import`** for **passive knowledge** you don't plan to edit: PDFs, third-party docs, source code from another project, OCR output, transcripts. They land in `omnimem_core` as chunks.
- **Use `omnimem note new`** for **decisions, learnings, conventions, project log** you'll want to link, edit, and search by tag. They land in `omnimem_notes` as one record per note.

`omnimem search --all` queries both at once.

## Can I use Obsidian on the same vault?

Yes. Point Obsidian at `$OMNIMEM_HOME/vault/`. Notes are plain Markdown with YAML frontmatter and `[[wikilinks]]` — Obsidian renders them natively. Edits you make in Obsidian are picked up the next time you run `omnimem note reindex`.

## Why did you choose `all-MiniLM-L6-v2`?

Small (22M params, 384-dim), fast on CPU, MIT-licensed, well-validated for short-text retrieval. It's the same default Mem0 and Basic Memory ship with. v1.4.0 will let you swap in larger models (`bge-large`, OpenAI, Voyage) when retrieval quality matters more than latency.

## What about secrets in my notes?

OmniMem does **not** automatically redact. You opt-in via `omnimem redact <text>` for high-precision patterns (AWS keys, GitHub PATs, OpenAI/Anthropic keys, PEM blocks, JWTs). Pipe content through `omnimem redact` before `omnimem add` if you're ingesting from untrusted sources.

A future minor will add `--redact` flags directly on `add` / `import` for opt-in auto-redaction.

## How do I sync a vault between two machines?

There's no built-in sync today. Most users:

1. Put `$OMNIMEM_HOME/vault/` inside a personal git repo and push/pull manually.
2. Use a cloud drive (Dropbox, iCloud, Syncthing) on the vault directory.
3. Use `omnimem backup` + `omnimem restore` for periodic snapshots.

Native sync (cloud bucket, git remote) is a v1.5+ stretch goal.

## Will my benchmark numbers match docs/benchmarks.md?

Probably close on Linux + similar hardware. The benchmark suite is reproducible — run `python -m benchmarks.run_all` and you'll get a JSON output you can compare. Hardware, Python version, ChromaDB version, and HuggingFace model file integrity all affect the numbers.

## Is OmniMem stable for daily use?

For personal use on a single machine: **yes**. The CLI surface, vault layout, and ChromaDB collection names are stable in the v1.x series. Backward compatibility is a release-discipline rule (see `ROADMAP.md`).

For team / production / SaaS use: **not yet**. There's no auth, no multi-tenant isolation, no observability, and no SLA story. Those are post-v1.x roadmap items.

## How can I help?

- Try OmniMem on your real workflow and open issues for what doesn't work.
- Submit PRs with new language parsers for the codemap registry — the contract is in `omni_codemap.LANGUAGE_PARSERS`.
- Submit PRs with new redaction patterns to `omni_redact._PATTERNS`.
- Improve docs based on first-use friction.

See [`CONTRIBUTING.md`](../CONTRIBUTING.md).

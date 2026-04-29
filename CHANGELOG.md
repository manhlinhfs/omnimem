# Changelog

## v1.2.1 - Adoption And Onboarding

A docs and UX patch on top of v1.2.0; no breaking changes, no runtime semantics changed.

- Added `QUICKSTART.md` (top-level, focused on the 60-second path) and `TROUBLESHOOTING.md` (common failures + fixes)
- Added `docs/faq.md` covering "is this offline?", "how does this differ from Mem0 / Basic Memory / MemPalace?", "note vs document?", and friends
- Added `omni_quickstart.py` and the `omnimem quickstart` CLI subcommand: an interactive wizard that detects installed agent CLIs, installs the rule block + MCP registration + lifecycle hooks, seeds a welcome note, and prints concrete next steps. Pass `--yes` for non-interactive runs (e.g. from `install.sh`)
- Added `install.sh` one-line installer that clones the repo, runs `setup.sh`, and points users at `omnimem quickstart`
- Added `CONTRIBUTING.md` and `.github/ISSUE_TEMPLATE/{bug_report,feature_request,question}.md`
- README rewritten so the Quickstart block sits at the very top
- Tests: `tests/test_quickstart.py` (7 cases) covering agent detection, init plumbing, welcome-note seeding, and the no-detected-agent path

## v1.2.0 - Initial Public Release

OmniMem 1.2.0 is the first public release of the offline-first second-brain CLI for AI coding agents.

### Highlights

- **Document RAG** — `omnimem add`, `omnimem import`, `omnimem search` over a local ChromaDB instance with offline-bootstrapped `all-MiniLM-L6-v2` embeddings. Kreuzberg ingests 56+ formats including PDF, DOCX, source code, and OCR images.
- **Structured notes** — `omnimem note` (new / show / update / rm / list / search / link / unlink / backlinks / graph / reindex / canvas) with a Markdown vault under `OMNIMEM_HOME/vault/notes/`, YAML frontmatter, and bi-directional `[[wikilinks]]` mirrored into a dedicated `omnimem_notes` ChromaDB collection.
- **Codemap** — `omnimem codemap` (build / update / query / rm) parses Python (stdlib `ast`), JavaScript, TypeScript, Go, and Rust into per-file Markdown maps under `vault/codemap/<repo>/...` plus per-symbol records in the `omnimem_codemap` collection so search returns precise function / class / method / struct / trait hits.
- **Multi-CLI integration** — `omnimem init --agent claude|codex|gemini|cursor|all` writes idempotent rule blocks (`<!-- OMNIMEM:START v1.2 -->` / `<!-- OMNIMEM:END -->`) into each agent's instructions file and registers the OmniMem MCP server in the agent's MCP config (`mcp.json`, `settings.json`, or `config.toml`).
- **MCP server** — `omnimem mcp serve` exposes `note_new`, `note_search`, `note_show`, `note_link`, `search_all`, and `import_file` over stdio JSON-RPC 2.0 with published JSON Schemas.
- **Lifecycle hooks** — `omnimem hook install --agent claude|codex|all` wires SessionStart / Stop / PostToolUse hooks into Claude Code's `settings.json` and Codex CLI's `config.toml`, tagged `omnimem-v1` so the installer can coexist with hand-authored hooks.
- **Federated search** — `omnimem search --all` ranks results across `omnimem_core` (documents), `omnimem_notes` (structured notes), and `omnimem_codemap` (source symbols) together, tagging each hit with its source collection.
- **Temporal queries** — `--at-date YYYY-MM-DD` on `note list`, `note search`, and `search` reconstructs vault state as of a given day.
- **Obsidian Canvas export** — `omnimem note canvas <output>` writes the note graph as `.canvas` JSON; optional `--root` and `--depth` for sub-graph extraction.
- **Secret redaction** — `omnimem redact` (and the `omni_redact` library) covering AWS, GitHub, OpenAI, Anthropic, Slack, Google, Stripe tokens, PEM private key blocks, JWTs, and obvious `password=...` / `api_key=...` shapes.
- **Vault round-trip** — `omnimem backup` / `omnimem export` / `omnimem restore` include the entire `vault/` tree alongside the ChromaDB collections, the embedding model, and the active config.
- **Diagnostics** — `omnimem doctor` reports vault inventory, agent integrations, ChromaDB collections, and the embedding model state with a `--deep` mode that exercises the runtime end to end.

### Operational baseline (v1.2.0 benchmark suite)

- Codemap parser macro-F1 = 1.00 across Python / JavaScript / TypeScript / Go / Rust on synthetic fixtures (regression guard, not a real-world fidelity claim).
- Search latency p50 = 38ms, p95 = 101ms, p99 = 200ms over 50 queries against a 200-note vault on a single Windows machine.
- Retrieval recall@5 = 1.00 and recall@10 = 1.00 on a synthetic 100-note 20-topic corpus (recall@1 = 0.20 because the corpus contains 5 near-duplicate notes per topic; this is the fixture floor).

See [docs/benchmarks.md](docs/benchmarks.md) for the full results, reading guide, and caveats.

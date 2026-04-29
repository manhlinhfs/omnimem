# Changelog

## v1.2.3 - Windows Hook Path Quoting Fix

A patch release for a Windows-specific bug discovered on the live install.

- **Bug**: hook commands stored in `~/.claude/settings.json` (and the equivalent Codex / MCP entries) used `sys.executable` directly. On Windows that returns a backslash path like `C:\Users\foo\venv\Scripts\python.exe`. JSON serialization preserves the backslashes, but Claude Code passes the command string through `bash -c`, where each backslash is interpreted as a shell escape and silently consumed — so the path becomes `C:Usersfoovenv...` and the Stop hook fails with `command not found`.
- **Fix**: `omni_hooks._omnimem_command()` and `omni_init._detect_omnimem_command()` now emit POSIX-style forward slashes. Python on Windows accepts forward-slash paths natively, and bash leaves them alone.
- **Cleanup**: re-running `omnimem init --agent <agent>` and `omnimem hook install --agent <agent>` rewrites the existing entries in place. Anyone hit by the bug just needs to re-run the install commands.
- Added `tests/test_hook_path_quoting.py` (5 cases): `_omnimem_command()` rewrites Windows backslashes, leaves POSIX paths untouched, falls back to `python` when `sys.executable` is empty; `_detect_omnimem_command()` does the same; `install_claude_hooks()` end-to-end never lets a backslash leak into the python part of the command string.

## v1.2.2 - Benchmark Isolation Fix And Translated Docs

A patch release. No CLI surface changes; user-visible behavior is unchanged.

- Fixed `benchmarks.common.isolated_omnimem_home`: the context manager now also writes a fresh `omnimem.json` into the tmp directory and exports `OMNIMEM_CONFIG`, so a benchmark with the user's repo-local `omnimem.json` no longer falls back to the user's real ChromaDB / models / vault. Pre-fix, the env var override only neutralised `OMNIMEM_HOME` and any pinned `db_dir` in the config file slipped through; benchmarks could write into the user's real notes collection.
- Added `tests/test_bench_isolation.py` (5 cases) as a regression guard for the isolation contract: env vars overridden, temp config file created, runtime helpers resolve to the tmp paths, env vars restored on exit, tmpdir removed on exit.
- Rewrote `README_vi.md` (Vietnamese) and `README_ru.md` (Russian) — they had been left at v1.8.3. They now mirror the v1.2.x English README structure: Quickstart block, six features, core architecture, install modes (clone, package, one-line installer), per-CLI integration cheat sheet, common commands, vault layout, and full docs index.
- README headline bumped to v1.2.2.

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

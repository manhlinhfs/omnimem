# Changelog

## v1.2.7 - Console-script hooks + auto-migration

Stop / SessionStart / PostToolUse hooks installed by v1.2.6 (and earlier
versions) emitted `<python> -m omnimem ...`. When any `sys.path` entry
resolved `omnimem` to a package or namespace package — possible after
editable installs, on machines with a sibling `omnimem/` directory, or on
certain Python build layouts — runpy refused with:

```
'omnimem' is a package and cannot be directly executed
```

This broke Stop hooks on Claude Code CLI and would surface for Codex /
Gemini hooks under the same conditions.

### Fixed

- **Hooks and MCP entries now use the `omnimem` console script**
  (`<venv>/Scripts/omnimem.exe` on Windows, `<venv>/bin/omnimem` on POSIX)
  instead of `<python> -m omnimem ...`. Console scripts dispatch through
  `importlib.metadata` entry points and bypass module-resolution
  machinery — immune to package / namespace collisions. Falls back to
  naked `omnimem` (PATH lookup) if the file is missing. Path emission
  stays POSIX-style so `bash -c` on Windows does not eat backslashes.
- **`omnimem hook ...` and `omnimem init ...` auto-migrate stale
  `-m omnimem` entries** (Claude `settings.json`, Codex `config.toml`
  hook block + MCP block, Claude / Cursor / Gemini `mcp.json`).
  Detection is by command shape, not by tag, so hand-installed entries
  from earlier docs are also rewritten. Migration is idempotent and runs
  on every non-`--gated-reindex` invocation.
- **Codex MCP TOML reinstall left orphan content.**
  `_TOML_BLOCK_PATTERN` stopped matching at the first `[` of `args = [...]`,
  so substituting the OmniMem block left the previous args list orphaned
  on disk. Pattern now extends to the next TOML table header.

### Docs

- `docs/integrations/{mcp,codex,gemini}.md` updated to recommend the
  `omnimem` console script. The legacy `<python> -m omnimem mcp serve`
  form is documented only as "do not use".

## v1.2.6 - Stdin UTF-8 And Hook Docs Sync

A small follow-up patch covering two Windows-hygiene issues that surfaced
when using v1.2.5 from a fresh shell.

### Fixed

- **`note new --body -` crashed on non-ASCII heredoc input on Windows**
  (`UnicodeEncodeError: '\\udc8d' surrogates not allowed`). v1.2.5
  reconfigured stdout/stderr to UTF-8 but missed stdin, so heredoc bytes
  still hit the cp1252 + `surrogateescape` decoder and produced
  surrogates that `Path.write_text(encoding="utf-8")` then refused.
  `_force_utf8_streams` now reconfigures all three standard streams.
- **Docs referenced an `install` subcommand that doesn't exist.** Every
  README / QUICKSTART / docs page wrote `omnimem hook install --agent
  claude`; the CLI has no positional `install` (installation is the
  default behavior of the `hook` subcommand). Users following the docs
  hit `argparse: unrecognized arguments: install`. Replaced across
  README (3 langs), QUICKSTART, docs/{hooks,codemap,benchmarks,faq}.md,
  one argparse help string, and the `omni_hooks` / `omni_quickstart`
  comments. CHANGELOG + ROADMAP historical entries were left as-is.

### CI

- Multi-OS matrix now lives on `main`. Every push / PR runs
  `ubuntu-latest` × `windows-latest` × `macos-latest` × Python `3.10` /
  `3.11` / `3.12`. v1.2.6 is the first release verified across all 9
  cells before being tagged.

### Internal

- New `tests/test_stdin_utf8.py` (3 cases) pins the stdin / stdout /
  stderr UTF-8 reconfigure contract — all three streams, plus the
  no-reconfigure-method and reconfigure-failure escape paths.

## v1.2.5 - Cross-Platform Defaults, Warm-Service Coverage, MCP Performance

A maintenance release that lands seven weeks of fixes covering correctness on
Windows, performance for long-lived agent sessions, portability of the runtime
home, and quality-of-life on the note CLI.

### Breaking changes (read first)

- **Default `OMNIMEM_HOME` is now `~/.omnimem/` on every OS** (Linux, macOS,
  Windows). Previously the default was `%LOCALAPPDATA%\omnimem\` on Windows,
  `~/.local/share/omnimem` on Linux, `~/Library/Application Support/omnimem`
  on macOS. Existing users with no `OMNIMEM_HOME` set should migrate their
  data: `mv ~/.local/share/omnimem ~/.omnimem` (Linux), or the equivalent on
  your platform. Existing users with a local `omnimem.json` are unaffected
  because the file pin wins over the default.
- **Default `home` for `git_clone` install mode no longer points at the repo
  root.** Fresh `git clone && setup.sh` installs now write the vault, db,
  and models to `~/.omnimem/` instead of inside the checkout. Devs who want
  repo-local data should add a local `omnimem.json` with `{"home": "."}`.
- **`omnimem.json` is no longer tracked by the repo.** The dev file shipped
  with v1.2.0..v1.2.4 leaked the maintainer's username into every clone.
  `omnimem.example.json` remains as a template; copy it to `omnimem.json`
  locally and the gitignore will keep your edits private.

### Fixed

- **Windows cp1252 UnicodeEncodeError** crashed `note search` / `note show`
  on vaults containing Vietnamese (or any non-ASCII) content. `main()` now
  reconfigures stdout/stderr to UTF-8 so the CLI no longer requires
  `PYTHONIOENCODING=utf-8` as a workaround.
- **Windows test suite is now hermetic.** Six pre-existing failures (8.3
  short-name vs resolved long-name path mismatch in tempfile, missing
  `CodemapRuntime` mock in federation tests) are fixed. 230+ tests pass on
  Windows; 0 regressions on Linux CI.
- **PostToolUse reindex no longer fires for every Edit/Write/MultiEdit.**
  Previously, every Claude Code or Codex CLI tool use triggered a full notes
  reindex, which loads the embedding model and rebuilds the
  `omnimem_notes` collection. Now `omnimem hook --gated-reindex` reads the
  hook payload from stdin and reindexes only when the touched file lives
  inside the vault. Re-run `omnimem hook install --agent claude|codex` to
  refresh the recipe.
- **`omnimem note ... --json` flag was a no-op** — every note CLI verb
  emitted indented JSON regardless of the flag. The non-JSON path now
  renders `key=value` summary lines, list counts, and indented multi-line
  bodies; `--json` still produces machine-readable JSON.
- **`omni_search.federate_with_notes`** logs federation failures to stderr
  instead of swallowing them silently.
- Replaced deprecated `datetime.utcnow()` with timezone-aware UTC across
  `omni_metadata`, `omni_add`, `omni_ops`, `omni_reindex` (output strings
  byte-for-byte identical).

### Performance

- **MCP server caches `OmniRuntime` and `NoteRuntime`** per `root_dir`
  across `tools/call` requests. A long-running Claude Desktop / Copilot
  session no longer reloads the embedding model on every tool invocation
  (~1-2 s saved per call). MCP `import_file` now prefers the warm search
  service.
- **Warm search service hosts notes and codemap collections** in addition
  to `omnimem_core`. CLI `note search` and `codemap query` now try the
  service first and fall back to the in-process path on
  `SearchServiceUnavailable`. Use `--direct` to bypass. Same effect as MCP
  caching but for terminal users running CLI commands across multiple
  shells.

### Internal

- `omni_note_index.search_notes` accepts an optional `runtime=` kwarg so
  cached callers (MCP, warm service) don't re-construct on every call.
- New tests: `test_mcp_runtime_cache.py` (5), `test_hook_gated_reindex.py`
  (7), `test_print_human.py` (9), `test_service_notes_codemap.py` (8).
- Default user-data and user-config helpers in `omni_paths.py` now return a
  single `~/.omnimem/` location across OSes (`get_default_user_data_root`,
  `get_default_user_config_root`).

## v1.2.4 - README Cleanup For v1.2.x Surface

A documentation patch — no runtime code changes.

The README from "Core Architecture" downward was last touched in the v1.8.x era and had drifted significantly from the v1.2.x CLI surface. v1.2.4 rewrites the affected sections so the README documents what the binary actually does today.

- **Replaced** `## How to integrate with AI Agents (Crucial Step)` (manual prompt-injection of three rules) with `## How to wire OmniMem into your agent CLI` documenting `omnimem quickstart`, `omnimem init --agent ...`, and `omnimem hook install`. The injected protocol now correctly describes MCP-tools-first, CLI-fallback, and references `note_search` / `note_new` / `search_all` / etc.
- **Rewrote** `## Unified CLI Usage` from a 14-bullet flat list into a topic-grouped reference covering all 20 subcommands: setup/diagnostics, documents (with `--all` and `--at-date` examples), notes (12 verbs + canvas), codemap, init, hook, mcp, redact, vault round-trip, and config. Replaced the unfortunate `"Server password is 123"` example with a non-credential one.
- **Replaced** `## Legacy standalone scripts` flat bullet list with a code-block reference plus a clear note that note / codemap / init / hook / mcp / quickstart / redact are unified-CLI-only.
- **Renamed** `## Development` to split into `## Documentation` (user-facing + contributor-facing index across QUICKSTART / TROUBLESHOOTING / FAQ / notes / codemap / hooks / redact / benchmarks / integrations / CONTRIBUTING) and `## Development` (test / benchmark / build commands plus reference docs).
- **Clarified** the `Installation` section: added the one-line installer block, made the `omnimem quickstart` follow-up explicit in every install mode, and documented that `<OMNIMEM_HOME>/.omnimem_models/` is in the OS user-data dir (not inside the repo).
- **Clarified** `## Offline-safe runtime`: model dir lives in `OMNIMEM_HOME`, not the repo; HF cache fallback behavior; `OMNIMEM_ALLOW_MODEL_DOWNLOAD` semantics.
- README headline bumped to v1.2.4.

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

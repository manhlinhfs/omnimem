# OmniMem Roadmap

This roadmap is intentionally conservative: each minor release should have one main theme, clear acceptance criteria, and a small enough scope to ship without weakening quality gates.

## Completed

### v1.2.0 - Initial Public Release
- Document RAG (`omnimem add` / `import` / `search`)
- Structured notes module with Markdown vault and `omnimem_notes` ChromaDB collection
- Multi-language codemap (Python / JS / TS / Go / Rust) with per-symbol records in `omnimem_codemap`
- Multi-CLI integration (`omnimem init --agent claude|codex|gemini|cursor|all`) and lifecycle hooks (`omnimem hook install --agent claude|codex|all`)
- Stdio MCP server with six introspectable tools
- Federated search across all three collections (`omnimem search --all`) and temporal `--at-date` filter
- Obsidian Canvas export and secret redaction utilities
- Vault round-tripping through `backup` / `export` / `restore`
- Reproducible benchmark suite under `benchmarks/` covering parser accuracy, latency, and retrieval recall

## Planned

### v1.3.0 - Adoption And Quality (tentative)
- README rewritten as a landing page with quick install, demo GIF, and 30-second value prop
- `omnimem doctor --quickstart` interactive first-run guide
- Issue templates and `CONTRIBUTING.md` so external contributors can land changes
- Automated end-to-end harness that drives Claude Code in CI to verify `init` + `hook install` flows actually result in tool calls

### v1.4.0 - Retrieval Quality
- Hybrid search (BM25 + vector) so recall@1 stops being chance-level on duplicate-topic corpora
- Optional reranker (Cohere / Voyage / local) gated behind config
- LOCOMO-style long-conversation benchmark for apples-to-apples comparison against Mem0 / MemPalace

### v1.5.0 - Smart Memory Maintenance
- LLM-driven note consolidation (`omnimem consolidate --since 7d`) gated by opt-in flag
- Real-codebase codemap accuracy benchmark on Django / React / Kubernetes / actix-web etc.
- Tree-sitter or subprocess parsers behind a feature flag for higher-fidelity multi-language codemap
- Documentation comments (`///`, JSDoc, Go doc comments) lifted into codemap notes

### v1.6.0+ - Stretch goals
- Caller / callee edges between codemap symbols
- Project-aware codemap build (Nx, Turborepo, Cargo workspaces, Go workspaces)
- `omnimem add --redact` / `omnimem import --redact` opt-in switches
- Multi-machine vault sync (cloud bucket / git remote)
- OpenTelemetry-based observability for the warm service path

## Release Discipline

- `1.x` minor releases must remain backward-compatible unless explicitly documented.
- Patch releases are for bug fixes and regressions only.
- Every release should have: a GitHub issue, changelog entry, docs updates, passing tests, and an OmniMem snapshot.

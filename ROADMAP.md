# OmniMem Roadmap

This roadmap is intentionally conservative: each minor release should have one main theme, clear acceptance criteria, and a small enough scope to ship without weakening quality gates.

## Completed

### v1.1.0
- Shared version source via `VERSION` and `omni_version.py`
- Runtime health diagnostics via `omni_doctor.py`

### v1.2.0
- Safe self-update flow via `omni_update.py`

### v1.3.0
- Stdlib-based tests, CI, changelog, and release checklist

### v1.4.0
- Unified `omnimem` CLI and cross-platform launchers

### v1.5.0 - Search Precision Foundation
- Normalize metadata creation for new records
- Add `search` filters for `source`, `since`, `until`, and `mime_type`
- Document search filter behavior and compatibility notes

### v1.6.0 - Packaging And Install Modes
- Add package metadata and console entry points
- Support installation without relying on a raw git clone
- Detect install mode in `update` and explain unsupported flows clearly

### v1.7.0 - Config And Operations
- Added a shared JSON config layer with clear precedence rules
- Added `backup`, `export`, and `restore` operations
- Expanded `doctor` output with effective config reporting

### v1.8.0 - Retrieval Quality
- Replaced blank-line chunking with a structure-aware chunker for prose, code, and OCR-like imports
- Added chunk size and overlap controls through shared config
- Added richer import metadata and a supported `reindex` workflow for older DBs

## Planned

### v1.9.0 - Security And Hygiene
- Add secret redaction rules for obvious credentials
- Add safety warnings for risky import/add flows
- Consider a dedicated secret storage path outside the vector DB

Exit criteria:
- Common token patterns are not indexed raw by default
- Docs explain safe OmniMem usage in ops-heavy environments

## Release Discipline

- `1.x` minor releases must remain backward-compatible unless explicitly documented.
- Patch releases are for bug fixes and regressions only.
- Every release should have: a GitHub issue, changelog entry, docs updates, passing tests, and an OmniMem snapshot.

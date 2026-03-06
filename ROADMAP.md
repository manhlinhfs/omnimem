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

## Planned

### v1.5.0 - Search Precision Foundation
- Normalize metadata creation for new records
- Add `search` filters for `source`, `since`, `until`, and `mime_type`
- Document search filter behavior and compatibility notes

Exit criteria:
- `omnimem search` supports the new metadata filters
- Old records remain searchable without a migration step
- Tests cover metadata normalization and filter wiring

### v1.6.0 - Packaging And Install Modes
- Add package metadata and console entry points
- Support installation without relying on a raw git clone
- Detect install mode in `update` and explain unsupported flows clearly

Exit criteria:
- `pip install .` exposes `omnimem`
- Docs explain clone mode vs package mode

### v1.7.0 - Config And Operations
- Add a config file with clear precedence rules
- Add backup/export/restore commands
- Expand doctor output with effective config reporting

Exit criteria:
- Users can move DB/model paths without editing code
- Export/restore roundtrips are tested

### v1.8.0 - Retrieval Quality
- Improve chunking beyond blank-line splits
- Add chunk sizing/overlap controls
- Explore better result grouping and reranking

Exit criteria:
- Import behavior is measurably better on text/code/document fixtures
- Retrieval regressions are covered by tests

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

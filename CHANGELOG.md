# Changelog

## v1.5.0
- Added shared metadata helpers in `omni_metadata.py` for timestamps, tags, and search filter parsing
- Added `search` filters for `source`, `since`, `until`, and `mime_type` in both `omni_search.py` and `omnimem search`
- Normalized metadata creation for new note/import records without requiring a migration
- Added `ROADMAP.md` and `docs/search-filters.md`
- Expanded stdlib-only tests to cover metadata normalization and filter wiring

## v1.4.0
- Added `omnimem.py` as a unified OmniMem CLI with `add`, `search`, `import`, `delete`, `doctor`, `bootstrap`, `update`, and `version` subcommands
- Added cross-platform repo launchers: `omnimem`, `omnimem.ps1`, and `omnimem.bat`
- Kept the legacy standalone `omni_*.py` scripts working for backward compatibility
- Added CLI coverage for the new unified command and launcher metadata

## v1.3.0
- Added a stdlib-based test suite under `tests/`
- Added GitHub Actions CI for compile, shell, and unittest quality gates
- Added release metadata files: `CHANGELOG.md` and `docs/release-checklist.md`
- Refactored heavyweight imports to be lazier so lightweight CLI paths are easier to validate

## v1.2.0
- Added `omni_update.py` for safe self-updates on tracked branches
- Added update checks with `--check` and `--json`
- Added dirty worktree protection, dependency refresh, and post-update bootstrap refresh

## v1.1.0
- Added `VERSION` and `omni_version.py` as the shared version source
- Added `omni_doctor.py` with human-readable and JSON diagnostics
- Added `--version` support to core CLI commands
- Aligned setup behavior across `setup.sh`, `setup.ps1`, and `setup.bat`

## v1.0.0
- Initial OmniMem public release

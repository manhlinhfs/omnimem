# Refactor Plan: `omnimem.py` + flat `omni_*.py` → `omnimem/` Package (v1.3.0)

**Status**: proposed, not yet executed.
**Target release**: v1.3.0 (semver: minor bump because import surface changes — breaking for any downstream code that imports `omni_X` directly).
**Estimated effort**: 3–5 hours including tests, manual verification, and CI cycles.

## Why

The repo currently has 28 top-level Python modules at the root:
`omnimem.py` plus 27 `omni_*.py` files. They cross-import each other
heavily (70+ `from omni_X import ...` statements). The flat layout
keeps every internal module visible as a top-level name on
`sys.path` and clutters the root with 28+ files.

Moving everything into a single `omnimem/` package is the standard
Python project shape. It cleans the root, namespaces internals, and
unlocks better IDE / mypy / isort integration.

This refactor was deferred from v1.2.8 (which only moved setup scripts
and the example config) because:

1. v1.2.7 had just shipped a fix predicated on `omnimem` being a
   single-file module. We wanted a cooldown before another structural
   change.
2. It is a breaking change to the import surface. Any downstream code
   doing `from omni_hooks import ...` or `import omni_paths` breaks.
3. The conversion needs careful validation — 70+ import sites,
   dynamic imports inside functions, lazy imports for heavy deps,
   tests that import directly, docs with code samples.

## Why this is safe to do *now* (after v1.2.7 ships)

The earlier guidance "do not convert `omnimem.py` to a package" was
narrowly scoped to the v1.2.6 → v1.2.7 fix window. The actual
constraint that fix introduced is:

- The console script `omnimem` (declared in `[project.scripts]
  omnimem = "omnimem:main"`) must keep working.
- Migration logic in `omni_hooks` / `omni_init` must keep detecting
  the legacy `<python> -m omnimem` shape so existing user configs are
  rewritten on next invocation.

Both survive the refactor:

- The entry point `omnimem:main` resolves whether `omnimem` is a
  module (`omnimem.py`) or a package (`omnimem/__init__.py` exporting
  `main`). No change to `pyproject.toml [project.scripts]`.
- Migration logic only **scans** for `-m omnimem` patterns in user
  config files. It never invokes `python -m omnimem` itself. The
  detection regex stays valid forever.

A useful side benefit: adding `omnimem/__main__.py` makes
`python -m omnimem` work again as defence in depth, since runpy will
find the package's `__main__.py`. We do not advertise this — the
console script is still canonical — but it eliminates the original
v1.2.6 footgun entirely.

## Target shape

```
.
├── omnimem/
│   ├── __init__.py                  # exports `main`
│   ├── __main__.py                  # `python -m omnimem` defence in depth
│   ├── cli.py                       # was omnimem.py — argparse + dispatcher
│   ├── add.py                       # was omni_add.py
│   ├── bootstrap.py                 # was omni_bootstrap.py
│   ├── canvas.py
│   ├── chunking.py
│   ├── codemap.py
│   ├── config.py
│   ├── del_.py                      # avoid Python `del` keyword collision
│   ├── doctor.py
│   ├── embeddings.py
│   ├── hooks.py
│   ├── import_.py                   # avoid `import` keyword collision
│   ├── init.py                      # avoid `__init__` shadowing — see note
│   ├── mcp.py
│   ├── metadata.py
│   ├── note.py
│   ├── note_index.py
│   ├── ops.py
│   ├── paths.py
│   ├── quickstart.py
│   ├── redact.py
│   ├── reindex.py
│   ├── search.py
│   ├── search_core.py
│   ├── service.py
│   ├── update.py
│   ├── vault.py
│   └── version.py
├── examples/
├── scripts/
├── tests/
├── docs/
├── benchmarks/
├── pyproject.toml
├── README.md, README_vi.md, README_ru.md
├── CHANGELOG.md, ROADMAP.md, QUICKSTART.md, TROUBLESHOOTING.md, CONTRIBUTING.md
├── VERSION
├── MANIFEST.in
├── requirements.txt
├── install.sh
├── omnimem, omnimem.bat, omnimem.ps1     # launchers stay at root
└── .gitignore, .github/, .claude/
```

Root drops from ~46 (post-v1.2.8) to ~25 entries.

### Naming notes

- `omni_del.py` → **`del_.py`**: `del` is a Python keyword, so `del.py`
  is illegal as a module name (`from omnimem import del` would not
  parse). Trailing underscore is the conventional escape.
- `omni_import.py` → **`import_.py`**: same reason.
- `omni_init.py` → conflict with package `__init__.py` is a *spelling*
  conflict only; `omnimem/init.py` is a perfectly legal sibling
  module. Importable as `from omnimem import init` or
  `from omnimem.init import ...`. **No rename needed.**
- Everything else: drop the `omni_` prefix.

## Step-by-step plan

Each step is a separate commit on the refactor branch. CI must pass
between commits where feasible.

### Step 1 — Create the package skeleton

1. `mkdir omnimem`
2. `touch omnimem/__init__.py omnimem/__main__.py`
3. `omnimem/__init__.py` — initially just `from omnimem.cli import main`
4. `omnimem/__main__.py` — `from omnimem.cli import main; main()`

**No code moved yet.** Verify `omnimem.py` still imports and console
script still works (the existing `omnimem.py` shadows the new package
because both can't coexist as the importable name — actually they
**can't** coexist; this step is part of step 2).

Skip step 1 in isolation; merge into step 2.

### Step 2 — Move `omnimem.py` into the package

1. `git mv omnimem.py omnimem/cli.py`
2. Create `omnimem/__init__.py`:
   ```python
   from omnimem.cli import main

   __all__ = ["main"]
   ```
3. Create `omnimem/__main__.py`:
   ```python
   from omnimem.cli import main

   raise SystemExit(main())
   ```
4. Update `pyproject.toml`:
   - Remove `omnimem` from `py-modules`.
   - Eventually replace the whole `py-modules = [...]` block with
     `packages = ["omnimem"]` (after step 4).
5. **At this point**, `from omni_hooks import ...` inside `cli.py`
   still references the old flat modules. They still exist at root
   — the package doesn't shadow them yet. CI should still pass.

### Step 3 — Move `omni_*.py` modules

For each of the 27 modules:

1. `git mv omni_X.py omnimem/X.py` (with rename if X is a keyword).
2. Inside the new file, rewrite `from omni_Y import ...` →
   `from omnimem.Y import ...`.

Mechanical via codemod:

```bash
# inside the refactor branch, after step 2
for f in omni_*.py; do
    base="${f#omni_}"
    base="${base%.py}"
    case "$base" in
        del)    new="del_" ;;
        import) new="import_" ;;
        *)      new="$base" ;;
    esac
    git mv "$f" "omnimem/$new.py"
done

# rewrite imports across the entire codebase
python - <<'PY'
import pathlib, re

renames = {
    "omni_del": "omnimem.del_",
    "omni_import": "omnimem.import_",
}
# default: omni_<name> → omnimem.<name>
def rewrite(match):
    old = match.group(1)
    if old in renames:
        return f"from {renames[old]} import"
    name = old[len("omni_"):]
    return f"from omnimem.{name} import"

pat_from = re.compile(r"from\s+(omni_[a-z_]+)\s+import")

def rewrite_import(match):
    old = match.group(1)
    if old in renames:
        return f"import {renames[old]}"
    name = old[len("omni_"):]
    return f"import omnimem.{name}"

pat_import = re.compile(r"import\s+(omni_[a-z_]+)(?!\w)")

for path in pathlib.Path(".").rglob("*.py"):
    if "/.git/" in str(path) or "/venv/" in str(path):
        continue
    text = path.read_text(encoding="utf-8")
    new = pat_from.sub(rewrite, text)
    new = pat_import.sub(rewrite_import, new)
    if new != text:
        path.write_text(new, encoding="utf-8")
        print(f"rewrote {path}")
PY
```

Manual review of the codemod output before committing.

### Step 4 — Update `pyproject.toml`

```toml
[tool.setuptools]
packages = ["omnimem"]
# remove the entire py-modules block
```

### Step 5 — Update CI workflow

`.github/workflows/ci.yml`: replace the explicit `compileall` list
with `python -m compileall omnimem/ tests/ benchmarks/`.

### Step 6 — Update launcher scripts

The repo-root launchers (`omnimem`, `omnimem.bat`, `omnimem.ps1`)
currently exec `python omnimem.py`. After the refactor that file no
longer exists. Switch to `python -m omnimem` (now safe because of
`__main__.py`).

### Step 7 — Update tests

`tests/test_*.py` files contain ~25 `from omni_X import ...` lines.
The codemod in step 3 should rewrite these too (the regex applies to
the whole tree). Manual review the diff to confirm.

### Step 8 — Update docs

- `docs/redact.md` line 45 (only doc with a Python `from omni_redact`
  example).
- Anywhere else mentioning `omni_X.py` in narrative — let `git grep`
  catch them.

### Step 9 — Update v1.2.7 migration logic

`omni_hooks.migrate_legacy_commands` and
`omni_init.migrate_legacy_mcp_commands` keep detecting `-m omnimem` in
user configs (no change). The detection regex matches whether or not
the local package is a module or a package — it inspects user files
on disk, not the local codebase.

After the refactor, the migration's *output* (the new launcher path)
is unchanged: it's the `omnimem` console script. The new
`__main__.py` does **not** change the migration's behaviour because
the migration never emits `-m omnimem`.

**Sanity check**: run the migration on a v1.2.6-shaped config inside
the test suite (already covered by `test_hook_migration.py`).

### Step 10 — Update memory + release notes

- Update `~/.claude/projects/.../memory/project_module_layout.md`:
  the "single-file module" claim is now false. Re-frame around the
  console-script invariant.
- v1.3.0 CHANGELOG entry must explicitly call out the import-surface
  break for downstream consumers.

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Dynamic imports / `getattr` references to `omni_X` we missed in codemod | Audit before commit: `git grep -E '\bomni_[a-z]'` after the codemod. Should return zero hits in `*.py` (only docs / comments may legitimately mention the legacy names). |
| Tests pass locally but break on Windows / macOS due to case-sensitivity in renames | The 9-cell CI matrix catches this. Don't merge until all 9 cells are green. |
| Downstream user scripts importing `omni_hooks` directly break | This is the breaking change. Document loudly in CHANGELOG. Anyone building on top of OmniMem internals re-imports as `from omnimem.hooks import ...`. |
| Editable install (`pip install -e .`) finds both old `omni_X.py` (still in working tree before commit) and new `omnimem/X.py` after step 3 | Delete the old files in the same commit as the move. Use `git mv`, not copy + remove. |
| `omnimem/__main__.py` makes `python -m omnimem` work again, contradicting v1.2.7 narrative ("do not use `-m omnimem`") | Treat `__main__.py` as defence in depth, not a recommended path. CHANGELOG: "console script is still canonical; `python -m omnimem` works as a fallback but is not advertised." |
| Tests that hard-coded the count of `py-modules` or specific module-name lists | None known. CI catches via `compileall` failure. |

## Rollback plan

If anything goes wrong post-merge:

1. `git revert` the merge commit on `main`.
2. Re-tag the previous v1.2.x release.
3. The v1.3.0 GitHub release stays as a marker for users to know it
   was attempted; mark it as pre-release / withdrawn in the
   description.

## Open questions

1. Should `omnimem/__init__.py` re-export public API beyond `main` so
   downstream code can `from omnimem import HookError, ...` directly?
   → Defer. Re-exports only on demand.
2. Drop `__main__.py` to keep the v1.2.7 narrative clean? → No. The
   one-liner `from omnimem.cli import main; raise SystemExit(main())`
   is harmless and gives users a fallback when their console-script
   shim is missing.
3. `src/` layout instead of flat? → No. Adds nesting without buying
   anything for a single-package repo. Reserve for projects with
   multiple distributions.

## Acceptance checklist

- [ ] `python -m unittest discover -s tests` — 250+ pass on local.
- [ ] 9-cell CI matrix all green.
- [ ] `pip install -e .` then `omnimem --version` works.
- [ ] `python -m omnimem --version` works (defence in depth).
- [ ] `./omnimem --version` (launcher script) works.
- [ ] `omnimem hook --status` runs the auto-migration on a
      synthetic v1.2.6-style settings file and rewrites it.
- [ ] No `omni_X` references remain in `*.py` source. Test:
      `git grep -nE '\b(from\s+omni_|import\s+omni_)' '*.py'` returns
      nothing.
- [ ] CHANGELOG v1.3.0 entry calls out the import-surface break.
- [ ] `docs/refactor-package-layout-v1.3.0.md` updated to reflect
      what actually shipped (or deleted, depending on preference).

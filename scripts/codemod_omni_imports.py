"""One-shot codemod: rewrite legacy `omni_X` imports to the new
`omnimem.X` package layout. Used during the v1.3.0 refactor.

After step 1 (file moves), every `from omni_X import Y` and
`import omni_X` in the codebase still references the legacy flat
module name. This script rewrites them in place across the whole
repo. Idempotent — running twice is a no-op.

Run from repo root:

    python scripts/codemod_omni_imports.py

Then `git diff` for review and remove this script (it's a one-time
tool, not part of the runtime package).
"""

import pathlib
import re
import sys

# Special-case modules whose new file name needed a trailing underscore
# because the natural name is a Python keyword (`del`, `import`).
RENAMES = {
    "omnimem.del_": "omnimem.del_",
    "omnimem.import_": "omnimem.import_",
}


def target_module(legacy: str) -> str:
    if legacy in RENAMES:
        return RENAMES[legacy]
    return "omnimem." + legacy[len("omni_"):]


# `from omni_X import Y` (single-line; multi-line `from ... import (` also
# matches because we only rewrite the prefix).
PAT_FROM = re.compile(r"\bfrom\s+(omni_[a-z_]+)\s+import\b")

# `import omni_X` (not followed by another word char so we don't match
# `import omnimem.xstuff as omni_xstuff`). When rewriting, alias back to the legacy name so
# any body references like `omni_X.foo` keep working without further
# editing.
PAT_IMPORT = re.compile(r"\bimport\s+(omni_[a-z_]+)(?!\w)")

# Module-path strings used by `mock.patch("omni_X.attr")` and
# `patch.dict(sys.modules, {"omni_X": ...})`. The dot-or-quote follower
# distinguishes module path strings from file names like `"omni_X.py"`.
PAT_MOD_STRING = re.compile(r'"(omni_[a-z_]+)(?=[".])')


def rewrite_from(match: re.Match) -> str:
    legacy = match.group(1)
    return f"from {target_module(legacy)} import"


def rewrite_import(match: re.Match) -> str:
    legacy = match.group(1)
    return f"import {target_module(legacy)} as {legacy}"


def rewrite_mod_string(match: re.Match) -> str:
    legacy = match.group(1)
    target = target_module(legacy)
    return f'"{target}'


def should_skip(path: pathlib.Path) -> bool:
    s = str(path).replace("\\", "/")
    skip_fragments = (
        "/.git/",
        "/venv/",
        "/.omnimem",
        "/__pycache__/",
        "/.claude/",
        "/omnimem.egg-info/",
        "/build/",
        "/dist/",
    )
    return any(frag in s for frag in skip_fragments)


def main() -> int:
    root = pathlib.Path(".")
    rewritten = []
    skipped = []
    for path in root.rglob("*.py"):
        if should_skip(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            skipped.append(str(path))
            continue
        new = PAT_FROM.sub(rewrite_from, text)
        new = PAT_IMPORT.sub(rewrite_import, new)
        new = PAT_MOD_STRING.sub(rewrite_mod_string, new)
        if new != text:
            path.write_text(new, encoding="utf-8")
            rewritten.append(str(path))
    print(f"rewrote {len(rewritten)} files")
    for p in rewritten:
        print(f"  {p}")
    if skipped:
        print(f"\nskipped {len(skipped)} files (non-UTF-8):")
        for p in skipped:
            print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

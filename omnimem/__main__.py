"""Defence-in-depth entry point for `python -m omnimem`.

The canonical way to invoke OmniMem is the `omnimem` console script that
`pip install` places next to the active interpreter. `python -m omnimem`
is supported as a fallback so users coming from older OmniMem versions
(which advertised that form) continue to work after upgrading. See
v1.2.7 / v1.3.0 CHANGELOG entries for the history.
"""

from omnimem.cli import main

raise SystemExit(main())

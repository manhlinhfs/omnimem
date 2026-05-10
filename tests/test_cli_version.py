import subprocess
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
EXPECTED_BANNER = f"OmniMem v{(ROOT_DIR / 'VERSION').read_text(encoding='utf-8').strip()}"

# Modules that historically lived as standalone scripts at the repo root and
# now live inside the `omnimem/` package. Each still carries its own argparse
# `--version` flag, runnable via `python -m omnimem.<name>`.
MODULES = (
    "omnimem",          # the package entry — `python -m omnimem --version`
    "omnimem.add",
    "omnimem.search",
    "omnimem.import_",
    "omnimem.del_",
    "omnimem.bootstrap",
    "omnimem.ops",
    "omnimem.reindex",
    "omnimem.service",
    "omnimem.doctor",
    "omnimem.update",
)


class TestCliVersion(unittest.TestCase):
    def test_version_flag_works_for_core_modules(self):
        env = {**__import__("os").environ, "PYTHONPATH": str(ROOT_DIR)}
        for module_name in MODULES:
            with self.subTest(module=module_name):
                result = subprocess.run(
                    [sys.executable, "-m", module_name, "--version"],
                    text=True,
                    capture_output=True,
                    env=env,
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                self.assertIn(EXPECTED_BANNER, result.stdout.strip())

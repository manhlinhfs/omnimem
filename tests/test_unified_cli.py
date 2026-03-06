import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
EXPECTED_BANNER = f"OmniMem v{(ROOT_DIR / 'VERSION').read_text(encoding='utf-8').strip()}"
SUBCOMMANDS = (
    "add",
    "search",
    "import",
    "delete",
    "doctor",
    "bootstrap",
    "update",
    "backup",
    "export",
    "restore",
    "reindex",
    "version",
)


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(ROOT_DIR / "omnimem.py"), *args],
        text=True,
        capture_output=True,
    )


class TestUnifiedCli(unittest.TestCase):
    def test_top_level_help_lists_supported_subcommands(self):
        result = run_cli("--help")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        for name in SUBCOMMANDS:
            with self.subTest(subcommand=name):
                self.assertIn(name, result.stdout)

    def test_version_subcommand_prints_release_banner(self):
        result = run_cli("version")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(EXPECTED_BANNER, result.stdout.strip())

    def test_search_help_is_wired_through_unified_cli(self):
        result = run_cli("search", "--help")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("--full", result.stdout)
        self.assertIn("--json", result.stdout)
        self.assertIn("--source", result.stdout)
        self.assertIn("--since", result.stdout)
        self.assertIn("--until", result.stdout)
        self.assertIn("--mime-type", result.stdout)

    def test_cross_platform_launchers_exist(self):
        self.assertTrue((ROOT_DIR / "omnimem").exists())
        self.assertTrue((ROOT_DIR / "omnimem.ps1").exists())
        self.assertTrue((ROOT_DIR / "omnimem.bat").exists())
        self.assertTrue((ROOT_DIR / "pyproject.toml").exists())

    @unittest.skipUnless(os.name == "posix", "POSIX launcher test only applies on POSIX hosts")
    def test_posix_launcher_prints_version(self):
        result = subprocess.run(
            [str(ROOT_DIR / "omnimem"), "--version"],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn(EXPECTED_BANNER, result.stdout.strip())

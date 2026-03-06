import unittest
from pathlib import Path

from omni_version import get_version, get_version_banner

ROOT_DIR = Path(__file__).resolve().parents[1]


class TestOmniVersion(unittest.TestCase):
    def test_version_matches_file(self):
        expected = (ROOT_DIR / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(get_version(), expected)

    def test_version_banner_uses_version(self):
        self.assertEqual(get_version_banner(), f"OmniMem v{get_version()}")

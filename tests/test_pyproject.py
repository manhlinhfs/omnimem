import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


class TestPyproject(unittest.TestCase):
    def test_pyproject_declares_console_entry_point(self):
        pyproject = (ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('name = "omnimem"', pyproject)
        self.assertIn('[project.scripts]', pyproject)
        self.assertIn('omnimem = "omnimem:main"', pyproject)

    def test_pyproject_uses_dynamic_version_from_version_file(self):
        pyproject = (ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('dynamic = ["version"]', pyproject)
        self.assertIn('version = {file = ["VERSION"]}', pyproject)

import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


class TestReleaseMetadata(unittest.TestCase):
    def test_changelog_contains_current_version(self):
        version = (ROOT_DIR / "VERSION").read_text(encoding="utf-8").strip()
        changelog = (ROOT_DIR / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## v{version}", changelog)

    def test_release_checklist_exists(self):
        checklist = ROOT_DIR / "docs" / "release-checklist.md"
        self.assertTrue(checklist.exists())
        self.assertIn("Release Checklist", checklist.read_text(encoding="utf-8"))

    def test_ci_workflow_exists(self):
        workflow = ROOT_DIR / ".github" / "workflows" / "ci.yml"
        self.assertTrue(workflow.exists())

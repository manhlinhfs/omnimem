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

    def test_roadmap_exists(self):
        roadmap = ROOT_DIR / "ROADMAP.md"
        self.assertTrue(roadmap.exists())
        self.assertIn("OmniMem Roadmap", roadmap.read_text(encoding="utf-8"))

    def test_search_filter_docs_exist(self):
        search_filters = ROOT_DIR / "docs" / "search-filters.md"
        self.assertTrue(search_filters.exists())
        self.assertIn("Search Filters", search_filters.read_text(encoding="utf-8"))

    def test_search_service_docs_exist(self):
        search_service = ROOT_DIR / "docs" / "search-service.md"
        self.assertTrue(search_service.exists())
        self.assertIn("Warm Runtime Service", search_service.read_text(encoding="utf-8"))

    def test_install_mode_docs_exist(self):
        install_modes = ROOT_DIR / "docs" / "install-modes.md"
        self.assertTrue(install_modes.exists())
        self.assertIn("Install Modes", install_modes.read_text(encoding="utf-8"))

    def test_configuration_docs_exist(self):
        configuration = ROOT_DIR / "docs" / "configuration.md"
        self.assertTrue(configuration.exists())
        self.assertIn("Configuration", configuration.read_text(encoding="utf-8"))

    def test_operations_docs_exist(self):
        operations = ROOT_DIR / "docs" / "operations.md"
        self.assertTrue(operations.exists())
        self.assertIn("Operations", operations.read_text(encoding="utf-8"))

    def test_chunking_docs_exist(self):
        chunking = ROOT_DIR / "docs" / "chunking.md"
        self.assertTrue(chunking.exists())
        self.assertIn("Chunking", chunking.read_text(encoding="utf-8"))

    def test_reindexing_docs_exist(self):
        reindexing = ROOT_DIR / "docs" / "reindexing.md"
        self.assertTrue(reindexing.exists())
        self.assertIn("Reindexing", reindexing.read_text(encoding="utf-8"))

    def test_example_config_exists(self):
        example = ROOT_DIR / "omnimem.example.json"
        self.assertTrue(example.exists())
        self.assertIn("\"db_dir\"", example.read_text(encoding="utf-8"))

    def test_manifest_exists(self):
        manifest = ROOT_DIR / "MANIFEST.in"
        self.assertTrue(manifest.exists())
        self.assertIn("recursive-include docs", manifest.read_text(encoding="utf-8"))

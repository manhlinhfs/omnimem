import os
import tempfile
import unittest
from pathlib import Path

from omni_init import (
    MARKER_END,
    MARKER_PATTERN,
    MARKER_START,
    install_rule_block,
    uninstall_rule_block,
)


class TestInitIdempotent(unittest.TestCase):
    def setUp(self):
        self.tmp_home = tempfile.mkdtemp()
        self.tmp_cwd = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp_home, ignore_errors=True)
        shutil.rmtree(self.tmp_cwd, ignore_errors=True)

    def _install(self, agent, scope="user"):
        return install_rule_block(
            agent,
            scope=scope,
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )

    def _read(self, path):
        return Path(path).read_text(encoding="utf-8")

    def test_install_writes_marked_block(self):
        result = self._install("claude")
        body = self._read(result["target"])
        self.assertIn(MARKER_START, body)
        self.assertIn(MARKER_END, body)
        self.assertIn("OmniMem Protocol", body)

    def test_reinstall_is_idempotent(self):
        first = self._install("claude")
        first_body = self._read(first["target"])
        second = self._install("claude")
        second_body = self._read(second["target"])
        self.assertEqual(first_body, second_body)

    def test_install_preserves_surrounding_content(self):
        target = Path(self.tmp_home) / ".claude" / "CLAUDE.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Existing user rules\n\nNo touchy.\n", encoding="utf-8")

        self._install("claude")
        body = self._read(target)
        self.assertIn("# Existing user rules", body)
        self.assertIn("No touchy.", body)
        self.assertIn(MARKER_START, body)

    def test_reinstall_replaces_only_marked_block(self):
        target = Path(self.tmp_home) / ".claude" / "CLAUDE.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "# Header\n\n"
            f"{MARKER_START}\nold OmniMem block\n{MARKER_END}\n\n"
            "## Tail content\n",
            encoding="utf-8",
        )
        self._install("claude")
        body = self._read(target)
        self.assertIn("# Header", body)
        self.assertIn("## Tail content", body)
        self.assertNotIn("old OmniMem block", body)
        self.assertIn("OmniMem Protocol", body)

    def test_uninstall_removes_marked_block_only(self):
        target = Path(self.tmp_home) / ".claude" / "CLAUDE.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "# Header\n\nKeep me.\n",
            encoding="utf-8",
        )
        self._install("claude")
        result = uninstall_rule_block(
            "claude",
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        self.assertTrue(result["removed"])
        body = self._read(target)
        self.assertNotIn(MARKER_START, body)
        self.assertIn("Keep me.", body)

    def test_uninstall_when_only_block_existed_removes_file(self):
        result = self._install("claude")
        target = Path(result["target"])
        self.assertTrue(target.exists())
        uninstall_rule_block(
            "claude",
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        self.assertFalse(target.exists())

    def test_uninstall_noop_when_not_installed(self):
        result = uninstall_rule_block(
            "claude",
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        self.assertFalse(result["removed"])

    def test_dry_run_does_not_touch_disk(self):
        target = Path(self.tmp_home) / ".claude" / "CLAUDE.md"
        result = install_rule_block(
            "claude",
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
            dry_run=True,
        )
        self.assertTrue(result.get("would_write"))
        self.assertFalse(target.exists())

    def test_marker_pattern_matches_versioned_blocks(self):
        sample = "# x\n<!-- OMNIMEM:START v9.9 -->\nbody\n<!-- OMNIMEM:END -->\n# y\n"
        match = MARKER_PATTERN.search(sample)
        self.assertIsNotNone(match)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from omnimem.hooks import (
    CODEX_BLOCK_END,
    CODEX_BLOCK_START,
    CODEX_DEFAULT_EVENTS,
    HookError,
    install,
    install_codex_hooks,
    uninstall,
    uninstall_codex_hooks,
)


def _remove_tree(path):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


class TestCodexHookInstaller(unittest.TestCase):
    def setUp(self):
        self.tmp_home = tempfile.mkdtemp()
        self.tmp_cwd = tempfile.mkdtemp()
        self.addCleanup(_remove_tree, self.tmp_home)
        self.addCleanup(_remove_tree, self.tmp_cwd)

    def _config(self):
        return Path(self.tmp_home) / ".codex" / "config.toml"

    def test_install_writes_marked_block_with_default_events(self):
        result = install_codex_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        path = Path(result["target"])
        text = path.read_text(encoding="utf-8")
        self.assertIn(CODEX_BLOCK_START, text)
        self.assertIn(CODEX_BLOCK_END, text)
        for event in CODEX_DEFAULT_EVENTS:
            self.assertIn(f"event = \"{event}\"", text)

    def test_install_preserves_existing_user_toml(self):
        target = self._config()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            '[server]\nmodel = "gpt-4"\n\n[hooks.user_specific]\ncommand = "echo hi"\n',
            encoding="utf-8",
        )
        install_codex_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        text = target.read_text(encoding="utf-8")
        self.assertIn("[server]", text)
        self.assertIn("model = \"gpt-4\"", text)
        self.assertIn("[hooks.user_specific]", text)
        self.assertIn(CODEX_BLOCK_START, text)

    def test_reinstall_replaces_only_marked_block(self):
        install_codex_hooks(
            events=("session_start",),
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        text_first = self._config().read_text(encoding="utf-8")
        install_codex_hooks(
            events=("stop",),
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        text_second = self._config().read_text(encoding="utf-8")
        self.assertEqual(text_second.count(CODEX_BLOCK_START), 1)
        self.assertNotIn("event = \"session_start\"", text_second)
        self.assertIn("event = \"stop\"", text_second)

    def test_uninstall_strips_marked_block(self):
        install_codex_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        result = uninstall_codex_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        self.assertTrue(result["removed"])
        if self._config().exists():
            text = self._config().read_text(encoding="utf-8")
            self.assertNotIn(CODEX_BLOCK_START, text)

    def test_uninstall_removes_file_when_only_marked_block_existed(self):
        install_codex_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        uninstall_codex_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        self.assertFalse(self._config().exists())

    def test_orchestrator_supports_codex_agent(self):
        results = install(["codex"], base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["agent"], "codex")
        self.assertTrue(self._config().exists())

    def test_orchestrator_supports_all_agents(self):
        install(["all"], base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        # Both Claude and Codex configs should exist after install --agent all.
        claude_path = Path(self.tmp_home) / ".claude" / "settings.json"
        codex_path = Path(self.tmp_home) / ".codex" / "config.toml"
        self.assertTrue(claude_path.exists())
        self.assertTrue(codex_path.exists())


if __name__ == "__main__":
    unittest.main()

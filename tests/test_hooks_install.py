import json
import tempfile
import unittest
from pathlib import Path

from omnimem.hooks import (
    DEFAULT_EVENTS,
    OMNIMEM_HOOK_TAG,
    HookError,
    install,
    install_claude_hooks,
    status,
    uninstall,
    uninstall_claude_hooks,
)


def _remove_tree(path):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


class TestClaudeHookInstaller(unittest.TestCase):
    def setUp(self):
        self.tmp_home = tempfile.mkdtemp()
        self.tmp_cwd = tempfile.mkdtemp()
        self.addCleanup(_remove_tree, self.tmp_home)
        self.addCleanup(_remove_tree, self.tmp_cwd)

    def _settings(self, scope="user"):
        if scope == "user":
            return Path(self.tmp_home) / ".claude" / "settings.json"
        return Path(self.tmp_cwd) / ".claude" / "settings.json"

    def test_install_writes_default_events_with_omnimem_tag(self):
        result = install_claude_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        path = Path(result["target"])
        data = json.loads(path.read_text(encoding="utf-8"))
        for event in DEFAULT_EVENTS:
            self.assertIn(event, data["hooks"])
            entries = data["hooks"][event]
            self.assertTrue(
                any(
                    nested.get("tag") == OMNIMEM_HOOK_TAG
                    for entry in entries
                    for nested in entry.get("hooks", [])
                ),
                f"omnimem tag missing in {event}",
            )

    def test_reinstall_is_idempotent(self):
        install_claude_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        first_text = self._settings().read_text(encoding="utf-8")
        install_claude_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        second_text = self._settings().read_text(encoding="utf-8")
        self.assertEqual(first_text, second_text)

    def test_install_preserves_existing_user_hooks(self):
        target = self._settings()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionStart": [
                            {
                                "matcher": "*",
                                "hooks": [{"type": "command", "command": "echo user"}],
                            }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        install_claude_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        data = json.loads(target.read_text(encoding="utf-8"))
        commands = []
        for entry in data["hooks"]["SessionStart"]:
            for nested in entry.get("hooks", []):
                commands.append(nested.get("command", ""))
        self.assertTrue(any("echo user" in cmd for cmd in commands))
        self.assertTrue(any("omnimem" in cmd for cmd in commands))

    def test_uninstall_strips_only_omnimem_entries(self):
        target = self._settings()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionStart": [
                            {
                                "matcher": "*",
                                "hooks": [{"type": "command", "command": "echo user"}],
                            }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        install_claude_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        result = uninstall_claude_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        self.assertTrue(result["removed"])

        data = json.loads(target.read_text(encoding="utf-8"))
        commands = []
        for entry in data["hooks"]["SessionStart"]:
            for nested in entry.get("hooks", []):
                commands.append(nested.get("command", ""))
        self.assertTrue(any("echo user" in cmd for cmd in commands))
        self.assertFalse(any("omnimem" in cmd for cmd in commands))

    def test_uninstall_removes_file_when_only_omnimem_entries_existed(self):
        result = install_claude_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        path = Path(result["target"])
        self.assertTrue(path.exists())
        uninstall_claude_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        self.assertFalse(path.exists())

    def test_install_with_custom_events_subset(self):
        install_claude_hooks(
            events=("SessionStart",),
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        data = json.loads(self._settings().read_text(encoding="utf-8"))
        self.assertIn("SessionStart", data["hooks"])
        self.assertNotIn("Stop", data["hooks"])
        self.assertNotIn("PostToolUse", data["hooks"])

    def test_status_reports_installed_events(self):
        install_claude_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        report = status(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        installed = sorted(report["claude"]["user"]["installed_events"])
        self.assertEqual(set(installed), set(DEFAULT_EVENTS))

    def test_install_orchestrator_routes_to_claude(self):
        results = install(["claude"], base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["agent"], "claude")
        self.assertTrue(self._settings().exists())

    def test_install_unknown_agent_raises(self):
        with self.assertRaises(HookError):
            install(["unknown-agent"], base_home=self.tmp_home, base_cwd=self.tmp_cwd)


if __name__ == "__main__":
    unittest.main()

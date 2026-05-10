"""Migration test for v1.2.6 → v1.2.7 hook + MCP command shape.

v1.2.6 emitted hook commands as `<python> -m omnimem note list ...` and MCP
entries as `{command: <python>, args: [-m, omnimem, mcp, serve]}`. On Python
versions / sys.path layouts where `omnimem` resolves to a package or namespace
package, runpy refuses with "'omnimem' is a package and cannot be directly
executed", which broke Claude/Codex/Gemini hosts.

v1.2.7 switched to the `omnimem` console script. To avoid stranding existing
installations, `migrate_legacy_commands` (hooks) and
`migrate_legacy_mcp_commands` (MCP) rewrite stale entries on the next
`omnimem hook` / `omnimem init` invocation.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omni_hooks import (
    OMNIMEM_HOOK_TAG,
    install_claude_hooks,
    install_codex_hooks,
    migrate_legacy_commands,
)
from omni_init import migrate_legacy_mcp_commands


def _remove_tree(path):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


def _make_fake_console_script(tmpdir):
    bin_dir = Path(tmpdir)
    bin_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".exe" if os.name == "nt" else ""
    python_path = bin_dir / f"python{suffix}"
    omnimem_path = bin_dir / f"omnimem{suffix}"
    python_path.write_text("", encoding="utf-8")
    omnimem_path.write_text("", encoding="utf-8")
    return str(python_path), str(omnimem_path)


def _legacy_claude_settings(python_path):
    return {
        "hooks": {
            "Stop": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                f"{python_path} -m omnimem note list --since today --json"
                            ),
                            "tag": OMNIMEM_HOOK_TAG,
                        }
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "Edit|Write|MultiEdit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"{python_path} -m omnimem hook --gated-reindex",
                            "tag": OMNIMEM_HOOK_TAG,
                        }
                    ],
                }
            ],
        }
    }


class TestHookMigration(unittest.TestCase):
    def setUp(self):
        self.tmp_home = tempfile.mkdtemp()
        self.tmp_cwd = tempfile.mkdtemp()
        self.tmp_bin = tempfile.mkdtemp()
        self.addCleanup(_remove_tree, self.tmp_home)
        self.addCleanup(_remove_tree, self.tmp_cwd)
        self.addCleanup(_remove_tree, self.tmp_bin)
        self.python_path, _ = _make_fake_console_script(self.tmp_bin)

    def _write_legacy_claude_settings(self, scope="user"):
        if scope == "user":
            target = Path(self.tmp_home) / ".claude" / "settings.json"
        else:
            target = Path(self.tmp_cwd) / ".claude" / "settings.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(_legacy_claude_settings(self.python_path)),
            encoding="utf-8",
        )
        return target

    def _claude_commands(self, target):
        data = json.loads(target.read_text(encoding="utf-8"))
        commands = []
        for entries in (data.get("hooks") or {}).values():
            for entry in entries or []:
                for nested in entry.get("hooks") or []:
                    if nested.get("tag") == OMNIMEM_HOOK_TAG:
                        commands.append(nested.get("command", ""))
        return commands

    def test_migration_rewrites_legacy_claude_user_scope(self):
        target = self._write_legacy_claude_settings("user")
        with patch("omni_hooks.sys.executable", self.python_path):
            migrated = migrate_legacy_commands(
                base_home=self.tmp_home, base_cwd=self.tmp_cwd
            )

        self.assertEqual(len(migrated), 1)
        self.assertEqual(migrated[0]["agent"], "claude")
        self.assertEqual(migrated[0]["scope"], "user")
        self.assertEqual(set(migrated[0]["events"]), {"Stop", "PostToolUse"})

        commands = self._claude_commands(target)
        self.assertTrue(commands, "expected migrated commands present")
        for command in commands:
            self.assertNotIn(" -m omnimem", command, f"legacy -m omnimem leaked: {command}")
            self.assertIn("omnimem", command.lower())

    def test_migration_rewrites_legacy_claude_project_scope(self):
        target = self._write_legacy_claude_settings("project")
        with patch("omni_hooks.sys.executable", self.python_path):
            migrated = migrate_legacy_commands(
                base_home=self.tmp_home, base_cwd=self.tmp_cwd
            )
        self.assertTrue(any(m["scope"] == "project" for m in migrated))
        for command in self._claude_commands(target):
            self.assertNotIn(" -m omnimem", command)

    def test_migration_is_idempotent(self):
        target = self._write_legacy_claude_settings("user")
        with patch("omni_hooks.sys.executable", self.python_path):
            first = migrate_legacy_commands(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
            second = migrate_legacy_commands(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [], "second migration should be a no-op")
        for command in self._claude_commands(target):
            self.assertNotIn(" -m omnimem", command)

    def test_migration_leaves_already_modern_settings_untouched(self):
        # Install a fresh (modern) hook block first, then ensure migration is a no-op.
        with patch("omni_hooks.sys.executable", self.python_path):
            install_claude_hooks(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
            target = Path(self.tmp_home) / ".claude" / "settings.json"
            before = target.read_text(encoding="utf-8")
            migrated = migrate_legacy_commands(
                base_home=self.tmp_home, base_cwd=self.tmp_cwd
            )
            after = target.read_text(encoding="utf-8")
        self.assertEqual(migrated, [])
        self.assertEqual(before, after)

    def test_migration_rewrites_untagged_legacy_entries(self):
        """Real-world case: a user hand-installed hooks from docs (or had them
        from a pre-tag OmniMem version), so the entries lack `omnimem-v1`.
        Migration must still detect and rewrite by command shape."""
        target = Path(self.tmp_home) / ".claude" / "settings.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {
                                "matcher": "*",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": (
                                            f"{self.python_path} -m omnimem note list "
                                            "--since today --json"
                                        ),
                                    }
                                ],
                            }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        with patch("omni_hooks.sys.executable", self.python_path):
            migrated = migrate_legacy_commands(
                base_home=self.tmp_home, base_cwd=self.tmp_cwd
            )
        self.assertTrue(migrated, "untagged legacy entry must be migrated")
        for command in self._claude_commands(target):
            self.assertNotIn(" -m omnimem", command, f"legacy -m omnimem leaked: {command}")
        # Also: the user's hand-installed entry stays in place — we don't
        # auto-tag it as ours, just fix the launcher.
        data = json.loads(target.read_text(encoding="utf-8"))
        nested = data["hooks"]["Stop"][0]["hooks"][0]
        self.assertNotIn("tag", nested, "migration must not silently take ownership")

    def test_migration_preserves_duplicate_user_entries(self):
        """User had two identical Stop hook entries (visible in production
        config after manual editing). Migration fixes both, drops neither."""
        target = Path(self.tmp_home) / ".claude" / "settings.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        legacy_cmd = f"{self.python_path} -m omnimem note list --since today --json"
        target.write_text(
            json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {"matcher": "*", "hooks": [{"type": "command", "command": legacy_cmd}]},
                            {"matcher": "*", "hooks": [{"type": "command", "command": legacy_cmd}]},
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        with patch("omni_hooks.sys.executable", self.python_path):
            migrate_legacy_commands(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        data = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(len(data["hooks"]["Stop"]), 2)
        for entry in data["hooks"]["Stop"]:
            for nested in entry["hooks"]:
                self.assertNotIn(" -m omnimem", nested["command"])

    def test_migration_rewrites_legacy_codex_block(self):
        codex_target = Path(self.tmp_home) / ".codex" / "config.toml"
        codex_target.parent.mkdir(parents=True, exist_ok=True)
        codex_target.write_text(
            (
                "# OmniMem hooks (omnimem-v1) - START\n"
                "[hooks.omnimem_stop]\n"
                'event = "stop"\n'
                f'command = "{self.python_path} -m omnimem note list --limit 5 --json"\n'
                "# OmniMem hooks (omnimem-v1) - END\n"
            ),
            encoding="utf-8",
        )
        with patch("omni_hooks.sys.executable", self.python_path):
            migrated = migrate_legacy_commands(
                base_home=self.tmp_home, base_cwd=self.tmp_cwd
            )
        self.assertTrue(any(m["agent"] == "codex" for m in migrated))
        text = codex_target.read_text(encoding="utf-8")
        self.assertNotIn("-m omnimem", text)


class TestMcpMigration(unittest.TestCase):
    def setUp(self):
        self.tmp_home = tempfile.mkdtemp()
        self.tmp_cwd = tempfile.mkdtemp()
        self.tmp_bin = tempfile.mkdtemp()
        self.addCleanup(_remove_tree, self.tmp_home)
        self.addCleanup(_remove_tree, self.tmp_cwd)
        self.addCleanup(_remove_tree, self.tmp_bin)
        self.python_path, _ = _make_fake_console_script(self.tmp_bin)

    def _write_legacy_claude_mcp(self):
        target = Path(self.tmp_home) / ".claude" / "mcp.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "omnimem": {
                            "command": self.python_path,
                            "args": ["-m", "omnimem", "mcp", "serve"],
                        }
                    }
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return target

    def test_legacy_claude_mcp_rewritten(self):
        target = self._write_legacy_claude_mcp()
        with patch("omni_init.sys.executable", self.python_path):
            migrated = migrate_legacy_mcp_commands(
                base_home=self.tmp_home, base_cwd=self.tmp_cwd
            )
        self.assertTrue(any(m["agent"] == "claude" for m in migrated))
        data = json.loads(target.read_text(encoding="utf-8"))
        server = data["mcpServers"]["omnimem"]
        self.assertNotIn("-m", server.get("args", []))
        self.assertEqual(server.get("args"), ["mcp", "serve"])
        self.assertIn("omnimem", server.get("command", "").lower())

    def test_legacy_codex_mcp_block_rewritten(self):
        target = Path(self.tmp_home) / ".codex" / "config.toml"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            (
                "[mcp_servers.omnimem]\n"
                f'command = "{self.python_path}"\n'
                'args = ["-m", "omnimem", "mcp", "serve"]\n'
            ),
            encoding="utf-8",
        )
        with patch("omni_init.sys.executable", self.python_path):
            migrated = migrate_legacy_mcp_commands(
                base_home=self.tmp_home, base_cwd=self.tmp_cwd
            )
        self.assertTrue(any(m["agent"] == "codex" for m in migrated))
        text = target.read_text(encoding="utf-8")
        self.assertNotIn("-m", text)
        self.assertIn("[mcp_servers.omnimem]", text)
        self.assertIn('"mcp"', text)

    def test_mcp_migration_is_idempotent(self):
        target = self._write_legacy_claude_mcp()
        with patch("omni_init.sys.executable", self.python_path):
            first = migrate_legacy_mcp_commands(
                base_home=self.tmp_home, base_cwd=self.tmp_cwd
            )
            second = migrate_legacy_mcp_commands(
                base_home=self.tmp_home, base_cwd=self.tmp_cwd
            )
        self.assertTrue(any(m["agent"] == "claude" for m in first))
        self.assertEqual(second, [])
        data = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(data["mcpServers"]["omnimem"].get("args"), ["mcp", "serve"])


if __name__ == "__main__":
    unittest.main()

"""Regression test for the Windows hook-path bug in v1.2.1 / v1.2.2.

`omnimem hook install` writes the Python interpreter path into Claude Code's
`settings.json`. On Windows `sys.executable` returns
`C:\\Users\\...\\python.exe` (backslashes). Claude Code passes hook commands
through `bash -c`, which interprets backslashes as escape characters and
silently consumes them — so `C:\\Users\\foo\\python.exe` ends up running as
`C:Usersfoopython.exe` and bash reports `command not found`.

The fix is to emit POSIX-style forward slashes when materializing hook /
MCP command entries. Python on Windows accepts forward-slash paths
natively, and bash leaves them alone.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omni_hooks import OMNIMEM_HOOK_TAG, _omnimem_command, install_claude_hooks
from omni_init import _detect_omnimem_command


def _remove_tree(path):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


class TestPathQuoting(unittest.TestCase):
    def test_omnimem_command_uses_forward_slashes(self):
        with patch("omni_hooks.sys.executable", r"C:\Users\foo\venv\Scripts\python.exe"):
            self.assertEqual(
                _omnimem_command(),
                "C:/Users/foo/venv/Scripts/python.exe",
            )

    def test_omnimem_command_unchanged_on_posix_paths(self):
        with patch("omni_hooks.sys.executable", "/usr/bin/python3"):
            self.assertEqual(_omnimem_command(), "/usr/bin/python3")

    def test_omnimem_command_falls_back_to_python(self):
        with patch("omni_hooks.sys.executable", ""):
            self.assertEqual(_omnimem_command(), "python")

    def test_init_detect_command_uses_forward_slashes(self):
        with patch("omni_init.sys.executable", r"C:\Users\foo\venv\Scripts\python.exe"):
            spec = _detect_omnimem_command()
            self.assertEqual(spec["command"], "C:/Users/foo/venv/Scripts/python.exe")
            self.assertNotIn("\\", spec["command"])


class TestInstalledHookCommandsAreShellSafe(unittest.TestCase):
    def setUp(self):
        self.tmp_home = tempfile.mkdtemp()
        self.tmp_cwd = tempfile.mkdtemp()
        self.addCleanup(_remove_tree, self.tmp_home)
        self.addCleanup(_remove_tree, self.tmp_cwd)

    def test_claude_settings_command_has_no_raw_backslashes(self):
        with patch("omni_hooks.sys.executable", r"C:\Users\foo\venv\Scripts\python.exe"):
            result = install_claude_hooks(
                base_home=self.tmp_home,
                base_cwd=self.tmp_cwd,
            )
        path = Path(result["target"])
        data = json.loads(path.read_text(encoding="utf-8"))

        commands = []
        for entries in data.get("hooks", {}).values():
            for entry in entries or []:
                for nested in entry.get("hooks", []) or []:
                    if nested.get("tag") == OMNIMEM_HOOK_TAG:
                        commands.append(nested.get("command", ""))

        self.assertTrue(commands, "expected at least one omnimem-tagged hook command")
        for command in commands:
            # The Python interpreter path must contain forward slashes only;
            # any backslash here would be eaten by bash on Windows.
            python_part = command.split(" ", 1)[0]
            self.assertNotIn("\\", python_part, f"backslash leaked into hook command: {command}")
            self.assertIn("/", python_part, f"command path missing forward slashes: {command}")


if __name__ == "__main__":
    unittest.main()

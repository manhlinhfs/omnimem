"""Regression test for the Windows hook-path bug in v1.2.1 / v1.2.2.

`omnimem hook --agent claude` writes a launcher path into Claude Code's
`settings.json`. On Windows the path comes from the active venv (e.g.
`C:\\Users\\...\\Scripts\\omnimem.exe`). Claude Code passes hook commands
through `bash -c`, which interprets backslashes as escape characters and
silently consumes them — so `C:\\Users\\foo\\omnimem.exe` ends up running
as `C:Usersfoo\\omnimem.exe` and bash reports `command not found`.

The fix is to emit POSIX-style forward slashes when materializing hook /
MCP command entries. Windows accepts forward-slash paths natively, and
bash leaves them alone.

v1.2.7 also moved off `python -m omnimem` to the `omnimem` console script
so a CWD or sys.path entry that resolves `omnimem` to a package can no
longer break runpy. The console-script binary lives next to the active
interpreter (`<venv>/Scripts/omnimem.exe` on Windows, `<venv>/bin/omnimem`
on POSIX), so we point at it via Path(sys.executable).parent.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omni_hooks import OMNIMEM_HOOK_TAG, _omnimem_command, install_claude_hooks
from omni_init import _detect_omnimem_command


def _remove_tree(path):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


def _make_fake_console_script(tmpdir, suffix=""):
    """Drop a fake `omnimem(.exe)` next to a fake python(.exe) and return the
    path to the python interpreter so sys.executable can be patched to it."""
    bin_dir = Path(tmpdir)
    bin_dir.mkdir(parents=True, exist_ok=True)
    python_path = bin_dir / f"python{suffix}"
    omnimem_path = bin_dir / f"omnimem{suffix}"
    python_path.write_text("", encoding="utf-8")
    omnimem_path.write_text("", encoding="utf-8")
    return str(python_path), str(omnimem_path)


class TestPathQuoting(unittest.TestCase):
    def test_omnimem_command_resolves_console_script_with_forward_slashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            suffix = ".exe" if os.name == "nt" else ""
            python_path, omnimem_path = _make_fake_console_script(tmp, suffix=suffix)
            with patch("omni_hooks.sys.executable", python_path):
                resolved = _omnimem_command()
            self.assertEqual(resolved, omnimem_path.replace("\\", "/"))
            self.assertNotIn("\\", resolved)

    def test_omnimem_command_falls_back_to_naked_omnimem_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            python_path = Path(tmp) / ("python.exe" if os.name == "nt" else "python")
            python_path.write_text("", encoding="utf-8")
            with patch("omni_hooks.sys.executable", str(python_path)):
                self.assertEqual(_omnimem_command(), "omnimem")

    def test_omnimem_command_falls_back_to_naked_omnimem_when_executable_blank(self):
        with patch("omni_hooks.sys.executable", ""):
            self.assertEqual(_omnimem_command(), "omnimem")

    def test_init_detect_command_resolves_console_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            suffix = ".exe" if os.name == "nt" else ""
            python_path, omnimem_path = _make_fake_console_script(tmp, suffix=suffix)
            with patch("omni_init.sys.executable", python_path):
                spec = _detect_omnimem_command()
            self.assertEqual(spec["command"], omnimem_path.replace("\\", "/"))
            self.assertEqual(spec["args"], ["mcp", "serve"])
            self.assertNotIn("\\", spec["command"])

    def test_init_detect_command_falls_back_to_naked_omnimem(self):
        with patch("omni_init.sys.executable", ""):
            spec = _detect_omnimem_command()
            self.assertEqual(spec["command"], "omnimem")
            self.assertEqual(spec["args"], ["mcp", "serve"])


class TestInstalledHookCommandsAreShellSafe(unittest.TestCase):
    def setUp(self):
        self.tmp_home = tempfile.mkdtemp()
        self.tmp_cwd = tempfile.mkdtemp()
        self.tmp_bin = tempfile.mkdtemp()
        self.addCleanup(_remove_tree, self.tmp_home)
        self.addCleanup(_remove_tree, self.tmp_cwd)
        self.addCleanup(_remove_tree, self.tmp_bin)

    def test_claude_settings_command_uses_console_script_with_no_dash_m(self):
        suffix = ".exe" if os.name == "nt" else ""
        python_path, omnimem_path = _make_fake_console_script(self.tmp_bin, suffix=suffix)
        with patch("omni_hooks.sys.executable", python_path):
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
            launcher = command.split(" ", 1)[0].strip('"')
            self.assertNotIn("\\", launcher, f"backslash leaked into hook command: {command}")
            self.assertIn("omnimem", launcher.lower(), f"launcher is not omnimem: {command}")
            # Critical: no `-m omnimem` anywhere in the rendered command.
            self.assertNotIn(" -m omnimem", command, f"legacy -m omnimem leaked: {command}")
            self.assertNotIn(" -m \"omnimem\"", command, f"legacy -m omnimem leaked: {command}")


if __name__ == "__main__":
    unittest.main()

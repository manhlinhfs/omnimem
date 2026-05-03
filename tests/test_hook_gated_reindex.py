"""Verify the PostToolUse hook only triggers reindex for vault file edits.

Without gating, every Edit/Write/MultiEdit on any file in the agent's
working directory rebuilt the full notes index. That's expensive and
unnecessary when the touched file is the user's source code, not a note.
"""

import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _restore_env(name, previous_value):
    if previous_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous_value


def _remove_tree(path):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


class TestGatedReindex(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmpdir_path = Path(self.tmpdir).resolve()
        self.previous_home = os.environ.get("OMNIMEM_HOME")
        self.addCleanup(_restore_env, "OMNIMEM_HOME", self.previous_home)
        self.addCleanup(_remove_tree, self.tmpdir)
        os.environ["OMNIMEM_HOME"] = str(self.tmpdir_path)

        from omni_vault import ensure_vault_layout, get_vault_root

        ensure_vault_layout(root_dir=self.tmpdir_path)
        self.vault_root = Path(get_vault_root(root_dir=self.tmpdir_path)).resolve()
        self.vault_note = self.vault_root / "notes" / "decision-foo.md"
        self.vault_note.parent.mkdir(parents=True, exist_ok=True)
        self.vault_note.write_text("---\nslug: decision-foo\n---\nbody\n", encoding="utf-8")

    def _run(self, payload, reindex_called=None):
        from omni_hooks import gated_reindex_from_stdin

        stdin = io.StringIO(json.dumps(payload) if payload is not None else "")
        calls = []

        def _fake_reindex(root_dir=None, dry_run=False):
            calls.append({"root_dir": root_dir, "dry_run": dry_run})
            return {"indexed": 1, "failed": [], "total": 1}

        with patch("omni_note_index.reindex_all_notes", _fake_reindex):
            report = gated_reindex_from_stdin(stdin=stdin, root_dir=self.tmpdir_path)
        if reindex_called is not None:
            self.assertEqual(len(calls), reindex_called, msg=f"report={report}")
        return report

    def test_skips_when_stdin_empty(self):
        report = self._run(None, reindex_called=0)
        self.assertFalse(report["acted"])
        self.assertEqual(report["reason"], "empty stdin")

    def test_skips_when_payload_is_invalid_json(self):
        from omni_hooks import gated_reindex_from_stdin

        with patch("omni_note_index.reindex_all_notes") as reindex:
            report = gated_reindex_from_stdin(
                stdin=io.StringIO("not-json"),
                root_dir=self.tmpdir_path,
            )
        self.assertFalse(report["acted"])
        self.assertTrue(report["reason"].startswith("invalid json"))
        reindex.assert_not_called()

    def test_skips_when_no_file_path_in_payload(self):
        report = self._run(
            {"hook_event_name": "PostToolUse", "tool_input": {"foo": "bar"}},
            reindex_called=0,
        )
        self.assertFalse(report["acted"])
        self.assertEqual(report["reason"], "no file_path in payload")

    def test_skips_when_file_outside_vault(self):
        outside = self.tmpdir_path / "src" / "main.py"
        outside.parent.mkdir(parents=True, exist_ok=True)
        outside.write_text("print('hi')\n", encoding="utf-8")
        report = self._run(
            {
                "hook_event_name": "PostToolUse",
                "tool_input": {"file_path": str(outside)},
            },
            reindex_called=0,
        )
        self.assertFalse(report["acted"])
        self.assertEqual(report["reason"], "file outside vault")

    def test_reindexes_when_vault_note_touched_via_claude_payload(self):
        report = self._run(
            {
                "hook_event_name": "PostToolUse",
                "tool_input": {"file_path": str(self.vault_note)},
            },
            reindex_called=1,
        )
        self.assertTrue(report["acted"])
        self.assertEqual(Path(report["file_path"]).resolve(), self.vault_note.resolve())

    def test_reindexes_when_vault_note_touched_via_codex_payload(self):
        # Codex passes hook events under `data.file_path`.
        report = self._run(
            {"event": "post_tool_use", "data": {"file_path": str(self.vault_note)}},
            reindex_called=1,
        )
        self.assertTrue(report["acted"])

    def test_post_tool_use_recipe_uses_gated_command(self):
        # Pin the wire format so a regression in `_hook_recipe` doesn't
        # silently revert to the old "always reindex" behavior.
        from omni_hooks import _hook_recipe

        recipe = _hook_recipe("PostToolUse")
        command = recipe["hooks"][0]["command"]
        self.assertIn("hook", command)
        self.assertIn("--gated-reindex", command)
        self.assertNotIn("note reindex", command)


if __name__ == "__main__":
    unittest.main()

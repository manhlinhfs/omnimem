import io
import os
import tempfile
import unittest
from pathlib import Path

from omnimem.quickstart import detect_agents, run as run_quickstart


def _restore_env(name, previous_value):
    if previous_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous_value


def _remove_tree(path):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


class TestDetectAgents(unittest.TestCase):
    def setUp(self):
        self.tmp_home = tempfile.mkdtemp()
        self.addCleanup(_remove_tree, self.tmp_home)

    def test_returns_empty_list_when_no_config_dirs(self):
        self.assertEqual(detect_agents(home=self.tmp_home), [])

    def test_detects_each_supported_agent(self):
        for sub in (".claude", ".codex", ".gemini", ".cursor"):
            (Path(self.tmp_home) / sub).mkdir(parents=True, exist_ok=True)
        detected = detect_agents(home=self.tmp_home)
        self.assertEqual(detected, ["claude", "codex", "gemini", "cursor"])

    def test_codex_detected_via_agents_md_fallback(self):
        (Path(self.tmp_home) / "AGENTS.md").write_text("# placeholder\n", encoding="utf-8")
        self.assertIn("codex", detect_agents(home=self.tmp_home))


class TestQuickstartRun(unittest.TestCase):
    def setUp(self):
        self.tmp_home = tempfile.mkdtemp()
        self.tmp_runtime = tempfile.mkdtemp()
        previous_home = os.environ.get("HOME")
        previous_omni = os.environ.get("OMNIMEM_HOME")
        self.addCleanup(_restore_env, "HOME", previous_home)
        self.addCleanup(_restore_env, "OMNIMEM_HOME", previous_omni)
        self.addCleanup(_remove_tree, self.tmp_home)
        self.addCleanup(_remove_tree, self.tmp_runtime)
        os.environ["HOME"] = self.tmp_home
        os.environ["OMNIMEM_HOME"] = self.tmp_runtime
        # Pretend Claude Code is installed.
        (Path(self.tmp_home) / ".claude").mkdir(parents=True, exist_ok=True)

    def test_assume_yes_skip_seed_no_hooks_runs_clean(self):
        buf = io.StringIO()
        report = run_quickstart(
            assume_yes=True,
            install_hooks=False,
            seed_note=False,
            home=self.tmp_home,
            stdout=buf,
        )
        self.assertEqual(report["detected"], ["claude"])
        # Without seeding the welcome note we should never touch the vault.
        self.assertIsNone(report["welcome_note"])
        # Init should have written CLAUDE.md.
        self.assertTrue((Path(self.tmp_home) / ".claude" / "CLAUDE.md").exists())

    def test_seed_note_creates_welcome_when_vault_empty(self):
        buf = io.StringIO()
        report = run_quickstart(
            assume_yes=True,
            install_hooks=False,
            seed_note=True,
            home=self.tmp_home,
            stdout=buf,
        )
        self.assertIsNotNone(report["welcome_note"])
        self.assertEqual(
            report["welcome_note"].get("slug"),
            "omnimem-welcome-note",
        )

    def test_seed_note_skips_when_vault_already_has_notes(self):
        from omnimem.note import create_note
        from omnimem.vault import ensure_vault_layout

        ensure_vault_layout(root_dir=self.tmp_runtime)
        create_note("Pre-existing", root_dir=self.tmp_runtime)

        buf = io.StringIO()
        report = run_quickstart(
            assume_yes=True,
            install_hooks=False,
            seed_note=True,
            home=self.tmp_home,
            stdout=buf,
        )
        self.assertIsNone(report["welcome_note"])

    def test_no_agents_detected_returns_empty_report_under_assume_yes_via_targets(self):
        # Remove the .claude dir so nothing is detected in the user home.
        import shutil

        shutil.rmtree(Path(self.tmp_home) / ".claude", ignore_errors=True)

        buf = io.StringIO()
        report = run_quickstart(
            assume_yes=True,
            install_hooks=False,
            seed_note=False,
            home=self.tmp_home,
            stdout=buf,
        )
        # Under --yes we install for the full default list anyway.
        self.assertEqual(report["detected"], [])
        # But init should still have been called for all four agents.
        self.assertEqual(len(report["init"]), 4)


if __name__ == "__main__":
    unittest.main()

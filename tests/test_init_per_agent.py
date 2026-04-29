import json
import tempfile
import unittest
from pathlib import Path

from omni_init import (
    SUPPORTED_AGENTS,
    detect_installed_agents,
    get_mcp_config_path,
    get_target_path,
    install,
    install_mcp_config,
    install_rule_block,
    status,
    uninstall_mcp_config,
)


class TestPerAgentTargets(unittest.TestCase):
    def setUp(self):
        self.tmp_home = tempfile.mkdtemp()
        self.tmp_cwd = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp_home, ignore_errors=True)
        shutil.rmtree(self.tmp_cwd, ignore_errors=True)

    def test_user_scope_paths(self):
        cases = {
            "claude": Path(self.tmp_home) / ".claude" / "CLAUDE.md",
            "codex": Path(self.tmp_home) / ".codex" / "AGENTS.md",
            "gemini": Path(self.tmp_home) / ".gemini" / "GEMINI.md",
            "cursor": Path(self.tmp_home) / ".cursor" / "rules" / "omnimem.mdc",
        }
        for agent, expected in cases.items():
            self.assertEqual(
                get_target_path(agent, "user", base_home=self.tmp_home, base_cwd=self.tmp_cwd),
                expected,
            )

    def test_project_scope_paths(self):
        cases = {
            "claude": Path(self.tmp_cwd) / "CLAUDE.md",
            "codex": Path(self.tmp_cwd) / "AGENTS.md",
            "gemini": Path(self.tmp_cwd) / "GEMINI.md",
            "cursor": Path(self.tmp_cwd) / ".cursor" / "rules" / "omnimem.mdc",
        }
        for agent, expected in cases.items():
            self.assertEqual(
                get_target_path(agent, "project", base_home=self.tmp_home, base_cwd=self.tmp_cwd),
                expected,
            )

    def test_cursor_block_includes_mdc_frontmatter(self):
        result = install_rule_block(
            "cursor",
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        body = Path(result["target"]).read_text(encoding="utf-8")
        self.assertIn("description: OmniMem second brain protocol", body)
        self.assertIn("alwaysApply: true", body)

    def test_install_all_writes_every_agent(self):
        results = install(
            ["all"],
            scope="user",
            include_mcp=False,
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        installed_agents = sorted(record["agent"] for record in results)
        self.assertEqual(installed_agents, sorted(SUPPORTED_AGENTS))
        for agent in SUPPORTED_AGENTS:
            target = get_target_path(agent, "user", base_home=self.tmp_home, base_cwd=self.tmp_cwd)
            self.assertTrue(target.exists(), f"Expected {target} to exist for {agent}")

    def test_status_reports_per_agent_state(self):
        install(
            ["claude"],
            scope="user",
            include_mcp=False,
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        report = status(base_home=self.tmp_home, base_cwd=self.tmp_cwd)
        self.assertTrue(report["claude"]["user"]["installed"])
        self.assertFalse(report["codex"]["user"]["installed"])

    def test_detect_installed_agents_uses_config_dirs(self):
        for sub in (".claude", ".codex", ".cursor"):
            (Path(self.tmp_home) / sub).mkdir(parents=True, exist_ok=True)
        detected = detect_installed_agents(base_home=self.tmp_home)
        self.assertIn("claude", detected)
        self.assertIn("codex", detected)
        self.assertIn("cursor", detected)
        self.assertNotIn("gemini", detected)


class TestMCPConfigInstall(unittest.TestCase):
    def setUp(self):
        self.tmp_home = tempfile.mkdtemp()
        self.tmp_cwd = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp_home, ignore_errors=True)
        shutil.rmtree(self.tmp_cwd, ignore_errors=True)

    def test_claude_mcp_json_registers_omnimem(self):
        result = install_mcp_config(
            "claude",
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        config_path = Path(result["target"])
        data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertIn("omnimem", data["mcpServers"])
        self.assertIn("command", data["mcpServers"]["omnimem"])

    def test_gemini_mcp_settings_merges_existing(self):
        target = get_mcp_config_path(
            "gemini",
            "user",
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps({"theme": "dark", "mcpServers": {"other": {"command": "x"}}}),
            encoding="utf-8",
        )
        install_mcp_config(
            "gemini",
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        data = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(data["theme"], "dark")
        self.assertIn("other", data["mcpServers"])
        self.assertIn("omnimem", data["mcpServers"])

    def test_codex_toml_block_replaced_on_reinstall(self):
        first = install_mcp_config(
            "codex",
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        path = Path(first["target"])
        original = path.read_text(encoding="utf-8")
        install_mcp_config(
            "codex",
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        self.assertEqual(original.count("[mcp_servers.omnimem]"), 1)
        self.assertEqual(
            path.read_text(encoding="utf-8").count("[mcp_servers.omnimem]"),
            1,
        )

    def test_codex_toml_block_uninstall_clears_section(self):
        install_mcp_config(
            "codex",
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        result = uninstall_mcp_config(
            "codex",
            base_home=self.tmp_home,
            base_cwd=self.tmp_cwd,
        )
        self.assertTrue(result.get("removed"))
        path = Path(result["target"])
        if path.exists():
            self.assertNotIn("[mcp_servers.omnimem]", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

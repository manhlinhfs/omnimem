import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
IGNORE_NAMES = {".git", "venv", "__pycache__", ".omnimem_db", ".omnimem_models", ".pytest_cache"}


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


class TestOmniUpdate(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.seed_repo = self.temp_path / "seed"
        self.remote_repo = self.temp_path / "remote.git"
        self.source_repo = self.temp_path / "source"
        self.client_repo = self.temp_path / "client"

        shutil.copytree(
            ROOT_DIR,
            self.seed_repo,
            ignore=shutil.ignore_patterns(*IGNORE_NAMES),
        )
        self._git(["git", "init"], cwd=self.seed_repo)
        self._git(["git", "config", "user.name", "Codex Test"], cwd=self.seed_repo)
        self._git(["git", "config", "user.email", "codex@example.com"], cwd=self.seed_repo)
        self._git(["git", "add", "."], cwd=self.seed_repo)
        self._git(["git", "commit", "-m", "seed"], cwd=self.seed_repo)
        self._git(["git", "branch", "-M", "main"], cwd=self.seed_repo)

        self._git(["git", "clone", "--bare", str(self.seed_repo), str(self.remote_repo)], cwd=self.temp_path)
        self._git(["git", "clone", str(self.remote_repo), str(self.source_repo)], cwd=self.temp_path)
        self._git(["git", "clone", str(self.remote_repo), str(self.client_repo)], cwd=self.temp_path)
        self._git(["git", "config", "user.name", "Codex Test"], cwd=self.source_repo)
        self._git(["git", "config", "user.email", "codex@example.com"], cwd=self.source_repo)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _git(self, cmd, cwd):
        result = run(cmd, cwd)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        return result

    def test_check_reports_update_available(self):
        marker = self.source_repo / "UPDATE_TEST_MARKER.txt"
        marker.write_text("update available\n", encoding="utf-8")
        self._git(["git", "add", "UPDATE_TEST_MARKER.txt"], cwd=self.source_repo)
        self._git(["git", "commit", "-m", "advance remote"], cwd=self.source_repo)
        self._git(["git", "push", "origin", "HEAD"], cwd=self.source_repo)

        result = run(
            [sys.executable, str(self.client_repo / "omni_update.py"), "--check", "--json"],
            cwd=self.client_repo,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "update_available")
        self.assertEqual(payload["branch"], "main")
        self.assertEqual(payload["behind"], 1)

    def test_update_applies_remote_commit_and_blocks_dirty_tree(self):
        marker = self.source_repo / "UPDATE_TEST_MARKER.txt"
        marker.write_text("updated content\n", encoding="utf-8")
        self._git(["git", "add", "UPDATE_TEST_MARKER.txt"], cwd=self.source_repo)
        self._git(["git", "commit", "-m", "advance remote"], cwd=self.source_repo)
        self._git(["git", "push", "origin", "HEAD"], cwd=self.source_repo)

        result = run(
            [
                sys.executable,
                str(self.client_repo / "omni_update.py"),
                "--skip-bootstrap",
                "--skip-deps",
            ],
            cwd=self.client_repo,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue((self.client_repo / "UPDATE_TEST_MARKER.txt").exists())

        readme = self.client_repo / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\nlocal dirty\n", encoding="utf-8")
        dirty_result = run(
            [sys.executable, str(self.client_repo / "omni_update.py"), "--skip-bootstrap"],
            cwd=self.client_repo,
        )
        self.assertNotEqual(dirty_result.returncode, 0)
        self.assertIn("Working tree is not clean", dirty_result.stdout)

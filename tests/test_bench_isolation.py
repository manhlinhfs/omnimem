"""Regression test for `benchmarks.common.isolated_omnimem_home`.

Pre-fix bug: the context manager only set $OMNIMEM_HOME, but if the user had
a repo-local `omnimem.json` pinning `db_dir` / `models_dir`, those paths
took precedence — so a benchmark ingested into the user's REAL ChromaDB.

Post-fix: the context manager also writes a fresh `omnimem.json` into the
tmpdir and exports `OMNIMEM_CONFIG` so config discovery uses the temp file.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from benchmarks.common import isolated_omnimem_home


def _restore_env(name, previous_value):
    if previous_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous_value


class TestIsolatedOmnimemHome(unittest.TestCase):
    def test_overrides_omnimem_home_env_var(self):
        previous = os.environ.get("OMNIMEM_HOME")
        self.addCleanup(_restore_env, "OMNIMEM_HOME", previous)
        with isolated_omnimem_home() as runtime_home:
            self.assertEqual(os.environ["OMNIMEM_HOME"], str(runtime_home))
            self.assertTrue(Path(runtime_home).exists())

    def test_overrides_omnimem_config_env_var_to_temp_file(self):
        previous_home = os.environ.get("OMNIMEM_HOME")
        previous_config = os.environ.get("OMNIMEM_CONFIG")
        self.addCleanup(_restore_env, "OMNIMEM_HOME", previous_home)
        self.addCleanup(_restore_env, "OMNIMEM_CONFIG", previous_config)
        with isolated_omnimem_home() as runtime_home:
            config_path = Path(os.environ["OMNIMEM_CONFIG"])
            self.assertTrue(config_path.exists())
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            # The temp config must pin db_dir and models_dir inside the tmpdir
            # so a benchmark never writes to the user's real ChromaDB.
            self.assertTrue(payload["db_dir"].startswith(str(runtime_home.parent)))
            self.assertTrue(payload["models_dir"].startswith(str(runtime_home.parent)))

    def test_runtime_resolves_db_dir_to_temp_dir(self):
        """The runtime helpers must observe the tmp config when active."""
        previous_home = os.environ.get("OMNIMEM_HOME")
        previous_config = os.environ.get("OMNIMEM_CONFIG")
        self.addCleanup(_restore_env, "OMNIMEM_HOME", previous_home)
        self.addCleanup(_restore_env, "OMNIMEM_CONFIG", previous_config)
        with isolated_omnimem_home() as runtime_home:
            from omnimem.paths import get_db_dir, get_models_root, get_runtime_home

            home = get_runtime_home()
            db = get_db_dir()
            models = get_models_root()
            tmp_root = str(runtime_home.parent)
            self.assertTrue(str(home).startswith(tmp_root))
            self.assertTrue(str(db).startswith(tmp_root))
            self.assertTrue(str(models).startswith(tmp_root))

    def test_env_vars_restored_after_exit(self):
        previous_home = os.environ.get("OMNIMEM_HOME")
        previous_config = os.environ.get("OMNIMEM_CONFIG")
        self.addCleanup(_restore_env, "OMNIMEM_HOME", previous_home)
        self.addCleanup(_restore_env, "OMNIMEM_CONFIG", previous_config)

        before_home = os.environ.get("OMNIMEM_HOME")
        before_config = os.environ.get("OMNIMEM_CONFIG")
        with isolated_omnimem_home():
            pass
        self.assertEqual(os.environ.get("OMNIMEM_HOME"), before_home)
        self.assertEqual(os.environ.get("OMNIMEM_CONFIG"), before_config)

    def test_tmpdir_cleaned_up_on_exit(self):
        with isolated_omnimem_home() as runtime_home:
            tmp_root = Path(runtime_home).parent
            self.assertTrue(tmp_root.exists())
        self.assertFalse(tmp_root.exists())


if __name__ == "__main__":
    unittest.main()

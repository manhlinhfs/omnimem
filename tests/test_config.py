import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omni_config import get_preferred_config_path, resolve_runtime_config, serialize_runtime_config


class TestOmniConfig(unittest.TestCase):
    def _clean_env(self, **updates):
        base = {key: value for key, value in os.environ.items() if not key.startswith("OMNIMEM_")}
        base.update(updates)
        return patch.dict(os.environ, base, clear=True)

    def test_repo_local_config_is_loaded_for_git_clone(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            root.mkdir()
            (root / ".git").mkdir()
            config_path = root / "omnimem.json"
            config_path.write_text(
                json.dumps(
                    {
                        "db_dir": str(root / "custom-db"),
                        "models_dir": str(root / "custom-models"),
                        "allow_model_download": True,
                        "async_extract_timeout_seconds": 33,
                        "chunk_target_tokens": 444,
                        "chunk_overlap_tokens": 77,
                        "search_service_enabled": False,
                        "search_service_port": 43123,
                    }
                ),
                encoding="utf-8",
            )

            with self._clean_env():
                report = resolve_runtime_config(root_dir=root)

            self.assertTrue(report["config"]["loaded"])
            self.assertEqual(report["config"]["selected_path"], str(config_path))
            self.assertEqual(report["values"]["db_dir"], root / "custom-db")
            self.assertEqual(report["values"]["models_dir"], root / "custom-models")
            self.assertTrue(report["values"]["allow_model_download"])
            self.assertEqual(report["values"]["async_extract_timeout_seconds"], 33)
            self.assertEqual(report["values"]["chunk_target_tokens"], 444)
            self.assertEqual(report["values"]["chunk_overlap_tokens"], 77)
            self.assertFalse(report["values"]["search_service_enabled"])
            self.assertEqual(report["values"]["search_service_port"], 43123)

    def test_environment_variables_override_config_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            root.mkdir()
            (root / ".git").mkdir()
            (root / "omnimem.json").write_text(
                json.dumps({"db_dir": str(root / "config-db")}),
                encoding="utf-8",
            )
            env_db = root / "env-db"

            with self._clean_env(OMNIMEM_DB_DIR=str(env_db)):
                report = resolve_runtime_config(root_dir=root)

            self.assertEqual(report["values"]["db_dir"], env_db)
            self.assertEqual(report["settings"]["db_dir"]["source"], "env:OMNIMEM_DB_DIR")

    def test_chunk_env_overrides_apply(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            root.mkdir()
            (root / ".git").mkdir()

            with self._clean_env(
                OMNIMEM_CHUNK_TARGET_TOKENS="512",
                OMNIMEM_CODE_CHUNK_OVERLAP_TOKENS="55",
                OMNIMEM_SEARCH_SERVICE_PORT="49000",
            ):
                report = resolve_runtime_config(root_dir=root)

            self.assertEqual(report["values"]["chunk_target_tokens"], 512)
            self.assertEqual(report["values"]["code_chunk_overlap_tokens"], 55)
            self.assertEqual(report["values"]["search_service_port"], 49000)

    def test_package_install_prefers_user_config_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            site_root = Path(temp_dir) / "site-packages"
            package_root = site_root / "omnimem"
            config_root = Path(temp_dir) / "config-home"
            config_file = config_root / "config.json"
            package_root.mkdir(parents=True)
            config_root.mkdir(parents=True)
            config_file.write_text(
                json.dumps({"home": str(Path(temp_dir) / "runtime-home")}),
                encoding="utf-8",
            )

            with self._clean_env(OMNIMEM_CONFIG_HOME=str(config_root)):
                report = resolve_runtime_config(root_dir=package_root, site_roots=[site_root])
                preferred = get_preferred_config_path(root_dir=package_root, site_roots=[site_root])

            self.assertEqual(preferred, config_file)
            self.assertEqual(report["config"]["selected_path"], str(config_file))
            self.assertEqual(report["values"]["home"], Path(temp_dir) / "runtime-home")

    def test_serialize_runtime_config_converts_paths_to_strings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            root.mkdir()
            (root / ".git").mkdir()

            with self._clean_env():
                report = resolve_runtime_config(root_dir=root)
                serialized = serialize_runtime_config(report)

            self.assertIsInstance(serialized["settings"]["home"]["value"], str)
            self.assertIn("db_dir", serialized["settings"])


if __name__ == "__main__":
    unittest.main()

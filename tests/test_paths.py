import tempfile
import unittest
from pathlib import Path

from omni_paths import detect_install_mode, get_db_dir, get_models_root, get_runtime_home


class TestOmniPaths(unittest.TestCase):
    def test_detect_install_mode_prefers_git_clone(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".git").mkdir()
            report = detect_install_mode(root_dir=root)
            self.assertEqual(report["mode"], "git_clone")

    def test_detect_install_mode_for_package_install(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            site_root = Path(temp_dir) / "site-packages"
            package_root = site_root / "omnimem"
            package_root.mkdir(parents=True)
            report = detect_install_mode(root_dir=package_root, site_roots=[site_root])
            self.assertEqual(report["mode"], "package_install")

    def test_runtime_home_uses_user_data_dir_for_package_install(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            site_root = Path(temp_dir) / "site-packages"
            package_root = site_root / "omnimem"
            user_data_root = Path(temp_dir) / "user-data"
            package_root.mkdir(parents=True)

            runtime_home = get_runtime_home(
                root_dir=package_root,
                site_roots=[site_root],
                user_data_root=user_data_root,
            )
            self.assertEqual(runtime_home, user_data_root)
            self.assertEqual(get_db_dir(root_dir=package_root, site_roots=[site_root], user_data_root=user_data_root), user_data_root / ".omnimem_db")
            self.assertEqual(get_models_root(root_dir=package_root, site_roots=[site_root], user_data_root=user_data_root), user_data_root / ".omnimem_models")

    def test_runtime_home_stays_in_source_tree_for_non_package_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "omnimem"
            root.mkdir()
            runtime_home = get_runtime_home(root_dir=root, site_roots=[])
            self.assertEqual(runtime_home, root.resolve())

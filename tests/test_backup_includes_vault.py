import os
import tarfile
import tempfile
import unittest
from pathlib import Path

from omni_note import create_note
from omni_ops import create_backup, restore_backup
from omni_vault import ensure_vault_layout, get_notes_dir


def _restore_env(name, previous_value):
    if previous_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous_value


def _remove_tree(path):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


class TestBackupIncludesVault(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        previous_home = os.environ.get("OMNIMEM_HOME")
        self.addCleanup(_restore_env, "OMNIMEM_HOME", previous_home)
        self.addCleanup(_remove_tree, self.tmpdir)
        os.environ["OMNIMEM_HOME"] = self.tmpdir

    def test_backup_archive_contains_vault_notes(self):
        ensure_vault_layout(root_dir=self.tmpdir)
        create_note(
            "Backup smoke note",
            body="Sample body for the vault backup test.\n",
            root_dir=self.tmpdir,
        )

        report = create_backup(
            output_path=str(Path(self.tmpdir) / "snapshot.tar.gz"),
            include_models=False,
            include_config=False,
            root_dir=self.tmpdir,
        )
        self.assertTrue(report["vault_included"])

        with tarfile.open(report["output_path"], "r:gz") as archive:
            members = archive.getnames()
        self.assertTrue(any(name.startswith("vault/") for name in members))
        self.assertTrue(any(name.endswith(".md") for name in members))

    def test_restore_recreates_vault_notes(self):
        ensure_vault_layout(root_dir=self.tmpdir)
        created = create_note(
            "Vault round trip",
            body="Body for round trip.\n",
            root_dir=self.tmpdir,
        )
        archive_path = Path(self.tmpdir) / "snapshot.tar.gz"
        create_backup(
            output_path=str(archive_path),
            include_models=False,
            include_config=False,
            root_dir=self.tmpdir,
        )

        notes_dir = get_notes_dir(root_dir=self.tmpdir)
        for path in notes_dir.glob("*.md"):
            path.unlink()
        self.assertEqual(list(notes_dir.glob("*.md")), [])

        restore_backup(str(archive_path), force=True, root_dir=self.tmpdir)

        restored = list(notes_dir.glob("*.md"))
        self.assertEqual(len(restored), 1)
        self.assertEqual(restored[0].name, f"{created['slug']}.md")


if __name__ == "__main__":
    unittest.main()

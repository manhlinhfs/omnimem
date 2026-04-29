import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from omni_del import delete_memory


class FakeCollection:
    def __init__(self, client, name, items=None):
        self._client = client
        self.name = name
        self.items = list(items or [])

    def delete(self, ids=None, where=None):
        if ids:
            id_set = set(ids)
            self.items = [item for item in self.items if item["id"] not in id_set]
            return
        if where:
            source = where.get("source")
            self.items = [item for item in self.items if (item.get("metadata") or {}).get("source") != source]


class FakePersistentClient:
    stores = {}

    def __init__(self, path):
        self.path = str(path)
        FakePersistentClient.stores.setdefault(self.path, {})

    def get_collection(self, name):
        try:
            return FakePersistentClient.stores[self.path][name]
        except KeyError as exc:
            not_found = type("NotFoundError", (Exception,), {})
            raise not_found(name) from exc

    def delete_collection(self, name):
        collections = FakePersistentClient.stores[self.path]
        if name not in collections:
            not_found = type("NotFoundError", (Exception,), {})
            raise not_found(name)
        del collections[name]


class _NonInteractiveStdin:
    def isatty(self):
        return False


class TestOmniDelete(unittest.TestCase):
    def setUp(self):
        FakePersistentClient.stores = {}

    def test_wipe_all_requires_force_in_non_interactive_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_dir = Path(temp_dir) / ".omnimem_db"
            client = FakePersistentClient(db_dir)
            FakePersistentClient.stores[str(db_dir)] = {
                "omnimem_core": FakeCollection(
                    client,
                    "omnimem_core",
                    [{"id": "note-1", "document": "hello", "metadata": {"source": "user_input"}}],
                )
            }
            fake_chromadb = types.SimpleNamespace(PersistentClient=FakePersistentClient)

            with patch.dict(sys.modules, {"chromadb": fake_chromadb}):
                with patch("omni_del.get_db_dir", return_value=db_dir):
                    with patch.object(sys, "stdin", _NonInteractiveStdin()):
                        rc = delete_memory(wipe_all=True)

        self.assertEqual(rc, 1)
        self.assertIn("omnimem_core", FakePersistentClient.stores[str(db_dir)])

    def test_wipe_all_force_skips_confirmation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_dir = Path(temp_dir) / ".omnimem_db"
            client = FakePersistentClient(db_dir)
            FakePersistentClient.stores[str(db_dir)] = {
                "omnimem_core": FakeCollection(
                    client,
                    "omnimem_core",
                    [{"id": "note-1", "document": "hello", "metadata": {"source": "user_input"}}],
                )
            }
            fake_chromadb = types.SimpleNamespace(PersistentClient=FakePersistentClient)

            with patch.dict(sys.modules, {"chromadb": fake_chromadb}):
                with patch("omni_del.get_db_dir", return_value=db_dir):
                    rc = delete_memory(wipe_all=True, force=True)

        self.assertEqual(rc, 0)
        self.assertNotIn("omnimem_core", FakePersistentClient.stores[str(db_dir)])


if __name__ == "__main__":
    unittest.main()

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from omni_ops import create_backup, export_memories, restore_backup, restore_export


class FakeCollection:
    def __init__(self, items=None):
        self.items = list(items or [])

    def get(self, include=None):
        return {
            "ids": [item["id"] for item in self.items],
            "documents": [item["document"] for item in self.items],
            "metadatas": [item["metadata"] for item in self.items],
        }

    def add(self, documents, metadatas, ids):
        for index, doc_id in enumerate(ids):
            self.items.append(
                {
                    "id": doc_id,
                    "document": documents[index],
                    "metadata": metadatas[index],
                }
            )

    def count(self):
        return len(self.items)


class FakePersistentClient:
    stores = {}

    def __init__(self, path):
        self.path = str(path)
        FakePersistentClient.stores.setdefault(self.path, {})

    def get_collection(self, name):
        try:
            return FakePersistentClient.stores[self.path][name]
        except KeyError as exc:
            raise ValueError(name) from exc

    def get_or_create_collection(self, name, embedding_function=None):
        collections = FakePersistentClient.stores[self.path]
        if name not in collections:
            collections[name] = FakeCollection()
        return collections[name]

    def delete_collection(self, name):
        FakePersistentClient.stores[self.path].pop(name, None)


class TestOmniOps(unittest.TestCase):
    def setUp(self):
        FakePersistentClient.stores = {}

    def test_backup_and_restore_roundtrip_restores_db_models_and_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            root.mkdir()
            (root / ".git").mkdir()
            db_file = root / ".omnimem_db" / "chroma.sqlite3"
            model_file = root / ".omnimem_models" / "all-MiniLM-L6-v2" / "config.json"
            config_file = root / "omnimem.json"
            db_file.parent.mkdir(parents=True)
            model_file.parent.mkdir(parents=True)
            db_file.write_text("db", encoding="utf-8")
            model_file.write_text("model", encoding="utf-8")
            config_file.write_text(json.dumps({"db_dir": str(root / ".omnimem_db")}), encoding="utf-8")

            report = create_backup(output_path=root / "snapshot.tar.gz", root_dir=root)
            self.assertEqual(report["status"], "pass")

            db_file.unlink()
            model_file.unlink()
            config_file.unlink()
            db_file.parent.rmdir()
            model_file.parent.rmdir()
            model_file.parent.parent.rmdir()

            restore_report = restore_backup(root / "snapshot.tar.gz", force=False, root_dir=root)
            self.assertEqual(restore_report["restore_kind"], "backup")
            self.assertTrue(db_file.exists())
            self.assertTrue(model_file.exists())
            self.assertTrue(config_file.exists())

    def test_export_and_restore_roundtrip_uses_collection_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir) / "source"
            restore_root = Path(temp_dir) / "restore"
            source_root.mkdir()
            restore_root.mkdir()
            (source_root / ".git").mkdir()
            (restore_root / ".git").mkdir()
            source_db = str(source_root / ".omnimem_db")
            FakePersistentClient.stores[source_db] = {
                "omnimem_core": FakeCollection(
                    [
                        {
                            "id": "memory-1",
                            "document": "release note",
                            "metadata": {"source": "omnimem"},
                        }
                    ]
                )
            }

            fake_chromadb = types.SimpleNamespace(PersistentClient=FakePersistentClient)
            fake_embeddings = types.SimpleNamespace(build_embedding_function=lambda: "ef")
            export_path = source_root / "export.json"
            with patch.dict(sys.modules, {"chromadb": fake_chromadb, "omni_embeddings": fake_embeddings}):
                export_report = export_memories(output_path=export_path, root_dir=source_root)
                restore_report = restore_export(export_path, root_dir=restore_root)

            self.assertEqual(export_report["record_count"], 1)
            self.assertEqual(restore_report["restored_count"], 1)
            restore_db = str(restore_root / ".omnimem_db")
            restored_items = FakePersistentClient.stores[restore_db]["omnimem_core"].items
            self.assertEqual(restored_items[0]["id"], "memory-1")
            self.assertEqual(restored_items[0]["document"], "release note")


if __name__ == "__main__":
    unittest.main()

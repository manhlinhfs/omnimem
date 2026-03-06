import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from omni_reindex import reindex_collection


class FakeCollection:
    def __init__(self, client, name, items=None):
        self._client = client
        self.name = name
        self.items = list(items or [])

    def get(self, include=None):
        return {
            "ids": [item["id"] for item in self.items],
            "documents": [item["document"] for item in self.items],
            "metadatas": [item["metadata"] for item in self.items],
        }

    def add(self, ids, documents, metadatas):
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

    def modify(self, name=None, metadata=None, configuration=None):
        if name is None or name == self.name:
            return
        collections = FakePersistentClient.stores[self._client.path]
        collections[name] = collections.pop(self.name)
        self.name = name


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

    def get_or_create_collection(self, name, embedding_function=None):
        collections = FakePersistentClient.stores[self.path]
        if name not in collections:
            collections[name] = FakeCollection(self, name)
        return collections[name]

    def delete_collection(self, name):
        collections = FakePersistentClient.stores[self.path]
        if name not in collections:
            not_found = type("NotFoundError", (Exception,), {})
            raise not_found(name)
        del collections[name]


class TestOmniReindex(unittest.TestCase):
    def setUp(self):
        FakePersistentClient.stores = {}

    def test_reindex_rebuilds_import_chunks_and_preserves_notes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            root.mkdir()
            (root / ".git").mkdir()
            db_path = str(root / ".omnimem_db")
            FakePersistentClient.stores[db_path] = {
                "omnimem_core": FakeCollection(
                    None,
                    "omnimem_core",
                    [
                        {
                            "id": "note-1",
                            "document": "plain note",
                            "metadata": {
                                "source": "user_input",
                                "timestamp": "2026-03-06T12:00:00.000000",
                                "record_kind": "note",
                            },
                        },
                        {
                            "id": "import-1",
                            "document": "# Guide\n\nFirst paragraph about retrieval quality and chunking.",
                            "metadata": {
                                "source": "guide.md",
                                "timestamp": "2026-03-06T12:00:01.000000",
                                "record_kind": "import_chunk",
                                "chunk_index": 0,
                                "mime_type": "text/markdown",
                            },
                        },
                        {
                            "id": "import-2",
                            "document": "Second paragraph adds more details so the new chunker has enough material to rebuild.",
                            "metadata": {
                                "source": "guide.md",
                                "timestamp": "2026-03-06T12:00:01.000000",
                                "record_kind": "import_chunk",
                                "chunk_index": 1,
                                "mime_type": "text/markdown",
                            },
                        },
                    ],
                )
            }
            FakePersistentClient.stores[db_path]["omnimem_core"]._client = FakePersistentClient(db_path)
            fake_chromadb = types.SimpleNamespace(PersistentClient=FakePersistentClient)
            fake_embeddings = types.SimpleNamespace(build_embedding_function=lambda: "ef")
            env = {
                "OMNIMEM_CHUNK_TARGET_TOKENS": "12",
                "OMNIMEM_CHUNK_OVERLAP_TOKENS": "4",
            }

            with patch.dict(sys.modules, {"chromadb": fake_chromadb, "omni_embeddings": fake_embeddings}):
                with patch.dict(os.environ, {**os.environ, **env}, clear=True):
                    report = reindex_collection(root_dir=root, skip_backup=True)

            self.assertEqual(report["status"], "reindexed")
            collection = FakePersistentClient.stores[db_path]["omnimem_core"]
            ids = [item["id"] for item in collection.items]
            self.assertIn("note-1", ids)
            rebuilt_imports = [item for item in collection.items if (item["metadata"] or {}).get("record_kind") == "import_chunk"]
            self.assertTrue(rebuilt_imports)
            self.assertTrue(all(item["metadata"].get("chunk_strategy") == "v2" for item in rebuilt_imports))
            self.assertGreaterEqual(len(rebuilt_imports), 2)

    def test_reindex_dry_run_does_not_mutate_collection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            root.mkdir()
            (root / ".git").mkdir()
            db_path = str(root / ".omnimem_db")
            collection = FakeCollection(
                None,
                "omnimem_core",
                [
                    {
                        "id": "import-1",
                        "document": "Paragraph one. Paragraph two.",
                        "metadata": {
                            "source": "guide.md",
                            "timestamp": "2026-03-06T12:00:01.000000",
                            "record_kind": "import_chunk",
                            "chunk_index": 0,
                            "mime_type": "text/markdown",
                        },
                    }
                ],
            )
            FakePersistentClient.stores[db_path] = {"omnimem_core": collection}
            collection._client = FakePersistentClient(db_path)
            fake_chromadb = types.SimpleNamespace(PersistentClient=FakePersistentClient)
            fake_embeddings = types.SimpleNamespace(build_embedding_function=lambda: "ef")

            with patch.dict(sys.modules, {"chromadb": fake_chromadb, "omni_embeddings": fake_embeddings}):
                report = reindex_collection(root_dir=root, dry_run=True, skip_backup=True)

            self.assertEqual(report["status"], "dry_run")
            self.assertEqual(FakePersistentClient.stores[db_path]["omnimem_core"].items[0]["id"], "import-1")


if __name__ == "__main__":
    unittest.main()

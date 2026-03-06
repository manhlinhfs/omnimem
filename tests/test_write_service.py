import asyncio
import io
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import omni_add
import omni_import
from omni_reindex import reindex_collection


class _DirectRuntime:
    def __init__(self):
        self.calls = []

    def add_records(self, documents, metadatas, ids):
        self.calls.append((documents, metadatas, ids))
        return {"added": len(documents)}

    def replace_core_records(self, records, batch_size=100):
        self.calls.append((records, batch_size))
        return {"replaced": len(records)}


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
            not_found = type("NotFoundError", (Exception,), {})
            raise not_found(name) from exc


class TestWriteService(unittest.TestCase):
    def test_add_memory_uses_service_when_available(self):
        captured = {}

        def _fake_add_records(documents, metadatas, ids, **kwargs):
            captured["documents"] = documents
            captured["metadatas"] = metadatas
            captured["ids"] = ids
            return {"status": "ok", "added": len(documents)}

        fake_service = types.SimpleNamespace(
            SearchServiceError=RuntimeError,
            add_records_via_service=_fake_add_records,
        )
        output = io.StringIO()
        with patch.dict(sys.modules, {"omni_service": fake_service}):
            with patch.object(omni_add, "OmniRuntime", side_effect=AssertionError("direct path should not run")):
                with redirect_stdout(output):
                    omni_add.add_memory("remember this", prefer_service=True)

        self.assertEqual(captured["documents"], ["remember this"])
        self.assertEqual(len(captured["ids"]), 1)
        self.assertEqual(captured["metadatas"][0]["record_kind"], "note")

    def test_add_memory_falls_back_to_direct_runtime_when_service_fails(self):
        class FakeServiceError(RuntimeError):
            pass

        fake_service = types.SimpleNamespace(
            SearchServiceError=FakeServiceError,
            add_records_via_service=lambda *args, **kwargs: (_ for _ in ()).throw(FakeServiceError("down")),
        )
        runtime = _DirectRuntime()
        output = io.StringIO()
        with patch.dict(sys.modules, {"omni_service": fake_service}):
            with patch.object(omni_add, "OmniRuntime", return_value=runtime):
                with redirect_stdout(output):
                    omni_add.add_memory("remember this", prefer_service=True)

        self.assertEqual(len(runtime.calls), 1)
        self.assertEqual(runtime.calls[0][0], ["remember this"])

    def test_import_uses_service_when_available(self):
        captured = {}

        async def _fake_extract(_file_path):
            return types.SimpleNamespace(content="Section one\n\nSection two", mime_type="text/plain", metadata={})

        def _fake_build_import_records(**kwargs):
            return {
                "profile": "prose",
                "target_tokens": 12,
                "overlap_tokens": 4,
                "documents": ["chunk one", "chunk two"],
                "metadatas": [
                    {"source": "sample.txt", "record_kind": "import_chunk"},
                    {"source": "sample.txt", "record_kind": "import_chunk"},
                ],
                "ids": ["chunk-1", "chunk-2"],
            }

        def _fake_add_records(documents, metadatas, ids, **kwargs):
            captured["documents"] = documents
            captured["metadatas"] = metadatas
            captured["ids"] = ids
            return {"status": "ok", "added": len(documents)}

        fake_service = types.SimpleNamespace(
            SearchServiceError=RuntimeError,
            add_records_via_service=_fake_add_records,
        )
        with patch.object(omni_import, "extract_with_fallback", _fake_extract):
            with patch.object(omni_import, "build_import_records", _fake_build_import_records):
                with patch.dict(sys.modules, {"omni_service": fake_service}):
                    with patch.object(omni_import, "OmniRuntime", side_effect=AssertionError("direct path should not run")):
                        asyncio.run(omni_import.import_file_advanced("/tmp/sample.txt", prefer_service=True))

        self.assertEqual(captured["documents"], ["chunk one", "chunk two"])
        self.assertEqual(captured["ids"], ["chunk-1", "chunk-2"])

    def test_reindex_uses_service_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            root.mkdir()
            (root / ".git").mkdir()
            db_path = str(root / ".omnimem_db")
            FakePersistentClient.stores = {
                db_path: {
                    "omnimem_core": FakeCollection(
                        None,
                        "omnimem_core",
                        [
                            {
                                "id": "import-1",
                                "document": "Paragraph one.\n\nParagraph two.",
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
                }
            }
            FakePersistentClient.stores[db_path]["omnimem_core"]._client = FakePersistentClient(db_path)
            fake_chromadb = types.SimpleNamespace(PersistentClient=FakePersistentClient)
            captured = {}

            def _fake_replace(records, **kwargs):
                captured["records"] = records
                return {"status": "ok", "replaced": len(records)}

            fake_service = types.SimpleNamespace(
                SearchServiceError=RuntimeError,
                replace_core_records_via_service=_fake_replace,
            )

            with patch.dict(sys.modules, {"chromadb": fake_chromadb, "omni_service": fake_service}):
                report = reindex_collection(root_dir=root, skip_backup=True, prefer_service=True)

        self.assertEqual(report["status"], "reindexed")
        self.assertEqual(report["ingest_mode"], "service")
        self.assertTrue(captured["records"])


if __name__ == "__main__":
    unittest.main()

import io
import sys
import types
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import omni_search
from omni_search_core import search_collection_records


class _ProgressiveCollection:
    def __init__(self):
        self.query_sizes = []

    def count(self):
        return 100

    def query(self, **kwargs):
        requested = kwargs["n_results"]
        self.query_sizes.append(requested)
        if requested < 40:
            return {
                "documents": [["too old"]],
                "metadatas": [[{"source": "fixture", "timestamp": "2026-03-01T00:00:00"}]],
                "distances": [[0.1]],
                "ids": [["old-1"]],
            }
        return {
            "documents": [["too old", "fresh enough"]],
            "metadatas": [[
                {"source": "fixture", "timestamp": "2026-03-01T00:00:00"},
                {"source": "fixture", "timestamp": "2026-03-06T12:00:00"},
            ]],
            "distances": [[0.1, 0.2]],
            "ids": [["old-1", "new-1"]],
        }


class _DirectRuntime:
    def search_records(self, *args, **kwargs):
        return [
            {
                "id": "direct-1",
                "distance": 0.25,
                "content": "direct result",
                "metadata": {"source": "direct", "timestamp": "2026-03-06T12:00:00"},
            }
        ]


class TestSearchService(unittest.TestCase):
    def test_search_memory_uses_service_when_available(self):
        fake_service = types.SimpleNamespace(
            SearchServiceError=RuntimeError,
            search_via_service=lambda *args, **kwargs: [
                {
                    "id": "service-1",
                    "distance": 0.1,
                    "content": "service result",
                    "metadata": {"source": "service", "timestamp": "2026-03-06T12:00:00"},
                }
            ],
        )
        output = io.StringIO()
        with patch.dict(sys.modules, {"omni_service": fake_service}):
            with patch.object(omni_search, "SearchRuntime", side_effect=AssertionError("direct path should not run")):
                with redirect_stdout(output):
                    omni_search.search_memory("release", prefer_service=True)
        self.assertIn("service result", output.getvalue())

    def test_search_memory_falls_back_to_direct_runtime_when_service_fails(self):
        class FakeServiceError(RuntimeError):
            pass

        fake_service = types.SimpleNamespace(
            SearchServiceError=FakeServiceError,
            search_via_service=lambda *args, **kwargs: (_ for _ in ()).throw(FakeServiceError("down")),
        )
        output = io.StringIO()
        with patch.dict(sys.modules, {"omni_service": fake_service}):
            with patch.object(omni_search, "SearchRuntime", return_value=_DirectRuntime()):
                with redirect_stdout(output):
                    omni_search.search_memory("release", prefer_service=True)
        self.assertIn("direct result", output.getvalue())

    def test_time_filtered_search_expands_progressively_instead_of_scanning_full_collection(self):
        collection = _ProgressiveCollection()
        records = search_collection_records(
            collection,
            "release",
            n_results=1,
            since="2026-03-06",
        )
        self.assertEqual([item["content"] for item in records], ["fresh enough"])
        self.assertEqual(collection.query_sizes, [20, 40])


if __name__ == "__main__":
    unittest.main()

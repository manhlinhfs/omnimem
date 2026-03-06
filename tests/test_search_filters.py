import io
import subprocess
import sys
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import omni_search
from omni_metadata import build_search_where

ROOT_DIR = Path(__file__).resolve().parents[1]


class FakeCollection:
    def __init__(self):
        self.query_kwargs = None

    def count(self):
        return 25

    def query(self, **kwargs):
        self.query_kwargs = kwargs
        return {
            "documents": [["release note"]],
            "metadatas": [[{"source": "omnimem", "timestamp": "2026-03-06T12:00:00.000000"}]],
            "distances": [[0.1]],
            "ids": [["memory-1"]],
        }


class FakePersistentClient:
    last_collection = None

    def __init__(self, path):
        self.path = path

    def get_or_create_collection(self, name, embedding_function):
        collection = FakeCollection()
        FakePersistentClient.last_collection = collection
        return collection


class TestSearchFilters(unittest.TestCase):
    def test_legacy_search_help_lists_filter_flags(self):
        result = subprocess.run(
            [sys.executable, str(ROOT_DIR / "omni_search.py"), "--help"],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("--source", result.stdout)
        self.assertIn("--since", result.stdout)
        self.assertIn("--until", result.stdout)
        self.assertIn("--mime-type", result.stdout)

    def _run_search(self, **kwargs):
        fake_chromadb = types.SimpleNamespace(PersistentClient=FakePersistentClient)
        fake_embeddings = types.SimpleNamespace(build_embedding_function=lambda: "ef")
        output = io.StringIO()
        with patch.dict(sys.modules, {"chromadb": fake_chromadb, "omni_embeddings": fake_embeddings}):
            with redirect_stdout(output):
                omni_search.search_memory("release", **kwargs)
        return output.getvalue(), FakePersistentClient.last_collection.query_kwargs

    def test_search_passes_where_clause_when_filters_are_present(self):
        output, query_kwargs = self._run_search(
            n_results=3,
            source="omnimem",
            since="2026-03-06",
            mime_type="Application/PDF",
        )
        self.assertEqual(
            query_kwargs["where"],
            build_search_where(
                source="omnimem",
                mime_type="Application/PDF",
            ),
        )
        self.assertIn("Filters: source=omnimem, since=2026-03-06, mime_type=application/pdf", output)
        self.assertEqual(query_kwargs["n_results"], 25)

    def test_search_omits_where_clause_without_filters(self):
        _, query_kwargs = self._run_search(n_results=2)
        self.assertEqual(query_kwargs["n_results"], 2)
        self.assertNotIn("where", query_kwargs)

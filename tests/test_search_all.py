import os
import tempfile
import unittest
from unittest.mock import patch

from omnimem.search import federate_with_notes


def _restore_env(name, previous_value):
    if previous_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous_value


def _remove_tree(path):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


class _EmptyCodemapRuntime:
    def __init__(self, *args, **kwargs):
        pass

    def query(self, query, n_results=5):
        return []


class TestFederateWithNotes(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        previous_home = os.environ.get("OMNIMEM_HOME")
        self.addCleanup(_restore_env, "OMNIMEM_HOME", previous_home)
        self.addCleanup(_remove_tree, self.tmpdir)
        os.environ["OMNIMEM_HOME"] = self.tmpdir

    def test_federation_tags_each_record_with_collection(self):
        core = [
            {"id": "c1", "distance": 0.4, "content": "doc one", "metadata": {}},
            {"id": "c2", "distance": 0.7, "content": "doc two", "metadata": {}},
        ]
        notes = [
            {
                "id": "n1",
                "distance": 0.5,
                "document": "note body",
                "metadata": {"id": "n1", "slug": "note-one", "title": "Note One"},
            }
        ]
        codemap = [
            {
                "id": "demo::symbol::a.py::function::alpha::L1",
                "distance": 0.6,
                "document": "alpha\nkind: function\nlanguage: python",
                "metadata": {"kind": "symbol", "name": "alpha", "language": "python"},
            }
        ]

        class _StubCodemapRuntime:
            def __init__(self, *args, **kwargs):
                pass

            def query(self, query, n_results=5):
                return codemap

        with patch("omnimem.note_index.search_notes", return_value=notes), patch(
            "omnimem.codemap.CodemapRuntime", _StubCodemapRuntime
        ):
            merged = federate_with_notes("query", core, n_results=10)

        collections = sorted(record["collection"] for record in merged)
        self.assertEqual(
            collections,
            ["omnimem_codemap", "omnimem_core", "omnimem_core", "omnimem_notes"],
        )

    def test_results_sort_by_distance_ascending(self):
        core = [{"id": "c1", "distance": 0.9, "content": "a", "metadata": {}}]
        notes = [
            {"id": "n1", "distance": 0.1, "document": "b", "metadata": {"id": "n1"}},
            {"id": "n2", "distance": 0.5, "document": "c", "metadata": {"id": "n2"}},
        ]

        with patch("omnimem.note_index.search_notes", return_value=notes), patch(
            "omnimem.codemap.CodemapRuntime", _EmptyCodemapRuntime
        ):
            merged = federate_with_notes("query", core, n_results=5)

        distances = [record["distance"] for record in merged]
        self.assertEqual(distances, sorted(distances))

    def test_limit_applied_after_merge(self):
        core = [{"id": f"c{i}", "distance": i * 0.1, "content": "x", "metadata": {}} for i in range(5)]
        notes = [
            {"id": f"n{i}", "distance": i * 0.05, "document": "y", "metadata": {"id": f"n{i}"}}
            for i in range(5)
        ]

        with patch("omnimem.note_index.search_notes", return_value=notes), patch(
            "omnimem.codemap.CodemapRuntime", _EmptyCodemapRuntime
        ):
            merged = federate_with_notes("query", core, n_results=3)

        self.assertEqual(len(merged), 3)

    def test_empty_notes_returns_just_core(self):
        core = [{"id": "c1", "distance": 0.2, "content": "a", "metadata": {}}]
        with patch("omnimem.note_index.search_notes", return_value=[]), patch(
            "omnimem.codemap.CodemapRuntime", _EmptyCodemapRuntime
        ):
            merged = federate_with_notes("query", core, n_results=5)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["collection"], "omnimem_core")

    def test_search_notes_failure_does_not_break_federation(self):
        core = [{"id": "c1", "distance": 0.2, "content": "a", "metadata": {}}]
        with patch("omnimem.note_index.search_notes", side_effect=RuntimeError("boom")), patch(
            "omnimem.codemap.CodemapRuntime", _EmptyCodemapRuntime
        ):
            merged = federate_with_notes("query", core, n_results=5)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["collection"], "omnimem_core")


if __name__ == "__main__":
    unittest.main()

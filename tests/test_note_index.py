import os
import tempfile
import unittest

from omni_note import create_note
from omni_note_index import (
    NOTES_COLLECTION_NAME,
    NoteRuntime,
    index_note_record,
    reindex_all_notes,
    render_document,
    render_metadata,
    search_notes,
    unindex_note_id,
)
from omni_vault import ensure_vault_layout


def _restore_env(name, previous_value):
    if previous_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous_value


def _remove_tree(path):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


class TestRenderHelpers(unittest.TestCase):
    def test_render_document_combines_title_and_body(self):
        document = render_document({"title": "Hello"}, "Body line.\n")
        self.assertIn("Hello", document)
        self.assertIn("Body line.", document)

    def test_render_metadata_serializes_lists_to_strings(self):
        metadata = render_metadata(
            {
                "id": "abc",
                "slug": "demo",
                "title": "Demo",
                "type": "note",
                "tags": ["one", "Two"],
                "source": "omnimem-cli",
            },
            "/tmp/demo.md",
        )
        self.assertEqual(metadata["id"], "abc")
        self.assertEqual(metadata["slug"], "demo")
        self.assertEqual(metadata["tags"], "one,two")
        self.assertEqual(metadata["path"], "/tmp/demo.md")


class TestNoteIndexLifecycle(unittest.TestCase):
    """ChromaDB-backed integration test for the notes index."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        previous_home = os.environ.get("OMNIMEM_HOME")
        self.addCleanup(_restore_env, "OMNIMEM_HOME", previous_home)
        self.addCleanup(_remove_tree, self.tmpdir)
        os.environ["OMNIMEM_HOME"] = self.tmpdir
        ensure_vault_layout(root_dir=self.tmpdir)
        try:
            self.runtime = NoteRuntime(root_dir=self.tmpdir)
        except Exception as exc:
            self.skipTest(f"ChromaDB unavailable: {exc}")

    def test_runtime_uses_notes_collection_name(self):
        self.assertEqual(self.runtime.collection.name, NOTES_COLLECTION_NAME)

    def test_index_then_search_finds_note(self):
        record = create_note(
            "Why we chose FastAPI for auth",
            body="FastAPI offered async, type hints, and great docs.\n",
            note_type="decision",
            tags="auth,backend",
            root_dir=self.tmpdir,
        )
        result = index_note_record(
            record["frontmatter"],
            "FastAPI offered async, type hints, and great docs.\n",
            record["path"],
            runtime=self.runtime,
            root_dir=self.tmpdir,
        )
        self.assertTrue(result["indexed"])

        results = search_notes("FastAPI auth", n_results=5, root_dir=self.tmpdir)
        self.assertTrue(any(r.get("metadata", {}).get("slug") == record["slug"] for r in results))

    def test_unindex_removes_record(self):
        record = create_note("Removable note", body="To be removed.\n", root_dir=self.tmpdir)
        index_note_record(
            record["frontmatter"],
            "To be removed.\n",
            record["path"],
            runtime=self.runtime,
            root_dir=self.tmpdir,
        )
        before = self.runtime.count()
        unindex_note_id(record["id"], runtime=self.runtime, root_dir=self.tmpdir)
        after = self.runtime.count()
        self.assertGreater(before, after)

    def test_reindex_rebuilds_from_disk(self):
        for index in range(3):
            create_note(f"Reindex sample {index}", body=f"Body {index}\n", root_dir=self.tmpdir)
        report = reindex_all_notes(root_dir=self.tmpdir)
        self.assertEqual(report["total"], 3)
        self.assertEqual(report["indexed"], 3)


if __name__ == "__main__":
    unittest.main()

import unittest

from omni_chunking import build_import_records, chunk_document, detect_chunk_profile


TEST_CONFIG = {
    "chunk_target_tokens": 18,
    "chunk_overlap_tokens": 5,
    "code_chunk_target_tokens": 10,
    "code_chunk_overlap_tokens": 3,
    "ocr_chunk_target_tokens": 12,
    "ocr_chunk_overlap_tokens": 4,
}


class TestOmniChunking(unittest.TestCase):
    def test_detect_chunk_profile_uses_code_extension(self):
        profile = detect_chunk_profile(mime_type="text/plain", file_path="example.py")
        self.assertEqual(profile, "code")

    def test_chunk_document_splits_prose_with_overlap_and_section_paths(self):
        content = """# Overview

First paragraph explains the overall release flow in enough detail to need splitting.

Second paragraph adds more retrieval context and keeps the chunker busy.

## Details

Third paragraph continues the story so overlap can carry context across chunks."""
        plan = chunk_document(
            content,
            mime_type="text/markdown",
            file_path="guide.md",
            config_values=TEST_CONFIG,
        )

        self.assertEqual(plan["profile"], "prose")
        self.assertGreaterEqual(len(plan["chunks"]), 2)
        self.assertEqual(plan["chunks"][0]["section_path"], "Overview")
        self.assertIn("Second paragraph", plan["chunks"][1]["text"])
        self.assertGreater(plan["chunks"][1]["chunk_tokens"], 0)

    def test_build_import_records_adds_chunk_metadata(self):
        records = build_import_records(
            content="Paragraph one. Paragraph two. Paragraph three.",
            mime_type="text/markdown",
            source_name="guide.md",
            doc_metadata={"doc_title": "Guide"},
            file_path="/tmp/guide.md",
            timestamp="2026-03-06T12:00:00.000000",
            import_group_id="group-1",
            config_values=TEST_CONFIG,
        )

        self.assertTrue(records["documents"])
        metadata = records["metadatas"][0]
        self.assertEqual(metadata["chunk_strategy"], "v2")
        self.assertEqual(metadata["import_group_id"], "group-1")
        self.assertEqual(metadata["doc_title"], "Guide")
        self.assertIn("chunk_target_tokens", metadata)
        self.assertIn("chunk_overlap_tokens", metadata)


if __name__ == "__main__":
    unittest.main()

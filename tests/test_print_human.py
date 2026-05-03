"""Verify the unified note CLI emits a readable plain-text format when
`--json` is not set.

Before this fix, both branches of `_print` dumped indented JSON, so the
`--json` flag was a no-op for every note CLI verb. These tests pin the
new shape (key=value summaries, nested expansion, list counts) so a
regression doesn't silently restore the JSON-only output.
"""

import io
import unittest
from contextlib import redirect_stdout

import omnimem


def _capture(payload, as_json=False):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        omnimem._print(payload, as_json)
    return buffer.getvalue()


class TestPrintHuman(unittest.TestCase):
    def test_json_path_still_emits_indented_json(self):
        out = _capture({"created": {"slug": "foo"}}, as_json=True)
        self.assertIn('"created"', out)
        self.assertIn('"slug": "foo"', out)

    def test_dict_with_scalar_value_renders_as_key_value(self):
        out = _capture({"deleted": "decision-foo"}, as_json=False)
        self.assertEqual(out.strip(), "deleted: decision-foo")

    def test_dict_with_summary_keys_collapses_to_inline(self):
        out = _capture(
            {"created": {"slug": "foo", "title": "Foo Title", "path": "/tmp/foo.md"}},
            as_json=False,
        )
        self.assertIn("created:", out)
        self.assertIn("slug=foo", out)
        self.assertIn("title=Foo Title", out)
        self.assertIn("path=/tmp/foo.md", out)

    def test_list_of_records_renders_numbered_with_count(self):
        payload = {
            "notes": [
                {"slug": "alpha", "title": "Alpha", "type": "note"},
                {"slug": "beta", "title": "Beta", "type": "decision"},
            ]
        }
        out = _capture(payload, as_json=False)
        self.assertIn("notes (2):", out)
        self.assertIn("1. slug=alpha", out)
        self.assertIn("title=Alpha", out)
        self.assertIn("2. slug=beta", out)

    def test_search_results_include_score(self):
        payload = {
            "query": "auth",
            "results": [
                {"slug": "auth-1", "title": "A1", "score": 0.123456},
            ],
        }
        out = _capture(payload, as_json=False)
        self.assertIn("query: auth", out)
        self.assertIn("results (1):", out)
        # score formatted to 3 decimals
        self.assertIn("score=0.123", out)

    def test_multiline_string_indents_each_line(self):
        out = _capture({"body": "line one\nline two\nline three"}, as_json=False)
        lines = out.splitlines()
        self.assertEqual(lines[0], "body:")
        self.assertEqual(lines[1], "  line one")
        self.assertEqual(lines[2], "  line two")
        self.assertEqual(lines[3], "  line three")

    def test_nested_dict_without_summary_keys_expands(self):
        payload = {"frontmatter": {"created_at": "2026-01-01", "tags": ["a", "b"]}}
        out = _capture(payload, as_json=False)
        self.assertIn("frontmatter:", out)
        self.assertIn("created_at: 2026-01-01", out)

    def test_empty_dict_prints_empty_marker(self):
        out = _capture({}, as_json=False)
        self.assertEqual(out.strip(), "(empty)")

    def test_empty_list_field_prints_zero_count(self):
        out = _capture({"backlinks": []}, as_json=False)
        self.assertIn("backlinks (0):", out)


if __name__ == "__main__":
    unittest.main()

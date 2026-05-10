import os
import tempfile
import unittest
from pathlib import Path

from omnimem.note import (
    NoteError,
    add_link,
    create_note,
    delete_note,
    extract_wikilinks,
    find_backlinks,
    list_notes,
    parse_frontmatter,
    read_note,
    remove_link,
    serialize_note,
    write_note,
)
from omnimem.vault import (
    DEFAULT_NOTE_TYPE,
    ensure_vault_layout,
    list_existing_note_slugs,
    slugify,
    unique_slug,
)


def _restore_env(name, previous_value):
    if previous_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous_value


def _remove_tree(path):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


class TestSlug(unittest.TestCase):
    def test_basic_kebab_case(self):
        self.assertEqual(slugify("Why we chose FastAPI"), "why-we-chose-fastapi")

    def test_unicode_normalized_to_ascii(self):
        self.assertEqual(slugify("Quyết định chọn FastAPI"), "quyet-dinh-chon-fastapi")

    def test_collapses_runs_of_punctuation(self):
        self.assertEqual(slugify("foo!!! bar___baz"), "foo-bar-baz")

    def test_empty_input_rejected(self):
        with self.assertRaises(ValueError):
            slugify("   ")

    def test_unique_slug_disambiguates(self):
        existing = {"foo", "foo-2"}
        self.assertEqual(unique_slug("foo", existing), "foo-3")
        self.assertEqual(unique_slug("bar", existing), "bar")


class TestFrontmatter(unittest.TestCase):
    def test_parse_round_trip(self):
        text = (
            "---\n"
            "id: abc-123\n"
            "slug: hello-world\n"
            "title: Hello\n"
            "tags:\n  - one\n  - two\n"
            "---\n"
            "\nBody content here.\n"
        )
        frontmatter, body = parse_frontmatter(text)
        self.assertEqual(frontmatter["slug"], "hello-world")
        self.assertEqual(frontmatter["tags"], ["one", "two"])
        self.assertIn("Body content", body)

    def test_no_frontmatter_returns_empty_dict(self):
        frontmatter, body = parse_frontmatter("Just a body, no frontmatter\n")
        self.assertEqual(frontmatter, {})
        self.assertIn("Just a body", body)

    def test_invalid_yaml_raises_note_error(self):
        bad = "---\nid: [unterminated\n---\nbody\n"
        with self.assertRaises(NoteError):
            parse_frontmatter(bad)

    def test_serialize_reparses_to_same_data(self):
        data = {
            "id": "abc",
            "slug": "demo",
            "title": "Demo",
            "tags": ["a", "b"],
            "links": ["other-slug"],
        }
        serialized = serialize_note(data, "Body line.\n")
        parsed_front, parsed_body = parse_frontmatter(serialized)
        self.assertEqual(parsed_front, data)
        self.assertIn("Body line", parsed_body)


class TestWikilinkParsing(unittest.TestCase):
    def test_extracts_basic_links_in_order(self):
        body = "See [[alpha]] and then [[beta|Beta Display]] also [[alpha]] again."
        self.assertEqual(extract_wikilinks(body), ["alpha", "beta"])

    def test_empty_body_returns_empty_list(self):
        self.assertEqual(extract_wikilinks(""), [])

    def test_ignores_malformed_brackets(self):
        body = "[not a link] and [[]] and [[ ]]"
        self.assertEqual(extract_wikilinks(body), [])


class TestNoteLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        previous_home = os.environ.get("OMNIMEM_HOME")
        self.addCleanup(_restore_env, "OMNIMEM_HOME", previous_home)
        self.addCleanup(_remove_tree, self.tmpdir)
        os.environ["OMNIMEM_HOME"] = self.tmpdir
        ensure_vault_layout(root_dir=self.tmpdir)

    def _root(self):
        return self.tmpdir

    def test_create_writes_file_with_expected_frontmatter(self):
        result = create_note(
            "Why we chose FastAPI",
            body="Pros: speed, types. Related: [[auth-flow-pattern]].\n",
            note_type="decision",
            tags="auth, backend",
            root_dir=self._root(),
        )

        self.assertEqual(result["slug"], "why-we-chose-fastapi")
        self.assertTrue(Path(result["path"]).exists())

        loaded = read_note(result["slug"], root_dir=self._root())
        self.assertEqual(loaded["frontmatter"]["type"], "decision")
        self.assertEqual(loaded["frontmatter"]["tags"], ["auth", "backend"])
        self.assertEqual(loaded["frontmatter"]["links"], ["auth-flow-pattern"])
        self.assertEqual(loaded["frontmatter"]["title"], "Why we chose FastAPI")

    def test_create_disambiguates_duplicate_titles(self):
        first = create_note("Same title", root_dir=self._root())
        second = create_note("Same title", root_dir=self._root())
        self.assertEqual(first["slug"], "same-title")
        self.assertEqual(second["slug"], "same-title-2")

    def test_invalid_type_rejected(self):
        with self.assertRaises(NoteError):
            create_note("X", note_type="bogus", root_dir=self._root())

    def test_write_refreshes_links_from_body(self):
        created = create_note("Note A", body="Empty body.\n", root_dir=self._root())
        record = read_note(created["slug"], root_dir=self._root())
        new_body = "Now references [[note-b]] and [[note-c]].\n"
        result = write_note(created["slug"], record["frontmatter"], new_body, root_dir=self._root())
        self.assertEqual(result["frontmatter"]["links"], ["note-b", "note-c"])

    def test_list_notes_filters_by_type_and_tag(self):
        create_note("A decision", note_type="decision", tags="auth", root_dir=self._root())
        create_note("A log entry", note_type="log", tags="ops", root_dir=self._root())
        create_note("Another log", note_type="log", tags="auth,ops", root_dir=self._root())

        decisions = list_notes(note_type="decision", root_dir=self._root())
        self.assertEqual(len(decisions), 1)

        auth_tagged = list_notes(tag="auth", root_dir=self._root())
        slugs = sorted(record["slug"] for record in auth_tagged)
        self.assertEqual(slugs, ["a-decision", "another-log"])

    def test_backlinks_finds_referencing_notes(self):
        create_note("Target note", root_dir=self._root())
        create_note(
            "Referrer one",
            body="Linking to [[target-note]].\n",
            root_dir=self._root(),
        )
        create_note(
            "Referrer two",
            body="Also using [[target-note|the target]] here.\n",
            root_dir=self._root(),
        )
        create_note("Unrelated", body="No links.\n", root_dir=self._root())

        backlinks = find_backlinks("target-note", root_dir=self._root())
        slugs = sorted(record["slug"] for record in backlinks)
        self.assertEqual(slugs, ["referrer-one", "referrer-two"])

    def test_add_and_remove_link_round_trip(self):
        create_note("Source", body="Initial body.\n", root_dir=self._root())
        create_note("Target", root_dir=self._root())

        add_link("source", "target", root_dir=self._root())
        record = read_note("source", root_dir=self._root())
        self.assertIn("target", record["frontmatter"]["links"])
        self.assertIn("[[target]]", record["body"])

        remove_link("source", "target", root_dir=self._root())
        record = read_note("source", root_dir=self._root())
        self.assertNotIn("target", record["frontmatter"]["links"])

    def test_delete_removes_file(self):
        created = create_note("Throwaway", root_dir=self._root())
        delete_note(created["slug"], root_dir=self._root())
        self.assertFalse(Path(created["path"]).exists())
        with self.assertRaises(NoteError):
            read_note(created["slug"], root_dir=self._root())

    def test_resolve_by_id_or_slug(self):
        created = create_note("Lookup target", root_dir=self._root())
        by_slug = read_note(created["slug"], root_dir=self._root())
        by_id = read_note(created["id"], root_dir=self._root())
        self.assertEqual(by_slug["path"], by_id["path"])

    def test_existing_slugs_listing_matches_disk(self):
        create_note("First note", root_dir=self._root())
        create_note("Second note", root_dir=self._root())
        self.assertEqual(
            list_existing_note_slugs(root_dir=self._root()),
            {"first-note", "second-note"},
        )

    def test_default_note_type_applied_when_unspecified(self):
        result = create_note("Some note", root_dir=self._root())
        loaded = read_note(result["slug"], root_dir=self._root())
        self.assertEqual(loaded["frontmatter"]["type"], DEFAULT_NOTE_TYPE)


if __name__ == "__main__":
    unittest.main()

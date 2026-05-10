import os
import tempfile
import time
import unittest
from pathlib import Path

import yaml

from omnimem.note import create_note, list_notes, parse_frontmatter
from omnimem.vault import ensure_vault_layout, note_path_for_slug


def _restore_env(name, previous_value):
    if previous_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous_value


def _remove_tree(path):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


class TestAtDateFilter(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        previous = os.environ.get("OMNIMEM_HOME")
        self.addCleanup(_restore_env, "OMNIMEM_HOME", previous)
        self.addCleanup(_remove_tree, self.tmpdir)
        os.environ["OMNIMEM_HOME"] = self.tmpdir
        ensure_vault_layout(root_dir=self.tmpdir)

    def _create_with_created_at(self, title, created_at):
        record = create_note(title, root_dir=self.tmpdir)
        path = note_path_for_slug(record["slug"], root_dir=self.tmpdir)
        text = path.read_text(encoding="utf-8")
        front, body = parse_frontmatter(text)
        front["created_at"] = created_at
        block = "---\n" + yaml.safe_dump(front, sort_keys=False, allow_unicode=True).strip() + "\n---\n"
        path.write_text(block + "\n" + body, encoding="utf-8")
        return record["slug"]

    def test_at_date_filters_by_created_at(self):
        old_slug = self._create_with_created_at("Old note", "2026-03-01T10:00:00.000000")
        new_slug = self._create_with_created_at("New note", "2026-04-15T10:00:00.000000")

        before = list_notes(at_date="2026-03-15", root_dir=self.tmpdir)
        slugs_before = {record["slug"] for record in before}
        self.assertIn(old_slug, slugs_before)
        self.assertNotIn(new_slug, slugs_before)

        after = list_notes(at_date="2026-04-30", root_dir=self.tmpdir)
        slugs_after = {record["slug"] for record in after}
        self.assertIn(old_slug, slugs_after)
        self.assertIn(new_slug, slugs_after)

    def test_at_date_iso_datetime_supported(self):
        early = self._create_with_created_at("Early", "2026-04-01T08:00:00.000000")
        late = self._create_with_created_at("Late", "2026-04-01T20:00:00.000000")

        records = list_notes(at_date="2026-04-01T12:00:00.000000", root_dir=self.tmpdir)
        slugs = {record["slug"] for record in records}
        self.assertIn(early, slugs)
        self.assertNotIn(late, slugs)

    def test_at_date_none_returns_everything(self):
        for index in range(3):
            create_note(f"Note {index}", root_dir=self.tmpdir)
        records = list_notes(root_dir=self.tmpdir)
        self.assertEqual(len(records), 3)


if __name__ == "__main__":
    unittest.main()

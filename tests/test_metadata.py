import unittest

from omni_metadata import (
    build_base_metadata,
    build_search_where,
    build_time_bounds,
    metadata_matches_time_bounds,
    normalize_tags,
    parse_time_filter,
)


class TestOmniMetadata(unittest.TestCase):
    def test_normalize_tags_deduplicates_and_sorts(self):
        self.assertEqual(normalize_tags(" Release,ops,release , Ops "), "ops,release")

    def test_build_base_metadata_normalizes_tags_and_extra_values(self):
        metadata = build_base_metadata(
            source=" omnimem ",
            timestamp="2026-03-06T12:00:00.000000",
            tags="Release, ops, release",
            record_kind="note",
            custom=["x", "y"],
        )
        self.assertEqual(metadata["source"], "omnimem")
        self.assertEqual(metadata["tags"], "ops,release")
        self.assertEqual(metadata["record_kind"], "note")
        self.assertEqual(metadata["custom"], "['x', 'y']")
        self.assertIsInstance(metadata["timestamp_epoch"], int)

    def test_parse_time_filter_expands_date_bounds(self):
        self.assertEqual(
            parse_time_filter("2026-03-06"),
            "2026-03-06T00:00:00.000000",
        )
        self.assertEqual(
            parse_time_filter("2026-03-06", upper_bound=True),
            "2026-03-06T23:59:59.999999",
        )

    def test_parse_time_filter_converts_zulu_to_naive_utc(self):
        self.assertEqual(
            parse_time_filter("2026-03-06T12:30:00Z"),
            "2026-03-06T12:30:00.000000",
        )

    def test_build_search_where_combines_supported_db_filters(self):
        where = build_search_where(source="omnimem", mime_type="Application/PDF")
        self.assertEqual(
            where,
            {
                "$and": [
                    {"source": "omnimem"},
                    {"mime_type": "application/pdf"},
                ]
            },
        )

    def test_build_time_bounds_returns_normalized_ranges(self):
        self.assertEqual(
            build_time_bounds("2026-03-06", "2026-03-07T01:02:03"),
            ("2026-03-06T00:00:00.000000", "2026-03-07T01:02:03.000000"),
        )

    def test_metadata_matches_time_bounds_uses_timestamp_field(self):
        lower_bound, upper_bound = build_time_bounds("2026-03-06", "2026-03-06")
        self.assertTrue(
            metadata_matches_time_bounds(
                {"timestamp": "2026-03-06T12:00:00.000000"},
                lower_bound,
                upper_bound,
            )
        )
        self.assertFalse(
            metadata_matches_time_bounds(
                {"timestamp": "2026-03-07T00:00:00.000000"},
                lower_bound,
                upper_bound,
            )
        )

    def test_parse_time_filter_rejects_invalid_values(self):
        with self.assertRaises(RuntimeError):
            parse_time_filter("not-a-date")

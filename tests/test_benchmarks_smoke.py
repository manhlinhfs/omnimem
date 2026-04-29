"""Smoke tests for the benchmark scripts.

Heavy benchmarks (ingest + search) need ChromaDB and the embedding model, so
those paths run lightly in CI. The tests below exercise the pure helpers and
the codemap-accuracy benchmark, which is stdlib-only.
"""

import unittest

from benchmarks.bench_codemap_accuracy import run as run_codemap_accuracy
from benchmarks.common import percentile, summarize_durations


class TestSummaryHelpers(unittest.TestCase):
    def test_percentile_with_empty_returns_none(self):
        self.assertIsNone(percentile([], 0.5))

    def test_percentile_returns_sorted_index(self):
        samples = [3.0, 1.0, 2.0, 4.0, 5.0]
        self.assertEqual(percentile(samples, 0.5), 3.0)
        self.assertEqual(percentile(samples, 0.95), 5.0)
        self.assertEqual(percentile(samples, 0.0), 1.0)

    def test_summarize_durations_includes_all_metrics(self):
        samples = [0.1, 0.2, 0.3, 0.4, 0.5]
        summary = summarize_durations(samples)
        self.assertEqual(summary["count"], 5)
        self.assertEqual(summary["min"], 0.1)
        self.assertEqual(summary["max"], 0.5)
        self.assertIn("p50", summary)
        self.assertIn("p95", summary)
        self.assertIn("p99", summary)
        self.assertIn("mean", summary)

    def test_summarize_empty_returns_count_zero(self):
        self.assertEqual(summarize_durations([]), {"count": 0})


class TestCodemapAccuracyBenchmark(unittest.TestCase):
    def test_each_language_reports_full_score(self):
        report = run_codemap_accuracy()
        for language in ("python", "javascript", "typescript", "go", "rust"):
            self.assertIn(language, report["languages"])
            score = report["languages"][language]
            for metric in ("precision", "recall", "f1"):
                self.assertGreaterEqual(score[metric], 0.0)
                self.assertLessEqual(score[metric], 1.0)
        aggregate = report["aggregate"]
        self.assertGreaterEqual(aggregate["macro_f1"], 0.0)
        self.assertLessEqual(aggregate["macro_f1"], 1.0)

    def test_synthetic_fixtures_hit_perfect_score(self):
        report = run_codemap_accuracy()
        self.assertEqual(report["aggregate"]["macro_f1"], 1.0)


if __name__ == "__main__":
    unittest.main()

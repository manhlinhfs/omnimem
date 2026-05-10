"""Retrieval accuracy benchmark.

Generates a synthetic vault where each note carries a unique anchor phrase, then
issues a query for each anchor to measure how often the matching note appears
in the top-K search results.

Reports recall@1, recall@5, recall@10 plus mean reciprocal rank (MRR).

Run from the repo root:

    python -m benchmarks.bench_retrieval --count 100
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.common import isolated_omnimem_home, write_result  # noqa: E402

DEFAULT_NOTES = 100
TOPICS = [
    "authentication and JWT token rotation",
    "payment webhooks from Stripe and PayPal",
    "embedding models for retrieval augmented generation",
    "Kubernetes blue-green deployments and rollback strategy",
    "React component hydration mismatches in SSR",
    "FastAPI dependency injection patterns for async sessions",
    "GitHub Actions matrix builds and caching",
    "incident response playbook for paging engineers",
    "schema migrations for partitioned Postgres tables",
    "end to end test fixtures for browser automation",
    "frontend bundle splitting and lazy loading",
    "service mesh sidecar configuration with Istio",
    "feature flag rollout phases and kill switches",
    "log aggregation pipelines through Vector and Loki",
    "Prometheus alert rules and silences for high cardinality",
    "Redis cluster failover behavior under network partition",
    "Kafka topic compaction and retention policies",
    "GraphQL schema federation across teams",
    "GPU scheduling for ML training workloads",
    "secret rotation through Vault dynamic credentials",
]


def _build_corpus(count, seed=42):
    rng = random.Random(seed)
    items = []
    for index in range(count):
        anchor_phrase = TOPICS[index % len(TOPICS)]
        unique_marker = f"unique-marker-{index:04d}-{rng.randint(10000, 99999)}"
        title = f"Note {index} - {anchor_phrase[:40]}"
        body = (
            f"This note covers {anchor_phrase}.\n\n"
            f"Anchor: {unique_marker}.\n"
            f"Background context filler. Index {index}.\n"
        )
        items.append(
            {
                "index": index,
                "title": title,
                "body": body,
                "anchor_phrase": anchor_phrase,
                "unique_marker": unique_marker,
            }
        )
    return items


def _seed_notes(items):
    from omnimem.note import create_note
    from omnimem.note_index import index_note_record

    by_marker = {}
    for item in items:
        record = create_note(item["title"], body=item["body"])
        index_note_record(record["frontmatter"], item["body"], record["path"])
        by_marker[item["unique_marker"]] = record["slug"]
    return by_marker


def _evaluate(items, by_marker, top_k=10):
    from omnimem.note_index import search_notes

    hit_at_1 = 0
    hit_at_5 = 0
    hit_at_10 = 0
    reciprocal_ranks = []
    misses = []

    for item in items:
        target_slug = by_marker[item["unique_marker"]]
        # Ask the query in a way that does NOT include the unique marker so
        # the retrieval has to use semantic similarity, not the exact token.
        query = item["anchor_phrase"]
        results = search_notes(query, n_results=top_k)
        slugs = []
        for record in results:
            meta = record.get("metadata") or {}
            slug = meta.get("slug")
            if slug:
                slugs.append(slug)
        try:
            rank = slugs.index(target_slug) + 1
        except ValueError:
            rank = None

        if rank is not None:
            reciprocal_ranks.append(1.0 / rank)
            if rank <= 1:
                hit_at_1 += 1
            if rank <= 5:
                hit_at_5 += 1
            if rank <= 10:
                hit_at_10 += 1
        else:
            reciprocal_ranks.append(0.0)
            misses.append(
                {
                    "anchor_phrase": item["anchor_phrase"],
                    "target_slug": target_slug,
                    "top_slugs": slugs[:5],
                }
            )

    total = len(items)
    return {
        "total": total,
        "recall_at_1": hit_at_1 / total if total else 0.0,
        "recall_at_5": hit_at_5 / total if total else 0.0,
        "recall_at_10": hit_at_10 / total if total else 0.0,
        "mrr": sum(reciprocal_ranks) / total if total else 0.0,
        "miss_count": len(misses),
        "miss_examples": misses[:5],
    }


def run(count=DEFAULT_NOTES, seed=42):
    items = _build_corpus(count, seed=seed)
    with isolated_omnimem_home():
        from omnimem.vault import ensure_vault_layout

        ensure_vault_layout()
        by_marker = _seed_notes(items)
        results = _evaluate(items, by_marker, top_k=10)

    return {
        "tool": "omnimem-bench-retrieval",
        "params": {"notes": count, "seed": seed, "top_k": 10},
        **results,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="OmniMem retrieval accuracy benchmark")
    parser.add_argument("--count", type=int, default=DEFAULT_NOTES)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save", default="retrieval", help="Result file name")
    args = parser.parse_args(argv)

    report = run(count=args.count, seed=args.seed)
    target = write_result(args.save, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote {target}")


if __name__ == "__main__":
    main()

"""Latency benchmark for OmniMem notes.

Generates a synthetic vault, then measures the wall-clock duration of:
- note creation (one record at a time)
- note search (semantic, n=5)

Outputs JSON with p50 / p95 / p99 / mean / min / max for each operation,
plus the total elapsed time.

Run from the repo root:

    python -m benchmarks.bench_latency --count 200 --queries 50
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.common import (  # noqa: E402
    isolated_omnimem_home,
    summarize_durations,
    timer,
    write_result,
)

DEFAULT_NOTES = 200
DEFAULT_QUERIES = 50

TOPICS = [
    ("auth", "JWT rotation, OAuth flows, session tokens, password reset"),
    ("payments", "Stripe webhooks, refund handling, invoice generation"),
    ("ml", "embedding models, vector similarity, retrieval augmented generation"),
    ("infra", "Kubernetes deployments, autoscaling, monitoring dashboards"),
    ("frontend", "React components, server side rendering, hydration errors"),
    ("backend", "FastAPI routers, async SQLAlchemy, dependency injection"),
    ("devops", "GitHub Actions workflows, container registries, blue-green deploys"),
    ("ops", "incident response, on-call rotation, SLO budgets"),
    ("data", "schema migrations, ETL pipelines, data warehouses"),
    ("testing", "unit testing, integration testing, end to end fixtures"),
]


def _seed_notes(count):
    from omni_note import create_note
    from omni_note_index import index_note_record

    durations = []
    for index in range(count):
        topic_name, topic_seed = TOPICS[index % len(TOPICS)]
        title = f"{topic_name.capitalize()} note {index}"
        body = (
            f"Notes on {topic_name}: {topic_seed}.\n"
            f"Index {index}, generated for the latency benchmark.\n"
        )
        with timer() as t:
            record = create_note(
                title,
                body=body,
                note_type="note",
                tags=topic_name,
            )
            index_note_record(record["frontmatter"], body, record["path"])
        durations.append(t["elapsed"])
    return durations


def _run_search_queries(query_count):
    from omni_note_index import search_notes

    durations = []
    for index in range(query_count):
        topic_name, topic_seed = TOPICS[index % len(TOPICS)]
        keyword = topic_seed.split(",")[0].strip().split()[0]
        with timer() as t:
            search_notes(keyword, n_results=5)
        durations.append(t["elapsed"])
    return durations


def run(count=DEFAULT_NOTES, queries=DEFAULT_QUERIES):
    with isolated_omnimem_home():
        with timer() as warm:
            from omni_vault import ensure_vault_layout

            ensure_vault_layout()

        with timer() as ingest:
            create_durations = _seed_notes(count)
        with timer() as search:
            search_durations = _run_search_queries(queries)

    return {
        "tool": "omnimem-bench-latency",
        "params": {"notes": count, "queries": queries},
        "warmup_seconds": warm["elapsed"],
        "total_ingest_seconds": ingest["elapsed"],
        "total_search_seconds": search["elapsed"],
        "create_note": summarize_durations(create_durations),
        "search_note": summarize_durations(search_durations),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="OmniMem latency benchmark")
    parser.add_argument("--count", type=int, default=DEFAULT_NOTES, help="Number of notes to ingest")
    parser.add_argument("--queries", type=int, default=DEFAULT_QUERIES, help="Number of search queries")
    parser.add_argument("--save", default="latency", help="Result file name (under benchmarks/results)")
    args = parser.parse_args(argv)

    report = run(count=args.count, queries=args.queries)
    target = write_result(args.save, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote {target}")


if __name__ == "__main__":
    main()

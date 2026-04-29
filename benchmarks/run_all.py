"""Run every benchmark in the OmniMem suite and emit one combined report."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.bench_codemap_accuracy import run as run_codemap_accuracy  # noqa: E402
from benchmarks.bench_latency import run as run_latency  # noqa: E402
from benchmarks.bench_retrieval import run as run_retrieval  # noqa: E402
from benchmarks.common import write_result  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run all OmniMem benchmarks")
    parser.add_argument("--latency-notes", type=int, default=200)
    parser.add_argument("--latency-queries", type=int, default=50)
    parser.add_argument("--retrieval-notes", type=int, default=100)
    parser.add_argument("--save", default="suite")
    args = parser.parse_args(argv)

    print("[1/3] Running latency benchmark...")
    latency = run_latency(count=args.latency_notes, queries=args.latency_queries)
    write_result("latency", latency)

    print("[2/3] Running retrieval accuracy benchmark...")
    retrieval = run_retrieval(count=args.retrieval_notes)
    write_result("retrieval", retrieval)

    print("[3/3] Running codemap accuracy benchmark...")
    codemap = run_codemap_accuracy()
    write_result("codemap_accuracy", codemap)

    suite = {
        "tool": "omnimem-benchmark-suite",
        "latency": latency,
        "retrieval": retrieval,
        "codemap_accuracy": codemap,
    }
    target = write_result(args.save, suite)
    print(json.dumps(suite, ensure_ascii=False, indent=2))
    print(f"\nWrote combined report to {target}")


if __name__ == "__main__":
    main()

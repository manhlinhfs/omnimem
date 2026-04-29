# benchmarks/

Reproducible measurement scripts for OmniMem. See [docs/benchmarks.md](../docs/benchmarks.md) for the full results and discussion.

## Quick start

```bash
python -m benchmarks.run_all
```

Per-suite scripts:

```bash
python -m benchmarks.bench_codemap_accuracy
python -m benchmarks.bench_latency --count 200 --queries 50
python -m benchmarks.bench_retrieval --count 100
```

Outputs land in `benchmarks/results/<name>.json`. The `results/` directory is git-tracked so result drift across releases stays visible in PR diffs.

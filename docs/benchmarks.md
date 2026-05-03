# OmniMem Benchmarks

Reproducible scripts that measure retrieval accuracy, latency, and parser quality. Results are written under `benchmarks/results/<name>.json` so numbers can be compared across releases.

The benchmark suite is **not** a substitute for end-to-end testing against real agent CLIs — those manual checks are documented in each PR's test plan.

## Running

From the repo root:

```bash
python -m benchmarks.bench_codemap_accuracy
python -m benchmarks.bench_latency --count 200 --queries 50
python -m benchmarks.bench_retrieval --count 100
python -m benchmarks.run_all                       # all three, combined report
```

Each benchmark accepts `--save <name>` to override the output file name.

## Codemap parser accuracy

What it measures: precision / recall / F1 of the per-language parser against a synthetic ground-truth source file with a known symbol set.

What it does NOT measure: real-world fidelity on production codebases. The regex parsers favor the common case over total coverage; expect a small drop on heavily macro-driven Rust, exotic JS export forms, or Go generics in the wild.

### Latest results (v1.2.0, all stdlib)

| Language | Expected | Captured | Precision | Recall | F1 |
|---|---|---|---|---|---|
| python | 5 | 5 | 1.00 | 1.00 | 1.00 |
| javascript | 3 | 3 | 1.00 | 1.00 | 1.00 |
| typescript | 5 | 5 | 1.00 | 1.00 | 1.00 |
| go | 4 | 4 | 1.00 | 1.00 | 1.00 |
| rust | 6 | 6 | 1.00 | 1.00 | 1.00 |

**Aggregate**: macro-precision 1.00, macro-recall 1.00, macro-F1 1.00.

The synthetic fixtures cover the common shapes each parser must handle. They function as a regression guard: any future refactor that drops a symbol type will fail this benchmark.

## Latency

What it measures: wall-clock time per `note new` (markdown write + ChromaDB upsert) and per `note search` (semantic top-5).

What it does NOT measure: throughput at concurrency, network effects, or warm-vs-cold variance beyond the first call.

### Latest results (v1.2.0, single Windows machine, 200 notes ingested, 50 queries)

| Metric | Create note (s) | Search note (s) |
|---|---|---|
| count | 200 | 50 |
| p50 | 0.078 | 0.038 |
| p95 | 0.277 | 0.101 |
| p99 | 0.301 | 0.201 |
| mean | 0.128 | 0.045 |
| min | 0.066 | 0.034 |
| max | 6.539 | 0.201 |

**Total ingest**: 25.6s for 200 notes (~7.8 notes/second sustained).
**Total search**: 2.2s for 50 queries (~22 queries/second sustained).
**First-create outlier**: the `max=6.5s` reflects embedding-model warm-up; subsequent notes hit p95.

These numbers come from a Python 3.10 + chromadb 1.5 + sentence-transformers `all-MiniLM-L6-v2` runtime. Linux runners typically post lower p99 numbers.

## Retrieval accuracy

What it measures: recall@1 / recall@5 / recall@10 and Mean Reciprocal Rank (MRR) on a synthetic Q&A set. Each note carries a unique anchor phrase from a topic pool; the query strips the per-note marker and asks just the topic phrase, so the retriever must rely on semantic similarity rather than exact-token match.

What it does NOT measure: long-conversation memory (LOCOMO-style), multi-hop reasoning, or temporal recency bias.

### Latest results (v1.2.0, 100 notes, 20 topics, seed 42)

| Metric | Value |
|---|---|
| recall@1 | 0.20 |
| recall@5 | 1.00 |
| recall@10 | 1.00 |
| MRR | 0.457 |
| miss_count | 0 |

**Reading the numbers**: 20 topic phrases are reused across 100 notes (5 notes per topic on average). recall@5 = 1.00 means the correct note always appears in the top 5. recall@1 = 0.20 = 1/5, which is exactly chance level **given that 5 notes per topic are essentially indistinguishable to the embedding**. To meaningfully push recall@1 we would need either (a) a corpus with no near-duplicate topics, or (b) re-ranking heuristics layered on top of the embedding.

This benchmark is therefore most useful as a **floor test**: any future change that drops recall@5 below 1.00 on this fixture is a regression.

## Caveats and roadmap

- **No third-party comparison yet.** Mem0 publishes LOCOMO numbers. We do not run the same dataset, so apples-to-apples claims are intentionally avoided.
- **No e2e against real agent CLIs.** `omnimem init`, `omnimem hook`, and the MCP server are exercised by unit tests but not by spawning an actual Claude Code / Codex / Gemini / Cursor session in the benchmark suite. Manual checks live in each PR's test plan.
- **No load test.** The latency numbers reflect single-threaded sequential calls. Concurrent ingest/search performance is not characterized.
- **Single hardware sample.** The numbers come from one developer machine; CI does not yet run the benchmarks.

Stretch goals (v1.3+):

- LOCOMO-style long-conversation benchmark to compare against Mem0 / MemPalace
- Concurrent-load benchmark for the warm service path
- Real-codebase codemap accuracy on Django / React / Kubernetes / actix-web etc.
- Automated e2e harness for Claude Code (gated by Claude Code CLI installed on the runner)

"""Shared helpers for OmniMem benchmarks."""

import json
import os
import statistics
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def ensure_repo_on_path():
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))


@contextmanager
def isolated_omnimem_home():
    """Spin up an empty OmniMem runtime tree for the duration of the block."""
    tmpdir = tempfile.mkdtemp(prefix="omnimem-bench-")
    previous = os.environ.get("OMNIMEM_HOME")
    os.environ["OMNIMEM_HOME"] = tmpdir
    try:
        yield Path(tmpdir)
    finally:
        if previous is None:
            os.environ.pop("OMNIMEM_HOME", None)
        else:
            os.environ["OMNIMEM_HOME"] = previous
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


@contextmanager
def timer():
    """Measure wall-clock duration of the block in seconds."""
    start = time.perf_counter()
    holder = {"elapsed": None}
    try:
        yield holder
    finally:
        holder["elapsed"] = time.perf_counter() - start


def percentile(samples, fraction):
    if not samples:
        return None
    ordered = sorted(samples)
    index = max(0, min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def summarize_durations(samples):
    if not samples:
        return {"count": 0}
    return {
        "count": len(samples),
        "p50": percentile(samples, 0.50),
        "p95": percentile(samples, 0.95),
        "p99": percentile(samples, 0.99),
        "mean": statistics.fmean(samples),
        "min": min(samples),
        "max": max(samples),
    }


def write_result(name, payload):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    target = RESULTS_DIR / f"{name}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target

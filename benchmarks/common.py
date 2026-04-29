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
    """Spin up a fully isolated OmniMem runtime tree for the duration of the block.

    Overrides every path the runtime cares about so a benchmark NEVER touches
    the user's real ChromaDB / models / vault / config:
    - `OMNIMEM_HOME`     → tmpdir/runtime
    - `OMNIMEM_CONFIG`   → tmpdir/omnimem.json (a fresh config that pins
                           db_dir / models_dir inside the tmpdir, overriding
                           any repo-local omnimem.json the user has edited)

    The previous values of both env vars are restored on exit.
    """
    import json as _json
    import shutil

    tmpdir = Path(tempfile.mkdtemp(prefix="omnimem-bench-"))
    runtime_home = tmpdir / "runtime"
    db_dir = tmpdir / "db"
    models_dir = tmpdir / "models"
    runtime_home.mkdir(parents=True, exist_ok=True)
    db_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    config_path = tmpdir / "omnimem.json"
    config_payload = {
        "home": str(runtime_home),
        "db_dir": str(db_dir),
        "models_dir": str(models_dir),
        "allow_model_download": False,
        "search_service_enabled": False,
    }
    config_path.write_text(_json.dumps(config_payload, indent=2), encoding="utf-8")

    previous_home = os.environ.get("OMNIMEM_HOME")
    previous_config = os.environ.get("OMNIMEM_CONFIG")
    os.environ["OMNIMEM_HOME"] = str(runtime_home)
    os.environ["OMNIMEM_CONFIG"] = str(config_path)

    try:
        yield runtime_home
    finally:
        if previous_home is None:
            os.environ.pop("OMNIMEM_HOME", None)
        else:
            os.environ["OMNIMEM_HOME"] = previous_home
        if previous_config is None:
            os.environ.pop("OMNIMEM_CONFIG", None)
        else:
            os.environ["OMNIMEM_CONFIG"] = previous_config
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

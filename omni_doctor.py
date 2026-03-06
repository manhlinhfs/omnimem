import argparse
import json
import os
import platform
import sys
from pathlib import Path

from omni_paths import (
    SOURCE_ROOT,
    detect_install_mode,
    get_bootstrap_command,
    get_db_dir,
    get_runtime_home,
)

from omni_embeddings import (  # noqa: E402
    MODEL_REPO_ID,
    build_embedding_function,
    ensure_model_ready,
    get_model_dir,
    is_model_bootstrapped,
)
from omni_version import add_version_argument, get_version, get_version_banner  # noqa: E402


def _result(name, status, detail, **extra):
    item = {"name": name, "status": status, "detail": detail}
    item.update(extra)
    return item


def _hf_cache_candidates():
    repo_cache_name = MODEL_REPO_ID.replace("/", "--")
    return [
        Path.home() / ".cache" / "huggingface" / "hub" / f"models--{repo_cache_name}",
        Path(os.getenv("HF_HOME", "")) / "hub" / f"models--{repo_cache_name}"
        if os.getenv("HF_HOME")
        else None,
    ]


def run_doctor(deep=False):
    install_mode_report = detect_install_mode(root_dir=SOURCE_ROOT)
    runtime_home = get_runtime_home(root_dir=SOURCE_ROOT, install_mode_report=install_mode_report)
    db_dir = get_db_dir(root_dir=SOURCE_ROOT, install_mode_report=install_mode_report)
    db_file = db_dir / "chroma.sqlite3"
    bootstrap_command = get_bootstrap_command(
        root_dir=SOURCE_ROOT,
        install_mode_report=install_mode_report,
    )
    results = []
    results.append(_result("version", "pass", get_version_banner(), version=get_version()))
    results.append(
        _result(
            "python",
            "pass" if sys.version_info >= (3, 10) else "warn",
            f"{platform.python_version()} ({sys.executable})",
        )
    )
    results.append(_result("source_root", "pass", str(SOURCE_ROOT)))
    results.append(
        _result(
            "install_mode",
            "pass",
            install_mode_report["mode"],
            detail_text=install_mode_report["detail"],
        )
    )
    results.append(_result("runtime_home", "pass", str(runtime_home)))

    if db_dir.exists():
        results.append(_result("db_dir", "pass", str(db_dir)))
    else:
        results.append(
            _result("db_dir", "warn", f"{db_dir} does not exist yet. It will be created on first use.")
        )

    if db_file.exists():
        results.append(_result("db_file", "pass", str(db_file)))
    else:
        results.append(
            _result(
                "db_file",
                "warn",
                f"{db_file} does not exist yet. Search/add/import has probably not created the DB yet.",
            )
        )

    try:
        import chromadb  # noqa: WPS433
    except Exception as exc:
        results.append(_result("chromadb_import", "fail", f"Import failed: {exc}"))
        chromadb = None
    else:
        results.append(_result("chromadb_import", "pass", "chromadb import succeeded"))

    if chromadb is not None and db_dir.exists():
        try:
            client = chromadb.PersistentClient(path=str(db_dir))
            try:
                collection = client.get_collection(name="omnimem_core")
            except ValueError:
                results.append(
                    _result("collection", "warn", "Collection 'omnimem_core' does not exist yet")
                )
            else:
                results.append(
                    _result(
                        "collection",
                        "pass",
                        f"Collection 'omnimem_core' is available with {collection.count()} items",
                    )
                )
        except Exception as exc:
            results.append(_result("db_client", "fail", f"PersistentClient init failed: {exc}"))
        else:
            results.append(_result("db_client", "pass", "PersistentClient init succeeded"))
    elif chromadb is not None:
        results.append(
            _result(
                "db_client",
                "warn",
                "Skipped client init because the DB directory does not exist yet",
            )
        )

    model_dir = get_model_dir()
    if is_model_bootstrapped(model_dir):
        results.append(_result("model_dir", "pass", str(model_dir)))
    else:
        results.append(
            _result(
                "model_dir",
                "warn",
                f"{model_dir} is missing or incomplete. Run `{bootstrap_command}`.",
            )
        )

    cache_hits = [path for path in _hf_cache_candidates() if path and path.exists()]
    if cache_hits:
        results.append(
            _result(
                "hf_cache",
                "pass",
                f"Found local Hugging Face cache candidates: {', '.join(str(path) for path in cache_hits)}",
            )
        )
    else:
        results.append(
            _result(
                "hf_cache",
                "warn",
                "No local Hugging Face cache found for the embedding model",
            )
        )

    try:
        import kreuzberg  # noqa: F401, WPS433
    except Exception as exc:
        results.append(_result("kreuzberg_import", "fail", f"Import failed: {exc}"))
    else:
        results.append(_result("kreuzberg_import", "pass", "kreuzberg import succeeded"))

    if deep:
        try:
            ready_path = ensure_model_ready()
        except Exception as exc:
            results.append(_result("model_ready", "fail", f"ensure_model_ready failed: {exc}"))
        else:
            results.append(_result("model_ready", "pass", str(ready_path)))

        try:
            build_embedding_function()
        except Exception as exc:
            results.append(
                _result("embedding_function", "fail", f"Embedding function build failed: {exc}")
            )
        else:
            results.append(
                _result("embedding_function", "pass", "Embedding function build succeeded")
            )

    overall = "pass"
    if any(item["status"] == "fail" for item in results):
        overall = "fail"
    elif any(item["status"] == "warn" for item in results):
        overall = "warn"

    return {
        "tool": "omni_doctor",
        "version": get_version(),
        "overall": overall,
        "deep": deep,
        "checks": results,
    }


def print_human_report(report):
    print(get_version_banner())
    print(f"Overall: {report['overall'].upper()}")
    print("")
    for item in report["checks"]:
        print(f"[{item['status'].upper():4}] {item['name']}: {item['detail']}")
        if item["name"] == "install_mode" and item.get("detail_text"):
            print(f"      {item['detail_text']}")


def main():
    parser = argparse.ArgumentParser(
        description="Inspect OmniMem runtime health, bootstrap state, and local dependencies"
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Also validate that the embedding model can be prepared and instantiated",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the doctor report as JSON",
    )
    add_version_argument(parser)
    args = parser.parse_args()

    report = run_doctor(deep=args.deep)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print_human_report(report)


if __name__ == "__main__":
    main()

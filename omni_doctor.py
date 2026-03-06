import argparse
import json
import os
import platform
import sys
from pathlib import Path

from omni_config import resolve_runtime_config, serialize_runtime_config
from omni_paths import SOURCE_ROOT, get_bootstrap_command, get_db_dir, get_runtime_home

from omni_embeddings import (  # noqa: E402
    MODEL_REPO_ID,
    build_embedding_function,
    ensure_model_ready,
    get_model_dir,
    is_model_bootstrapped,
)
from omni_version import add_version_argument, get_version, get_version_banner  # noqa: E402


COLLECTION_NAME = "omnimem_core"


def _result(name, status, detail, **extra):
    item = {"name": name, "status": status, "detail": detail}
    item.update(extra)
    return item


def _is_missing_collection_error(exc):
    return isinstance(exc, ValueError) or exc.__class__.__name__ == "NotFoundError"


def _hf_cache_candidates():
    repo_cache_name = MODEL_REPO_ID.replace("/", "--")
    return [
        Path.home() / ".cache" / "huggingface" / "hub" / f"models--{repo_cache_name}",
        Path(os.getenv("HF_HOME", "")) / "hub" / f"models--{repo_cache_name}"
        if os.getenv("HF_HOME")
        else None,
    ]


def run_doctor(deep=False):
    runtime_config = resolve_runtime_config(root_dir=SOURCE_ROOT, ignore_errors=True)
    config_snapshot = serialize_runtime_config(runtime_config)
    install_mode_report = runtime_config["install_mode"]
    config_report = runtime_config["config"]
    runtime_home = get_runtime_home(root_dir=SOURCE_ROOT)
    db_dir = get_db_dir(root_dir=SOURCE_ROOT)
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

    if config_report.get("error"):
        results.append(
            _result(
                "config_file",
                "fail",
                config_report["error"],
                config=config_report,
            )
        )
    elif config_report.get("loaded"):
        results.append(
            _result(
                "config_file",
                "pass",
                f"Loaded config from {config_report['selected_path']}",
                config=config_report,
            )
        )
    else:
        results.append(
            _result(
                "config_file",
                "warn",
                f"No config file loaded. Preferred path: {config_report['preferred_path']}",
                config=config_report,
            )
        )

    results.append(
        _result(
            "effective_config",
            "pass",
            "Resolved runtime settings from overrides/env/config/defaults",
            settings=config_snapshot["settings"],
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
                collection = client.get_collection(name=COLLECTION_NAME)
            except Exception as exc:
                if not _is_missing_collection_error(exc):
                    raise
                results.append(
                    _result("collection", "warn", f"Collection '{COLLECTION_NAME}' does not exist yet")
                )
            else:
                results.append(
                    _result(
                        "collection",
                        "pass",
                        f"Collection '{COLLECTION_NAME}' is available with {collection.count()} items",
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
        "effective_config": config_snapshot,
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
        if item["name"] == "config_file":
            config = item.get("config") or {}
            if config.get("candidates"):
                print("      Candidates:")
                for candidate in config["candidates"]:
                    print(f"      - {candidate}")
        if item["name"] == "effective_config":
            for setting_name, setting in (item.get("settings") or {}).items():
                print(
                    f"      {setting_name} = {setting.get('value')} "
                    f"({setting.get('source')})"
                )


def main():
    parser = argparse.ArgumentParser(
        description="Inspect OmniMem runtime health, config resolution, bootstrap state, and local dependencies"
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

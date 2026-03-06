import argparse
import datetime
import io
import json
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

from omni_config import discover_config, get_preferred_config_path, resolve_runtime_config
from omni_paths import SOURCE_ROOT, get_db_dir, get_models_root, get_runtime_home
from omni_version import add_version_argument, get_version, get_version_banner

COLLECTION_NAME = "omnimem_core"


class OpsError(RuntimeError):
    pass


def _is_missing_collection_error(exc):
    return isinstance(exc, ValueError) or exc.__class__.__name__ == "NotFoundError"


def _utc_timestamp():
    return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _ensure_output_path(output_path, default_dir, prefix, suffix, overwrite):
    if output_path:
        target = Path(output_path).expanduser()
    else:
        target = Path(default_dir).expanduser() / f"{prefix}-{_utc_timestamp()}{suffix}"

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        raise OpsError(f"Output path already exists: {target}")
    return target


def _path_has_content(path):
    candidate = Path(path)
    if not candidate.exists():
        return False
    if candidate.is_file():
        return True
    return any(candidate.iterdir())


def _write_tar_json(tar_handle, arcname, payload):
    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    info = tarfile.TarInfo(name=arcname)
    info.size = len(body)
    info.mtime = int(datetime.datetime.utcnow().timestamp())
    tar_handle.addfile(info, io.BytesIO(body))


def create_backup(
    output_path=None,
    overwrite=False,
    include_models=True,
    include_config=True,
    root_dir=SOURCE_ROOT,
):
    runtime_config = resolve_runtime_config(root_dir=root_dir)
    config_report = runtime_config["config"]
    runtime_home = get_runtime_home(root_dir=root_dir)
    db_dir = get_db_dir(root_dir=root_dir)
    models_dir = get_models_root(root_dir=root_dir)
    backup_dir = runtime_home / "backups"
    archive_path = _ensure_output_path(output_path, backup_dir, "omnimem-backup", ".tar.gz", overwrite)

    config_path = None
    if include_config and config_report.get("selected_path"):
        candidate = Path(config_report["selected_path"])
        if candidate.exists():
            config_path = candidate

    manifest = {
        "tool": "omni_backup",
        "version": get_version(),
        "created_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "install_mode": runtime_config["install_mode"],
        "runtime_home": str(runtime_home),
        "db_dir": str(db_dir),
        "models_dir": str(models_dir),
        "config_path": str(config_path) if config_path else None,
        "include_models": include_models,
        "include_config": include_config,
    }

    with tarfile.open(archive_path, "w:gz") as archive:
        _write_tar_json(archive, "manifest.json", manifest)
        if db_dir.exists():
            archive.add(db_dir, arcname="db")
        if include_models and models_dir.exists():
            archive.add(models_dir, arcname="models")
        if config_path is not None:
            archive.add(config_path, arcname="config/config.json")

    return {
        "tool": "omni_backup",
        "status": "pass",
        "output_path": str(archive_path),
        "db_included": db_dir.exists(),
        "models_included": include_models and models_dir.exists(),
        "config_included": config_path is not None,
    }


def export_memories(output_path=None, overwrite=False, root_dir=SOURCE_ROOT):
    runtime_home = get_runtime_home(root_dir=root_dir)
    export_dir = runtime_home / "exports"
    target_path = _ensure_output_path(output_path, export_dir, "omnimem-export", ".json", overwrite)

    import chromadb

    client = chromadb.PersistentClient(path=str(get_db_dir(root_dir=root_dir)))
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception as exc:
        if not _is_missing_collection_error(exc):
            raise
        items = []
    else:
        payload = collection.get(include=["documents", "metadatas"])
        documents = payload.get("documents") or []
        metadatas = payload.get("metadatas") or []
        ids = payload.get("ids") or []
        items = []
        for index, doc_id in enumerate(ids):
            items.append(
                {
                    "id": doc_id,
                    "document": documents[index],
                    "metadata": metadatas[index] if index < len(metadatas) else {},
                }
            )

    export_payload = {
        "tool": "omni_export",
        "version": get_version(),
        "exported_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "collection_name": COLLECTION_NAME,
        "record_count": len(items),
        "items": items,
    }
    target_path.write_text(json.dumps(export_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "tool": "omni_export",
        "status": "pass",
        "output_path": str(target_path),
        "record_count": len(items),
    }


def _prepare_restore_target(path, force):
    candidate = Path(path)
    if _path_has_content(candidate):
        if not force:
            raise OpsError(f"Restore target already exists and is not empty: {candidate}")
        if candidate.is_dir():
            shutil.rmtree(candidate)
        else:
            candidate.unlink()
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def restore_backup(archive_path, force=False, root_dir=SOURCE_ROOT):
    archive_path = Path(archive_path).expanduser()
    if not archive_path.exists():
        raise OpsError(f"Backup archive not found: {archive_path}")
    if not tarfile.is_tarfile(archive_path):
        raise OpsError(f"Not a valid backup archive: {archive_path}")

    db_dir = get_db_dir(root_dir=root_dir)
    models_dir = get_models_root(root_dir=root_dir)
    config_target = get_preferred_config_path(root_dir=root_dir)

    restored_targets = []
    with tempfile.TemporaryDirectory() as temp_dir:
        extract_root = Path(temp_dir)
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(extract_root)

        extracted_db = extract_root / "db"
        extracted_models = extract_root / "models"
        extracted_config = extract_root / "config" / "config.json"

        if extracted_db.exists():
            _prepare_restore_target(db_dir, force)
            shutil.copytree(extracted_db, db_dir, dirs_exist_ok=False)
            restored_targets.append(str(db_dir))

        if extracted_models.exists():
            _prepare_restore_target(models_dir, force)
            shutil.copytree(extracted_models, models_dir, dirs_exist_ok=False)
            restored_targets.append(str(models_dir))

        if extracted_config.exists():
            target_file = _prepare_restore_target(config_target, force)
            shutil.copy2(extracted_config, target_file)
            restored_targets.append(str(target_file))

    return {
        "tool": "omni_restore",
        "status": "pass",
        "input_path": str(archive_path),
        "restore_kind": "backup",
        "restored_targets": restored_targets,
    }


def restore_export(export_path, force=False, root_dir=SOURCE_ROOT):
    export_path = Path(export_path).expanduser()
    if not export_path.exists():
        raise OpsError(f"Export file not found: {export_path}")

    try:
        payload = json.loads(export_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OpsError(f"Failed to parse export JSON at '{export_path}': {exc}") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise OpsError(f"Export file '{export_path}' is missing an 'items' list")

    import chromadb

    from omni_embeddings import build_embedding_function

    client = chromadb.PersistentClient(path=str(get_db_dir(root_dir=root_dir)))

    try:
        existing = client.get_collection(name=COLLECTION_NAME)
    except Exception as exc:
        if not _is_missing_collection_error(exc):
            raise
        existing = None

    cleared_existing = False
    if existing is not None:
        existing_count = existing.count()
        if existing_count and not force:
            raise OpsError(
                f"Collection '{COLLECTION_NAME}' already contains {existing_count} items. Use --force to replace it."
            )
        client.delete_collection(name=COLLECTION_NAME)
        cleared_existing = True

    items = payload.get("items") or []
    if items:
        documents = [item["document"] for item in items]
        metadatas = [item.get("metadata") or {} for item in items]
        ids = [item["id"] for item in items]
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=build_embedding_function(),
        )
        collection.add(documents=documents, metadatas=metadatas, ids=ids)

    return {
        "tool": "omni_restore",
        "status": "pass",
        "input_path": str(export_path),
        "restore_kind": "export",
        "restored_count": len(items),
        "cleared_existing": cleared_existing,
    }


def restore_snapshot(input_path, force=False, root_dir=SOURCE_ROOT):
    candidate = Path(input_path).expanduser()
    if tarfile.is_tarfile(candidate):
        return restore_backup(candidate, force=force, root_dir=root_dir)
    return restore_export(candidate, force=force, root_dir=root_dir)


def print_human_report(report):
    print(get_version_banner())
    print(f"Status: {report['status'].upper()}")
    if report["tool"] == "omni_backup":
        print(f"Backup archive: {report['output_path']}")
        print(f"DB included: {report['db_included']}")
        print(f"Models included: {report['models_included']}")
        print(f"Config included: {report['config_included']}")
    elif report["tool"] == "omni_export":
        print(f"Export file: {report['output_path']}")
        print(f"Records exported: {report['record_count']}")
    else:
        print(f"Restore source: {report['input_path']}")
        print(f"Restore kind: {report['restore_kind']}")
        if report["restore_kind"] == "backup":
            print(f"Restored targets: {len(report.get('restored_targets', []))}")
            for path in report.get("restored_targets", []):
                print(f"- {path}")
        else:
            print(f"Restored records: {report.get('restored_count', 0)}")
            print(f"Cleared existing collection: {report.get('cleared_existing', False)}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run OmniMem backup/export/restore operations"
    )
    add_version_argument(parser)
    subparsers = parser.add_subparsers(dest="command")

    backup_parser = subparsers.add_parser("backup", help="Create a runtime backup archive")
    backup_parser.add_argument("--output", help="Write the backup archive to this path")
    backup_parser.add_argument("--overwrite", action="store_true", help="Overwrite the output path if it exists")
    backup_parser.add_argument("--no-models", action="store_true", help="Skip backing up the model directory")
    backup_parser.add_argument("--no-config", action="store_true", help="Skip backing up the active config file")
    backup_parser.add_argument("--json", action="store_true", help="Output the report as JSON")

    export_parser = subparsers.add_parser("export", help="Export the vector collection to JSON")
    export_parser.add_argument("--output", help="Write the export JSON to this path")
    export_parser.add_argument("--overwrite", action="store_true", help="Overwrite the output path if it exists")
    export_parser.add_argument("--json", action="store_true", help="Output the report as JSON")

    restore_parser = subparsers.add_parser("restore", help="Restore from a backup archive or export JSON")
    restore_parser.add_argument("input_path", help="Path to a .tar.gz backup archive or .json export file")
    restore_parser.add_argument("--force", action="store_true", help="Replace existing data at the restore target")
    restore_parser.add_argument("--json", action="store_true", help="Output the report as JSON")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == "backup":
            report = create_backup(
                output_path=args.output,
                overwrite=args.overwrite,
                include_models=not args.no_models,
                include_config=not args.no_config,
            )
        elif args.command == "export":
            report = export_memories(output_path=args.output, overwrite=args.overwrite)
        else:
            report = restore_snapshot(args.input_path, force=args.force)
    except OpsError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"tool": "omni_ops", "status": "fail", "detail": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}")
        return 1
    except RuntimeError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"tool": "omni_ops", "status": "fail", "detail": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}")
        return 1

    if getattr(args, "json", False):
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print_human_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())

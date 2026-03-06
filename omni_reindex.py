import argparse
import datetime
import json
import sys
from collections import defaultdict
from pathlib import Path

from omni_chunking import build_import_records
from omni_ops import COLLECTION_NAME, export_memories
from omni_paths import SOURCE_ROOT, get_db_dir, get_runtime_home
from omni_version import add_version_argument, get_version, get_version_banner


class ReindexError(RuntimeError):
    pass


def _is_missing_collection_error(exc):
    return isinstance(exc, ValueError) or exc.__class__.__name__ == "NotFoundError"


def _utc_stamp():
    return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _normalize_source_filter(source):
    if source is None:
        return None
    return str(source).strip()


def _is_import_record(metadata):
    if not metadata:
        return False
    return metadata.get("record_kind") == "import_chunk" or metadata.get("chunk_index") is not None


def _document_group_key(metadata):
    if metadata.get("import_group_id"):
        return str(metadata["import_group_id"])

    parts = [
        str(metadata.get("source", "")),
        str(metadata.get("timestamp", "")),
        str(metadata.get("mime_type", "")),
        str(metadata.get("doc_title", "")),
        str(metadata.get("source_path", "")),
    ]
    return "|".join(parts)


def _read_collection_items(collection):
    payload = collection.get(include=["documents", "metadatas"])
    ids = payload.get("ids") or []
    documents = payload.get("documents") or []
    metadatas = payload.get("metadatas") or []
    items = []
    for index, doc_id in enumerate(ids):
        items.append(
            {
                "id": doc_id,
                "document": documents[index],
                "metadata": metadatas[index] if index < len(metadatas) else {},
            }
        )
    return items


def _extract_doc_metadata(metadata):
    ignored_keys = {
        "source",
        "timestamp",
        "timestamp_epoch",
        "record_kind",
        "chunk_index",
        "mime_type",
        "chunk_profile",
        "chunk_strategy",
        "chunk_target_tokens",
        "chunk_overlap_tokens",
        "chunk_tokens",
        "chunk_chars",
        "import_group_id",
        "section_path",
        "reindexed_from_chunk_count",
    }
    return {
        key: value
        for key, value in (metadata or {}).items()
        if key not in ignored_keys
    }


def _rebuild_import_group(group_items):
    sorted_items = sorted(
        group_items,
        key=lambda item: int((item.get("metadata") or {}).get("chunk_index", 0)),
    )
    first_meta = sorted_items[0].get("metadata") or {}
    source_name = first_meta.get("source", "unknown")
    timestamp = first_meta.get("timestamp")
    mime_type = first_meta.get("mime_type")
    file_path = first_meta.get("source_path")
    doc_metadata = _extract_doc_metadata(first_meta)
    content = "\n\n".join(item.get("document", "").strip() for item in sorted_items if item.get("document"))
    import_group_id = first_meta.get("import_group_id")
    rebuilt = build_import_records(
        content=content,
        mime_type=mime_type,
        source_name=source_name,
        doc_metadata=doc_metadata,
        file_path=file_path,
        timestamp=timestamp,
        import_group_id=import_group_id,
        reindexed_from_chunk_count=len(sorted_items),
    )
    records = []
    for index, doc_id in enumerate(rebuilt["ids"]):
        records.append(
            {
                "id": doc_id,
                "document": rebuilt["documents"][index],
                "metadata": rebuilt["metadatas"][index],
            }
        )
    return records, rebuilt


def plan_reindex(items, source=None):
    normalized_source = _normalize_source_filter(source)
    passthrough = []
    grouped_imports = defaultdict(list)

    for item in items:
        metadata = item.get("metadata") or {}
        if _is_import_record(metadata):
            if normalized_source is not None and str(metadata.get("source", "")).strip() != normalized_source:
                passthrough.append(item)
                continue
            grouped_imports[_document_group_key(metadata)].append(item)
            continue
        passthrough.append(item)

    rebuilt_records = []
    rebuilt_groups = []
    for key in sorted(grouped_imports):
        records, details = _rebuild_import_group(grouped_imports[key])
        rebuilt_records.extend(records)
        rebuilt_groups.append(
            {
                "group_key": key,
                "source": (grouped_imports[key][0].get("metadata") or {}).get("source"),
                "original_chunks": len(grouped_imports[key]),
                "rebuilt_chunks": len(records),
                "profile": details["profile"],
                "target_tokens": details["target_tokens"],
                "overlap_tokens": details["overlap_tokens"],
            }
        )

    return {
        "matched_import_groups": len(grouped_imports),
        "matched_import_chunks": sum(len(group) for group in grouped_imports.values()),
        "passthrough_records": len(passthrough),
        "rebuilt_records": rebuilt_records,
        "rebuilt_groups": rebuilt_groups,
        "all_records": passthrough + rebuilt_records,
    }


def _add_records(collection, records, batch_size=100):
    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        collection.add(
            ids=[record["id"] for record in batch],
            documents=[record["document"] for record in batch],
            metadatas=[record.get("metadata") or {} for record in batch],
        )


def reindex_collection(
    source=None,
    dry_run=False,
    skip_backup=False,
    backup_output=None,
    root_dir=SOURCE_ROOT,
):
    import chromadb

    from omni_embeddings import build_embedding_function

    client = chromadb.PersistentClient(path=str(get_db_dir(root_dir=root_dir)))
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception as exc:
        if _is_missing_collection_error(exc):
            raise ReindexError("Collection 'omnimem_core' does not exist yet.") from exc
        raise

    items = _read_collection_items(collection)
    plan = plan_reindex(items, source=source)
    report = {
        "tool": "omni_reindex",
        "version": get_version(),
        "source": _normalize_source_filter(source),
        "total_records_before": len(items),
        "matched_import_groups": plan["matched_import_groups"],
        "matched_import_chunks": plan["matched_import_chunks"],
        "passthrough_records": plan["passthrough_records"],
        "rebuilt_groups": plan["rebuilt_groups"],
        "total_records_after": len(plan["all_records"]),
        "dry_run": dry_run,
        "backup_output": None,
    }

    if plan["matched_import_groups"] == 0:
        report["status"] = "no_import_groups"
        return report

    if dry_run:
        report["status"] = "dry_run"
        return report

    if not skip_backup:
        runtime_home = get_runtime_home(root_dir=root_dir)
        backup_path = backup_output
        if backup_path is None:
            backup_path = runtime_home / "backups" / f"omnimem-reindex-pre-{_utc_stamp()}.json"
        backup_report = export_memories(output_path=backup_path, overwrite=False, root_dir=root_dir)
        report["backup_output"] = backup_report["output_path"]

    temp_name = f"{COLLECTION_NAME}_reindex_{_utc_stamp()}"
    legacy_name = f"{COLLECTION_NAME}_legacy_{_utc_stamp()}"
    try:
        client.delete_collection(name=temp_name)
    except Exception as exc:
        if not _is_missing_collection_error(exc):
            raise

    temp_collection = client.get_or_create_collection(
        name=temp_name,
        embedding_function=build_embedding_function(),
    )
    _add_records(temp_collection, plan["all_records"])

    collection.modify(name=legacy_name)
    temp_collection.modify(name=COLLECTION_NAME)
    client.delete_collection(name=legacy_name)

    report["status"] = "reindexed"
    report["collection_name"] = COLLECTION_NAME
    return report


def print_human_report(report):
    print(get_version_banner())
    print(f"Status: {report['status'].upper()}")
    print(f"Matched import groups: {report['matched_import_groups']}")
    print(f"Matched import chunks: {report['matched_import_chunks']}")
    print(f"Records before: {report['total_records_before']}")
    print(f"Records after: {report['total_records_after']}")
    if report.get("source"):
        print(f"Source filter: {report['source']}")
    if report.get("backup_output"):
        print(f"Backup export: {report['backup_output']}")
    for group in report.get("rebuilt_groups", []):
        print(
            f"- {group['source']}: {group['original_chunks']} -> {group['rebuilt_chunks']} "
            f"({group['profile']}, target={group['target_tokens']}, overlap={group['overlap_tokens']})"
        )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Rebuild imported OmniMem chunks using the current chunking strategy"
    )
    parser.add_argument("--source", help="Only reindex imported memories from this exact source")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be rebuilt without mutating the collection",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip exporting a JSON backup before mutating the collection",
    )
    parser.add_argument(
        "--backup-output",
        help="Write the pre-reindex JSON backup to this path",
    )
    parser.add_argument("--json", action="store_true", help="Output the report as JSON")
    add_version_argument(parser)
    args = parser.parse_args(argv)

    try:
        report = reindex_collection(
            source=args.source,
            dry_run=args.dry_run,
            skip_backup=args.skip_backup,
            backup_output=args.backup_output,
        )
    except ReindexError as exc:
        if args.json:
            print(json.dumps({"tool": "omni_reindex", "status": "fail", "detail": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}")
        return 1
    except RuntimeError as exc:
        if args.json:
            print(json.dumps({"tool": "omni_reindex", "status": "fail", "detail": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}")
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print_human_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())

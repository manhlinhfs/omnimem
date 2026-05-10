import argparse
import sys

from omnimem.paths import SOURCE_ROOT
from omnimem.search_core import SearchRuntime, render_search_results
from omnimem.version import add_version_argument


def search_memory(
    query,
    n_results=5,
    full=False,
    as_json=False,
    source=None,
    since=None,
    until=None,
    mime_type=None,
    prefer_service=False,
    federate=False,
):
    records = None
    if prefer_service:
        try:
            from omnimem.service import SearchServiceError, search_via_service

            records = search_via_service(
                query,
                n_results=n_results,
                source=source,
                since=since,
                until=until,
                mime_type=mime_type,
                root_dir=SOURCE_ROOT,
                autostart=True,
            )
        except SearchServiceError:
            records = None

    if records is None:
        runtime = SearchRuntime()
        records = runtime.search_records(
            query,
            n_results=n_results,
            source=source,
            since=since,
            until=until,
            mime_type=mime_type,
        )

    if federate:
        records = federate_with_notes(query, records, n_results=n_results)

    render_search_results(
        query,
        records,
        full=full,
        as_json=as_json,
        source=source,
        since=since,
        until=until,
        mime_type=mime_type,
    )
    return records


def federate_with_notes(query, core_records, n_results=5):
    """Merge core (omnimem_core), notes, and codemap results by distance.

    Each record gains a `collection` field (`omnimem_core`, `omnimem_notes`, or
    `omnimem_codemap`) so callers can tell where a hit came from. Records are
    returned in the same shape as `search_records` (id, distance, content,
    metadata).
    """
    federated = []
    for record in core_records or []:
        item = dict(record)
        item.setdefault("collection", "omnimem_core")
        federated.append(item)

    try:
        from omnimem.note_index import search_notes

        note_records = search_notes(query, n_results=n_results)
    except Exception as exc:
        print(f"warn: notes federation skipped: {exc}", file=sys.stderr)
        note_records = []

    for record in note_records:
        meta = record.get("metadata") or {}
        federated.append(
            {
                "id": meta.get("id") or record.get("id"),
                "distance": float(record.get("distance") or 0.0),
                "content": record.get("document") or "",
                "metadata": meta,
                "collection": "omnimem_notes",
            }
        )

    try:
        from omnimem.codemap import CodemapRuntime

        codemap_runtime = CodemapRuntime()
        codemap_records = codemap_runtime.query(query, n_results=n_results)
    except Exception as exc:
        print(f"warn: codemap federation skipped: {exc}", file=sys.stderr)
        codemap_records = []

    for record in codemap_records:
        meta = record.get("metadata") or {}
        federated.append(
            {
                "id": record.get("id"),
                "distance": float(record.get("distance") or 0.0),
                "content": record.get("document") or "",
                "metadata": meta,
                "collection": "omnimem_codemap",
            }
        )

    federated.sort(key=lambda item: item.get("distance") or 0.0)
    return federated[:n_results]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search OmniMem's knowledge base")
    parser.add_argument("query", help="The search query")
    parser.add_argument("--n", type=int, default=5, help="Number of results")
    parser.add_argument("--full", action="store_true", help="Print full content without truncating")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--source", help="Only search memories from an exact source value")
    parser.add_argument("--since", help="Only search memories at or after YYYY-MM-DD or ISO-8601 datetime")
    parser.add_argument("--until", help="Only search memories at or before YYYY-MM-DD or ISO-8601 datetime")
    parser.add_argument("--mime-type", help="Only search imported memories with the exact MIME type")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Bypass the local warm search service and run the one-shot search path directly",
    )
    add_version_argument(parser)
    args = parser.parse_args()
    try:
        search_memory(
            args.query,
            args.n,
            args.full,
            args.json,
            source=args.source,
            since=args.since,
            until=args.until,
            mime_type=args.mime_type,
            prefer_service=not args.direct,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

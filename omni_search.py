import argparse
import sys

from omni_paths import SOURCE_ROOT
from omni_search_core import SearchRuntime, render_search_results
from omni_version import add_version_argument


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
):
    records = None
    if prefer_service:
        try:
            from omni_service import SearchServiceError, search_via_service

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

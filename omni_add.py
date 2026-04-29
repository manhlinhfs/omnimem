import argparse
import datetime
import sys
import uuid

from omni_metadata import build_base_metadata
from omni_paths import SOURCE_ROOT
from omni_search_core import OmniRuntime
from omni_version import add_version_argument

def add_memory(text, source="user_input", tags=None, prefer_service=False):
    doc_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat(timespec="microseconds")
    metadata = build_base_metadata(
        source=source,
        timestamp=timestamp,
        tags=tags,
        record_kind="note",
    )

    print(f"Adding memory: '{text[:50]}...'")
    documents = [text]
    metadatas = [metadata]
    ids = [doc_id]

    if prefer_service:
        try:
            from omni_service import SearchServiceError, add_records_via_service

            add_records_via_service(documents, metadatas, ids, root_dir=SOURCE_ROOT, autostart=True)
        except SearchServiceError:
            runtime = OmniRuntime(root_dir=SOURCE_ROOT)
            runtime.add_records(documents, metadatas, ids)
    else:
        runtime = OmniRuntime(root_dir=SOURCE_ROOT)
        runtime.add_records(documents, metadatas, ids)

    print(f"Success! Memory ID: {doc_id}")
    return doc_id

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add memory to OmniMem's ChromaDB")
    parser.add_argument("text", help="The text content to remember")
    parser.add_argument("--source", default="user_input", help="Source of the information")
    parser.add_argument("--tags", default=None, help="Comma separated tags")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Bypass the warm local runtime service and ingest directly in this process",
    )
    add_version_argument(parser)
    args = parser.parse_args()
    try:
        add_memory(args.text, args.source, args.tags, prefer_service=not args.direct)
    except RuntimeError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

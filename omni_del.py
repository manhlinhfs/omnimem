import argparse
import sys

from omni_paths import get_db_dir
from omni_version import add_version_argument


def _is_missing_collection_error(exc):
    return isinstance(exc, ValueError) or exc.__class__.__name__ == "NotFoundError"


def delete_memory(doc_id=None, source=None, wipe_all=False, force=False):
    import chromadb

    client = chromadb.PersistentClient(path=str(get_db_dir()))
    
    try:
        collection = client.get_collection(name="omnimem_core")
    except Exception as exc:
        if not _is_missing_collection_error(exc):
            raise
        print("OmniMem knowledge base is currently empty.")
        return 0

    if wipe_all:
        if not force:
            if not sys.stdin or not sys.stdin.isatty():
                print("Error: --wipe-all requires interactive confirmation or --force in non-interactive mode.")
                return 1
            try:
                confirm = input("Are you sure you want to completely WIPE ALL memories? (y/N): ")
            except EOFError:
                print("Error: Unable to read confirmation. Re-run interactively or pass --force.")
                return 1
            if confirm.lower() != "y":
                print("Wipe-all aborted.")
                return 1
        client.delete_collection(name="omnimem_core")
        print("OmniMem has been completely wiped.")
        return 0

    if doc_id:
        collection.delete(ids=[doc_id])
        print(f"Deleted memory with ID: {doc_id}")
        return 0
    elif source:
        collection.delete(where={"source": source})
        print(f"Deleted all memories with source: {source}")
        return 0
    else:
        print("Please provide an ID, source, or use --wipe-all")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete memories from OmniMem")
    parser.add_argument("--id", help="Delete specific memory by ID")
    parser.add_argument("--source", help="Delete all memories from a specific source file")
    parser.add_argument("--wipe-all", action="store_true", help="Completely wipe the OmniMem core")
    parser.add_argument("--force", action="store_true", help="Skip confirmation for destructive actions")
    add_version_argument(parser)
    
    args = parser.parse_args()
    sys.exit(delete_memory(doc_id=args.id, source=args.source, wipe_all=args.wipe_all, force=args.force))

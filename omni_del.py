import argparse

from omni_paths import get_db_dir
from omni_version import add_version_argument


def _is_missing_collection_error(exc):
    return isinstance(exc, ValueError) or exc.__class__.__name__ == "NotFoundError"


def delete_memory(doc_id=None, source=None, wipe_all=False):
    import chromadb

    client = chromadb.PersistentClient(path=str(get_db_dir()))
    
    try:
        collection = client.get_collection(name="omnimem_core")
    except Exception as exc:
        if not _is_missing_collection_error(exc):
            raise
        print("OmniMem knowledge base is currently empty.")
        return

    if wipe_all:
        confirm = input("Are you sure you want to completely WIPE ALL memories? (y/N): ")
        if confirm.lower() == 'y':
            client.delete_collection(name="omnimem_core")
            print("OmniMem has been completely wiped.")
        return

    if doc_id:
        collection.delete(ids=[doc_id])
        print(f"Deleted memory with ID: {doc_id}")
    elif source:
        collection.delete(where={"source": source})
        print(f"Deleted all memories with source: {source}")
    else:
        print("Please provide an ID, source, or use --wipe-all")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete memories from OmniMem")
    parser.add_argument("--id", help="Delete specific memory by ID")
    parser.add_argument("--source", help="Delete all memories from a specific source file")
    parser.add_argument("--wipe-all", action="store_true", help="Completely wipe the OmniMem core")
    add_version_argument(parser)
    
    args = parser.parse_args()
    delete_memory(doc_id=args.id, source=args.source, wipe_all=args.wipe_all)

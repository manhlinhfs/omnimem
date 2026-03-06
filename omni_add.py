import argparse
import datetime
import os
import sys
import uuid

from omni_metadata import build_base_metadata
from omni_version import add_version_argument

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".omnimem_db")

def add_memory(text, source="user_input", tags=None):
    import chromadb

    from omni_embeddings import build_embedding_function

    client = chromadb.PersistentClient(path=DB_PATH)
    ef = build_embedding_function()
    collection = client.get_or_create_collection(name="omnimem_core", embedding_function=ef)
    
    doc_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat(timespec="microseconds")
    metadata = build_base_metadata(
        source=source,
        timestamp=timestamp,
        tags=tags,
        record_kind="note",
    )

    print(f"Adding memory: '{text[:50]}...'")
    collection.add(documents=[text], metadatas=[metadata], ids=[doc_id])
    print(f"Success! Memory ID: {doc_id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add memory to OmniMem's ChromaDB")
    parser.add_argument("text", help="The text content to remember")
    parser.add_argument("--source", default="user_input", help="Source of the information")
    parser.add_argument("--tags", default=None, help="Comma separated tags")
    add_version_argument(parser)
    args = parser.parse_args()
    try:
        add_memory(args.text, args.source, args.tags)
    except RuntimeError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

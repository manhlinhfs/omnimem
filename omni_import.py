import argparse
import asyncio
import os
import sys

from omni_config import get_async_extract_timeout_seconds
from omni_chunking import build_import_records
from omni_metadata import current_timestamp
from omni_paths import get_db_dir
from omni_version import add_version_argument

async def extract_with_fallback(file_path):
    try:
        from kreuzberg import extract_file, extract_file_sync
    except ImportError:
        print("Error: The 'kreuzberg' library is not installed. Run 'pip install kreuzberg'.")
        sys.exit(1)

    try:
        timeout_seconds = get_async_extract_timeout_seconds()
        print(
            f"[OmniMem] Trying async extraction (timeout: {timeout_seconds}s)..."
        )
        extraction_result = await asyncio.wait_for(
            extract_file(file_path),
            timeout=timeout_seconds,
        )
        print("[OmniMem] Async extraction succeeded.")
        return extraction_result
    except asyncio.TimeoutError:
        print("[OmniMem] Async extraction timed out. Falling back to sync extraction...")
    except Exception as e:
        print(f"[OmniMem] Async extraction failed: {e}. Falling back to sync extraction...")

    try:
        extraction_result = extract_file_sync(file_path)
        print("[OmniMem] Sync extraction succeeded.")
        return extraction_result
    except Exception as e:
        print(f"Extraction failed for {file_path} with both async and sync paths: {e}")
        sys.exit(1)


async def import_file_advanced(file_path):
    import chromadb

    from omni_embeddings import build_embedding_function

    print(f"[OmniMem] Reading file: {file_path}")

    extraction_result = await extract_with_fallback(file_path)
    content = extraction_result.content
    mime_type = getattr(extraction_result, "mime_type", "unknown")
    doc_metadata = getattr(extraction_result, "metadata", {}) or {}

    if not content or not content.strip():
        print("Error: No content could be extracted.")
        sys.exit(1)

    client = chromadb.PersistentClient(path=str(get_db_dir()))
    ef = build_embedding_function()
    collection = client.get_or_create_collection(name="omnimem_core", embedding_function=ef)

    timestamp = current_timestamp()
    source_name = os.path.basename(file_path)
    import_records = build_import_records(
        content=content,
        mime_type=mime_type,
        source_name=source_name,
        doc_metadata={f"doc_{key}": value for key, value in doc_metadata.items()},
        file_path=file_path,
        timestamp=timestamp,
    )
    documents = import_records["documents"]
    metadatas = import_records["metadatas"]
    ids = import_records["ids"]

    print(
        "[OmniMem] Chunk profile: "
        f"{import_records['profile']} | target={import_records['target_tokens']} | "
        f"overlap={import_records['overlap_tokens']}"
    )
    print(f"Extracted {len(documents)} chunks. Ingesting to OmniMem...")

    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print(f"Success! Imported {len(documents)} memories from {file_path} (MIME: {mime_type}).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OmniMem Advanced Bulk Import (PDF, DOCX, Code, Images)"
    )
    parser.add_argument("file_path", help="Path to the file to import")
    add_version_argument(parser)
    args = parser.parse_args()
    if os.path.exists(args.file_path):
        try:
            asyncio.run(import_file_advanced(args.file_path))
        except RuntimeError as exc:
            print(f"Error: {exc}")
            sys.exit(1)
    else:
        print(f"Error: File not found: {args.file_path}")

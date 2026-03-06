import argparse
import asyncio
import datetime
import os
import sys
import uuid

from omni_metadata import build_base_metadata, coerce_metadata_value, normalize_mime_type
from omni_paths import get_db_dir
from omni_version import add_version_argument

ASYNC_EXTRACTION_TIMEOUT_SECONDS = int(os.getenv("OMNIMEM_ASYNC_EXTRACT_TIMEOUT", "20"))


async def extract_with_fallback(file_path):
    try:
        from kreuzberg import extract_file, extract_file_sync
    except ImportError:
        print("Error: The 'kreuzberg' library is not installed. Run 'pip install kreuzberg'.")
        sys.exit(1)

    try:
        print(
            f"[OmniMem] Trying async extraction (timeout: {ASYNC_EXTRACTION_TIMEOUT_SECONDS}s)..."
        )
        extraction_result = await asyncio.wait_for(
            extract_file(file_path),
            timeout=ASYNC_EXTRACTION_TIMEOUT_SECONDS,
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

    chunks = content.split("\n\n")
    client = chromadb.PersistentClient(path=str(get_db_dir()))
    ef = build_embedding_function()
    collection = client.get_or_create_collection(name="omnimem_core", embedding_function=ef)

    documents, metadatas, ids = [], [], []
    timestamp = datetime.datetime.utcnow().isoformat(timespec="microseconds")
    source_name = os.path.basename(file_path)
    valid_chunks = [c.strip() for c in chunks if c.strip()]

    print(f"Extracted {len(valid_chunks)} Markdown chunks. Ingesting to OmniMem...")

    for i, chunk in enumerate(valid_chunks):
        doc_id = str(uuid.uuid4())
        meta = build_base_metadata(
            source=source_name,
            timestamp=timestamp,
            record_kind="import_chunk",
            chunk_index=i,
            mime_type=normalize_mime_type(mime_type) or "unknown",
        )
        for k, v in doc_metadata.items():
            meta[f"doc_{k}"] = coerce_metadata_value(v)
        documents.append(chunk)
        metadatas.append(meta)
        ids.append(doc_id)

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

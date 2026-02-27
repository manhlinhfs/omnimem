import argparse
import chromadb
from chromadb.utils import embedding_functions
import os
import uuid
import datetime
import asyncio
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".omnimem_db")

async def import_file_advanced(file_path):
    print(f"[OmniMem] Reading file: {file_path}")
    try:
        from kreuzberg import extract_file
    except ImportError:
        print("Error: The 'kreuzberg' library is not installed. Run 'pip install kreuzberg'.")
        sys.exit(1)

    try:
        extraction_result = await extract_file(file_path)
        content = extraction_result.content
        mime_type = getattr(extraction_result, "mime_type", "unknown")
        doc_metadata = getattr(extraction_result, "metadata", {}) or {}
    except Exception as e:
        print(f"Extraction failed for {file_path}: {e}")
        sys.exit(1)

    if not content or not content.strip():
        print("Error: No content could be extracted.")
        sys.exit(1)

    chunks = content.split('\n\n')
    client = chromadb.PersistentClient(path=DB_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    collection = client.get_or_create_collection(name="omnimem_core", embedding_function=ef)
    
    documents, metadatas, ids = [], [], []
    timestamp = datetime.datetime.now().isoformat()
    source_name = os.path.basename(file_path)
    valid_chunks = [c.strip() for c in chunks if c.strip()]
    
    print(f"Extracted {len(valid_chunks)} Markdown chunks. Ingesting to OmniMem...")
    
    for i, chunk in enumerate(valid_chunks):
        doc_id = str(uuid.uuid4())
        meta = {"source": source_name, "timestamp": timestamp, "chunk_index": i, "mime_type": str(mime_type)}
        for k, v in doc_metadata.items():
            if isinstance(v, (str, int, float, bool)):
                meta[f"doc_{k}"] = v
            else:
                meta[f"doc_{k}"] = str(v)
        documents.append(chunk)
        metadatas.append(meta)
        ids.append(doc_id)

    if documents:
        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        print(f"Success! Imported {len(documents)} memories from {file_path} (MIME: {mime_type}).")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OmniMem Advanced Bulk Import (PDF, DOCX, Code, Images)")
    parser.add_argument("file_path", help="Path to the file to import")
    args = parser.parse_args()
    if os.path.exists(args.file_path):
        asyncio.run(import_file_advanced(args.file_path))
    else:
        print(f"Error: File not found: {args.file_path}")

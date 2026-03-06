import argparse
import json
import os
import sys

from omni_metadata import (
    build_search_where,
    build_time_bounds,
    describe_search_filters,
    metadata_matches_time_bounds,
)
from omni_version import add_version_argument

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".omnimem_db")

def search_memory(
    query,
    n_results=5,
    full=False,
    as_json=False,
    source=None,
    since=None,
    until=None,
    mime_type=None,
):
    where = build_search_where(source=source, mime_type=mime_type)
    lower_bound, upper_bound = build_time_bounds(since=since, until=until)

    import chromadb

    from omni_embeddings import build_embedding_function

    client = chromadb.PersistentClient(path=DB_PATH)
    ef = build_embedding_function()
    collection = client.get_or_create_collection(name="omnimem_core", embedding_function=ef)
    
    query_n_results = n_results
    if lower_bound is not None or upper_bound is not None:
        query_n_results = max(n_results, collection.count())

    query_kwargs = {"query_texts": [query], "n_results": query_n_results}
    if where is not None:
        query_kwargs["where"] = where
    results = collection.query(**query_kwargs)

    if lower_bound is not None or upper_bound is not None:
        filtered_documents = []
        filtered_metadatas = []
        filtered_distances = []
        filtered_ids = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]

        for index, metadata in enumerate(metadatas):
            if metadata_matches_time_bounds(metadata or {}, lower_bound, upper_bound):
                filtered_documents.append(documents[index])
                filtered_metadatas.append(metadata)
                if distances:
                    filtered_distances.append(distances[index])
                if ids:
                    filtered_ids.append(ids[index])

        results["documents"] = [filtered_documents[:n_results]]
        results["metadatas"] = [filtered_metadatas[:n_results]]
        results["distances"] = [filtered_distances[:n_results]]
        results["ids"] = [filtered_ids[:n_results]]
    
    if not results['documents'] or not results['documents'][0]:
        if as_json:
            print(json.dumps([]))
        else:
            print("No results found in OmniMem.")
        return

    documents = results['documents'][0]
    metadatas = results['metadatas'][0]
    distances = results['distances'][0]
    ids = results['ids'][0]
    
    if as_json:
        out_data = []
        for i, doc in enumerate(documents):
            out_data.append({
                "id": ids[i],
                "distance": distances[i] if distances else 0.0,
                "content": doc,
                "metadata": metadatas[i] if metadatas else {}
            })
        print(json.dumps(out_data, ensure_ascii=False, indent=2))
        return

    print(f"""
[OmniMem Search]: '{query}'""")
    filter_parts = describe_search_filters(
        source=source,
        since=since,
        until=until,
        mime_type=mime_type,
    )
    if filter_parts:
        print(f"Filters: {', '.join(filter_parts)}")
    print("""
--- FOUND MEMORIES ---""")
    for i, doc in enumerate(documents):
        meta = metadatas[i] if metadatas else {}
        dist = distances[i] if distances else 0.0
        print(f"[{i+1}] ID: {ids[i]} (Distance: {dist:.4f})")
        print(f"""Content:
{doc}""" if full else f"Content: {doc[:200]}..." if len(doc) > 200 else f"Content: {doc}")
        print(f"""Source: {meta.get('source', 'N/A')} | Time: {meta.get('timestamp', 'N/A')}
""" + "-"*30)

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
        )
    except RuntimeError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

import json

from omni_metadata import (
    build_search_where,
    build_time_bounds,
    describe_search_filters,
    metadata_matches_time_bounds,
)
from omni_paths import get_db_dir

TIME_FILTER_MIN_CANDIDATES = 20
TIME_FILTER_MULTIPLIER = 4


class SearchRuntime:
    def __init__(self):
        import chromadb

        from omni_embeddings import build_embedding_function

        self.client = chromadb.PersistentClient(path=str(get_db_dir()))
        self.embedding_function = build_embedding_function()
        self.collection = self.client.get_or_create_collection(
            name="omnimem_core",
            embedding_function=self.embedding_function,
        )

    def search_records(
        self,
        query,
        n_results=5,
        source=None,
        since=None,
        until=None,
        mime_type=None,
    ):
        return search_collection_records(
            self.collection,
            query,
            n_results=n_results,
            source=source,
            since=since,
            until=until,
            mime_type=mime_type,
        )


def _results_to_records(results, lower_bound=None, upper_bound=None):
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    ids = results.get("ids", [[]])[0]

    records = []
    for index, document in enumerate(documents):
        metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
        if lower_bound is not None or upper_bound is not None:
            if not metadata_matches_time_bounds(metadata, lower_bound, upper_bound):
                continue
        records.append(
            {
                "id": ids[index] if index < len(ids) else None,
                "distance": distances[index] if index < len(distances) else 0.0,
                "content": document,
                "metadata": metadata,
            }
        )
    return records


def search_collection_records(
    collection,
    query,
    n_results=5,
    source=None,
    since=None,
    until=None,
    mime_type=None,
):
    where = build_search_where(source=source, mime_type=mime_type)
    lower_bound, upper_bound = build_time_bounds(since=since, until=until)

    query_kwargs = {"query_texts": [query]}
    if where is not None:
        query_kwargs["where"] = where

    if lower_bound is None and upper_bound is None:
        results = collection.query(n_results=n_results, **query_kwargs)
        return _results_to_records(results)

    total_count = collection.count()
    query_n_results = min(total_count, max(n_results * TIME_FILTER_MULTIPLIER, TIME_FILTER_MIN_CANDIDATES))
    if query_n_results <= 0:
        return []

    while True:
        results = collection.query(n_results=query_n_results, **query_kwargs)
        records = _results_to_records(
            results,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )
        if len(records) >= n_results or query_n_results >= total_count:
            return records[:n_results]

        next_query_n_results = min(total_count, max(query_n_results * 2, query_n_results + n_results))
        if next_query_n_results == query_n_results:
            return records[:n_results]
        query_n_results = next_query_n_results


def render_search_results(
    query,
    records,
    full=False,
    as_json=False,
    source=None,
    since=None,
    until=None,
    mime_type=None,
):
    if not records:
        if as_json:
            print(json.dumps([], ensure_ascii=False))
        else:
            print("No results found in OmniMem.")
        return

    if as_json:
        print(json.dumps(records, ensure_ascii=False, indent=2))
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
    for index, record in enumerate(records, start=1):
        meta = record.get("metadata") or {}
        dist = record.get("distance") or 0.0
        doc = record.get("content") or ""
        print(f"[{index}] ID: {record.get('id')} (Distance: {dist:.4f})")
        print(
            f"""Content:
{doc}"""
            if full
            else f"Content: {doc[:200]}..." if len(doc) > 200 else f"Content: {doc}"
        )
        print(
            f"""Source: {meta.get('source', 'N/A')} | Time: {meta.get('timestamp', 'N/A')}
"""
            + "-" * 30
        )

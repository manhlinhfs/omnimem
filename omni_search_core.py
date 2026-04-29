import json
import threading

from omni_metadata import (
    build_search_where,
    build_time_bounds,
    describe_search_filters,
    metadata_matches_time_bounds,
)
from omni_ops import COLLECTION_NAME
from omni_paths import SOURCE_ROOT, get_db_dir

TIME_FILTER_MIN_CANDIDATES = 20
TIME_FILTER_MULTIPLIER = 4


class OmniRuntime:
    def __init__(self, root_dir=SOURCE_ROOT):
        import chromadb

        from omni_embeddings import build_embedding_function

        self.root_dir = root_dir
        self.client = chromadb.PersistentClient(path=str(get_db_dir(root_dir=root_dir)))
        self.embedding_function = build_embedding_function()
        self._lock = threading.RLock()
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_function,
        )

    def _refresh_core_collection(self):
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_function,
        )
        return self.collection

    def search_records(
        self,
        query,
        n_results=5,
        source=None,
        since=None,
        until=None,
        mime_type=None,
    ):
        with self._lock:
            return search_collection_records(
                self.collection,
                query,
                n_results=n_results,
                source=source,
                since=since,
                until=until,
                mime_type=mime_type,
            )

    def add_records(self, documents, metadatas, ids):
        if not documents:
            return {"added": 0}
        with self._lock:
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
            return {"added": len(documents)}

    def replace_core_records(self, records, batch_size=100):
        temp_name = f"{COLLECTION_NAME}_runtime_swap"
        legacy_name = f"{COLLECTION_NAME}_runtime_legacy"
        with self._lock:
            for candidate in (temp_name, legacy_name):
                try:
                    self.client.delete_collection(name=candidate)
                except Exception:
                    pass

            temp_collection = self.client.get_or_create_collection(
                name=temp_name,
                embedding_function=self.embedding_function,
            )
            _add_records_batched(temp_collection, records, batch_size=batch_size)

            try:
                current_collection = self.client.get_collection(name=COLLECTION_NAME)
            except Exception:
                current_collection = None

            if current_collection is not None:
                current_collection.modify(name=legacy_name)
            temp_collection.modify(name=COLLECTION_NAME)
            try:
                self.client.delete_collection(name=legacy_name)
            except Exception:
                pass
            self._refresh_core_collection()

        return {"replaced": len(records)}


SearchRuntime = OmniRuntime


def _add_records_batched(collection, records, batch_size=100):
    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        if not batch:
            continue
        collection.add(
            ids=[record["id"] for record in batch],
            documents=[record["document"] for record in batch],
            metadatas=[record.get("metadata") or {} for record in batch],
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

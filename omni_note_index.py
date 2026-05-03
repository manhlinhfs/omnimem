"""ChromaDB indexing layer for OmniMem notes.

The vault on disk is the source of truth. This module mirrors note state into
ChromaDB so semantic search can run against titles + bodies. All write paths
are best-effort: if ChromaDB is unavailable, the disk write must still succeed
and a warning is logged.
"""

import threading

from omni_metadata import (
    build_search_where,
    build_time_bounds,
    metadata_matches_time_bounds,
)
from omni_paths import SOURCE_ROOT, get_db_dir

NOTES_COLLECTION_NAME = "omnimem_notes"


class NoteIndexError(RuntimeError):
    pass


class NoteRuntime:
    """Direct ChromaDB runtime for the notes collection.

    Mirrors the shape of `omni_search_core.OmniRuntime` but is bound to
    `NOTES_COLLECTION_NAME` so the imports collection stays untouched.
    """

    def __init__(self, root_dir=SOURCE_ROOT):
        import chromadb

        from omni_embeddings import build_embedding_function

        self.root_dir = root_dir
        self.client = chromadb.PersistentClient(path=str(get_db_dir(root_dir=root_dir)))
        self.embedding_function = build_embedding_function()
        self._lock = threading.RLock()
        self.collection = self.client.get_or_create_collection(
            name=NOTES_COLLECTION_NAME,
            embedding_function=self.embedding_function,
        )

    def upsert(self, note_id, document, metadata):
        with self._lock:
            try:
                self.collection.delete(ids=[note_id])
            except Exception:
                pass
            self.collection.add(documents=[document], metadatas=[metadata], ids=[note_id])
            return {"upserted": 1, "id": note_id}

    def delete(self, note_id):
        with self._lock:
            try:
                self.collection.delete(ids=[note_id])
                return {"deleted": 1, "id": note_id}
            except Exception:
                return {"deleted": 0, "id": note_id}

    def clear(self):
        with self._lock:
            try:
                self.client.delete_collection(name=NOTES_COLLECTION_NAME)
            except Exception:
                pass
            self.collection = self.client.get_or_create_collection(
                name=NOTES_COLLECTION_NAME,
                embedding_function=self.embedding_function,
            )

    def count(self):
        with self._lock:
            try:
                return int(self.collection.count())
            except Exception:
                return 0

    def search(self, query, n_results=5, note_type=None, tag=None, since=None, until=None):
        with self._lock:
            where = _build_notes_where(note_type=note_type, tag=tag)
            lower_bound, upper_bound = build_time_bounds(since=since, until=until)

            kwargs = {"query_texts": [query], "n_results": max(1, int(n_results) * 2)}
            if where is not None:
                kwargs["where"] = where

            results = self.collection.query(**kwargs)
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
                        "document": document,
                        "metadata": metadata,
                    }
                )
                if len(records) >= int(n_results):
                    break
            return records


def _build_notes_where(note_type=None, tag=None):
    clauses = []
    if note_type:
        clauses.append({"type": str(note_type).strip()})
    if tag:
        clauses.append({"tags": {"$contains": str(tag).strip().lower()}})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def render_document(frontmatter, body):
    title = (frontmatter or {}).get("title", "")
    body_text = body or ""
    return f"{title}\n\n{body_text}".strip() or title or body_text


def render_metadata(frontmatter, path):
    front = frontmatter or {}
    tags_value = front.get("tags") or []
    if isinstance(tags_value, list):
        tags_str = ",".join(str(item).strip().lower() for item in tags_value if str(item).strip())
    else:
        tags_str = str(tags_value).strip().lower()
    return {
        "id": front.get("id"),
        "slug": front.get("slug"),
        "title": front.get("title", ""),
        "type": front.get("type", "note"),
        "tags": tags_str,
        "created_at": front.get("created_at", ""),
        "updated_at": front.get("updated_at", ""),
        "source": front.get("source", "omnimem-cli"),
        "agent": front.get("agent") or "",
        "project": front.get("project") or "",
        "path": str(path) if path else "",
    }


def index_note_record(frontmatter, body, path, runtime=None, root_dir=SOURCE_ROOT):
    """Best-effort: index a note in the notes collection. Returns a status dict."""
    note_id = (frontmatter or {}).get("id")
    if not note_id:
        return {"indexed": False, "reason": "missing id"}

    document = render_document(frontmatter, body)
    metadata = render_metadata(frontmatter, path)

    try:
        local_runtime = runtime or NoteRuntime(root_dir=root_dir)
        local_runtime.upsert(note_id, document, metadata)
        return {"indexed": True, "id": note_id}
    except Exception as exc:
        return {"indexed": False, "reason": str(exc)}


def unindex_note_id(note_id, runtime=None, root_dir=SOURCE_ROOT):
    if not note_id:
        return {"deleted": False, "reason": "missing id"}
    try:
        local_runtime = runtime or NoteRuntime(root_dir=root_dir)
        local_runtime.delete(note_id)
        return {"deleted": True, "id": note_id}
    except Exception as exc:
        return {"deleted": False, "reason": str(exc)}


def reindex_all_notes(root_dir=SOURCE_ROOT, dry_run=False):
    """Rebuild the notes collection from the vault on disk."""
    from omni_note import list_notes, read_note

    records = list_notes(root_dir=root_dir)
    if dry_run:
        return {"would_index": len(records), "indexed": 0}

    try:
        runtime = NoteRuntime(root_dir=root_dir)
    except Exception as exc:
        raise NoteIndexError(f"Failed to initialize notes runtime: {exc}") from exc

    runtime.clear()
    indexed = 0
    failed = []
    for record in records:
        slug = record.get("slug")
        try:
            loaded = read_note(slug, root_dir=root_dir)
        except Exception as exc:
            failed.append({"slug": slug, "reason": str(exc)})
            continue

        result = index_note_record(
            loaded.get("frontmatter") or {},
            loaded.get("body") or "",
            loaded.get("path"),
            runtime=runtime,
            root_dir=root_dir,
        )
        if result.get("indexed"):
            indexed += 1
        else:
            failed.append({"slug": slug, "reason": result.get("reason")})

    return {"indexed": indexed, "failed": failed, "total": len(records)}


def search_notes(
    query,
    n_results=5,
    note_type=None,
    tag=None,
    since=None,
    until=None,
    root_dir=SOURCE_ROOT,
    runtime=None,
):
    local_runtime = runtime or NoteRuntime(root_dir=root_dir)
    return local_runtime.search(
        query,
        n_results=n_results,
        note_type=note_type,
        tag=tag,
        since=since,
        until=until,
    )

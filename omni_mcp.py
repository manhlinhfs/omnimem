"""Minimal stdio MCP server for OmniMem.

Implements the subset of the Model Context Protocol that agent CLIs need:
- `initialize`
- `tools/list`
- `tools/call`
- `notifications/initialized` (acknowledged but ignored)
- `shutdown` / `exit`

Transport: newline-delimited JSON-RPC 2.0 over stdin/stdout.
"""

import json
import sys
import traceback

from omni_paths import SOURCE_ROOT
from omni_version import get_version

JSONRPC_VERSION = "2.0"
PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "omnimem"


def _ok(request_id, result):
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}


def _error(request_id, code, message, data=None):
    payload = {"code": code, "message": message}
    if data is not None:
        payload["data"] = data
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": payload}


def list_tool_definitions():
    """Return the static tool registry exposed by `tools/list`."""
    return [
        {
            "name": "note_new",
            "description": "Create a structured second-brain note in the OmniMem vault.",
            "inputSchema": {
                "type": "object",
                "required": ["title"],
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["note", "decision", "log", "reference", "conversation"],
                    },
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "project": {"type": "string"},
                    "agent": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "note_search",
            "description": "Semantic search across structured notes in the OmniMem vault.",
            "inputSchema": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string"},
                    "type": {"type": "string"},
                    "tag": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                    "full": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "note_show",
            "description": "Read a single note (frontmatter + body + backlinks) by slug or id.",
            "inputSchema": {
                "type": "object",
                "required": ["slug_or_id"],
                "properties": {"slug_or_id": {"type": "string"}},
                "additionalProperties": False,
            },
        },
        {
            "name": "note_link",
            "description": "Append a wikilink from one note to another.",
            "inputSchema": {
                "type": "object",
                "required": ["from", "to"],
                "properties": {
                    "from": {"type": "string"},
                    "to": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "search_all",
            "description": "Federated search across imported documents and structured notes.",
            "inputSchema": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                    "full": {"type": "boolean"},
                    "source": {"type": "string"},
                    "since": {"type": "string"},
                    "mime_type": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "import_file",
            "description": "Ingest a PDF / DOCX / source file into the OmniMem document collection.",
            "inputSchema": {
                "type": "object",
                "required": ["path"],
                "properties": {"path": {"type": "string"}},
                "additionalProperties": False,
            },
        },
    ]


def _content_text(value):
    return [{"type": "text", "text": value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)}]


def dispatch_tool(name, arguments, root_dir=SOURCE_ROOT):
    arguments = arguments or {}
    if name == "note_new":
        return _tool_note_new(arguments, root_dir=root_dir)
    if name == "note_search":
        return _tool_note_search(arguments, root_dir=root_dir)
    if name == "note_show":
        return _tool_note_show(arguments, root_dir=root_dir)
    if name == "note_link":
        return _tool_note_link(arguments, root_dir=root_dir)
    if name == "search_all":
        return _tool_search_all(arguments, root_dir=root_dir)
    if name == "import_file":
        return _tool_import_file(arguments, root_dir=root_dir)
    raise ValueError(f"Unknown tool: {name}")


def _tool_note_new(args, root_dir):
    from omni_note import create_note
    from omni_note_index import index_note_record
    from omni_vault import ensure_vault_layout

    ensure_vault_layout(root_dir=root_dir)
    title = args.get("title")
    if not title:
        raise ValueError("note_new requires a non-empty 'title'")

    tags = args.get("tags")
    if isinstance(tags, list):
        tags = ",".join(str(item) for item in tags)

    record = create_note(
        title=title,
        body=args.get("body") or "",
        note_type=args.get("type") or "note",
        tags=tags,
        agent=args.get("agent"),
        project=args.get("project"),
        root_dir=root_dir,
    )

    index_note_record(
        record["frontmatter"],
        args.get("body") or "",
        record["path"],
        root_dir=root_dir,
    )

    return {
        "content": _content_text(
            {
                "id": record["id"],
                "slug": record["slug"],
                "path": record["path"],
            }
        )
    }


def _tool_note_search(args, root_dir):
    from omni_note_index import search_notes

    query = args.get("query")
    if not query:
        raise ValueError("note_search requires 'query'")
    results = search_notes(
        query,
        n_results=int(args.get("limit") or 5),
        note_type=args.get("type"),
        tag=args.get("tag"),
        root_dir=root_dir,
    )
    payload = []
    for record in results:
        meta = record.get("metadata") or {}
        document = record.get("document") or ""
        snippet = document if args.get("full") else (document[:300] + ("..." if len(document) > 300 else ""))
        payload.append(
            {
                "id": meta.get("id") or record.get("id"),
                "slug": meta.get("slug"),
                "title": meta.get("title"),
                "type": meta.get("type"),
                "tags": meta.get("tags"),
                "path": meta.get("path"),
                "score": float(record.get("distance") or 0.0),
                "snippet": snippet,
            }
        )
    return {"content": _content_text({"results": payload})}


def _tool_note_show(args, root_dir):
    from omni_note import find_backlinks, read_note

    slug_or_id = args.get("slug_or_id")
    if not slug_or_id:
        raise ValueError("note_show requires 'slug_or_id'")
    loaded = read_note(slug_or_id, root_dir=root_dir)
    front = loaded.get("frontmatter") or {}
    backlinks = find_backlinks(front.get("slug"), root_dir=root_dir)
    return {
        "content": _content_text(
            {
                "id": front.get("id"),
                "slug": front.get("slug"),
                "title": front.get("title"),
                "frontmatter": front,
                "body": loaded.get("body"),
                "path": loaded.get("path"),
                "backlinks": backlinks,
            }
        )
    }


def _tool_note_link(args, root_dir):
    from omni_note import add_link
    from omni_note_index import index_note_record, NoteRuntime
    from omni_note import read_note

    from_slug = args.get("from")
    to_slug = args.get("to")
    if not (from_slug and to_slug):
        raise ValueError("note_link requires 'from' and 'to'")
    add_link(from_slug, to_slug, root_dir=root_dir)
    refreshed = read_note(from_slug, root_dir=root_dir)
    try:
        runtime = NoteRuntime(root_dir=root_dir)
        index_note_record(
            refreshed.get("frontmatter") or {},
            refreshed.get("body") or "",
            refreshed.get("path"),
            runtime=runtime,
            root_dir=root_dir,
        )
    except Exception:
        pass
    return {"content": _content_text({"updated": True, "from": from_slug, "to": to_slug})}


def _tool_search_all(args, root_dir):
    from omni_note_index import search_notes
    from omni_search_core import OmniRuntime

    query = args.get("query")
    if not query:
        raise ValueError("search_all requires 'query'")
    limit = int(args.get("limit") or 5)
    full = bool(args.get("full"))

    federated = []

    try:
        notes_results = search_notes(query, n_results=limit, root_dir=root_dir)
    except Exception:
        notes_results = []
    for record in notes_results:
        meta = record.get("metadata") or {}
        document = record.get("document") or ""
        federated.append(
            {
                "collection": "omnimem_notes",
                "id": meta.get("id") or record.get("id"),
                "title": meta.get("title"),
                "path": meta.get("path"),
                "score": float(record.get("distance") or 0.0),
                "content": document if full else (document[:300] + ("..." if len(document) > 300 else "")),
            }
        )

    try:
        core = OmniRuntime(root_dir=root_dir)
        core_results = core.search_records(
            query,
            n_results=limit,
            source=args.get("source"),
            since=args.get("since"),
            mime_type=args.get("mime_type"),
        )
    except Exception:
        core_results = []
    for record in core_results:
        meta = record.get("metadata") or {}
        content = record.get("content") or ""
        federated.append(
            {
                "collection": "omnimem_core",
                "id": record.get("id"),
                "title": meta.get("source"),
                "path": meta.get("source"),
                "score": float(record.get("distance") or 0.0),
                "content": content if full else (content[:300] + ("..." if len(content) > 300 else "")),
            }
        )

    federated.sort(key=lambda item: item.get("score", 0.0))
    federated = federated[:limit]
    return {"content": _content_text({"results": federated})}


def _tool_import_file(args, root_dir):
    import asyncio

    from omni_import import import_file_advanced

    path = args.get("path")
    if not path:
        raise ValueError("import_file requires 'path'")
    asyncio.run(import_file_advanced(path, prefer_service=False))
    return {"content": _content_text({"imported": True, "path": path})}


def handle_request(request, root_dir=SOURCE_ROOT):
    method = request.get("method")
    request_id = request.get("id")
    params = request.get("params") or {}

    if method == "initialize":
        return _ok(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": get_version()},
            },
        )
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return _ok(request_id, {"tools": list_tool_definitions()})
    if method == "tools/call":
        try:
            name = params.get("name")
            arguments = params.get("arguments") or {}
            tool_result = dispatch_tool(name, arguments, root_dir=root_dir)
            return _ok(request_id, tool_result)
        except ValueError as exc:
            return _error(request_id, -32602, str(exc))
        except Exception as exc:
            return _error(request_id, -32000, f"tool error: {exc}", {"trace": traceback.format_exc()})
    if method == "shutdown":
        return _ok(request_id, None)
    if method == "exit":
        return None

    return _error(request_id, -32601, f"Method not found: {method}")


def serve_stdio(stdin=None, stdout=None, root_dir=SOURCE_ROOT):
    """Run the MCP server loop until stdin closes or 'exit' is received."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    while True:
        line = stdin.readline()
        if not line:
            return 0
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            response = _error(None, -32700, f"Parse error: {exc}")
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()
            continue

        if request.get("method") == "exit":
            return 0

        response = handle_request(request, root_dir=root_dir)
        if response is None:
            continue
        stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        stdout.flush()

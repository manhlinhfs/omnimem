import argparse
import asyncio
import json
import os
import sys

from omni_version import add_version_argument, get_version_banner


def handle_add(args):
    from omni_add import add_memory

    add_memory(args.text, args.source, args.tags, prefer_service=not args.direct)
    return 0


def handle_search(args):
    from omni_search import search_memory

    until = args.until
    at_date = getattr(args, "at_date", None)
    if at_date and not until:
        until = _at_date_eod(at_date)

    search_memory(
        args.query,
        args.n,
        args.full,
        args.json,
        source=args.source,
        since=args.since,
        until=until,
        mime_type=args.mime_type,
        prefer_service=not args.direct,
        federate=getattr(args, "all", False),
    )
    return 0


def handle_import(args):
    from omni_import import import_file_advanced

    if not os.path.exists(args.file_path):
        print(f"Error: File not found: {args.file_path}")
        return 1

    asyncio.run(import_file_advanced(args.file_path, prefer_service=not args.direct))
    return 0


def handle_delete(args):
    from omni_del import delete_memory

    return delete_memory(doc_id=args.id, source=args.source, wipe_all=args.wipe_all, force=args.force)


def handle_doctor(args):
    from omni_doctor import print_human_report, run_doctor

    report = run_doctor(deep=args.deep)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print_human_report(report)
    return 0


def handle_bootstrap(args):
    from omni_embeddings import MODEL_REPO_ID, bootstrap_model, get_model_dir

    print(f"[OmniMem] Model repo: {MODEL_REPO_ID}")
    print(f"[OmniMem] Local model dir: {get_model_dir()}")
    model_dir = bootstrap_model(local_files_only=args.offline_only, force=args.force)
    print(f"[OmniMem] Model is ready at: {model_dir}")
    return 0


def handle_update(args):
    from omni_update import UpdateError, inspect_update_state, perform_update, print_human_report

    try:
        report = inspect_update_state() if args.check else perform_update(
            skip_deps=args.skip_deps,
            skip_bootstrap=args.skip_bootstrap,
            allow_model_download=args.allow_model_download,
        )
    except UpdateError as exc:
        if args.json:
            print(
                json.dumps(
                    {"tool": "omni_update", "status": "fail", "detail": str(exc)},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(f"Error: {exc}")
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print_human_report(report)
    return 0


def handle_backup(args):
    from omni_ops import OpsError, create_backup, print_human_report

    try:
        report = create_backup(
            output_path=args.output,
            overwrite=args.overwrite,
            include_models=not args.no_models,
            include_config=not args.no_config,
        )
    except OpsError as exc:
        if args.json:
            print(json.dumps({"tool": "omni_backup", "status": "fail", "detail": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}")
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print_human_report(report)
    return 0


def handle_export(args):
    from omni_ops import OpsError, export_memories, print_human_report

    try:
        report = export_memories(output_path=args.output, overwrite=args.overwrite)
    except OpsError as exc:
        if args.json:
            print(json.dumps({"tool": "omni_export", "status": "fail", "detail": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}")
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print_human_report(report)
    return 0


def handle_restore(args):
    from omni_ops import OpsError, print_human_report, restore_snapshot

    try:
        report = restore_snapshot(args.input_path, force=args.force)
    except OpsError as exc:
        if args.json:
            print(json.dumps({"tool": "omni_restore", "status": "fail", "detail": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}")
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print_human_report(report)
    return 0


def handle_reindex(args):
    from omni_reindex import ReindexError, print_human_report, reindex_collection

    try:
        report = reindex_collection(
            source=args.source,
            dry_run=args.dry_run,
            skip_backup=args.skip_backup,
            backup_output=args.backup_output,
            prefer_service=not args.direct,
        )
    except ReindexError as exc:
        if args.json:
            print(json.dumps({"tool": "omni_reindex", "status": "fail", "detail": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}")
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print_human_report(report)
    return 0


def handle_version(_args):
    print(get_version_banner())
    return 0


def _print(payload, as_json):
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    _render_human(payload)


_SUMMARY_KEYS = ("slug", "title", "id", "name", "path", "score", "from", "to")


def _format_scalar(value):
    if isinstance(value, float):
        return f"{value:.3f}"
    if value is None:
        return ""
    return str(value)


def _summary_line(item):
    if not isinstance(item, dict):
        return None
    parts = []
    for key in _SUMMARY_KEYS:
        if key not in item:
            continue
        value = item[key]
        if value in (None, ""):
            continue
        parts.append(f"{key}={_format_scalar(value)}")
        if len(parts) >= 4:
            break
    return " ".join(parts) if parts else None


def _render_human(payload, indent=0):
    pad = "  " * indent
    if payload is None:
        print(f"{pad}(none)")
        return
    if isinstance(payload, dict):
        if not payload:
            print(f"{pad}(empty)")
            return
        for key, value in payload.items():
            _render_field(key, value, indent)
        return
    if isinstance(payload, list):
        if not payload:
            print(f"{pad}(empty)")
            return
        for index, item in enumerate(payload, 1):
            _render_item(index, item, indent)
        return
    print(f"{pad}{_format_scalar(payload)}")


def _render_field(key, value, indent):
    pad = "  " * indent
    if isinstance(value, str) and "\n" in value:
        print(f"{pad}{key}:")
        for line in value.splitlines():
            print(f"{pad}  {line}")
        return
    if isinstance(value, list):
        print(f"{pad}{key} ({len(value)}):")
        for index, item in enumerate(value, 1):
            _render_item(index, item, indent + 1)
        return
    if isinstance(value, dict):
        summary = _summary_line(value)
        if summary:
            print(f"{pad}{key}: {summary}")
            return
        print(f"{pad}{key}:")
        _render_human(value, indent + 1)
        return
    print(f"{pad}{key}: {_format_scalar(value)}")


def _render_item(index, item, indent):
    pad = "  " * indent
    if isinstance(item, dict):
        summary = _summary_line(item)
        if summary:
            print(f"{pad}{index}. {summary}")
            return
        print(f"{pad}{index}.")
        _render_human(item, indent + 1)
        return
    print(f"{pad}{index}. {_format_scalar(item)}")


def _at_date_eod(at_date):
    """Translate `--at-date YYYY-MM-DD` into an end-of-day ISO timestamp."""
    if not at_date:
        return None
    raw = str(at_date).strip()
    if "T" in raw:
        return raw
    return f"{raw}T23:59:59.999999"


def handle_note(args):
    from omni_note import (
        NoteError,
        add_link,
        create_note,
        delete_note,
        find_backlinks,
        list_notes,
        read_note,
        remove_link,
        write_note,
    )
    from omni_note_index import (
        NoteIndexError,
        index_note_record,
        reindex_all_notes,
        search_notes,
        unindex_note_id,
    )
    from omni_vault import ensure_vault_layout

    ensure_vault_layout()
    action = args.note_command
    as_json = getattr(args, "json", False)

    try:
        if action == "new":
            body = args.body
            if body == "-":
                body = sys.stdin.read()
            record = create_note(
                title=args.title,
                body=body,
                note_type=args.type,
                tags=args.tags,
                agent=args.agent,
                project=args.project,
            )
            index_note_record(
                record["frontmatter"],
                body or "",
                record["path"],
            )
            _print({"created": record}, as_json)
            return 0

        if action == "show":
            loaded = read_note(args.slug_or_id)
            front = loaded.get("frontmatter") or {}
            backlinks = find_backlinks(front.get("slug"))
            _print(
                {
                    "frontmatter": front,
                    "body": loaded.get("body"),
                    "path": loaded.get("path"),
                    "backlinks": backlinks,
                },
                as_json,
            )
            return 0

        if action == "update":
            loaded = read_note(args.slug_or_id)
            front = dict(loaded.get("frontmatter") or {})
            if args.title:
                front["title"] = args.title
            if args.add_tag:
                tags = list(front.get("tags") or [])
                for tag in args.add_tag:
                    if tag and tag not in tags:
                        tags.append(tag)
                front["tags"] = tags
            if args.rm_tag:
                front["tags"] = [tag for tag in (front.get("tags") or []) if tag not in set(args.rm_tag)]
            updated = write_note(front["slug"], front, loaded.get("body") or "")
            index_note_record(updated["frontmatter"], loaded.get("body") or "", updated["path"])
            _print({"updated": updated}, as_json)
            return 0

        if action == "rm":
            loaded = read_note(args.slug_or_id)
            front = loaded.get("frontmatter") or {}
            unindex_note_id(front.get("id"))
            delete_note(args.slug_or_id)
            _print({"deleted": args.slug_or_id}, as_json)
            return 0

        if action == "list":
            records = list_notes(
                note_type=args.type,
                tag=args.tag,
                since=args.since,
                until=getattr(args, "until", None),
                at_date=getattr(args, "at_date", None),
                limit=args.limit,
            )
            _print({"notes": records}, as_json)
            return 0

        if action == "search":
            at_date = getattr(args, "at_date", None)
            at_date_eod = _at_date_eod(at_date)
            requested_n = (args.limit or 5) * (3 if at_date_eod else 1)
            records = None
            if not getattr(args, "direct", False):
                try:
                    from omni_service import (
                        SearchServiceError,
                        search_notes_via_service,
                    )

                    records = search_notes_via_service(
                        args.query,
                        n_results=requested_n,
                        note_type=args.type,
                        tag=args.tag,
                    )
                except SearchServiceError:
                    records = None
            if records is None:
                records = search_notes(
                    args.query,
                    n_results=requested_n,
                    note_type=args.type,
                    tag=args.tag,
                )
            if at_date_eod:
                records = [
                    record
                    for record in records
                    if (record.get("metadata") or {}).get("created_at", "") <= at_date_eod
                ][: args.limit or 5]
            simplified = []
            for record in records:
                meta = record.get("metadata") or {}
                document = record.get("document") or ""
                snippet = document if args.full else (document[:300] + ("..." if len(document) > 300 else ""))
                simplified.append(
                    {
                        "id": meta.get("id") or record.get("id"),
                        "slug": meta.get("slug"),
                        "title": meta.get("title"),
                        "score": float(record.get("distance") or 0.0),
                        "path": meta.get("path"),
                        "snippet": snippet,
                    }
                )
            _print({"query": args.query, "results": simplified}, as_json)
            return 0

        if action == "link":
            updated = add_link(args.from_slug, args.to_slug)
            index_note_record(
                updated["frontmatter"],
                read_note(args.from_slug).get("body") or "",
                updated["path"],
            )
            _print({"linked": {"from": args.from_slug, "to": args.to_slug}}, as_json)
            return 0

        if action == "unlink":
            updated = remove_link(args.from_slug, args.to_slug)
            index_note_record(
                updated["frontmatter"],
                read_note(args.from_slug).get("body") or "",
                updated["path"],
            )
            _print({"unlinked": {"from": args.from_slug, "to": args.to_slug}}, as_json)
            return 0

        if action == "backlinks":
            records = find_backlinks(args.slug_or_id)
            _print({"slug": args.slug_or_id, "backlinks": records}, as_json)
            return 0

        if action == "graph":
            records = list_notes()
            edges = []
            slug_index = {record["slug"] for record in records}
            for record in records:
                slug = record["slug"]
                loaded = read_note(slug)
                from omni_note import extract_wikilinks

                for target in extract_wikilinks(loaded.get("body") or ""):
                    if not args.root or target == args.root or slug == args.root:
                        edges.append({"from": slug, "to": target})
            _print(
                {
                    "nodes": [
                        {"slug": record["slug"], "title": record.get("title"), "type": record.get("type")}
                        for record in records
                    ],
                    "edges": edges,
                },
                as_json,
            )
            return 0

        if action == "reindex":
            report = reindex_all_notes(dry_run=args.dry_run)
            _print(report, as_json)
            return 0

        print(f"Unknown note action: {action}")
        return 2

    except NoteError as exc:
        if as_json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}")
        return 1
    except NoteIndexError as exc:
        if as_json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}")
        return 1


def handle_init(args):
    from omni_hooks import migrate_legacy_commands
    from omni_init import (
        InitError,
        install,
        migrate_legacy_mcp_commands,
        status,
        uninstall,
    )

    as_json = getattr(args, "json", False)
    include_mcp = not args.no_mcp

    try:
        migrated = []
        if not args.dry_run:
            migrated = migrate_legacy_commands() + migrate_legacy_mcp_commands()

        if args.status:
            report = status()
            if migrated:
                report = {"agents": report, "migrated": migrated}
            _print(report, as_json)
            return 0
        if args.uninstall:
            results = uninstall(
                args.agent,
                scope=args.scope,
                include_mcp=include_mcp,
                dry_run=args.dry_run,
            )
            payload = {"uninstalled": results}
            if migrated:
                payload["migrated"] = migrated
            _print(payload, as_json)
            return 0
        results = install(
            args.agent,
            scope=args.scope,
            include_mcp=include_mcp,
            dry_run=args.dry_run,
        )
        payload = {"installed": results}
        if migrated:
            payload["migrated"] = migrated
        _print(payload, as_json)
        return 0
    except InitError as exc:
        if as_json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}")
        return 1


def handle_quickstart(args):
    from omni_quickstart import run as run_quickstart

    as_json = getattr(args, "json", False)
    report = run_quickstart(
        assume_yes=args.yes,
        install_hooks=not args.skip_hooks,
        seed_note=not args.skip_seed,
    )
    if as_json:
        import copy

        printable = copy.deepcopy(report)
        if printable.get("welcome_note"):
            printable["welcome_note"] = {
                "slug": printable["welcome_note"].get("slug"),
                "id": printable["welcome_note"].get("id"),
                "path": printable["welcome_note"].get("path"),
            }
        print(json.dumps(printable, ensure_ascii=False, indent=2))
    return 0


def handle_redact(args):
    from omni_redact import detect_secrets, redact

    as_json = getattr(args, "json", False)
    if args.text == "-":
        text = sys.stdin.read()
    else:
        text = args.text or ""
    if args.detect_only:
        findings = detect_secrets(text)
        _print({"findings": findings}, as_json)
        return 0
    redacted, findings = redact(text)
    if as_json:
        _print({"redacted": redacted, "findings": findings}, as_json=True)
    else:
        print(redacted)
    return 0


def handle_canvas(args):
    from omni_canvas import CanvasError, export_canvas

    as_json = getattr(args, "json", False)
    try:
        report = export_canvas(
            args.output,
            root_slug=args.root,
            depth=args.depth,
        )
    except CanvasError as exc:
        if as_json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}")
        return 1
    if as_json:
        _print(report, as_json=True)
    else:
        print(f"Wrote {report['node_count']} nodes / {report['edge_count']} edges to {report['output']}")
    return 0


def handle_codemap(args):
    from omni_codemap import (
        CodemapError,
        CodemapRuntime,
        ensure_codemap_layout,
        index_repo,
        query_local_index,
        remove_repo_codemap,
        update_single_file,
    )

    as_json = getattr(args, "json", False)
    ensure_codemap_layout()
    try:
        if args.codemap_command == "build":
            report = index_repo(
                args.repo_path,
                repo_name=args.repo_name,
                languages=args.language or None,
            )
            _print(report, as_json)
            return 0
        if args.codemap_command == "update":
            report = update_single_file(args.source_path, args.repo_path, repo_name=args.repo_name)
            _print(report, as_json)
            return 0
        if args.codemap_command == "query":
            local_results = query_local_index(args.query, limit=args.limit or 20)
            semantic_results = []
            if not getattr(args, "direct", False):
                try:
                    from omni_service import (
                        SearchServiceError,
                        query_codemap_via_service,
                    )

                    semantic_results = query_codemap_via_service(
                        args.query, n_results=args.limit or 5
                    )
                except SearchServiceError:
                    semantic_results = []
            if not semantic_results:
                try:
                    runtime = CodemapRuntime()
                    semantic_results = runtime.query(args.query, n_results=args.limit or 5)
                except Exception:
                    semantic_results = []
            _print({"local": local_results, "semantic": semantic_results}, as_json)
            return 0
        if args.codemap_command == "rm":
            report = remove_repo_codemap(args.repo_name)
            _print(report, as_json)
            return 0
        print(f"Unknown codemap action: {args.codemap_command}")
        return 2
    except CodemapError as exc:
        if as_json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}")
        return 1


def handle_hook(args):
    from omni_hooks import (
        HookError,
        gated_reindex_from_stdin,
        install,
        migrate_legacy_commands,
        status,
        uninstall,
    )
    from omni_init import migrate_legacy_mcp_commands

    as_json = getattr(args, "json", False)
    try:
        if getattr(args, "gated_reindex", False):
            report = gated_reindex_from_stdin()
            _print(report, as_json)
            return 0

        # Auto-rewrite v1.2.6-era `python -m omnimem ...` entries to the
        # console-script shape before any user-facing operation. Silent on the
        # common no-op path; on dry-run we surface a `migrated` field instead
        # of mutating disk.
        migrated = []
        if not args.dry_run:
            migrated = migrate_legacy_commands() + migrate_legacy_mcp_commands()

        if args.status:
            report = status()
            if migrated:
                report = {**report, "migrated": migrated}
            _print(report, as_json)
            return 0
        if args.uninstall:
            results = uninstall(args.agent, scope=args.scope, dry_run=args.dry_run)
            payload = {"uninstalled": results}
            if migrated:
                payload["migrated"] = migrated
            _print(payload, as_json)
            return 0
        events = args.event or None
        results = install(
            args.agent,
            events=events,
            scope=args.scope,
            dry_run=args.dry_run,
        )
        payload = {"installed": results}
        if migrated:
            payload["migrated"] = migrated
        _print(payload, as_json)
        return 0
    except HookError as exc:
        if as_json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}")
        return 1


def handle_mcp(args):
    from omni_mcp import list_tool_definitions, serve_stdio

    if args.mcp_command == "tools":
        tools = list_tool_definitions()
        if args.json:
            print(json.dumps(tools, ensure_ascii=False, indent=2))
        else:
            for tool in tools:
                print(f"- {tool['name']}: {tool['description']}")
        return 0
    if args.mcp_command == "serve":
        return serve_stdio()
    print("Unknown mcp action")
    return 2


def handle_serve(args):
    from omni_service import handle_serve as run_service
    from omni_service import handle_status as show_service_status

    if args.status:
        return show_service_status(args)
    return run_service(args)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Unified OmniMem CLI for add/search/import/doctor/update/operations/reindex workflows"
    )
    add_version_argument(parser)
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Add a text memory")
    add_parser.add_argument("text", help="The text content to remember")
    add_parser.add_argument("--source", default="user_input", help="Source of the information")
    add_parser.add_argument("--tags", default=None, help="Comma separated tags")
    add_parser.add_argument(
        "--direct",
        action="store_true",
        help="Bypass the warm local runtime service and ingest directly in this process",
    )
    add_parser.set_defaults(handler=handle_add)

    search_parser = subparsers.add_parser("search", help="Search OmniMem")
    search_parser.add_argument("query", help="The search query")
    search_parser.add_argument("--n", type=int, default=5, help="Number of results")
    search_parser.add_argument(
        "--full",
        action="store_true",
        help="Print full content without truncating",
    )
    search_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )
    search_parser.add_argument(
        "--source",
        help="Only search memories from an exact source value",
    )
    search_parser.add_argument(
        "--since",
        help="Only search memories at or after YYYY-MM-DD or ISO-8601 datetime",
    )
    search_parser.add_argument(
        "--until",
        help="Only search memories at or before YYYY-MM-DD or ISO-8601 datetime",
    )
    search_parser.add_argument(
        "--mime-type",
        help="Only search imported memories with the exact MIME type",
    )
    search_parser.add_argument(
        "--all",
        action="store_true",
        help="Federate results across imported documents (omnimem_core), structured notes (omnimem_notes), and codemap (omnimem_codemap)",
    )
    search_parser.add_argument(
        "--at-date",
        dest="at_date",
        help="Restrict to memories indexed on or before this YYYY-MM-DD",
    )
    search_parser.add_argument(
        "--direct",
        action="store_true",
        help="Bypass the local warm search service and run the one-shot path directly",
    )
    search_parser.set_defaults(handler=handle_search)

    import_parser = subparsers.add_parser("import", help="Import a file into OmniMem")
    import_parser.add_argument("file_path", help="Path to the file to import")
    import_parser.add_argument(
        "--direct",
        action="store_true",
        help="Bypass the warm local runtime service and ingest directly in this process",
    )
    import_parser.set_defaults(handler=handle_import)

    delete_parser = subparsers.add_parser(
        "delete",
        aliases=["del"],
        help="Delete memories by id, source, or wipe all",
    )
    delete_parser.add_argument("--id", help="Delete specific memory by ID")
    delete_parser.add_argument("--source", help="Delete all memories from a specific source file")
    delete_parser.add_argument(
        "--wipe-all",
        action="store_true",
        help="Completely wipe the OmniMem core",
    )
    delete_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation for destructive actions",
    )
    delete_parser.set_defaults(handler=handle_delete)

    doctor_parser = subparsers.add_parser("doctor", help="Inspect OmniMem runtime health")
    doctor_parser.add_argument(
        "--deep",
        action="store_true",
        help="Also validate that the embedding model can be prepared and instantiated",
    )
    doctor_parser.add_argument(
        "--json",
        action="store_true",
        help="Output the doctor report as JSON",
    )
    doctor_parser.set_defaults(handler=handle_doctor)

    bootstrap_parser = subparsers.add_parser(
        "bootstrap",
        help="Download or restore the local embedding model",
    )
    bootstrap_parser.add_argument(
        "--offline-only",
        action="store_true",
        help="Only restore from local Hugging Face cache, never hit the network",
    )
    bootstrap_parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download the model into the local OmniMem directory",
    )
    bootstrap_parser.set_defaults(handler=handle_bootstrap)

    update_parser = subparsers.add_parser(
        "update",
        help="Update the current OmniMem install safely (git clones only)",
    )
    update_parser.add_argument(
        "--check",
        action="store_true",
        help="Only inspect whether an update is available",
    )
    update_parser.add_argument(
        "--json",
        action="store_true",
        help="Output the update report as JSON",
    )
    update_parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip reinstalling requirements even if requirements.txt changed",
    )
    update_parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Skip the post-update model bootstrap check",
    )
    update_parser.add_argument(
        "--allow-model-download",
        action="store_true",
        help="Allow OmniMem to download the embedding model during update if needed",
    )
    update_parser.set_defaults(handler=handle_update)

    backup_parser = subparsers.add_parser("backup", help="Create a runtime backup archive")
    backup_parser.add_argument("--output", help="Write the backup archive to this path")
    backup_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output path if it exists",
    )
    backup_parser.add_argument(
        "--no-models",
        action="store_true",
        help="Skip backing up the model directory",
    )
    backup_parser.add_argument(
        "--no-config",
        action="store_true",
        help="Skip backing up the active config file",
    )
    backup_parser.add_argument(
        "--json",
        action="store_true",
        help="Output the backup report as JSON",
    )
    backup_parser.set_defaults(handler=handle_backup)

    export_parser = subparsers.add_parser("export", help="Export the vector collection to JSON")
    export_parser.add_argument("--output", help="Write the export JSON to this path")
    export_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output path if it exists",
    )
    export_parser.add_argument(
        "--json",
        action="store_true",
        help="Output the export report as JSON",
    )
    export_parser.set_defaults(handler=handle_export)

    restore_parser = subparsers.add_parser(
        "restore",
        help="Restore from a backup archive or export JSON",
    )
    restore_parser.add_argument("input_path", help="Path to a backup archive or export JSON file")
    restore_parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing data at the restore target",
    )
    restore_parser.add_argument(
        "--json",
        action="store_true",
        help="Output the restore report as JSON",
    )
    restore_parser.set_defaults(handler=handle_restore)

    reindex_parser = subparsers.add_parser(
        "reindex",
        help="Rebuild imported chunks using the current retrieval strategy",
    )
    reindex_parser.add_argument("--source", help="Only reindex imported memories from this source")
    reindex_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be rebuilt without mutating the collection",
    )
    reindex_parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip exporting a JSON backup before reindexing",
    )
    reindex_parser.add_argument(
        "--backup-output",
        help="Write the pre-reindex JSON backup to this path",
    )
    reindex_parser.add_argument(
        "--direct",
        action="store_true",
        help="Bypass the warm local runtime service and rebuild directly in this process",
    )
    reindex_parser.add_argument(
        "--json",
        action="store_true",
        help="Output the reindex report as JSON",
    )
    reindex_parser.set_defaults(handler=handle_reindex)

    serve_parser = subparsers.add_parser(
        "serve",
        help="Run or inspect the local warm search service",
    )
    serve_parser.add_argument(
        "--host",
        help="Bind host for the local search service",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        help="Bind port for the local search service",
    )
    serve_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress HTTP access logs while serving",
    )
    serve_parser.add_argument(
        "--status",
        action="store_true",
        help="Report whether the local search service is reachable instead of serving",
    )
    serve_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit service status as JSON when used with --status",
    )
    serve_parser.set_defaults(handler=handle_serve)

    version_parser = subparsers.add_parser("version", help="Print the OmniMem version")
    version_parser.set_defaults(handler=handle_version)

    note_parser = subparsers.add_parser("note", help="Second-brain notes (vault CRUD + search)")
    note_subparsers = note_parser.add_subparsers(dest="note_command", required=True)

    note_new = note_subparsers.add_parser("new", help="Create a new note")
    note_new.add_argument("title")
    note_new.add_argument("--body", help="Body string, or '-' to read from stdin")
    note_new.add_argument(
        "--type",
        default="note",
        choices=["note", "decision", "log", "reference", "conversation"],
    )
    note_new.add_argument("--tags", help="Comma separated tags")
    note_new.add_argument("--agent")
    note_new.add_argument("--project")
    note_new.add_argument("--json", action="store_true")

    note_show = note_subparsers.add_parser("show", help="Show a note by slug or id")
    note_show.add_argument("slug_or_id")
    note_show.add_argument("--json", action="store_true")

    note_update = note_subparsers.add_parser("update", help="Update a note's metadata")
    note_update.add_argument("slug_or_id")
    note_update.add_argument("--title")
    note_update.add_argument("--add-tag", action="append", default=[])
    note_update.add_argument("--rm-tag", action="append", default=[])
    note_update.add_argument("--json", action="store_true")

    note_rm = note_subparsers.add_parser("rm", help="Delete a note")
    note_rm.add_argument("slug_or_id")
    note_rm.add_argument("--json", action="store_true")

    note_list = note_subparsers.add_parser("list", help="List notes")
    note_list.add_argument("--type")
    note_list.add_argument("--tag")
    note_list.add_argument("--since")
    note_list.add_argument("--until")
    note_list.add_argument("--at-date", dest="at_date", help="Show only notes created at or before this YYYY-MM-DD")
    note_list.add_argument("--limit", type=int)
    note_list.add_argument("--json", action="store_true")

    note_search = note_subparsers.add_parser("search", help="Semantic search across notes")
    note_search.add_argument("query")
    note_search.add_argument("--type")
    note_search.add_argument("--tag")
    note_search.add_argument("--at-date", dest="at_date", help="Filter to notes created at or before this YYYY-MM-DD")
    note_search.add_argument("--limit", type=int)
    note_search.add_argument("--full", action="store_true")
    note_search.add_argument(
        "--direct",
        action="store_true",
        help="Bypass the warm search service and run the one-shot path directly",
    )
    note_search.add_argument("--json", action="store_true")

    note_link = note_subparsers.add_parser("link", help="Add a wikilink between notes")
    note_link.add_argument("from_slug")
    note_link.add_argument("to_slug")
    note_link.add_argument("--json", action="store_true")

    note_unlink = note_subparsers.add_parser("unlink", help="Remove wikilinks between notes")
    note_unlink.add_argument("from_slug")
    note_unlink.add_argument("to_slug")
    note_unlink.add_argument("--json", action="store_true")

    note_backlinks = note_subparsers.add_parser("backlinks", help="Show notes that reference a given slug")
    note_backlinks.add_argument("slug_or_id")
    note_backlinks.add_argument("--json", action="store_true")

    note_graph = note_subparsers.add_parser("graph", help="Dump the note adjacency graph as JSON")
    note_graph.add_argument("--root", help="Restrict graph to edges touching this slug")
    note_graph.add_argument("--json", action="store_true")

    note_reindex = note_subparsers.add_parser("reindex", help="Rebuild the notes ChromaDB collection from disk")
    note_reindex.add_argument("--dry-run", action="store_true")
    note_reindex.add_argument("--json", action="store_true")

    note_canvas = note_subparsers.add_parser("canvas", help="Export the note graph as Obsidian Canvas JSON")
    note_canvas.add_argument("output", help="Path to write the .canvas file")
    note_canvas.add_argument("--root", help="Restrict export to slugs reachable from this slug")
    note_canvas.add_argument("--depth", type=int, help="Limit BFS depth from --root")
    note_canvas.add_argument("--json", action="store_true")
    note_canvas.set_defaults(handler=handle_canvas)

    note_parser.set_defaults(handler=handle_note)

    init_parser = subparsers.add_parser("init", help="Install or remove agent CLI integration rules")
    init_parser.add_argument(
        "--agent",
        action="append",
        default=[],
        choices=["claude", "codex", "gemini", "cursor", "all"],
        help="Target agent. Repeat to install for multiple agents.",
    )
    init_parser.add_argument(
        "--scope",
        default="user",
        choices=["user", "project"],
    )
    init_parser.add_argument("--no-mcp", action="store_true", help="Skip MCP server config registration")
    init_parser.add_argument("--uninstall", action="store_true")
    init_parser.add_argument("--status", action="store_true")
    init_parser.add_argument("--dry-run", action="store_true")
    init_parser.add_argument("--json", action="store_true")
    init_parser.set_defaults(handler=handle_init)

    codemap_parser = subparsers.add_parser("codemap", help="Source code structural map (Python / JS / TS / Go / Rust)")
    codemap_subparsers = codemap_parser.add_subparsers(dest="codemap_command", required=True)

    codemap_build = codemap_subparsers.add_parser("build", help="Walk a repo and build codemap notes")
    codemap_build.add_argument("repo_path")
    codemap_build.add_argument("--repo-name")
    codemap_build.add_argument(
        "--language",
        action="append",
        default=[],
        choices=["python", "javascript", "typescript", "go", "rust"],
        help="Restrict the walk to one language. Repeat to combine. Default: all supported languages.",
    )
    codemap_build.add_argument("--json", action="store_true")

    codemap_update = codemap_subparsers.add_parser("update", help="Refresh the codemap for a single source file")
    codemap_update.add_argument("source_path")
    codemap_update.add_argument("--repo-path", required=True)
    codemap_update.add_argument("--repo-name")
    codemap_update.add_argument("--json", action="store_true")

    codemap_query = codemap_subparsers.add_parser("query", help="Search codemap symbols (substring + semantic)")
    codemap_query.add_argument("query")
    codemap_query.add_argument("--limit", type=int)
    codemap_query.add_argument("--json", action="store_true")
    codemap_query.add_argument(
        "--direct",
        action="store_true",
        help="Bypass the warm search service and run the one-shot path directly",
    )

    codemap_rm = codemap_subparsers.add_parser("rm", help="Delete the codemap for a repo")
    codemap_rm.add_argument("repo_name")
    codemap_rm.add_argument("--json", action="store_true")

    codemap_parser.set_defaults(handler=handle_codemap)

    hook_parser = subparsers.add_parser("hook", help="Install or remove agent CLI lifecycle hooks")
    hook_parser.add_argument(
        "--agent",
        action="append",
        default=[],
        choices=["claude", "codex", "all"],
        help="Target agent. Repeat to install for multiple agents.",
    )
    hook_parser.add_argument(
        "--event",
        action="append",
        default=[],
        help="Lifecycle event to install (SessionStart, Stop, PostToolUse). Repeat for multiple.",
    )
    hook_parser.add_argument("--scope", default="user", choices=["user", "project"])
    hook_parser.add_argument("--uninstall", action="store_true")
    hook_parser.add_argument("--status", action="store_true")
    hook_parser.add_argument("--dry-run", action="store_true")
    hook_parser.add_argument("--json", action="store_true")
    hook_parser.add_argument(
        "--gated-reindex",
        action="store_true",
        help=(
            "Internal: read a PostToolUse hook payload from stdin and only "
            "reindex notes when the touched file lives inside the vault. "
            "Used by `omnimem hook`'s installed PostToolUse recipe."
        ),
    )
    hook_parser.set_defaults(handler=handle_hook)

    quickstart_parser = subparsers.add_parser(
        "quickstart",
        help="Interactive wizard to wire OmniMem into your agent CLIs",
    )
    quickstart_parser.add_argument(
        "--yes",
        action="store_true",
        help="Accept every default; install for every supported agent without prompting",
    )
    quickstart_parser.add_argument(
        "--skip-hooks",
        action="store_true",
        help="Don't install Claude/Codex lifecycle hooks",
    )
    quickstart_parser.add_argument(
        "--skip-seed",
        action="store_true",
        help="Don't create a welcome note in the vault",
    )
    quickstart_parser.add_argument("--json", action="store_true", help="Emit a machine-readable report")
    quickstart_parser.set_defaults(handler=handle_quickstart)

    redact_parser = subparsers.add_parser(
        "redact",
        help="Detect or redact common secret patterns in input text",
    )
    redact_parser.add_argument(
        "text",
        help="Text to redact, or '-' to read from stdin",
    )
    redact_parser.add_argument(
        "--detect-only",
        action="store_true",
        help="Report findings without modifying the text",
    )
    redact_parser.add_argument("--json", action="store_true")
    redact_parser.set_defaults(handler=handle_redact)

    mcp_parser = subparsers.add_parser("mcp", help="MCP server (stdio) and tool introspection")
    mcp_subparsers = mcp_parser.add_subparsers(dest="mcp_command", required=True)
    mcp_serve = mcp_subparsers.add_parser("serve", help="Run the OmniMem MCP server over stdio")
    mcp_serve.set_defaults(handler=handle_mcp)
    mcp_tools = mcp_subparsers.add_parser("tools", help="List the OmniMem MCP tool registry")
    mcp_tools.add_argument("--json", action="store_true")
    mcp_tools.set_defaults(handler=handle_mcp)
    mcp_parser.set_defaults(handler=handle_mcp)

    return parser


def _force_utf8_streams():
    # stdin matters for `note new --body -` and similar verbs that read body
    # text from a heredoc. On Windows, the default cp1252 decoder turns any
    # non-cp1252 byte into a surrogate via `surrogateescape`, and the surrogate
    # then blows up at write time with "surrogates not allowed".
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


def main(argv=None):
    _force_utf8_streams()
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "handler"):
        parser.print_help()
        return 0

    try:
        return args.handler(args)
    except RuntimeError as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

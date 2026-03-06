import argparse
import asyncio
import json
import os
import sys

from omni_version import add_version_argument, get_version_banner


def handle_add(args):
    from omni_add import add_memory

    add_memory(args.text, args.source, args.tags)
    return 0


def handle_search(args):
    from omni_search import search_memory

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
    return 0


def handle_import(args):
    from omni_import import import_file_advanced

    if not os.path.exists(args.file_path):
        print(f"Error: File not found: {args.file_path}")
        return 1

    asyncio.run(import_file_advanced(args.file_path))
    return 0


def handle_delete(args):
    from omni_del import delete_memory

    delete_memory(doc_id=args.id, source=args.source, wipe_all=args.wipe_all)
    return 0


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


def handle_version(_args):
    print(get_version_banner())
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Unified OmniMem CLI for add/search/import/doctor/update workflows"
    )
    add_version_argument(parser)
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Add a text memory")
    add_parser.add_argument("text", help="The text content to remember")
    add_parser.add_argument("--source", default="user_input", help="Source of the information")
    add_parser.add_argument("--tags", default=None, help="Comma separated tags")
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
    search_parser.set_defaults(handler=handle_search)

    import_parser = subparsers.add_parser("import", help="Import a file into OmniMem")
    import_parser.add_argument("file_path", help="Path to the file to import")
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
        help="Update the current OmniMem git clone safely",
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

    version_parser = subparsers.add_parser("version", help="Print the OmniMem version")
    version_parser.set_defaults(handler=handle_version)

    return parser


def main(argv=None):
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

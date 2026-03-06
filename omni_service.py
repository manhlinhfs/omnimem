import argparse
import json
import os
import socket
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error, request

from omni_config import get_search_service_settings as get_config_search_service_settings
from omni_paths import SOURCE_ROOT, get_runtime_home
from omni_search_core import SearchRuntime
from omni_version import add_version_argument, get_version_banner

DEFAULT_SERVICE_HOST = "127.0.0.1"
DEFAULT_SERVICE_PORT = 41733
DEFAULT_STARTUP_TIMEOUT_SECONDS = 20
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10
SERVICE_LOG_FILE = ".omnimem_search_service.log"


class SearchServiceError(RuntimeError):
    pass


class SearchServiceUnavailable(SearchServiceError):
    pass


class SearchServiceProtocolError(SearchServiceError):
    pass


class _SearchServiceServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class _SearchServiceHandler(BaseHTTPRequestHandler):
    server_version = "OmniMemSearchService/1"

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/health":
            self._send_json({"status": "not_found"}, status=404)
            return
        self._send_json(
            {
                "status": "ok",
                "pid": os.getpid(),
                "version": get_version_banner(),
                "host": getattr(self.server, "service_host", DEFAULT_SERVICE_HOST),
                "port": getattr(self.server, "service_port", DEFAULT_SERVICE_PORT),
            }
        )

    def do_POST(self):
        if self.path != "/search":
            self._send_json({"status": "not_found"}, status=404)
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8") if raw_body else "{}")
        except json.JSONDecodeError:
            self._send_json({"status": "fail", "detail": "Invalid JSON body"}, status=400)
            return

        try:
            records = self.server.runtime.search_records(
                payload.get("query", ""),
                n_results=int(payload.get("n_results", 5) or 5),
                source=payload.get("source"),
                since=payload.get("since"),
                until=payload.get("until"),
                mime_type=payload.get("mime_type"),
            )
        except Exception as exc:
            self._send_json({"status": "fail", "detail": str(exc)}, status=500)
            return

        self._send_json({"status": "ok", "records": records})

    def log_message(self, fmt, *args):
        if getattr(self.server, "quiet", False):
            return
        super().log_message(fmt, *args)


def get_search_service_settings(root_dir=SOURCE_ROOT):
    values = get_config_search_service_settings(root_dir=root_dir)
    return {
        "enabled": bool(values["enabled"]),
        "host": DEFAULT_SERVICE_HOST,
        "port": int(values["port"]),
        "startup_timeout_seconds": int(values["startup_timeout_seconds"]),
        "request_timeout_seconds": int(values["request_timeout_seconds"]),
    }


def _get_service_log_path(root_dir=SOURCE_ROOT):
    runtime_home = get_runtime_home(root_dir=root_dir)
    runtime_home.mkdir(parents=True, exist_ok=True)
    return runtime_home / SERVICE_LOG_FILE


def _build_service_url(host, port, path):
    return f"http://{host}:{port}{path}"


def _request_json(method, url, payload=None, timeout_seconds=DEFAULT_REQUEST_TIMEOUT_SECONDS):
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SearchServiceProtocolError(
            f"Search service responded with HTTP {exc.code}: {detail}"
        ) from exc
    except (error.URLError, TimeoutError, socket.timeout, ConnectionError) as exc:
        raise SearchServiceUnavailable(str(exc)) from exc


def inspect_search_service(host=None, port=None, request_timeout_seconds=None, root_dir=SOURCE_ROOT):
    settings = get_search_service_settings(root_dir=root_dir)
    host = host or settings["host"]
    port = int(port or settings["port"])
    timeout_seconds = request_timeout_seconds or settings["request_timeout_seconds"]
    try:
        payload = _request_json(
            "GET",
            _build_service_url(host, port, "/health"),
            timeout_seconds=timeout_seconds,
        )
        return {
            "status": "ok",
            "reachable": True,
            "host": host,
            "port": port,
            "detail": payload,
        }
    except SearchServiceError as exc:
        return {
            "status": "down",
            "reachable": False,
            "host": host,
            "port": port,
            "detail": str(exc),
        }


def _launch_search_service(host, port, root_dir=SOURCE_ROOT):
    log_path = _get_service_log_path(root_dir=root_dir)
    command = [
        sys.executable,
        str(Path(root_dir).expanduser().resolve() / "omnimem.py"),
        "serve",
        "--host",
        host,
        "--port",
        str(port),
        "--quiet",
    ]

    with open(log_path, "ab") as log_handle:
        process = subprocess.Popen(
            command,
            cwd=str(Path(root_dir).expanduser().resolve()),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            close_fds=True,
            start_new_session=True,
        )
    return {"pid": process.pid, "log_path": str(log_path)}


def ensure_search_service(root_dir=SOURCE_ROOT, host=None, port=None):
    settings = get_search_service_settings(root_dir=root_dir)
    if not settings["enabled"]:
        raise SearchServiceUnavailable("Search service is disabled by configuration")

    host = host or settings["host"]
    port = int(port or settings["port"])
    status = inspect_search_service(
        host=host,
        port=port,
        request_timeout_seconds=settings["request_timeout_seconds"],
        root_dir=root_dir,
    )
    if status["reachable"]:
        return {
            "status": "ready",
            "host": host,
            "port": port,
            "started": False,
            "detail": status,
        }

    launch_report = _launch_search_service(host=host, port=port, root_dir=root_dir)
    deadline = time.monotonic() + settings["startup_timeout_seconds"]
    while time.monotonic() < deadline:
        status = inspect_search_service(
            host=host,
            port=port,
            request_timeout_seconds=settings["request_timeout_seconds"],
            root_dir=root_dir,
        )
        if status["reachable"]:
            return {
                "status": "ready",
                "host": host,
                "port": port,
                "started": True,
                "detail": status,
                "launch": launch_report,
            }
        time.sleep(0.25)

    raise SearchServiceUnavailable(
        f"Search service failed to become ready on {host}:{port} within {settings['startup_timeout_seconds']}s. "
        f"Check {_get_service_log_path(root_dir=root_dir)} for startup logs."
    )


def search_via_service(
    query,
    n_results=5,
    source=None,
    since=None,
    until=None,
    mime_type=None,
    root_dir=SOURCE_ROOT,
    autostart=True,
):
    settings = get_search_service_settings(root_dir=root_dir)
    host = settings["host"]
    port = settings["port"]

    if not settings["enabled"]:
        raise SearchServiceUnavailable("Search service is disabled by configuration")

    if autostart:
        ensure_search_service(root_dir=root_dir, host=host, port=port)
    else:
        status = inspect_search_service(
            host=host,
            port=port,
            request_timeout_seconds=settings["request_timeout_seconds"],
            root_dir=root_dir,
        )
        if not status["reachable"]:
            raise SearchServiceUnavailable(str(status["detail"]))

    payload = _request_json(
        "POST",
        _build_service_url(host, port, "/search"),
        payload={
            "query": query,
            "n_results": n_results,
            "source": source,
            "since": since,
            "until": until,
            "mime_type": mime_type,
        },
        timeout_seconds=settings["request_timeout_seconds"],
    )
    if payload.get("status") != "ok":
        raise SearchServiceProtocolError(payload.get("detail") or "Unexpected search service response")
    return payload.get("records") or []


def run_search_service(host=None, port=None, quiet=False, root_dir=SOURCE_ROOT):
    settings = get_search_service_settings(root_dir=root_dir)
    host = host or settings["host"]
    port = int(port or settings["port"])

    runtime = SearchRuntime()
    server = _SearchServiceServer((host, port), _SearchServiceHandler)
    server.runtime = runtime
    server.quiet = quiet
    server.service_host = host
    server.service_port = port

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


def handle_status(args):
    report = inspect_search_service(host=args.host, port=args.port)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["reachable"] else 1

    if report["reachable"]:
        print(f"[OmniMem] Search service is reachable at {report['host']}:{report['port']}")
        return 0

    print(f"[OmniMem] Search service is not reachable at {report['host']}:{report['port']}")
    print(f"Detail: {report['detail']}")
    return 1


def handle_serve(args):
    return run_search_service(host=args.host, port=args.port, quiet=args.quiet)


def build_parser():
    parser = argparse.ArgumentParser(description="OmniMem local search service")
    add_version_argument(parser)
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Run the local warm search service")
    serve_parser.add_argument("--host", help="Bind host (default: 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, help="Bind port")
    serve_parser.add_argument("--quiet", action="store_true", help="Suppress HTTP access logs")
    serve_parser.set_defaults(handler=handle_serve)

    status_parser = subparsers.add_parser("status", help="Check local search service reachability")
    status_parser.add_argument("--host", help="Service host")
    status_parser.add_argument("--port", type=int, help="Service port")
    status_parser.add_argument("--json", action="store_true", help="Emit service status as JSON")
    status_parser.set_defaults(handler=handle_status)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 0
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())

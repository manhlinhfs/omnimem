"""Verify the warm search service hosts the notes and codemap collections.

Before this change, the warm service only served `omnimem_core` (imports).
`note search` and `codemap query` had to spin up their own NoteRuntime /
CodemapRuntime in-process, which meant reloading the embedding model on
every CLI invocation. These tests pin both halves of the contract:

- Server side: POST /notes/search and POST /codemap/query proxy to
  cached NoteRuntime / CodemapRuntime instances stored on the server.
- Client side: search_notes_via_service and query_codemap_via_service
  raise SearchServiceUnavailable when the service is disabled, and emit
  the right JSON body when it's reachable.
"""

import json
import unittest
from io import BytesIO
from unittest.mock import patch

import omnimem.service as omni_service


class _RecordingHandler:
    """Bare-minimum stand-in for BaseHTTPRequestHandler."""

    def __init__(self, server, body):
        self.server = server
        self.path = None
        self.headers = {"Content-Length": str(len(body))}
        self.rfile = BytesIO(body)
        self.wfile = BytesIO()
        self.status = None
        self.response_headers = []
        self.payload = None

    # --- methods used by _SearchServiceHandler ---
    def send_response(self, status):
        self.status = status

    def send_header(self, name, value):
        self.response_headers.append((name, value))

    def end_headers(self):
        pass

    def _send_json(self, payload, status=200):
        self.payload = payload
        self.status = status

    def _read_json_payload(self):
        raw = self.rfile.read()
        try:
            return json.loads(raw.decode("utf-8") if raw else "{}")
        except json.JSONDecodeError:
            self._send_json({"status": "fail", "detail": "Invalid JSON body"}, status=400)
            return None


class _FakeNoteRuntime:
    instances = 0

    def __init__(self, root_dir=None):
        type(self).instances += 1
        self.root_dir = root_dir
        self.calls = []

    def search(self, query, n_results=5, note_type=None, tag=None, since=None, until=None):
        self.calls.append(
            {
                "query": query,
                "n_results": n_results,
                "note_type": note_type,
                "tag": tag,
                "since": since,
                "until": until,
            }
        )
        return [{"id": "n1", "document": "note body", "metadata": {"slug": "n1"}, "distance": 0.2}]


class _FakeCodemapRuntime:
    instances = 0

    def __init__(self, root_dir=None):
        type(self).instances += 1
        self.root_dir = root_dir
        self.calls = []

    def query(self, query, n_results=5, kinds=None):
        self.calls.append({"query": query, "n_results": n_results, "kinds": kinds})
        return [{"id": "c1", "document": "alpha", "metadata": {"name": "alpha"}, "distance": 0.4}]


class _FakeServer:
    def __init__(self, root_dir="/tmp/vault"):
        self.root_dir = root_dir


class TestNotesSearchEndpoint(unittest.TestCase):
    def setUp(self):
        _FakeNoteRuntime.instances = 0

    def test_returns_records_from_note_runtime(self):
        server = _FakeServer()
        handler = _RecordingHandler(server, body=json.dumps({"query": "hello"}).encode("utf-8"))

        with patch("omnimem.note_index.NoteRuntime", _FakeNoteRuntime):
            omni_service._SearchServiceHandler._handle_notes_search(handler)

        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.payload["status"], "ok")
        self.assertEqual(len(handler.payload["records"]), 1)
        self.assertEqual(handler.payload["records"][0]["id"], "n1")

    def test_caches_note_runtime_on_server(self):
        server = _FakeServer()
        body = json.dumps({"query": "hello"}).encode("utf-8")

        with patch("omnimem.note_index.NoteRuntime", _FakeNoteRuntime):
            for _ in range(3):
                handler = _RecordingHandler(server, body=body)
                omni_service._SearchServiceHandler._handle_notes_search(handler)
        # Three requests, one runtime construction
        self.assertEqual(_FakeNoteRuntime.instances, 1)
        # And the cached runtime saw all 3 calls
        self.assertEqual(len(server.note_runtime.calls), 3)


class TestCodemapQueryEndpoint(unittest.TestCase):
    def setUp(self):
        _FakeCodemapRuntime.instances = 0

    def test_returns_records_from_codemap_runtime(self):
        server = _FakeServer()
        handler = _RecordingHandler(server, body=json.dumps({"query": "alpha"}).encode("utf-8"))

        with patch("omnimem.codemap.CodemapRuntime", _FakeCodemapRuntime):
            omni_service._SearchServiceHandler._handle_codemap_query(handler)

        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.payload["status"], "ok")
        self.assertEqual(handler.payload["records"][0]["id"], "c1")

    def test_caches_codemap_runtime_on_server(self):
        server = _FakeServer()
        body = json.dumps({"query": "alpha"}).encode("utf-8")

        with patch("omnimem.codemap.CodemapRuntime", _FakeCodemapRuntime):
            for _ in range(2):
                handler = _RecordingHandler(server, body=body)
                omni_service._SearchServiceHandler._handle_codemap_query(handler)
        self.assertEqual(_FakeCodemapRuntime.instances, 1)


class TestSearchNotesViaService(unittest.TestCase):
    def test_disabled_settings_raises_unavailable(self):
        with patch.object(
            omni_service,
            "get_search_service_settings",
            return_value={"enabled": False, "host": "127.0.0.1", "port": 1, "request_timeout_seconds": 1, "startup_timeout_seconds": 1},
        ):
            with self.assertRaises(omni_service.SearchServiceUnavailable):
                omni_service.search_notes_via_service("hello", autostart=False)

    def test_posts_expected_payload(self):
        captured = {}

        def _fake_request(method, url, payload=None, timeout_seconds=None):
            captured["url"] = url
            captured["payload"] = payload
            return {"status": "ok", "records": [{"id": "n1"}]}

        with patch.object(
            omni_service,
            "get_search_service_settings",
            return_value={
                "enabled": True,
                "host": "127.0.0.1",
                "port": 41733,
                "request_timeout_seconds": 5,
                "startup_timeout_seconds": 5,
            },
        ), patch.object(omni_service, "_request_json", _fake_request):
            records = omni_service.search_notes_via_service(
                "hello",
                n_results=7,
                note_type="decision",
                tag="release",
                autostart=False,
            )
        self.assertEqual(records, [{"id": "n1"}])
        self.assertTrue(captured["url"].endswith("/notes/search"))
        self.assertEqual(captured["payload"]["query"], "hello")
        self.assertEqual(captured["payload"]["n_results"], 7)
        self.assertEqual(captured["payload"]["note_type"], "decision")
        self.assertEqual(captured["payload"]["tag"], "release")


class TestQueryCodemapViaService(unittest.TestCase):
    def test_disabled_settings_raises_unavailable(self):
        with patch.object(
            omni_service,
            "get_search_service_settings",
            return_value={"enabled": False, "host": "127.0.0.1", "port": 1, "request_timeout_seconds": 1, "startup_timeout_seconds": 1},
        ):
            with self.assertRaises(omni_service.SearchServiceUnavailable):
                omni_service.query_codemap_via_service("alpha", autostart=False)

    def test_posts_expected_payload(self):
        captured = {}

        def _fake_request(method, url, payload=None, timeout_seconds=None):
            captured["url"] = url
            captured["payload"] = payload
            return {"status": "ok", "records": [{"id": "c1"}]}

        with patch.object(
            omni_service,
            "get_search_service_settings",
            return_value={
                "enabled": True,
                "host": "127.0.0.1",
                "port": 41733,
                "request_timeout_seconds": 5,
                "startup_timeout_seconds": 5,
            },
        ), patch.object(omni_service, "_request_json", _fake_request):
            records = omni_service.query_codemap_via_service(
                "alpha",
                n_results=3,
                kinds=["function", "class"],
                autostart=False,
            )
        self.assertEqual(records, [{"id": "c1"}])
        self.assertTrue(captured["url"].endswith("/codemap/query"))
        self.assertEqual(captured["payload"]["query"], "alpha")
        self.assertEqual(captured["payload"]["n_results"], 3)
        self.assertEqual(captured["payload"]["kinds"], ["function", "class"])


if __name__ == "__main__":
    unittest.main()

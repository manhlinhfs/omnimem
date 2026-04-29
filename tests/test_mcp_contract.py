import json
import os
import tempfile
import unittest

from omni_mcp import (
    PROTOCOL_VERSION,
    SERVER_NAME,
    handle_request,
    list_tool_definitions,
)
from omni_vault import ensure_vault_layout


def _restore_env(name, previous_value):
    if previous_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous_value


def _remove_tree(path):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


def _request(method, params=None, request_id=1):
    payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        payload["params"] = params
    return payload


class TestToolDefinitions(unittest.TestCase):
    def test_six_tools_registered(self):
        names = sorted(tool["name"] for tool in list_tool_definitions())
        self.assertEqual(
            names,
            sorted(["import_file", "note_link", "note_new", "note_search", "note_show", "search_all"]),
        )

    def test_each_tool_has_input_schema(self):
        for tool in list_tool_definitions():
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            schema = tool.get("inputSchema")
            self.assertIsNotNone(schema, f"{tool['name']} missing inputSchema")
            self.assertEqual(schema.get("type"), "object")

    def test_input_schemas_validate_via_jsonschema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        for tool in list_tool_definitions():
            jsonschema.Draft202012Validator.check_schema(tool["inputSchema"])


class TestProtocolHandlers(unittest.TestCase):
    def test_initialize_returns_server_info(self):
        response = handle_request(_request("initialize", {"protocolVersion": "2024-11-05"}))
        self.assertIn("result", response)
        self.assertEqual(response["result"]["protocolVersion"], PROTOCOL_VERSION)
        self.assertEqual(response["result"]["serverInfo"]["name"], SERVER_NAME)

    def test_tools_list_returns_registry(self):
        response = handle_request(_request("tools/list"))
        self.assertIn("tools", response["result"])
        self.assertEqual(len(response["result"]["tools"]), len(list_tool_definitions()))

    def test_unknown_method_returns_jsonrpc_error(self):
        response = handle_request(_request("does/not/exist"))
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32601)

    def test_initialized_notification_returns_none(self):
        response = handle_request({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertIsNone(response)

    def test_tools_call_with_invalid_args_returns_invalid_params(self):
        response = handle_request(
            _request("tools/call", {"name": "note_new", "arguments": {}}),
        )
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32602)

    def test_tools_call_unknown_tool_returns_invalid_params(self):
        response = handle_request(
            _request("tools/call", {"name": "missing_tool", "arguments": {}}),
        )
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32602)


class TestNoteToolHappyPath(unittest.TestCase):
    """End-to-end: note_new + note_show through MCP dispatch.

    The notes ChromaDB index call inside note_new is best-effort; failures there
    must not break the disk write or the response.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        previous_home = os.environ.get("OMNIMEM_HOME")
        self.addCleanup(_restore_env, "OMNIMEM_HOME", previous_home)
        self.addCleanup(_remove_tree, self.tmpdir)
        os.environ["OMNIMEM_HOME"] = self.tmpdir
        ensure_vault_layout(root_dir=self.tmpdir)

    def test_note_new_then_note_show(self):
        new_response = handle_request(
            _request(
                "tools/call",
                {
                    "name": "note_new",
                    "arguments": {
                        "title": "MCP smoke test",
                        "body": "Body for the smoke test.\n",
                        "type": "log",
                        "tags": ["mcp", "test"],
                    },
                },
            ),
            root_dir=self.tmpdir,
        )
        self.assertIn("result", new_response)
        new_payload = json.loads(new_response["result"]["content"][0]["text"])
        self.assertIn("slug", new_payload)
        slug = new_payload["slug"]

        show_response = handle_request(
            _request(
                "tools/call",
                {
                    "name": "note_show",
                    "arguments": {"slug_or_id": slug},
                },
            ),
            root_dir=self.tmpdir,
        )
        self.assertIn("result", show_response)
        show_payload = json.loads(show_response["result"]["content"][0]["text"])
        self.assertEqual(show_payload["slug"], slug)
        self.assertEqual(show_payload["frontmatter"]["title"], "MCP smoke test")


if __name__ == "__main__":
    unittest.main()

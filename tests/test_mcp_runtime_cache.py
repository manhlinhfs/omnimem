"""Verify the MCP server reuses long-lived OmniRuntime / NoteRuntime instances.

Each runtime construction loads ChromaDB and a SentenceTransformer embedding
function. Without caching, every `tools/call` would pay that cost (~1-2 s on
first call, smaller but non-zero subsequently). These tests pin the cache
behavior so a regression would be caught.
"""

import unittest
from unittest.mock import patch

import omni_mcp


class _CountingOmniRuntime:
    instances = 0

    def __init__(self, root_dir=None):
        type(self).instances += 1
        self.root_dir = root_dir

    def search_records(self, *args, **kwargs):
        return []


class _CountingNoteRuntime:
    instances = 0

    def __init__(self, root_dir=None):
        type(self).instances += 1
        self.root_dir = root_dir

    def search(self, *args, **kwargs):
        return []


class TestRuntimeCache(unittest.TestCase):
    def setUp(self):
        omni_mcp._reset_runtime_cache()
        _CountingOmniRuntime.instances = 0
        _CountingNoteRuntime.instances = 0

    def tearDown(self):
        omni_mcp._reset_runtime_cache()

    def test_get_omni_runtime_returns_same_instance_for_same_root(self):
        with patch("omni_search_core.OmniRuntime", _CountingOmniRuntime):
            first = omni_mcp._get_omni_runtime("/tmp/vault-a")
            second = omni_mcp._get_omni_runtime("/tmp/vault-a")
        self.assertIs(first, second)
        self.assertEqual(_CountingOmniRuntime.instances, 1)

    def test_get_omni_runtime_separates_by_root_dir(self):
        with patch("omni_search_core.OmniRuntime", _CountingOmniRuntime):
            first = omni_mcp._get_omni_runtime("/tmp/vault-a")
            second = omni_mcp._get_omni_runtime("/tmp/vault-b")
        self.assertIsNot(first, second)
        self.assertEqual(_CountingOmniRuntime.instances, 2)

    def test_get_note_runtime_returns_same_instance_for_same_root(self):
        with patch("omni_note_index.NoteRuntime", _CountingNoteRuntime):
            first = omni_mcp._get_note_runtime("/tmp/vault-a")
            second = omni_mcp._get_note_runtime("/tmp/vault-a")
        self.assertIs(first, second)
        self.assertEqual(_CountingNoteRuntime.instances, 1)

    def test_get_note_runtime_separates_by_root_dir(self):
        with patch("omni_note_index.NoteRuntime", _CountingNoteRuntime):
            first = omni_mcp._get_note_runtime("/tmp/vault-a")
            second = omni_mcp._get_note_runtime("/tmp/vault-b")
        self.assertIsNot(first, second)
        self.assertEqual(_CountingNoteRuntime.instances, 2)

    def test_search_all_tool_reuses_runtimes_across_calls(self):
        """Two consecutive `search_all` calls must construct each runtime once."""
        with patch("omni_search_core.OmniRuntime", _CountingOmniRuntime), patch(
            "omni_note_index.NoteRuntime", _CountingNoteRuntime
        ):
            omni_mcp.dispatch_tool(
                "search_all", {"query": "hello"}, root_dir="/tmp/vault-x"
            )
            omni_mcp.dispatch_tool(
                "search_all", {"query": "world"}, root_dir="/tmp/vault-x"
            )
        self.assertEqual(_CountingOmniRuntime.instances, 1)
        self.assertEqual(_CountingNoteRuntime.instances, 1)


if __name__ == "__main__":
    unittest.main()

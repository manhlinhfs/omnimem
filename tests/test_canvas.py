import json
import os
import tempfile
import unittest
from pathlib import Path

from omni_canvas import CanvasError, collect_graph, export_canvas
from omni_note import create_note
from omni_vault import ensure_vault_layout


def _restore_env(name, previous_value):
    if previous_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous_value


def _remove_tree(path):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


class TestCanvasExport(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        previous = os.environ.get("OMNIMEM_HOME")
        self.addCleanup(_restore_env, "OMNIMEM_HOME", previous)
        self.addCleanup(_remove_tree, self.tmpdir)
        os.environ["OMNIMEM_HOME"] = self.tmpdir
        ensure_vault_layout(root_dir=self.tmpdir)

    def _seed_graph(self):
        create_note("Alpha", body="Linked to [[beta]] and [[gamma]].\n", root_dir=self.tmpdir)
        create_note("Beta", body="Calls back to [[alpha]].\n", root_dir=self.tmpdir)
        create_note("Gamma", body="Standalone.\n", root_dir=self.tmpdir)
        create_note("Delta", body="No incoming or outgoing links.\n", root_dir=self.tmpdir)

    def test_collect_graph_returns_node_per_note_and_edges_for_links(self):
        self._seed_graph()
        nodes, edges = collect_graph(root_dir=self.tmpdir)
        slugs = sorted(node["id"] for node in nodes)
        self.assertEqual(slugs, ["alpha", "beta", "delta", "gamma"])

        edge_pairs = sorted((edge["fromNode"], edge["toNode"]) for edge in edges)
        self.assertIn(("alpha", "beta"), edge_pairs)
        self.assertIn(("alpha", "gamma"), edge_pairs)
        self.assertIn(("beta", "alpha"), edge_pairs)

    def test_root_and_depth_restrict_subgraph(self):
        self._seed_graph()
        nodes, edges = collect_graph(root_dir=self.tmpdir, root_slug="alpha", depth=1)
        slugs = sorted(node["id"] for node in nodes)
        self.assertEqual(sorted(slugs), ["alpha", "beta", "gamma"])
        for edge in edges:
            self.assertIn(edge["fromNode"], slugs)
            self.assertIn(edge["toNode"], slugs)

    def test_unknown_root_raises(self):
        self._seed_graph()
        with self.assertRaises(CanvasError):
            collect_graph(root_dir=self.tmpdir, root_slug="missing-slug")

    def test_export_writes_canvas_json(self):
        self._seed_graph()
        output = Path(self.tmpdir) / "graph.canvas"
        report = export_canvas(str(output), root_dir=self.tmpdir)
        self.assertTrue(output.exists())
        data = json.loads(output.read_text(encoding="utf-8"))
        self.assertIn("nodes", data)
        self.assertIn("edges", data)
        self.assertEqual(report["node_count"], len(data["nodes"]))
        self.assertEqual(report["edge_count"], len(data["edges"]))


if __name__ == "__main__":
    unittest.main()

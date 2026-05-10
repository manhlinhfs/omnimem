import os
import tempfile
import unittest
from pathlib import Path

from omnimem.codemap import (
    CodemapError,
    build_repo_codemap,
    detect_language,
    iter_source_files,
    parse_codemap_note,
    parse_python_module,
    query_local_index,
    render_frontmatter,
    render_markdown,
    update_single_file,
)
from omnimem.vault import ensure_vault_layout


def _restore_env(name, previous_value):
    if previous_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous_value


def _remove_tree(path):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


class TestPythonParser(unittest.TestCase):
    def test_module_doc_imports_classes_functions(self):
        source = '''"""Top docstring."""

import os
from pathlib import Path as P

CONSTANT = 1


def hello(name, *args, **kwargs):
    """Say hi."""
    return f"hi {name}"


async def stream():
    """Async helper."""
    yield 1


class Greeter(Base, Mixin):
    """A greeter."""

    def __init__(self, target):
        self.target = target

    async def greet(self):
        return self.target
'''
        model = parse_python_module(source, path="demo.py")
        self.assertEqual(model["language"], "python")
        self.assertEqual(model["module_doc"], "Top docstring.")

        modules = sorted(item["module"] for item in model["imports"])
        self.assertIn("os", modules)
        self.assertIn("pathlib.Path", modules)

        functions = {func["name"] for func in model["functions"]}
        self.assertEqual(functions, {"hello", "stream"})

        async_func = next(func for func in model["functions"] if func["name"] == "stream")
        self.assertEqual(async_func["kind"], "async_function")

        self.assertEqual(len(model["classes"]), 1)
        cls = model["classes"][0]
        self.assertEqual(cls["name"], "Greeter")
        self.assertEqual(cls["bases"], ["Base", "Mixin"])
        method_names = sorted(method["name"] for method in cls["methods"])
        self.assertEqual(method_names, ["__init__", "greet"])

    def test_syntax_error_raises_codemap_error(self):
        with self.assertRaises(CodemapError):
            parse_python_module("def broken(\n", path="x.py")

    def test_render_markdown_lists_classes_and_functions(self):
        source = '''def alpha(x):
    """alpha doc."""
    pass


class Beta:
    """beta doc."""
    def gamma(self):
        pass
'''
        model = parse_python_module(source, path="m.py")
        body = render_markdown(model, repo_name="demo", relative_path="m.py")
        self.assertIn("# m.py", body)
        self.assertIn("## Functions", body)
        self.assertIn("alpha(x)", body)
        self.assertIn("## Classes", body)
        self.assertIn("Beta", body)
        self.assertIn("gamma(self)", body)

    def test_render_frontmatter_lists_symbols(self):
        source = '''class Foo:
    def bar(self):
        pass

def baz():
    pass
'''
        model = parse_python_module(source, path="m.py")
        front = render_frontmatter(model, repo_name="demo", relative_path="m.py", source_path="m.py")
        names = sorted(symbol["name"] for symbol in front["symbols"])
        self.assertEqual(names, ["Foo", "Foo.bar", "baz"])
        self.assertEqual(front["language"], "python")
        self.assertEqual(front["repo"], "demo")
        self.assertEqual(front["symbol_count"], 3)


class TestSourceWalker(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(_remove_tree, self.repo)

    def _write(self, relative, body):
        target = Path(self.repo) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        return target

    def test_iter_source_files_skips_dot_dirs_and_venv(self):
        self._write("pkg/main.py", "def x(): pass\n")
        self._write("pkg/__pycache__/cache.py", "")
        self._write(".git/config.py", "")
        self._write("venv/lib/whatever.py", "")
        self._write("node_modules/foo.py", "")
        self._write("docs/readme.md", "irrelevant")

        sources = list(iter_source_files(self.repo))
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].name, "main.py")

    def test_detect_language_returns_python_for_py(self):
        self.assertEqual(detect_language("foo.py"), "python")
        self.assertEqual(detect_language("foo.PY"), "python")
        self.assertIsNone(detect_language("foo.unknown"))


class TestBuildRepoCodemap(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        previous = os.environ.get("OMNIMEM_HOME")
        self.addCleanup(_restore_env, "OMNIMEM_HOME", previous)
        self.addCleanup(_remove_tree, self.tmpdir)
        os.environ["OMNIMEM_HOME"] = self.tmpdir
        ensure_vault_layout(root_dir=self.tmpdir)
        self.repo = tempfile.mkdtemp()
        self.addCleanup(_remove_tree, self.repo)

    def _write(self, relative, body):
        target = Path(self.repo) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        return target

    def test_build_writes_one_map_per_source_file(self):
        self._write("pkg/__init__.py", "")
        self._write("pkg/api.py", "def public(): pass\n")
        self._write("pkg/util.py", "class Helper:\n    def go(self):\n        pass\n")

        report = build_repo_codemap(self.repo, repo_name="demo", root_dir=self.tmpdir)
        written_paths = [Path(entry["map"]) for entry in report["written"]]
        self.assertEqual(len(written_paths), 3)
        for path in written_paths:
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            front, body = parse_codemap_note(text)
            self.assertEqual(front["kind"], "codemap")
            self.assertEqual(front["repo"], "demo")

    def test_update_single_file_round_trips(self):
        source = self._write("pkg/api.py", "def alpha(): pass\n")
        build_repo_codemap(self.repo, repo_name="demo", root_dir=self.tmpdir)
        source.write_text("def beta(): pass\n", encoding="utf-8")
        result = update_single_file(source, self.repo, repo_name="demo", root_dir=self.tmpdir)
        text = Path(result["map"]).read_text(encoding="utf-8")
        self.assertIn("beta", text)
        self.assertNotIn("alpha", text)

    def test_query_local_index_finds_symbol_substring(self):
        self._write("pkg/auth.py", "class TokenManager:\n    def rotate(self):\n        pass\n")
        build_repo_codemap(self.repo, repo_name="demo", root_dir=self.tmpdir)
        results = query_local_index("rotate", root_dir=self.tmpdir)
        self.assertTrue(any(r["symbol"]["name"].endswith("rotate") for r in results))


if __name__ == "__main__":
    unittest.main()

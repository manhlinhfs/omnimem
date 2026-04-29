import os
import tempfile
import unittest
from pathlib import Path

from omni_codemap import (
    SUPPORTED_LANGUAGES,
    build_repo_codemap,
    detect_language,
    flatten_symbols,
    iter_source_files,
    parse_codemap_note,
    parse_go_module,
    parse_javascript_module,
    parse_rust_module,
    parse_typescript_module,
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


class TestExtensionRegistry(unittest.TestCase):
    def test_supports_python_javascript_typescript_go_rust(self):
        self.assertEqual(
            sorted(SUPPORTED_LANGUAGES),
            sorted(["python", "javascript", "typescript", "go", "rust"]),
        )

    def test_detect_language_for_each_extension(self):
        self.assertEqual(detect_language("a.py"), "python")
        self.assertEqual(detect_language("a.js"), "javascript")
        self.assertEqual(detect_language("a.jsx"), "javascript")
        self.assertEqual(detect_language("a.mjs"), "javascript")
        self.assertEqual(detect_language("a.ts"), "typescript")
        self.assertEqual(detect_language("a.tsx"), "typescript")
        self.assertEqual(detect_language("a.go"), "go")
        self.assertEqual(detect_language("a.rs"), "rust")


class TestJavaScriptParser(unittest.TestCase):
    def test_extracts_imports_classes_functions(self):
        source = """
import { useState } from 'react';
import './styles.css';

export class Widget extends React.Component {
  render() {
    return null;
  }
}

export default function helper(name, options) {
  return name;
}

export const arrow = async (id) => {
  return id;
};
"""
        model = parse_javascript_module(source, path="widget.js")
        self.assertEqual(model["language"], "javascript")
        modules = sorted(item["module"] for item in model["imports"])
        self.assertEqual(modules, ["./styles.css", "react"])

        class_names = [cls["name"] for cls in model["classes"]]
        self.assertEqual(class_names, ["Widget"])
        self.assertEqual(model["classes"][0]["bases"], ["React.Component"])

        function_names = sorted(func["name"] for func in model["functions"])
        self.assertEqual(function_names, ["arrow", "helper"])

        arrow = next(func for func in model["functions"] if func["name"] == "arrow")
        self.assertEqual(arrow["kind"], "async_function")


class TestTypeScriptParser(unittest.TestCase):
    def test_includes_interface_type_alias_enum(self):
        source = """
interface User {
  id: string;
  name: string;
}

type Callback = (input: string) => void;

enum Color {
  Red,
  Green,
}

export function login(user: User): boolean {
  return true;
}
"""
        model = parse_typescript_module(source, path="user.ts")
        self.assertEqual(model["language"], "typescript")
        kinds = sorted({cls["kind"] for cls in model["classes"]})
        self.assertEqual(kinds, ["enum", "interface"])
        function_names = sorted(func["name"] for func in model["functions"])
        self.assertIn("login", function_names)
        self.assertIn("Callback", function_names)


class TestGoParser(unittest.TestCase):
    def test_parses_funcs_methods_and_imports(self):
        source = """package server

import (
    "fmt"
    "net/http"
)

import "context"

type Handler struct {
    name string
}

type Logger interface {
    Log(line string)
}

func New(name string) *Handler {
    return &Handler{name: name}
}

func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    fmt.Println(h.name)
}
"""
        model = parse_go_module(source, path="server.go")
        self.assertEqual(model["language"], "go")
        self.assertIn("package server", model.get("module_doc") or "")

        modules = sorted(item["module"] for item in model["imports"])
        self.assertEqual(modules, ["context", "fmt", "net/http"])

        kinds = {cls["kind"] for cls in model["classes"]}
        self.assertIn("struct", kinds)
        self.assertIn("interface", kinds)

        function_names = sorted(func["name"] for func in model["functions"])
        self.assertIn("New", function_names)
        self.assertIn("Handler.ServeHTTP", function_names)


class TestRustParser(unittest.TestCase):
    def test_parses_use_struct_enum_trait_impl_fn(self):
        source = """
use std::collections::HashMap;
use serde::{Serialize, Deserialize};

pub struct Config {
    name: String,
}

pub enum Status {
    Ready,
    Failed,
}

trait Renderer {
    fn render(&self) -> String;
}

impl Config {
    pub fn new(name: &str) -> Config {
        Config { name: name.to_string() }
    }
}

pub async fn run(config: Config) -> Status {
    Status::Ready
}
"""
        model = parse_rust_module(source, path="lib.rs")
        self.assertEqual(model["language"], "rust")

        kinds = {cls["kind"] for cls in model["classes"]}
        self.assertEqual(kinds, {"struct", "enum", "trait", "impl"})

        function_names = sorted(func["name"] for func in model["functions"])
        self.assertEqual(function_names, ["new", "render", "run"])


class TestFlattenSymbols(unittest.TestCase):
    def test_flatten_includes_classes_methods_and_functions(self):
        source = """class Foo:
    def bar(self):
        pass

def baz():
    pass
"""
        from omni_codemap import parse_python_module

        model = parse_python_module(source, path="m.py")
        records = flatten_symbols(model)
        names = sorted(record["name"] for record in records)
        self.assertEqual(names, ["Foo", "Foo.bar", "baz"])

        kinds = {record["name"]: record["kind"] for record in records}
        self.assertEqual(kinds["Foo"], "class")
        self.assertEqual(kinds["Foo.bar"], "method")
        self.assertEqual(kinds["baz"], "function")


class TestMixedRepoBuild(unittest.TestCase):
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

    def test_build_handles_mixed_languages(self):
        self._write("py/main.py", "def alpha(): pass\n")
        self._write("js/main.js", "function beta(name) { return name; }\n")
        self._write("ts/main.ts", "interface User { id: string }\nfunction gamma(): void {}\n")
        self._write("go/main.go", "package x\nfunc Delta() {}\n")
        self._write("rs/main.rs", "pub fn epsilon() {}\n")

        report = build_repo_codemap(self.repo, repo_name="demo", root_dir=self.tmpdir)
        languages = set()
        for entry in report["written"]:
            text = Path(entry["map"]).read_text(encoding="utf-8")
            front, _body = parse_codemap_note(text)
            languages.add(front.get("language"))
        self.assertEqual(languages, {"python", "javascript", "typescript", "go", "rust"})

    def test_language_filter_restricts_walk(self):
        self._write("py/a.py", "def x(): pass\n")
        self._write("js/a.js", "function y() {}\n")
        sources = list(iter_source_files(self.repo, languages="python"))
        self.assertEqual(len(sources), 1)
        self.assertTrue(str(sources[0]).endswith("a.py"))


if __name__ == "__main__":
    unittest.main()

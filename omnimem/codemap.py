"""Codemap module: parse source files into structural maps stored as
markdown notes alongside the second-brain vault.

v2.0 ships Python parsing via the stdlib `ast` module so the feature stays
zero-extra-dependency. Adding more languages is a matter of registering a
parser in `LANGUAGE_PARSERS` that returns the same structural model.
"""

import ast
import datetime
import json
import re
import threading
from pathlib import Path

from omnimem.metadata import current_timestamp
from omnimem.paths import SOURCE_ROOT, get_db_dir, get_runtime_home
from omnimem.vault import VAULT_DIRNAME

CODEMAP_DIRNAME = "codemap"
CODEMAP_COLLECTION_NAME = "omnimem_codemap"

PYTHON_EXTENSIONS = (".py", ".pyi")
JAVASCRIPT_EXTENSIONS = (".js", ".jsx", ".mjs", ".cjs")
TYPESCRIPT_EXTENSIONS = (".ts", ".tsx")
GO_EXTENSIONS = (".go",)
RUST_EXTENSIONS = (".rs",)
SUPPORTED_LANGUAGES = ("python", "javascript", "typescript", "go", "rust")

_LANGUAGE_BY_EXTENSION = {}
for ext in PYTHON_EXTENSIONS:
    _LANGUAGE_BY_EXTENSION[ext] = "python"
for ext in JAVASCRIPT_EXTENSIONS:
    _LANGUAGE_BY_EXTENSION[ext] = "javascript"
for ext in TYPESCRIPT_EXTENSIONS:
    _LANGUAGE_BY_EXTENSION[ext] = "typescript"
for ext in GO_EXTENSIONS:
    _LANGUAGE_BY_EXTENSION[ext] = "go"
for ext in RUST_EXTENSIONS:
    _LANGUAGE_BY_EXTENSION[ext] = "rust"

_EXTENSIONS_BY_LANGUAGE = {
    "python": PYTHON_EXTENSIONS,
    "javascript": JAVASCRIPT_EXTENSIONS,
    "typescript": TYPESCRIPT_EXTENSIONS,
    "go": GO_EXTENSIONS,
    "rust": RUST_EXTENSIONS,
}


class CodemapError(RuntimeError):
    pass


def get_codemap_root(root_dir=SOURCE_ROOT):
    return Path(get_runtime_home(root_dir=root_dir)) / VAULT_DIRNAME / CODEMAP_DIRNAME


def ensure_codemap_layout(root_dir=SOURCE_ROOT):
    target = get_codemap_root(root_dir=root_dir)
    target.mkdir(parents=True, exist_ok=True)
    return str(target)


def detect_language(path):
    suffix = Path(path).suffix.lower()
    return _LANGUAGE_BY_EXTENSION.get(suffix)


def parse_python_module(source, path=None):
    """Return a structural model for a Python source string."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise CodemapError(f"Failed to parse Python source: {exc}") from exc

    module_doc = ast.get_docstring(tree)
    imports = []
    classes = []
    functions = []

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({"module": alias.name, "alias": alias.asname, "line": node.lineno})
        elif isinstance(node, ast.ImportFrom):
            module = node.module or "."
            for alias in node.names:
                imports.append(
                    {
                        "module": f"{module}.{alias.name}".strip("."),
                        "alias": alias.asname,
                        "line": node.lineno,
                    }
                )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(_describe_function(node))
        elif isinstance(node, ast.ClassDef):
            classes.append(_describe_class(node))

    return {
        "language": "python",
        "path": str(path) if path else None,
        "module_doc": module_doc,
        "imports": imports,
        "classes": classes,
        "functions": functions,
    }


def _describe_function(node):
    params = []
    for arg in node.args.args:
        params.append(arg.arg)
    if node.args.vararg:
        params.append(f"*{node.args.vararg.arg}")
    if node.args.kwarg:
        params.append(f"**{node.args.kwarg.arg}")
    return {
        "kind": "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
        "name": node.name,
        "line": node.lineno,
        "params": params,
        "docstring": ast.get_docstring(node),
    }


def _describe_class(node):
    bases = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            bases.append(base.id)
        elif isinstance(base, ast.Attribute):
            parts = []
            cursor = base
            while isinstance(cursor, ast.Attribute):
                parts.insert(0, cursor.attr)
                cursor = cursor.value
            if isinstance(cursor, ast.Name):
                parts.insert(0, cursor.id)
            bases.append(".".join(parts))

    methods = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_describe_function(item))

    return {
        "kind": "class",
        "name": node.name,
        "line": node.lineno,
        "bases": bases,
        "docstring": ast.get_docstring(node),
        "methods": methods,
    }


_JS_FUNCTION_RE = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?(?P<async>async\s+)?function\s*\*?\s*(?P<name>[A-Za-z_$][\w$]*)\s*\((?P<params>[^)]*)\)",
    re.MULTILINE,
)
_JS_ARROW_RE = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*(?P<async>async\s+)?\(?(?P<params>[^=)]*)\)?\s*=>",
    re.MULTILINE,
)
_JS_CLASS_RE = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?class\s+(?P<name>[A-Za-z_$][\w$]*)(?:\s+extends\s+(?P<base>[\w$.<>]+))?",
    re.MULTILINE,
)
_JS_IMPORT_RE = re.compile(
    r"^\s*(?:import\s+[^;]+from\s+['\"](?P<module>[^'\"]+)['\"]|import\s+['\"](?P<plain>[^'\"]+)['\"])",
    re.MULTILINE,
)
_TS_INTERFACE_RE = re.compile(
    r"^\s*(?:export\s+)?interface\s+(?P<name>[A-Za-z_$][\w$]*)", re.MULTILINE
)
_TS_TYPE_RE = re.compile(
    r"^\s*(?:export\s+)?type\s+(?P<name>[A-Za-z_$][\w$]*)\s*=", re.MULTILINE
)
_TS_ENUM_RE = re.compile(
    r"^\s*(?:export\s+)?enum\s+(?P<name>[A-Za-z_$][\w$]*)", re.MULTILINE
)


def _line_of(source, position):
    return source.count("\n", 0, position) + 1


def _split_params(raw):
    if raw is None:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def parse_javascript_module(source, path=None, language="javascript"):
    """Regex-based structural parser for JavaScript / TypeScript source."""
    imports = []
    for match in _JS_IMPORT_RE.finditer(source):
        module = match.group("module") or match.group("plain")
        imports.append({"module": module, "alias": None, "line": _line_of(source, match.start())})

    classes = []
    for match in _JS_CLASS_RE.finditer(source):
        bases = [match.group("base")] if match.group("base") else []
        classes.append(
            {
                "kind": "class",
                "name": match.group("name"),
                "line": _line_of(source, match.start()),
                "bases": bases,
                "docstring": None,
                "methods": [],
            }
        )

    functions = []
    for match in _JS_FUNCTION_RE.finditer(source):
        functions.append(
            {
                "kind": "async_function" if match.group("async") else "function",
                "name": match.group("name"),
                "line": _line_of(source, match.start()),
                "params": _split_params(match.group("params")),
                "docstring": None,
            }
        )
    for match in _JS_ARROW_RE.finditer(source):
        functions.append(
            {
                "kind": "async_function" if match.group("async") else "function",
                "name": match.group("name"),
                "line": _line_of(source, match.start()),
                "params": _split_params(match.group("params")),
                "docstring": None,
            }
        )

    if language == "typescript":
        for match in _TS_INTERFACE_RE.finditer(source):
            classes.append(
                {
                    "kind": "interface",
                    "name": match.group("name"),
                    "line": _line_of(source, match.start()),
                    "bases": [],
                    "docstring": None,
                    "methods": [],
                }
            )
        for match in _TS_TYPE_RE.finditer(source):
            functions.append(
                {
                    "kind": "type_alias",
                    "name": match.group("name"),
                    "line": _line_of(source, match.start()),
                    "params": [],
                    "docstring": None,
                }
            )
        for match in _TS_ENUM_RE.finditer(source):
            classes.append(
                {
                    "kind": "enum",
                    "name": match.group("name"),
                    "line": _line_of(source, match.start()),
                    "bases": [],
                    "docstring": None,
                    "methods": [],
                }
            )

    return {
        "language": language,
        "path": str(path) if path else None,
        "module_doc": None,
        "imports": imports,
        "classes": classes,
        "functions": functions,
    }


def parse_typescript_module(source, path=None):
    return parse_javascript_module(source, path=path, language="typescript")


_GO_PACKAGE_RE = re.compile(r"^\s*package\s+(\w+)", re.MULTILINE)
_GO_IMPORT_SINGLE_RE = re.compile(r"^\s*import\s+(?:\w+\s+)?\"([^\"]+)\"", re.MULTILINE)
_GO_IMPORT_BLOCK_RE = re.compile(r"import\s*\(([^)]*)\)", re.DOTALL)
_GO_IMPORT_BLOCK_LINE_RE = re.compile(r"\"([^\"]+)\"")
_GO_FUNC_RE = re.compile(
    r"^\s*func\s+(?:\((?P<receiver>[^)]+)\)\s+)?(?P<name>[A-Za-z_]\w*)\s*\((?P<params>[^)]*)\)",
    re.MULTILINE,
)
_GO_TYPE_STRUCT_RE = re.compile(
    r"^\s*type\s+(?P<name>[A-Za-z_]\w*)\s+struct\b", re.MULTILINE
)
_GO_TYPE_INTERFACE_RE = re.compile(
    r"^\s*type\s+(?P<name>[A-Za-z_]\w*)\s+interface\b", re.MULTILINE
)


def parse_go_module(source, path=None):
    imports = []
    for match in _GO_IMPORT_SINGLE_RE.finditer(source):
        imports.append({"module": match.group(1), "alias": None, "line": _line_of(source, match.start())})
    for block_match in _GO_IMPORT_BLOCK_RE.finditer(source):
        block_text = block_match.group(1)
        block_start = block_match.start()
        for line_match in _GO_IMPORT_BLOCK_LINE_RE.finditer(block_text):
            imports.append(
                {
                    "module": line_match.group(1),
                    "alias": None,
                    "line": _line_of(source, block_start + line_match.start()),
                }
            )

    classes = []
    for match in _GO_TYPE_STRUCT_RE.finditer(source):
        classes.append(
            {
                "kind": "struct",
                "name": match.group("name"),
                "line": _line_of(source, match.start()),
                "bases": [],
                "docstring": None,
                "methods": [],
            }
        )
    for match in _GO_TYPE_INTERFACE_RE.finditer(source):
        classes.append(
            {
                "kind": "interface",
                "name": match.group("name"),
                "line": _line_of(source, match.start()),
                "bases": [],
                "docstring": None,
                "methods": [],
            }
        )

    functions = []
    for match in _GO_FUNC_RE.finditer(source):
        receiver = (match.group("receiver") or "").strip()
        if receiver:
            receiver_type = receiver.split()[-1].lstrip("*")
            display_name = f"{receiver_type}.{match.group('name')}"
            kind = "method"
        else:
            display_name = match.group("name")
            kind = "function"
        functions.append(
            {
                "kind": kind,
                "name": display_name,
                "line": _line_of(source, match.start()),
                "params": _split_params(match.group("params")),
                "docstring": None,
            }
        )

    package_match = _GO_PACKAGE_RE.search(source)
    module_doc = f"package {package_match.group(1)}" if package_match else None

    return {
        "language": "go",
        "path": str(path) if path else None,
        "module_doc": module_doc,
        "imports": imports,
        "classes": classes,
        "functions": functions,
    }


_RUST_USE_RE = re.compile(r"^\s*use\s+(?P<path>[^;]+);", re.MULTILINE)
_RUST_FN_RE = re.compile(
    r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:const\s+|unsafe\s+)?fn\s+(?P<name>[A-Za-z_]\w*)\s*(?:<[^>]*>)?\s*\((?P<params>[^)]*)\)",
    re.MULTILINE,
)
_RUST_STRUCT_RE = re.compile(
    r"^\s*(?:pub(?:\([^)]*\))?\s+)?struct\s+(?P<name>[A-Za-z_]\w*)", re.MULTILINE
)
_RUST_ENUM_RE = re.compile(
    r"^\s*(?:pub(?:\([^)]*\))?\s+)?enum\s+(?P<name>[A-Za-z_]\w*)", re.MULTILINE
)
_RUST_TRAIT_RE = re.compile(
    r"^\s*(?:pub(?:\([^)]*\))?\s+)?trait\s+(?P<name>[A-Za-z_]\w*)", re.MULTILINE
)
_RUST_IMPL_RE = re.compile(
    r"^\s*impl\s+(?:<[^>]*>\s+)?(?P<name>[A-Za-z_][\w:<>, ]*?)\s*\{", re.MULTILINE
)


def parse_rust_module(source, path=None):
    imports = []
    for match in _RUST_USE_RE.finditer(source):
        imports.append(
            {
                "module": match.group("path").strip(),
                "alias": None,
                "line": _line_of(source, match.start()),
            }
        )

    classes = []
    for match in _RUST_STRUCT_RE.finditer(source):
        classes.append(
            {
                "kind": "struct",
                "name": match.group("name"),
                "line": _line_of(source, match.start()),
                "bases": [],
                "docstring": None,
                "methods": [],
            }
        )
    for match in _RUST_ENUM_RE.finditer(source):
        classes.append(
            {
                "kind": "enum",
                "name": match.group("name"),
                "line": _line_of(source, match.start()),
                "bases": [],
                "docstring": None,
                "methods": [],
            }
        )
    for match in _RUST_TRAIT_RE.finditer(source):
        classes.append(
            {
                "kind": "trait",
                "name": match.group("name"),
                "line": _line_of(source, match.start()),
                "bases": [],
                "docstring": None,
                "methods": [],
            }
        )
    for match in _RUST_IMPL_RE.finditer(source):
        classes.append(
            {
                "kind": "impl",
                "name": match.group("name").strip(),
                "line": _line_of(source, match.start()),
                "bases": [],
                "docstring": None,
                "methods": [],
            }
        )

    functions = []
    for match in _RUST_FN_RE.finditer(source):
        functions.append(
            {
                "kind": "function",
                "name": match.group("name"),
                "line": _line_of(source, match.start()),
                "params": _split_params(match.group("params")),
                "docstring": None,
            }
        )

    return {
        "language": "rust",
        "path": str(path) if path else None,
        "module_doc": None,
        "imports": imports,
        "classes": classes,
        "functions": functions,
    }


LANGUAGE_PARSERS = {
    "python": parse_python_module,
    "javascript": parse_javascript_module,
    "typescript": parse_typescript_module,
    "go": parse_go_module,
    "rust": parse_rust_module,
}


def flatten_symbols(model):
    """Flatten a structural model into one record per symbol.

    Each record is suitable for indexing as its own ChromaDB document so search
    can return precise symbol-level hits instead of file-level hits.
    """
    records = []
    language = model.get("language")
    file_path = model.get("path")
    for cls in model.get("classes") or []:
        records.append(
            {
                "kind": cls.get("kind") or "class",
                "name": cls.get("name"),
                "line": cls.get("line"),
                "language": language,
                "path": file_path,
                "docstring": cls.get("docstring"),
            }
        )
        for method in cls.get("methods") or []:
            records.append(
                {
                    "kind": "method",
                    "name": f"{cls.get('name')}.{method.get('name')}",
                    "line": method.get("line"),
                    "language": language,
                    "path": file_path,
                    "docstring": method.get("docstring"),
                    "params": method.get("params"),
                }
            )
    for func in model.get("functions") or []:
        records.append(
            {
                "kind": func.get("kind") or "function",
                "name": func.get("name"),
                "line": func.get("line"),
                "language": language,
                "path": file_path,
                "docstring": func.get("docstring"),
                "params": func.get("params"),
            }
        )
    return records


def parse_source_file(path):
    language = detect_language(path)
    if language is None:
        return None
    parser = LANGUAGE_PARSERS.get(language)
    if parser is None:
        raise CodemapError(f"No parser registered for language '{language}'")
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return parser(text, path=path)


def render_markdown(model, repo_name=None, relative_path=None):
    """Render a structural model into a Markdown body."""
    lines = []
    title = relative_path or model.get("path") or "module"
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- Language: `{model['language']}`")
    if model.get("path"):
        lines.append(f"- Path: `{model['path']}`")
    if repo_name:
        lines.append(f"- Repo: `{repo_name}`")
    lines.append("")

    doc = model.get("module_doc")
    if doc:
        lines.append("## Module docstring")
        lines.append("")
        lines.append(doc.strip())
        lines.append("")

    if model.get("imports"):
        lines.append("## Imports")
        lines.append("")
        for entry in model["imports"]:
            alias = f" as {entry['alias']}" if entry.get("alias") else ""
            lines.append(f"- L{entry['line']}: `{entry['module']}{alias}`")
        lines.append("")

    if model.get("classes"):
        lines.append("## Classes")
        lines.append("")
        for cls in model["classes"]:
            bases = f"({', '.join(cls['bases'])})" if cls.get("bases") else ""
            lines.append(f"### `{cls['name']}{bases}` (L{cls['line']})")
            if cls.get("docstring"):
                lines.append("")
                lines.append(cls["docstring"].strip())
            if cls.get("methods"):
                lines.append("")
                lines.append("Methods:")
                for method in cls["methods"]:
                    params = ", ".join(method.get("params") or [])
                    lines.append(f"- L{method['line']}: `{method['name']}({params})`")
            lines.append("")

    if model.get("functions"):
        lines.append("## Functions")
        lines.append("")
        for func in model["functions"]:
            params = ", ".join(func.get("params") or [])
            lines.append(f"### `{func['name']}({params})` (L{func['line']})")
            if func.get("docstring"):
                lines.append("")
                lines.append(func["docstring"].strip())
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_frontmatter(model, repo_name=None, relative_path=None, source_path=None):
    timestamp = current_timestamp()
    symbols = []
    for cls in model.get("classes") or []:
        symbols.append({"name": cls["name"], "kind": "class", "line": cls["line"]})
        for method in cls.get("methods") or []:
            symbols.append(
                {
                    "name": f"{cls['name']}.{method['name']}",
                    "kind": "method",
                    "line": method["line"],
                }
            )
    for func in model.get("functions") or []:
        symbols.append({"name": func["name"], "kind": func["kind"], "line": func["line"]})

    return {
        "kind": "codemap",
        "language": model.get("language"),
        "repo": repo_name,
        "path": str(source_path) if source_path else model.get("path"),
        "relative_path": relative_path,
        "generated_at": timestamp,
        "symbol_count": len(symbols),
        "symbols": symbols,
    }


def map_path_for_source(repo_name, relative_path, root_dir=SOURCE_ROOT):
    """Translate a source-relative path into a codemap markdown path."""
    safe_relative = relative_path.replace("\\", "/")
    return get_codemap_root(root_dir=root_dir) / repo_name / f"{safe_relative}.md"


def write_codemap_note(map_path, frontmatter, body):
    import yaml

    map_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    block = f"---\n{yaml_text}\n---\n"
    text = block + "\n" + body
    map_path.write_text(text, encoding="utf-8")
    return str(map_path)


def parse_codemap_note(text):
    """Inverse of write_codemap_note. Returns (frontmatter_dict, body)."""
    import yaml

    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", text, re.DOTALL)
    if not match:
        return {}, text
    raw_yaml = match.group(1)
    body = match.group(2)
    loaded = yaml.safe_load(raw_yaml) or {}
    if not isinstance(loaded, dict):
        return {}, body
    return loaded, body


def iter_source_files(root, languages=None):
    """Yield source files inside `root` matching one of the requested languages.

    `languages` may be a string (single language), an iterable of language names,
    or `None` (which means "every language in `SUPPORTED_LANGUAGES`").
    """
    base = Path(root).expanduser().resolve()
    if not base.exists():
        raise CodemapError(f"Source root does not exist: {base}")

    if languages is None:
        wanted = set(SUPPORTED_LANGUAGES)
    elif isinstance(languages, str):
        wanted = {languages}
    else:
        wanted = set(languages)

    valid_extensions = set()
    for language in wanted:
        valid_extensions.update(_EXTENSIONS_BY_LANGUAGE.get(language, ()))
    if not valid_extensions:
        return

    if base.is_file():
        if base.suffix.lower() in valid_extensions:
            yield base
        return

    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in valid_extensions:
            continue
        relative_parts = path.relative_to(base).parts
        if any(part.startswith(".") for part in relative_parts):
            continue
        if any(
            part in {"venv", ".venv", "node_modules", "__pycache__", "dist", "build", "target", "vendor"}
            for part in relative_parts
        ):
            continue
        yield path


def build_repo_codemap(
    repo_path,
    repo_name=None,
    languages=None,
    root_dir=SOURCE_ROOT,
):
    """Walk a repo, parse every supported file, write codemap markdown notes.

    `languages` defaults to every language in `SUPPORTED_LANGUAGES`. Pass a
    string or list to restrict the walk (e.g. `languages="python"`).
    """
    base = Path(repo_path).expanduser().resolve()
    if not base.exists():
        raise CodemapError(f"Source root does not exist: {base}")
    repo_name = repo_name or base.name

    written = []
    failed = []
    for source_path in iter_source_files(base, languages=languages):
        try:
            model = parse_source_file(source_path)
        except CodemapError as exc:
            failed.append({"path": str(source_path), "reason": str(exc)})
            continue
        if model is None:
            continue
        relative_path = str(source_path.relative_to(base))
        map_path = map_path_for_source(repo_name, relative_path, root_dir=root_dir)
        body = render_markdown(model, repo_name=repo_name, relative_path=relative_path)
        frontmatter = render_frontmatter(
            model,
            repo_name=repo_name,
            relative_path=relative_path,
            source_path=source_path,
        )
        write_codemap_note(map_path, frontmatter, body)
        written.append({"source": str(source_path), "map": str(map_path)})

    return {"written": written, "failed": failed, "repo": repo_name}


def update_single_file(
    source_path,
    repo_path,
    repo_name=None,
    root_dir=SOURCE_ROOT,
):
    """Re-parse a single source file and update its codemap note."""
    base = Path(repo_path).expanduser().resolve()
    source_path = Path(source_path).expanduser().resolve()
    if not source_path.exists():
        raise CodemapError(f"Source file does not exist: {source_path}")
    if not str(source_path).startswith(str(base)):
        raise CodemapError(f"Source file {source_path} is outside repo {base}")

    repo_name = repo_name or base.name
    relative_path = str(source_path.relative_to(base))
    model = parse_source_file(source_path)
    if model is None:
        raise CodemapError(f"Unsupported language for {source_path}")
    map_path = map_path_for_source(repo_name, relative_path, root_dir=root_dir)
    body = render_markdown(model, repo_name=repo_name, relative_path=relative_path)
    frontmatter = render_frontmatter(
        model,
        repo_name=repo_name,
        relative_path=relative_path,
        source_path=source_path,
    )
    write_codemap_note(map_path, frontmatter, body)
    return {"source": str(source_path), "map": str(map_path)}


def remove_repo_codemap(repo_name, root_dir=SOURCE_ROOT):
    target = get_codemap_root(root_dir=root_dir) / repo_name
    if not target.exists():
        return {"removed": False, "reason": "not present"}
    import shutil

    shutil.rmtree(target)
    return {"removed": True, "path": str(target)}


def query_local_index(query, root_dir=SOURCE_ROOT, limit=20):
    """Filesystem-only search: scan symbols and return matches by simple substring.

    This is the no-ChromaDB fallback so codemap is useful even before the
    runtime spins up. Pair with `query_semantic` for ranked semantic results.
    """
    needle = query.strip().lower()
    if not needle:
        return []
    results = []
    base = get_codemap_root(root_dir=root_dir)
    if not base.exists():
        return results
    for path in base.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        frontmatter, _body = parse_codemap_note(text)
        symbols = frontmatter.get("symbols") or []
        for symbol in symbols:
            if needle in str(symbol.get("name", "")).lower():
                results.append(
                    {
                        "repo": frontmatter.get("repo"),
                        "path": frontmatter.get("path"),
                        "relative_path": frontmatter.get("relative_path"),
                        "symbol": symbol,
                        "map": str(path),
                    }
                )
                if len(results) >= limit:
                    return results
    return results


class CodemapRuntime:
    """ChromaDB runtime for the codemap collection."""

    def __init__(self, root_dir=SOURCE_ROOT):
        import chromadb

        from omnimem.embeddings import build_embedding_function

        self.root_dir = root_dir
        self.client = chromadb.PersistentClient(path=str(get_db_dir(root_dir=root_dir)))
        self.embedding_function = build_embedding_function()
        self._lock = threading.RLock()
        self.collection = self.client.get_or_create_collection(
            name=CODEMAP_COLLECTION_NAME,
            embedding_function=self.embedding_function,
        )

    def upsert_map(self, frontmatter, body):
        document = body
        path = frontmatter.get("path") or frontmatter.get("relative_path") or ""
        record_id = f"{frontmatter.get('repo')}::file::{path}"
        metadata = {
            "kind": "file",
            "repo": frontmatter.get("repo") or "",
            "path": path,
            "language": frontmatter.get("language") or "",
            "symbol_count": int(frontmatter.get("symbol_count") or 0),
            "generated_at": frontmatter.get("generated_at") or "",
        }
        with self._lock:
            try:
                self.collection.delete(ids=[record_id])
            except Exception:
                pass
            self.collection.add(documents=[document], metadatas=[metadata], ids=[record_id])
        return {"upserted": 1, "id": record_id}

    def upsert_symbols(self, repo, path, language, symbols):
        """Write one ChromaDB record per symbol so search can return precise hits."""
        if not symbols:
            return {"upserted": 0}
        ids = []
        documents = []
        metadatas = []
        for symbol in symbols:
            symbol_id = f"{repo}::symbol::{path}::{symbol.get('kind')}::{symbol.get('name')}::L{symbol.get('line')}"
            params = symbol.get("params") or []
            signature = f"{symbol.get('name')}({', '.join(params)})" if params else str(symbol.get("name") or "")
            doc_parts = [signature]
            doc_parts.append(f"kind: {symbol.get('kind')}")
            doc_parts.append(f"language: {language}")
            doc_parts.append(f"path: {path}")
            if symbol.get("docstring"):
                doc_parts.append("")
                doc_parts.append(symbol["docstring"].strip())
            ids.append(symbol_id)
            documents.append("\n".join(doc_parts))
            metadatas.append(
                {
                    "kind": "symbol",
                    "symbol_kind": symbol.get("kind") or "",
                    "name": symbol.get("name") or "",
                    "line": int(symbol.get("line") or 0),
                    "language": language or "",
                    "repo": repo or "",
                    "path": path or "",
                }
            )

        with self._lock:
            try:
                self.collection.delete(ids=ids)
            except Exception:
                pass
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
        return {"upserted": len(ids)}

    def delete_path_records(self, repo, path):
        """Remove the file map and any per-symbol records for a given source path."""
        with self._lock:
            try:
                self.collection.delete(
                    where={
                        "$and": [
                            {"repo": repo or ""},
                            {"path": path or ""},
                        ]
                    }
                )
            except Exception:
                pass

    def delete_repo_records(self, repo):
        """Remove every record for a given repo."""
        with self._lock:
            try:
                self.collection.delete(where={"repo": repo or ""})
            except Exception:
                pass

    def query(self, query, n_results=5, kinds=None):
        with self._lock:
            kwargs = {"query_texts": [query], "n_results": n_results}
            if kinds:
                if len(kinds) == 1:
                    kwargs["where"] = {"kind": kinds[0]}
                else:
                    kwargs["where"] = {"$or": [{"kind": kind} for kind in kinds]}
            results = self.collection.query(**kwargs)
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            ids = results.get("ids", [[]])[0]
            records = []
            for idx, doc in enumerate(documents):
                records.append(
                    {
                        "id": ids[idx] if idx < len(ids) else None,
                        "distance": distances[idx] if idx < len(distances) else 0.0,
                        "document": doc,
                        "metadata": metadatas[idx] if idx < len(metadatas) else {},
                    }
                )
            return records


def index_repo(repo_path, repo_name=None, languages=None, root_dir=SOURCE_ROOT):
    """Build codemap markdown notes AND mirror them into ChromaDB.

    For every source file we index two kinds of records:
    - one `kind=file` record carrying the whole markdown body
    - one `kind=symbol` record per top-level symbol (function, class, method,
      struct, interface, trait, etc.) for precise symbol-level search hits
    """
    report = build_repo_codemap(
        repo_path,
        repo_name=repo_name,
        languages=languages,
        root_dir=root_dir,
    )

    indexed_files = 0
    indexed_symbols = 0
    try:
        runtime = CodemapRuntime(root_dir=root_dir)
    except Exception as exc:
        report["index_error"] = str(exc)
        return report

    base = Path(repo_path).expanduser().resolve()
    for entry in report["written"]:
        text = Path(entry["map"]).read_text(encoding="utf-8")
        frontmatter, body = parse_codemap_note(text)
        path_meta = frontmatter.get("path") or ""
        try:
            runtime.upsert_map(frontmatter, body)
            indexed_files += 1
        except Exception as exc:
            entry["index_error"] = str(exc)

        try:
            source_path = Path(entry["source"])
            model = parse_source_file(source_path)
        except CodemapError:
            continue
        if model is None:
            continue
        symbols = flatten_symbols(model)
        try:
            outcome = runtime.upsert_symbols(
                repo=frontmatter.get("repo"),
                path=path_meta,
                language=model.get("language"),
                symbols=symbols,
            )
            indexed_symbols += outcome.get("upserted", 0)
        except Exception as exc:
            entry["symbol_index_error"] = str(exc)

    report["indexed"] = indexed_files
    report["indexed_symbols"] = indexed_symbols
    return report

# OmniMem Codemap

The codemap module turns a source tree into a navigable structural map: one Markdown note per source file, listing imports, classes, and functions with line numbers. Both you and the AI agent can search the map without re-reading the codebase.

OmniMem ships parsers for Python (stdlib `ast`), JavaScript, TypeScript, Go, and Rust. Non-Python parsers are regex-based and stdlib-only — accurate enough to be a useful navigation aid but they will miss exotic constructs. Tree-sitter or subprocess parsers can plug into the same registry when higher fidelity is needed.

## Where it lives

```
$OMNIMEM_HOME/vault/codemap/<repo-name>/<relative/path>.py.md
```

Codemap notes share the vault tree with regular notes but stay in a separate `codemap/` subdirectory so list/search verbs can scope to one or the other.

## CLI reference

### Build a codemap for a repo

```bash
omnimem codemap build /path/to/repo --repo-name myproject
omnimem codemap build /path/to/repo --language python --language go
```

Walks the tree (skipping `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `dist`, `build`, `target`, `vendor`), parses every supported source file, and writes a markdown note per source file. Each note has YAML frontmatter listing every symbol with its line number. Use `--language` (repeatable) to restrict the walk to a subset of languages; the default scans every supported language.

Indexing produces both:

- a `kind=file` ChromaDB record per source file (whole markdown body)
- a `kind=symbol` record per top-level symbol so `query` returns precise function / class / method / struct / trait hits

### Update a single file

```bash
omnimem codemap update /path/to/repo/src/auth.py --repo-path /path/to/repo
```

Re-parses one source file in place. Use this from a `PostToolUse` hook (see `omnimem hook`) so the codemap stays current as code changes.

### Query symbols

```bash
omnimem codemap query "rotate" --json
```

Returns two views:

- **local** — substring match against symbol names from the codemap notes (no LLM, no embeddings, instant).
- **semantic** — ChromaDB semantic search over the `omnimem_codemap` collection (top-N ranked by embedding distance).

### Remove a repo's codemap

```bash
omnimem codemap rm myproject
```

## Parser registry

`omni_codemap.LANGUAGE_PARSERS` is a dict mapping language → callable. Adding a new language is a matter of:

1. Implementing a parser that returns the same structural model (`{language, path, module_doc, imports, classes, functions}`).
2. Registering it in `LANGUAGE_PARSERS`.
3. Extending `detect_language(path)` with the new file extensions.

For Python, the parser walks `ast` and extracts top-level `Import`, `ImportFrom`, `FunctionDef`, `AsyncFunctionDef`, and `ClassDef` nodes. Class methods are nested under their owning class.

## Language matrix

| Language | Extension(s) | Parser | Captures |
|---|---|---|---|
| Python | `.py`, `.pyi` | stdlib `ast` | imports, classes, methods, functions, async functions, docstrings |
| JavaScript | `.js`, `.jsx`, `.mjs`, `.cjs` | regex | imports, classes (with `extends`), functions, arrow functions, async |
| TypeScript | `.ts`, `.tsx` | regex | everything JavaScript captures, plus interfaces, type aliases, enums |
| Go | `.go` | regex | package, imports (single + block), structs, interfaces, funcs, methods (`Receiver.Name`) |
| Rust | `.rs` | regex | `use`, `struct`, `enum`, `trait`, `impl`, `fn` (incl. `pub`, `async`) |

Regex parsers favor correctness on the common case over total coverage. They will miss heavily macro-driven Rust or unusual JS export forms. When you need full fidelity, plug a tree-sitter or subprocess parser into `LANGUAGE_PARSERS`.

## Roadmap (post-v1.2)

- **Tree-sitter integration** for languages where regex coverage is uncomfortable (likely Rust + advanced TS).
- **Documentation comments** — capture `///`, `//!`, JSDoc `/** ... */`, and Go doc comments and surface them in the codemap notes.
- **Caller / callee edges** between symbols so search can answer "what calls X" without re-reading source.
- **Project-aware build** — auto-detect monorepo layouts (Nx, Turborepo, Cargo workspaces, Go workspaces) and split codemaps per package.

# Troubleshooting

Common issues and fixes for OmniMem v1.2.x. Start with `omnimem doctor` — it reports most of these conditions in plain text.

## Install / bootstrap

### `omnimem` command not found after `scripts/setup.sh`

You're either not in the repo root or your shell hasn't added the launcher to `PATH`. Run with the explicit path:

```bash
./omnimem --version
```

For package installs (`pip install .`), make sure your Python user bin (`~/.local/bin`) is on `PATH`.

### `bootstrap` fails with `Repository not found` or DNS errors

The setup script tried to download `all-MiniLM-L6-v2` from Hugging Face and the network blocked it. Two options:

```bash
# (a) point OmniMem at an existing local cache
OMNIMEM_ALLOW_MODEL_DOWNLOAD=0 python omni_bootstrap.py --offline-only

# (b) allow on-demand download once your network can reach huggingface.co
OMNIMEM_ALLOW_MODEL_DOWNLOAD=1 python omni_bootstrap.py
```

### `chromadb` import fails with `ModuleNotFoundError`

Re-run `scripts/setup.sh`, or in package mode reinstall:

```bash
pip install --upgrade chromadb sentence-transformers
```

If you're on Windows and ChromaDB import fails on first use, delete `$OMNIMEM_HOME/chroma/` and let it rebuild. Some Windows file-lock combinations corrupt the on-disk SQLite.

## Agent integration

### Claude Code does not see `omnimem_*` tools

1. Confirm the rule block exists: `grep -A 5 "OMNIMEM:START" ~/.claude/CLAUDE.md`
2. Confirm MCP registration: `cat ~/.claude/mcp.json` should have `"omnimem"` under `mcpServers`.
3. **Restart Claude Code.** MCP servers are loaded once per session.
4. Use `/mcp` inside Claude Code — it lists registered servers and any startup error.

If you see `omnimem` in `/mcp` but tools fail, run `omnimem mcp serve` in a terminal and pipe a sample request:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | omnimem mcp serve
```

You should get a JSON-RPC response within 1-2 seconds.

### Stop hook fails with `'omnimem' is a package and cannot be directly executed`

Symptom — Claude Code shows:

```
Stop hook error: ... C:\...\python.exe: No module named omnimem.__main__;
'omnimem' is a package and cannot be directly executed
```

Cause — your `~/.claude/settings.json` (or `~/.codex/config.toml`, or
an MCP `mcp.json` / `settings.json`) was installed by OmniMem v1.2.6 or
earlier, or hand-copied from older docs. The entries call
`<python> -m omnimem ...`, which runpy refuses whenever any `sys.path`
entry resolves `omnimem` to a package or namespace package.

Fix — upgrade to v1.2.7+ and run any of:

```bash
pip install --upgrade omnimem        # or: cd <checkout> && git pull && pip install -e .
omnimem hook --status                # auto-migrates Claude / Codex hook entries
omnimem init --status                # auto-migrates Claude / Codex / Gemini / Cursor MCP entries
```

Both `hook` and `init` rewrite stale `<python> -m omnimem ...` commands to
the `omnimem` console-script form on every invocation (idempotent). After
running once, restart your agent CLI so it re-reads the config.

If you still see the error after migration, check the hook entry by hand
in `~/.claude/settings.json` — the `command` field should start with the
path to `omnimem.exe` (Windows) or `omnimem` (POSIX), with no `-m omnimem`.

### Codex CLI hooks don't fire

Codex CLI's hook key surface has shifted across versions. The OmniMem installer ships the **most-common shape** but your version may use different keys. Open `~/.codex/config.toml` and edit between the marker comments:

```toml
# OmniMem hooks (omnimem-v1) - START
...
# OmniMem hooks (omnimem-v1) - END
```

Reinstalling preserves your edits as long as they stay between the markers.

### `init --status` shows everything as not installed

You probably ran `init` from a different `$HOME`. Confirm with:

```bash
echo $HOME
omnimem init --status
```

If the paths in `--status` don't match your real home, set `HOME` correctly or use `--scope project` and re-run from inside the project directory.

## Notes / Vault

### "Note not found" after I edited the file by hand

OmniMem resolves notes by slug or id from frontmatter. Check that:

1. Your edit kept the `slug:` field intact in frontmatter.
2. The filename still matches `<slug>.md`.

Run `omnimem note reindex` to rebuild the ChromaDB collection from the current vault state.

### `note search` returns nothing for a freshly created note

The first note creation in a session loads the embedding model (~6 seconds). Subsequent calls are fast. If `note search` consistently returns empty after `note new`, run:

```bash
omnimem note reindex
```

### Wikilinks don't resolve

Use `[[slug]]` (kebab-case from the title), not `[[Title]]`. Slugs are visible in `note list --json`.

## Codemap

### Codemap built but `query` returns nothing

Two paths to check:

```bash
omnimem codemap query "<your query>" --json
```

The output has `local` (filesystem substring match) and `semantic` (ChromaDB) sections. If `local` is empty, the symbol wasn't captured by the parser. If `semantic` is empty but `local` has hits, ChromaDB indexing failed — check `omnimem doctor`.

### Regex parsers miss a function in JS / TS / Go / Rust

By design, the regex parsers favor the common case. Heavily macro-driven Rust, JSX with unusual export forms, and Go generics in declaration position can be missed. Two options:

1. Edit the captured codemap markdown by hand — it's just markdown.
2. File an issue with a minimal example so we can extend the regex.

Tree-sitter parsers are on the roadmap (v1.5.0+).

## Backup / restore

### `restore` says "target already exists and is not empty"

Pass `--force` to overwrite:

```bash
omnimem restore /path/to/snapshot.tar.gz --force
```

Or move/rename the existing `OMNIMEM_HOME` first.

### `backup` archive doesn't include vault/

You're on a pre-v1.2 binary. `omnimem backup` from v1.2.0+ always includes the vault tree. Check `omnimem --version`.

## Still stuck

Open an issue: <https://github.com/manhlinhfs/omnimem/issues/new/choose>. Include:

- `omnimem --version`
- The full output of `omnimem doctor --json`
- The exact command that failed
- The full error message and traceback

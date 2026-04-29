# OmniMem MCP Server

OmniMem ships a stdio Model Context Protocol server so any MCP-compatible agent can call into your second brain without a custom integration.

## Run

```bash
omnimem mcp serve
```

The server speaks newline-delimited JSON-RPC 2.0 over stdin/stdout. Your agent CLI launches and owns this process.

## Inspect the tool registry

```bash
omnimem mcp tools          # human-readable
omnimem mcp tools --json   # full JSON Schemas
```

## Tools exposed in v1.2

| Tool | Purpose |
|---|---|
| `note_new` | Create a structured note in the OmniMem vault. |
| `note_search` | Semantic search across structured notes. |
| `note_show` | Read a note's frontmatter, body, and backlinks. |
| `note_link` | Append a wikilink between two notes. |
| `search_all` | Federated search across `omnimem_notes` and `omnimem_core`. |
| `import_file` | Ingest a PDF / DOCX / source file via Kreuzberg. |

Each tool publishes a JSON Schema via `tools/list`. Agents can rely on standard MCP introspection — no out-of-band documentation required.

## Manual MCP registration

If you would rather wire OmniMem in by hand instead of using `omnimem init`, here are the snippets:

### Claude Code (`~/.claude/mcp.json`)

```json
{
  "mcpServers": {
    "omnimem": {
      "command": "/path/to/python",
      "args": ["-m", "omnimem", "mcp", "serve"]
    }
  }
}
```

### Codex CLI (`~/.codex/config.toml`)

```toml
[mcp_servers.omnimem]
command = "/path/to/python"
args = ["-m", "omnimem", "mcp", "serve"]
```

### Gemini CLI (`~/.gemini/settings.json`)

```json
{
  "mcpServers": {
    "omnimem": {
      "command": "/path/to/python",
      "args": ["-m", "omnimem", "mcp", "serve"]
    }
  }
}
```

### Cursor (`~/.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "omnimem": {
      "command": "/path/to/python",
      "args": ["-m", "omnimem", "mcp", "serve"]
    }
  }
}
```

## Debugging

- Run `omnimem mcp serve` directly in a terminal and pipe a JSON-RPC `initialize` request into it to confirm the server responds.
- The server logs uncaught tool errors to JSON-RPC error responses with code `-32000`. Standard MCP errors (`-32601` method not found, `-32602` invalid params, `-32700` parse error) are also implemented.
- Tool calls that fail to index into ChromaDB still succeed if the disk write succeeded — the index is best-effort. Run `omnimem note reindex` to recover.

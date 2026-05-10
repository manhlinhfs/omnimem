# OmniMem + Gemini CLI

## Install

```bash
omnimem init --agent gemini
```

This writes:

- `~/.gemini/GEMINI.md` — appends the OmniMem rule block.
- `~/.gemini/settings.json` — merges an `omnimem` entry under `mcpServers`.

The installer is non-destructive: existing keys in `settings.json` are preserved.

## Project scope

```bash
omnimem init --agent gemini --scope project
```

Writes the rule block into `./GEMINI.md`. MCP server registration stays in the user-scope `settings.json`.

## Verifying

```bash
omnimem init --status
omnimem mcp tools
```

Inspect `~/.gemini/settings.json` — you should see:

```json
{
  "mcpServers": {
    "omnimem": {
      "command": "/path/to/omnimem",
      "args": ["mcp", "serve"]
    }
  }
}
```

> `command` must point at the `omnimem` console script (`<venv>/bin/omnimem`
> or `<venv>/Scripts/omnimem.exe`). The earlier `<python> -m omnimem mcp serve`
> form is fragile — when any `sys.path` entry resolves `omnimem` to a package
> or namespace package, runpy refuses with "'omnimem' is a package and cannot
> be directly executed". `omnimem init` auto-rewrites stale entries.

## Uninstall

```bash
omnimem init --uninstall --agent gemini
```

## Notes

- Gemini CLI reloads MCP servers on session start. After `init`, restart your Gemini session.
- Keep the rest of `settings.json` (theme, auth tokens, etc.) untouched — the installer only writes the `mcpServers.omnimem` key.

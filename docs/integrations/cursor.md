# OmniMem + Cursor

## Install

```bash
omnimem init --agent cursor
```

This writes:

- `~/.cursor/rules/omnimem.mdc` — Cursor rule file with the OmniMem protocol. The file uses Cursor's `.mdc` frontmatter so the rule is always applied.
- `~/.cursor/mcp.json` — registers the `omnimem` MCP server.

## Project scope

```bash
omnimem init --agent cursor --scope project
```

Writes:

- `./.cursor/rules/omnimem.mdc`
- `./.cursor/mcp.json`

Project-scope rules take precedence inside the project directory.

## What the rule looks like

The rule file starts with:

```mdc
---
description: OmniMem second brain protocol
alwaysApply: true
---
```

followed by the marked OmniMem block.

## Verifying

```bash
omnimem init --status
omnimem mcp tools
```

Reload Cursor's window after install so the rule and MCP server are picked up.

## Uninstall

```bash
omnimem init --uninstall --agent cursor
```

Removes the `.mdc` rule file (or strips just the OmniMem block if you added other content) and the `omnimem` entry from `mcp.json`.

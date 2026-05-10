# OmniMem + Claude Code

OmniMem ships a one-command installer for Claude Code. The installer writes a marked block into `CLAUDE.md` and registers the OmniMem MCP server so Claude can call `note_search`, `note_new`, `search_all`, and friends directly.

## Install

```bash
omnimem init --agent claude
```

This writes:

- `~/.claude/CLAUDE.md` — appends the OmniMem rule block (between `<!-- OMNIMEM:START v1.2 -->` and `<!-- OMNIMEM:END -->` markers).
- `~/.claude.json` — registers the `omnimem` MCP server under `mcpServers.omnimem` (the same file `claude mcp add -s user` writes; merged in place, every other key preserved).

## Project scope

Use `--scope project` to install the rule block in `./CLAUDE.md` (and `./.mcp.json`) for the current project only:

```bash
omnimem init --agent claude --scope project
```

## What Claude does after install

The injected protocol tells Claude to:

1. Prefer the `omnimem` MCP tools when available.
2. Fall back to the `omnimem` CLI shell commands otherwise.
3. Always search OmniMem before answering project-specific questions.
4. Always save a note after non-trivial tasks, with wiki-link cross-references.

## Verifying

```bash
omnimem init --status
omnimem mcp tools
```

Restart Claude Code and the `omnimem` tools should appear in the tool list.

## Uninstall

```bash
omnimem init --uninstall --agent claude
```

This strips the marked block from `CLAUDE.md` (preserving any surrounding content) and removes the `omnimem` entry from `~/.claude.json`. If you upgraded from OmniMem v1.3.1 or earlier, the orphan entry that lived in the (unread) `~/.claude/mcp.json` file is also dropped, and that file is deleted when no other servers remain.

## Troubleshooting

- **Claude does not see the tools** — Confirm `claude mcp list` shows `omnimem` (the entry lives in `~/.claude.json` under `mcpServers`). Restart Claude Code so it re-reads the file.
- **`omnimem` not on PATH inside Claude** — Install the package (`pip install .`) or absolute-path the launcher in your rule block.
- **Rule block was deleted** — Re-run `omnimem init --agent claude`. The installer is idempotent and only touches the marked region.

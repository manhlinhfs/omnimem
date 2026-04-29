# OmniMem + Codex CLI

Codex CLI uses the cross-vendor `AGENTS.md` convention for agent instructions and a TOML config for MCP servers.

## Install

```bash
omnimem init --agent codex
```

This writes:

- `~/.codex/AGENTS.md` — appends the OmniMem rule block between `<!-- OMNIMEM:START v1.2 -->` / `<!-- OMNIMEM:END -->` markers.
- `~/.codex/config.toml` — adds an `[mcp_servers.omnimem]` block with the `command` and `args` needed to launch `omnimem mcp serve`.

## Project scope

```bash
omnimem init --agent codex --scope project
```

Writes the rule block into `./AGENTS.md`. The TOML MCP config still lives at `~/.codex/config.toml` because Codex CLI consumes server configs from the user-scope file.

## Verifying

```bash
omnimem init --status
cat ~/.codex/config.toml
```

The TOML block should look like:

```toml
[mcp_servers.omnimem]
command = "/path/to/python"
args = ["-m", "omnimem", "mcp", "serve"]
```

## Uninstall

```bash
omnimem init --uninstall --agent codex
```

Removes both the marked AGENTS.md block and the `[mcp_servers.omnimem]` section from `config.toml`.

## Notes

- `AGENTS.md` is a shared convention. If both Codex CLI and another agent (e.g., Cursor) read the same project-scope `AGENTS.md`, the OmniMem block applies to both.
- Codex CLI re-reads `config.toml` on session start. Restart your Codex session after `init`.

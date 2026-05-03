# OmniMem Lifecycle Hooks

`omnimem hook` wires OmniMem into an agent CLI's lifecycle so the agent doesn't have to remember to call OmniMem on every turn. v1.2 supports Claude Code (`~/.claude/settings.json`) and Codex CLI (`~/.codex/config.toml`).

## Supported events (Claude Code)

| Event | What OmniMem does |
|---|---|
| `SessionStart` | Lists the 5 most recent notes so the agent has fresh project context loaded into its prompt. |
| `Stop` | Lists today's notes, prompting the agent to reflect on what was just completed. |
| `PostToolUse` (Edit, Write, MultiEdit) | Triggers `omnimem note reindex` so any agent-edited note files re-sync to the ChromaDB notes collection. |

Each entry is tagged with `"tag": "omnimem-v1"` inside the hook so reinstalling and uninstalling can target only the OmniMem entries without touching user-defined hooks.

## Install

```bash
omnimem hook --agent claude
```

This writes (or updates) `~/.claude/settings.json` `hooks` section with all default events.

To install only a subset:

```bash
omnimem hook --agent claude --event SessionStart --event Stop
```

To install for the current project only:

```bash
omnimem hook --agent claude --scope project
```

## Status

```bash
omnimem hook --status
```

Returns a per-scope summary listing which lifecycle events have OmniMem hooks registered.

## Uninstall

```bash
omnimem hook --uninstall --agent claude
```

Strips only OmniMem-tagged entries. Other entries you wrote by hand or that were added by other tools are preserved. If removing OmniMem leaves the `hooks` section empty, the section (or the whole file) is removed.

## Idempotency

The installer is idempotent:

- Pre-existing OmniMem entries are removed before new ones are written.
- Reinstalling produces an identical file.
- User-defined hooks alongside the OmniMem ones are preserved across install / reinstall / uninstall.

## Customizing the recipe

The default commands are in `omni_hooks._hook_recipe()`. You can fork that function or, more cleanly, write your own hook entries in `settings.json` with a different `tag` — the OmniMem installer only touches entries tagged `omnimem-v1`.

## Codex CLI hooks (experimental)

Codex CLI's lifecycle hook API has shifted across versions. OmniMem ships a best-effort installer that writes a clearly-marked block into `~/.codex/config.toml`:

```toml
# OmniMem hooks (omnimem-v1) - START
[hooks.omnimem_session_start]
event = "session_start"
command = "..."

[hooks.omnimem_stop]
event = "stop"
command = "..."

[hooks.omnimem_post_tool_use]
event = "post_tool_use"
command = "..."
# OmniMem hooks (omnimem-v1) - END
```

Install / uninstall with:

```bash
omnimem hook --agent codex
omnimem hook --uninstall --agent codex
```

If your Codex version expects different hook section names or schema, edit the block directly. The installer only modifies content between the marker comments, so your edits to surrounding TOML are preserved across reinstalls.

## Install for both agents

```bash
omnimem hook --agent all
omnimem hook --status
omnimem hook --uninstall --agent all
```

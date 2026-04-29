"""Lifecycle hook installer for OmniMem.

`omnimem hook install` wires OmniMem into an agent CLI's lifecycle so the
agent does not have to remember to call OmniMem on every turn. v2.0 ships
support for Claude Code's `settings.json` hook section. Codex CLI hooks land
once their lifecycle API is stable.
"""

import json
import re
import sys
from pathlib import Path

OMNIMEM_HOOK_TAG = "omnimem-v1"
SUPPORTED_AGENTS = ("claude", "codex")
DEFAULT_EVENTS = ("SessionStart", "Stop", "PostToolUse")
CODEX_DEFAULT_EVENTS = ("session_start", "stop", "post_tool_use")
CODEX_BLOCK_START = "# OmniMem hooks (omnimem-v1) - START"
CODEX_BLOCK_END = "# OmniMem hooks (omnimem-v1) - END"


class HookError(RuntimeError):
    pass


def _home():
    return Path.home()


def _omnimem_command():
    """Return the Python interpreter path in a shell-safe form.

    Hook commands are stored in JSON config files. Claude Code and Codex CLI
    on Windows pass them through `bash -c`, which interprets backslashes as
    escape characters and silently strips them. So `C:\\Users\\foo\\python.exe`
    becomes `C:Usersfoopython.exe`. We always emit POSIX-style forward slashes
    — Python on Windows accepts them natively, and bash leaves them alone.
    """
    raw = sys.executable or "python"
    return raw.replace("\\", "/")


def _omnimem_args(*extra):
    return ["-m", "omnimem", *extra]


def _claude_settings_path(scope, base_home=None, base_cwd=None):
    home = Path(base_home) if base_home else _home()
    cwd = Path(base_cwd) if base_cwd else Path.cwd()
    if scope == "user":
        return home / ".claude" / "settings.json"
    return cwd / ".claude" / "settings.json"


def _hook_recipe(event):
    """Return the OmniMem command + matcher for a given lifecycle event."""
    if event == "SessionStart":
        return {
            "matcher": "*",
            "hooks": [
                {
                    "type": "command",
                    "command": _format_command(_omnimem_args("note", "list", "--limit", "5", "--json")),
                    "tag": OMNIMEM_HOOK_TAG,
                }
            ],
        }
    if event == "Stop":
        return {
            "matcher": "*",
            "hooks": [
                {
                    "type": "command",
                    "command": _format_command(_omnimem_args("note", "list", "--since", "today", "--json")),
                    "tag": OMNIMEM_HOOK_TAG,
                }
            ],
        }
    if event == "PostToolUse":
        return {
            "matcher": "Edit|Write|MultiEdit",
            "hooks": [
                {
                    "type": "command",
                    "command": _format_command(_omnimem_args("note", "reindex")),
                    "tag": OMNIMEM_HOOK_TAG,
                }
            ],
        }
    raise HookError(f"Unknown hook event: {event}")


def _format_command(args):
    """Render a shell-friendly command string from arg list."""
    parts = [_omnimem_command(), *args]
    return " ".join(_quote(part) for part in parts)


def _quote(value):
    if any(ch in value for ch in (' ', '\t', '"', "'")):
        return json.dumps(value)
    return value


def install_claude_hooks(events=None, scope="user", base_home=None, base_cwd=None, dry_run=False):
    """Install OmniMem hooks into Claude Code's settings.json.

    Removes any pre-existing OmniMem-tagged entries before adding the new ones,
    so reinstalling is idempotent and `events` always reflects the desired set.
    """
    events = tuple(events) if events else DEFAULT_EVENTS
    target = _claude_settings_path(scope, base_home=base_home, base_cwd=base_cwd)

    settings = {}
    if target.exists():
        try:
            settings = json.loads(target.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError as exc:
            raise HookError(f"Cannot parse {target}: {exc}") from exc

    hooks_section = settings.setdefault("hooks", {})
    for event in DEFAULT_EVENTS + events:
        existing = hooks_section.get(event) or []
        hooks_section[event] = [
            entry for entry in existing if not _entry_is_omnimem(entry)
        ]

    for event in events:
        recipe = _hook_recipe(event)
        hooks_section.setdefault(event, []).append(recipe)

    for event in list(hooks_section.keys()):
        if not hooks_section[event]:
            hooks_section.pop(event, None)
    if not hooks_section:
        settings.pop("hooks", None)

    serialized = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
    if dry_run:
        return {"target": str(target), "would_write": True, "events": list(events), "preview": serialized}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(serialized, encoding="utf-8")
    return {"target": str(target), "installed": True, "events": list(events)}


def uninstall_claude_hooks(scope="user", base_home=None, base_cwd=None, dry_run=False):
    target = _claude_settings_path(scope, base_home=base_home, base_cwd=base_cwd)
    if not target.exists():
        return {"target": str(target), "removed": False, "reason": "not present"}
    try:
        settings = json.loads(target.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError:
        return {"target": str(target), "removed": False, "reason": "invalid json"}

    hooks_section = settings.get("hooks") or {}
    removed_events = []
    for event in list(hooks_section.keys()):
        entries = hooks_section.get(event) or []
        filtered = [entry for entry in entries if not _entry_is_omnimem(entry)]
        if len(filtered) != len(entries):
            removed_events.append(event)
        if filtered:
            hooks_section[event] = filtered
        else:
            hooks_section.pop(event, None)
    if not hooks_section:
        settings.pop("hooks", None)

    serialized = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
    if dry_run:
        return {"target": str(target), "would_remove": True, "events": removed_events}
    if settings:
        target.write_text(serialized, encoding="utf-8")
    else:
        target.unlink()
    return {"target": str(target), "removed": bool(removed_events), "events": removed_events}


def status(base_home=None, base_cwd=None):
    """Inspect which OmniMem hooks are installed across user + project scope."""
    report = {}
    for scope in ("user", "project"):
        target = _claude_settings_path(scope, base_home=base_home, base_cwd=base_cwd)
        scope_report = {"target": str(target), "installed_events": []}
        if target.exists():
            try:
                settings = json.loads(target.read_text(encoding="utf-8") or "{}")
            except json.JSONDecodeError:
                settings = {}
            hooks_section = settings.get("hooks") or {}
            for event, entries in hooks_section.items():
                if any(_entry_is_omnimem(entry) for entry in entries or []):
                    scope_report["installed_events"].append(event)
        report[scope] = scope_report
    return {"claude": report}


def _entry_is_omnimem(entry):
    if not isinstance(entry, dict):
        return False
    for nested in entry.get("hooks") or []:
        if isinstance(nested, dict) and nested.get("tag") == OMNIMEM_HOOK_TAG:
            return True
    return False


def _codex_config_path(scope, base_home=None, base_cwd=None):
    home = Path(base_home) if base_home else _home()
    cwd = Path(base_cwd) if base_cwd else Path.cwd()
    if scope == "user":
        return home / ".codex" / "config.toml"
    return cwd / ".codex" / "config.toml"


def _codex_recipe(events):
    """Render the Codex TOML hook block. Note: Codex's exact hook key surface
    varies by version, so we ship the most-common shape and let users tweak.
    """
    args = " ".join(_quote(part) for part in [_omnimem_command(), *_omnimem_args("note", "list", "--limit", "5", "--json")])
    reindex_args = " ".join(
        _quote(part) for part in [_omnimem_command(), *_omnimem_args("note", "reindex")]
    )

    block_lines = [CODEX_BLOCK_START]
    if "session_start" in events:
        block_lines.extend(
            [
                "[hooks.omnimem_session_start]",
                f"event = \"session_start\"",
                f"command = {json.dumps(args)}",
            ]
        )
    if "stop" in events:
        block_lines.extend(
            [
                "[hooks.omnimem_stop]",
                f"event = \"stop\"",
                f"command = {json.dumps(args)}",
            ]
        )
    if "post_tool_use" in events:
        block_lines.extend(
            [
                "[hooks.omnimem_post_tool_use]",
                f"event = \"post_tool_use\"",
                f"command = {json.dumps(reindex_args)}",
            ]
        )
    block_lines.append(CODEX_BLOCK_END)
    return "\n".join(block_lines) + "\n"


_CODEX_BLOCK_RE = re.compile(
    rf"\n*{re.escape(CODEX_BLOCK_START)}.*?{re.escape(CODEX_BLOCK_END)}\s*",
    re.DOTALL,
)


def install_codex_hooks(events=None, scope="user", base_home=None, base_cwd=None, dry_run=False):
    """Append (or replace) the OmniMem hook block in `~/.codex/config.toml`.

    The exact hook key names are best-effort: Codex CLI's hook API has shifted
    across versions. The block is wrapped in clear marker comments so users
    can hand-edit the keys to match their installed Codex version.
    """
    events = tuple(events) if events else CODEX_DEFAULT_EVENTS
    target = _codex_config_path(scope, base_home=base_home, base_cwd=base_cwd)

    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    block = _codex_recipe(events)

    if _CODEX_BLOCK_RE.search(existing):
        new_text = _CODEX_BLOCK_RE.sub("\n" + block, existing)
    else:
        if existing and not existing.endswith("\n"):
            existing += "\n"
        new_text = existing + "\n" + block

    if dry_run:
        return {"target": str(target), "would_write": True, "events": list(events), "preview": new_text}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new_text, encoding="utf-8")
    return {"target": str(target), "installed": True, "events": list(events)}


def uninstall_codex_hooks(scope="user", base_home=None, base_cwd=None, dry_run=False):
    target = _codex_config_path(scope, base_home=base_home, base_cwd=base_cwd)
    if not target.exists():
        return {"target": str(target), "removed": False, "reason": "not present"}
    existing = target.read_text(encoding="utf-8")
    if not _CODEX_BLOCK_RE.search(existing):
        return {"target": str(target), "removed": False, "reason": "no marked block"}
    new_text = _CODEX_BLOCK_RE.sub("\n", existing).strip() + "\n"
    if dry_run:
        return {"target": str(target), "would_remove": True}
    if new_text.strip():
        target.write_text(new_text, encoding="utf-8")
    else:
        target.unlink()
    return {"target": str(target), "removed": True}


def install(agents, events=None, scope="user", base_home=None, base_cwd=None, dry_run=False):
    if "all" in agents:
        agents = list(SUPPORTED_AGENTS)
    if not agents:
        raise HookError("No agents specified")

    results = []
    for agent in agents:
        if agent == "claude":
            results.append(
                {
                    "agent": "claude",
                    "result": install_claude_hooks(
                        events=events,
                        scope=scope,
                        base_home=base_home,
                        base_cwd=base_cwd,
                        dry_run=dry_run,
                    ),
                }
            )
        elif agent == "codex":
            codex_events = tuple(_normalize_codex_event(e) for e in events) if events else CODEX_DEFAULT_EVENTS
            results.append(
                {
                    "agent": "codex",
                    "result": install_codex_hooks(
                        events=codex_events,
                        scope=scope,
                        base_home=base_home,
                        base_cwd=base_cwd,
                        dry_run=dry_run,
                    ),
                }
            )
        else:
            raise HookError(f"Hook installer for '{agent}' is not supported")
    return results


def uninstall(agents, scope="user", base_home=None, base_cwd=None, dry_run=False):
    if "all" in agents:
        agents = list(SUPPORTED_AGENTS)
    if not agents:
        raise HookError("No agents specified")

    results = []
    for agent in agents:
        if agent == "claude":
            results.append(
                {
                    "agent": "claude",
                    "result": uninstall_claude_hooks(
                        scope=scope,
                        base_home=base_home,
                        base_cwd=base_cwd,
                        dry_run=dry_run,
                    ),
                }
            )
        elif agent == "codex":
            results.append(
                {
                    "agent": "codex",
                    "result": uninstall_codex_hooks(
                        scope=scope,
                        base_home=base_home,
                        base_cwd=base_cwd,
                        dry_run=dry_run,
                    ),
                }
            )
        else:
            raise HookError(f"Hook installer for '{agent}' is not supported")
    return results


def _normalize_codex_event(event):
    """Translate Claude-style event names to Codex snake_case if needed."""
    mapping = {
        "SessionStart": "session_start",
        "Stop": "stop",
        "PostToolUse": "post_tool_use",
    }
    return mapping.get(event, event)

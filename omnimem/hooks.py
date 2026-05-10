"""Lifecycle hook installer for OmniMem.

`omnimem hook --agent claude|codex` wires OmniMem into an agent CLI's
lifecycle so the agent does not have to remember to call OmniMem on every
turn. v2.0 ships support for Claude Code's `settings.json` hook section.
Codex CLI hooks land once their lifecycle API is stable.
"""

import json
import os
import re
import sys
from pathlib import Path

from omnimem.paths import SOURCE_ROOT

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
    """Return the omnimem console-script path in a shell-safe form.

    `python -m omnimem` is fragile: on any sys.path entry that resolves
    `omnimem` to a package or namespace package (e.g. CWD containing a sibling
    `omnimem/` directory), runpy raises "'omnimem' is a package and cannot be
    directly executed". Console scripts dispatch through importlib.metadata
    entry points and bypass module-resolution machinery entirely, so they are
    immune.

    Path emission uses POSIX-style forward slashes so the entry survives
    `bash -c` quoting on Windows — bash treats backslashes as escape chars
    and silently consumes them, turning `C:\\Users\\foo\\omnimem.exe` into
    `C:Usersfoo\\omnimem.exe`. Forward slashes work natively on both Windows
    and POSIX shells.
    """
    raw = sys.executable or ""
    if raw:
        bin_dir = Path(raw).parent
        for name in ("omnimem.exe", "omnimem") if os.name == "nt" else ("omnimem",):
            candidate = bin_dir / name
            if candidate.exists():
                return str(candidate).replace("\\", "/")
    return "omnimem"


def _omnimem_args(*extra):
    return list(extra)


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
                    "command": _format_command(_omnimem_args("hook", "--gated-reindex")),
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
        _quote(part) for part in [_omnimem_command(), *_omnimem_args("hook", "--gated-reindex")]
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


def _extract_file_path(payload):
    """Best-effort: pull a file path out of a hook payload from Claude or Codex."""
    if not isinstance(payload, dict):
        return None
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        path = tool_input.get("file_path") or tool_input.get("path")
        if path:
            return path
    data = payload.get("data")
    if isinstance(data, dict):
        path = data.get("file_path") or data.get("path")
        if path:
            return path
    return payload.get("file_path") or payload.get("path")


def _path_is_inside(child, parent):
    try:
        Path(child).expanduser().resolve().relative_to(
            Path(parent).expanduser().resolve()
        )
    except (ValueError, OSError):
        return False
    return True


def gated_reindex_from_stdin(stdin=None, root_dir=SOURCE_ROOT):
    """Read a PostToolUse payload from stdin and reindex only when a vault
    file was touched.

    Without this gate, every Edit/Write/MultiEdit on any file in the agent's
    working directory triggers a full notes reindex — which loads the
    embedding model and rebuilds the whole `omnimem_notes` collection. On a
    coding session that edits dozens of files, the cumulative latency is
    measured in tens of seconds.

    Returns a status dict so the caller can print/log it. Failures (no
    payload, bad json, no file path, file outside the vault) are NOT errors
    — they just mean "skip reindex".
    """
    stream = stdin if stdin is not None else sys.stdin
    try:
        raw = stream.read() if hasattr(stream, "read") else ""
    except Exception as exc:
        return {"acted": False, "reason": f"stdin error: {exc}"}

    if not (raw or "").strip():
        return {"acted": False, "reason": "empty stdin"}

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"acted": False, "reason": f"invalid json: {exc}"}

    file_path = _extract_file_path(payload)
    if not file_path:
        return {"acted": False, "reason": "no file_path in payload"}

    from omnimem.vault import get_vault_root

    vault_root = get_vault_root(root_dir=root_dir)
    if not _path_is_inside(file_path, vault_root):
        return {"acted": False, "reason": "file outside vault"}

    from omnimem.note_index import reindex_all_notes

    result = reindex_all_notes(root_dir=root_dir)
    return {"acted": True, "file_path": str(file_path), "result": result}


_LEGACY_CMD_RE = re.compile(
    r'^\s*(?:"[^"]+"|\'[^\']+\'|\S+)\s+-m\s+omnimem(\s|$)'
)


def _rewrite_legacy_command(command, new_launcher):
    """If `command` starts with `<some-launcher> -m omnimem`, swap the launcher
    for `new_launcher` and drop the `-m omnimem` segment. Returns the rewritten
    string, or `None` if the command does not match the legacy shape."""
    if not isinstance(command, str):
        return None
    if not _LEGACY_CMD_RE.match(command):
        return None
    return _LEGACY_CMD_RE.sub(lambda m: new_launcher + m.group(1), command, count=1)


def _command_is_legacy(command):
    return _rewrite_legacy_command(command, "_") is not None


def _rewrite_legacy_in_settings(settings, new_launcher):
    """Walk a Claude settings.json dict and rewrite any hook command that
    matches the legacy `<python> -m omnimem ...` shape, regardless of whether
    it carries our `omnimem-v1` tag. Returns the sorted list of events that
    were touched (empty when no rewrite happened)."""
    changed = set()
    for event, entries in (settings.get("hooks") or {}).items():
        for entry in entries or []:
            for nested in entry.get("hooks") or []:
                rewritten = _rewrite_legacy_command(nested.get("command"), new_launcher)
                if rewritten is None:
                    continue
                nested["command"] = rewritten
                changed.add(event)
    return sorted(changed)


def _claude_legacy_events(target):
    """Return the list of events in `target` that contain at least one hook
    command still matching the legacy `<python> -m omnimem ...` shape — used
    by tests and status reporting."""
    if not target.exists():
        return []
    try:
        settings = json.loads(target.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError:
        return []
    legacy = []
    for event, entries in (settings.get("hooks") or {}).items():
        for entry in entries or []:
            for nested in entry.get("hooks") or []:
                if _command_is_legacy(nested.get("command")):
                    legacy.append(event)
                    break
    return legacy


def _rewrite_legacy_in_codex_toml(text, new_launcher):
    """Rewrite legacy `command = "<python> -m omnimem ..."` lines inside the
    OmniMem START/END marker block. Returns (new_text, changed_bool)."""
    match = _CODEX_BLOCK_RE.search(text)
    if not match:
        return text, False
    block = match.group(0)
    new_block, count = re.subn(
        r'(command\s*=\s*)"([^"]+)"',
        lambda m: m.group(1) + json.dumps(
            _rewrite_legacy_command(m.group(2), new_launcher) or m.group(2)
        ),
        block,
    )
    if new_block == block:
        return text, False
    return text[: match.start()] + new_block + text[match.end():], True


def _codex_block_is_legacy(target):
    if not target.exists():
        return False
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return False
    match = _CODEX_BLOCK_RE.search(text)
    if not match:
        return False
    return bool(re.search(r"-m\s+omnimem", match.group(0)))


def migrate_legacy_commands(base_home=None, base_cwd=None):
    """Rewrite `<python> -m omnimem ...` hook commands to the console-script
    shape introduced in v1.2.7.

    Detection is by command **shape** (regex match on `-m omnimem`), not by
    the `omnimem-v1` tag — older OmniMem versions and hand-installed entries
    from docs lack the tag, and we still need to fix them.

    Rewriting is in-place: structure (matchers, sibling entries, ordering) is
    preserved. We do NOT auto-tag entries we did not previously own. We do NOT
    deduplicate — that is a separate user-driven concern.

    Idempotent: running twice on already-migrated config is a no-op. Returns a
    list of `{agent, scope, events}` records describing what was migrated.
    """
    new_launcher = _omnimem_command()
    migrations = []

    for scope in ("user", "project"):
        target = _claude_settings_path(scope, base_home=base_home, base_cwd=base_cwd)
        if not target.exists():
            continue
        try:
            settings = json.loads(target.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            continue
        changed_events = _rewrite_legacy_in_settings(settings, new_launcher)
        if changed_events:
            target.write_text(
                json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            migrations.append(
                {"agent": "claude", "scope": scope, "events": changed_events}
            )

    for scope in ("user", "project"):
        target = _codex_config_path(scope, base_home=base_home, base_cwd=base_cwd)
        if not target.exists():
            continue
        try:
            text = target.read_text(encoding="utf-8")
        except OSError:
            continue
        new_text, changed = _rewrite_legacy_in_codex_toml(text, new_launcher)
        if changed:
            target.write_text(new_text, encoding="utf-8")
            migrations.append({"agent": "codex", "scope": scope})
    return migrations

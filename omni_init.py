"""Multi-CLI integration installer for OmniMem.

`omnimem init` writes a marked rule block into each agent's instructions file
so users can wire OmniMem into Claude Code, Codex CLI, Gemini CLI, or Cursor
with a single command. Reinstalling replaces the marked block; uninstalling
strips it. Anything outside the markers is left untouched.
"""

import json
import os
import re
import sys
from pathlib import Path

MARKER_VERSION = "v1.2"
MARKER_START = f"<!-- OMNIMEM:START {MARKER_VERSION} -->"
MARKER_END = "<!-- OMNIMEM:END -->"
MARKER_PATTERN = re.compile(
    r"<!-- OMNIMEM:START [^>]*-->.*?<!-- OMNIMEM:END -->\s*",
    re.DOTALL,
)

SUPPORTED_AGENTS = ("claude", "codex", "gemini", "cursor")
DEFAULT_SCOPE = "user"

PROTOCOL_BODY = """## OmniMem Protocol (Second Brain)

OmniMem is your persistent memory layer. Use it BEFORE answering anything that
depends on prior context, and AFTER finishing a meaningful unit of work.

Tooling priority:
1. If an `omnimem` MCP server is registered, prefer its tools (`note_search`,
   `search_all`, `note_new`, `note_show`, `import_file`).
2. Otherwise, call the OmniMem CLI directly:
   - `omnimem note search "<query>" --full` - search structured notes
   - `omnimem search "<query>" --full` - search imported documents
   - `omnimem note new "<title>" --type decision --tags t1,t2 --body -` - save a note (body via stdin)
   - `omnimem import <path>` - ingest a PDF / DOCX / source file

Rules:
- ALWAYS search OmniMem before answering project-specific questions.
- ALWAYS save a note after resolving a non-trivial task, with a clear title and
  links `[[other-slug]]` to related notes.
- NEVER duplicate an existing note - search first, then update or link.
- Tag liberally. Prefer reusing tags returned by `note search`."""


class InitError(RuntimeError):
    pass


def _home():
    return Path.home()


def _cwd():
    return Path.cwd()


def get_target_path(agent, scope, base_home=None, base_cwd=None):
    """Return the instructions file path for an agent + scope."""
    home = Path(base_home) if base_home else _home()
    cwd = Path(base_cwd) if base_cwd else _cwd()

    if agent == "claude":
        return (home / ".claude" / "CLAUDE.md") if scope == "user" else (cwd / "CLAUDE.md")
    if agent == "codex":
        if scope == "user":
            return home / ".codex" / "AGENTS.md"
        return cwd / "AGENTS.md"
    if agent == "gemini":
        return (home / ".gemini" / "GEMINI.md") if scope == "user" else (cwd / "GEMINI.md")
    if agent == "cursor":
        if scope == "user":
            return home / ".cursor" / "rules" / "omnimem.mdc"
        return cwd / ".cursor" / "rules" / "omnimem.mdc"
    raise InitError(f"Unsupported agent: {agent}")


def get_mcp_config_path(agent, scope, base_home=None, base_cwd=None):
    home = Path(base_home) if base_home else _home()
    cwd = Path(base_cwd) if base_cwd else _cwd()

    if agent == "claude":
        return home / ".claude" / "mcp.json" if scope == "user" else cwd / ".mcp.json"
    if agent == "codex":
        return home / ".codex" / "config.toml"
    if agent == "gemini":
        return home / ".gemini" / "settings.json"
    if agent == "cursor":
        return home / ".cursor" / "mcp.json" if scope == "user" else cwd / ".cursor" / "mcp.json"
    raise InitError(f"Unsupported agent: {agent}")


def render_block(agent):
    body = PROTOCOL_BODY
    if agent == "cursor":
        wrapped = (
            "---\n"
            "description: OmniMem second brain protocol\n"
            "alwaysApply: true\n"
            "---\n"
            f"{body}\n"
        )
        return f"{MARKER_START}\n{wrapped}{MARKER_END}\n"
    return f"{MARKER_START}\n{body}\n{MARKER_END}\n"


def _replace_or_append(existing_text, block):
    if not existing_text:
        return block
    if MARKER_PATTERN.search(existing_text):
        return MARKER_PATTERN.sub(block, existing_text)
    if not existing_text.endswith("\n"):
        existing_text += "\n"
    return existing_text + "\n" + block


def _strip_block(existing_text):
    if not existing_text:
        return ""
    return MARKER_PATTERN.sub("", existing_text).rstrip() + "\n"


def install_rule_block(agent, scope=DEFAULT_SCOPE, base_home=None, base_cwd=None, dry_run=False):
    target = get_target_path(agent, scope, base_home=base_home, base_cwd=base_cwd)
    block = render_block(agent)

    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    new_text = _replace_or_append(existing, block)

    if dry_run:
        return {
            "agent": agent,
            "scope": scope,
            "target": str(target),
            "would_write": True,
            "diff_preview": _diff_preview(existing, new_text),
        }

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new_text, encoding="utf-8")
    return {
        "agent": agent,
        "scope": scope,
        "target": str(target),
        "installed": True,
    }


def uninstall_rule_block(agent, scope=DEFAULT_SCOPE, base_home=None, base_cwd=None, dry_run=False):
    target = get_target_path(agent, scope, base_home=base_home, base_cwd=base_cwd)
    if not target.exists():
        return {"agent": agent, "scope": scope, "target": str(target), "removed": False, "reason": "not present"}
    existing = target.read_text(encoding="utf-8")
    if not MARKER_PATTERN.search(existing):
        return {"agent": agent, "scope": scope, "target": str(target), "removed": False, "reason": "no marked block"}
    new_text = _strip_block(existing)
    if dry_run:
        return {"agent": agent, "scope": scope, "target": str(target), "would_remove": True}
    if new_text.strip():
        target.write_text(new_text, encoding="utf-8")
    else:
        target.unlink()
    return {"agent": agent, "scope": scope, "target": str(target), "removed": True}


def install_mcp_config(agent, scope=DEFAULT_SCOPE, base_home=None, base_cwd=None, dry_run=False):
    """Register the omnimem MCP server in the agent's config file."""
    config_path = get_mcp_config_path(agent, scope, base_home=base_home, base_cwd=base_cwd)
    omnimem_command = _detect_omnimem_command()

    if agent in ("claude", "cursor"):
        return _install_mcp_json(config_path, omnimem_command, key_path=("mcpServers",), dry_run=dry_run)
    if agent == "gemini":
        return _install_mcp_json(config_path, omnimem_command, key_path=("mcpServers",), dry_run=dry_run)
    if agent == "codex":
        return _install_mcp_toml_block(config_path, omnimem_command, dry_run=dry_run)
    raise InitError(f"Unsupported agent: {agent}")


def uninstall_mcp_config(agent, scope=DEFAULT_SCOPE, base_home=None, base_cwd=None, dry_run=False):
    config_path = get_mcp_config_path(agent, scope, base_home=base_home, base_cwd=base_cwd)
    if agent in ("claude", "cursor", "gemini"):
        return _uninstall_mcp_json(config_path, key_path=("mcpServers",), dry_run=dry_run)
    if agent == "codex":
        return _uninstall_mcp_toml_block(config_path, dry_run=dry_run)
    raise InitError(f"Unsupported agent: {agent}")


def _detect_omnimem_command():
    """Return command + args needed to launch the OmniMem MCP server.

    Always emit POSIX-style forward slashes in the path so the entry survives
    JSON / TOML round-tripping. Some agent CLIs invoke MCP servers via a shell
    on Windows; bash interprets backslashes as escapes and silently strips
    them, turning `C:\\Users\\foo\\python.exe` into `C:Usersfoopython.exe`.
    Python on Windows accepts forward slashes natively, so this is safe.
    """
    raw = sys.executable or "python"
    return {
        "command": raw.replace("\\", "/"),
        "args": ["-m", "omnimem", "mcp", "serve"],
    }


def _install_mcp_json(path, server_spec, key_path, dry_run=False):
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError as exc:
            raise InitError(f"Cannot parse {path}: {exc}") from exc
    cursor = data
    for key in key_path:
        cursor = cursor.setdefault(key, {})
    cursor["omnimem"] = server_spec

    serialized = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if dry_run:
        return {"target": str(path), "would_write": True, "preview": serialized}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized, encoding="utf-8")
    return {"target": str(path), "installed": True}


def _uninstall_mcp_json(path, key_path, dry_run=False):
    if not path.exists():
        return {"target": str(path), "removed": False, "reason": "not present"}
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError:
        return {"target": str(path), "removed": False, "reason": "invalid json"}

    cursor = data
    for key in key_path[:-1]:
        cursor = cursor.get(key)
        if not isinstance(cursor, dict):
            return {"target": str(path), "removed": False, "reason": "no mcp section"}
    leaf = cursor.get(key_path[-1]) if cursor else None
    if not isinstance(leaf, dict) or "omnimem" not in leaf:
        return {"target": str(path), "removed": False, "reason": "omnimem not registered"}
    leaf.pop("omnimem", None)

    serialized = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if dry_run:
        return {"target": str(path), "would_remove": True}
    path.write_text(serialized, encoding="utf-8")
    return {"target": str(path), "removed": True}


_TOML_BLOCK_PATTERN = re.compile(
    r"\n*\[mcp_servers\.omnimem\][^\[]*",
    re.DOTALL,
)


def _install_mcp_toml_block(path, server_spec, dry_run=False):
    block = _render_codex_toml_block(server_spec)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if _TOML_BLOCK_PATTERN.search(existing):
        new_text = _TOML_BLOCK_PATTERN.sub("\n" + block, existing)
    else:
        if existing and not existing.endswith("\n"):
            existing += "\n"
        new_text = existing + "\n" + block
    if dry_run:
        return {"target": str(path), "would_write": True, "preview": new_text}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_text, encoding="utf-8")
    return {"target": str(path), "installed": True}


def _uninstall_mcp_toml_block(path, dry_run=False):
    if not path.exists():
        return {"target": str(path), "removed": False, "reason": "not present"}
    existing = path.read_text(encoding="utf-8")
    if not _TOML_BLOCK_PATTERN.search(existing):
        return {"target": str(path), "removed": False, "reason": "omnimem not registered"}
    new_text = _TOML_BLOCK_PATTERN.sub("\n", existing).strip() + "\n"
    if dry_run:
        return {"target": str(path), "would_remove": True}
    if new_text.strip():
        path.write_text(new_text, encoding="utf-8")
    else:
        path.unlink()
    return {"target": str(path), "removed": True}


def _render_codex_toml_block(server_spec):
    args_repr = "[" + ", ".join(json.dumps(arg) for arg in server_spec.get("args", [])) + "]"
    return (
        "[mcp_servers.omnimem]\n"
        f"command = {json.dumps(server_spec.get('command', 'python'))}\n"
        f"args = {args_repr}\n"
    )


def _diff_preview(before, after, max_lines=8):
    before_lines = (before or "").splitlines()
    after_lines = after.splitlines()
    head_after = after_lines[:max_lines]
    return {
        "before_length": len(before_lines),
        "after_length": len(after_lines),
        "preview": "\n".join(head_after),
    }


def detect_installed_agents(base_home=None):
    """Return a list of agents whose user-scope config dir already exists."""
    home = Path(base_home) if base_home else _home()
    detected = []
    if (home / ".claude").exists():
        detected.append("claude")
    if (home / ".codex").exists() or (home / "AGENTS.md").exists():
        detected.append("codex")
    if (home / ".gemini").exists():
        detected.append("gemini")
    if (home / ".cursor").exists():
        detected.append("cursor")
    return detected


def status(base_home=None, base_cwd=None):
    """Return a per-agent install status across user and project scopes."""
    report = {}
    for agent in SUPPORTED_AGENTS:
        agent_status = {}
        for scope in ("user", "project"):
            target = get_target_path(agent, scope, base_home=base_home, base_cwd=base_cwd)
            if target.exists():
                text = target.read_text(encoding="utf-8")
                agent_status[scope] = {
                    "target": str(target),
                    "installed": bool(MARKER_PATTERN.search(text)),
                }
            else:
                agent_status[scope] = {"target": str(target), "installed": False}
        report[agent] = agent_status
    return report


def install(
    agents,
    scope=DEFAULT_SCOPE,
    include_mcp=True,
    base_home=None,
    base_cwd=None,
    dry_run=False,
):
    """Install rule blocks (and optionally MCP config) for one or more agents."""
    if "all" in agents:
        agents = list(SUPPORTED_AGENTS)
    if not agents:
        raise InitError("No agents specified")

    results = []
    for agent in agents:
        if agent not in SUPPORTED_AGENTS:
            raise InitError(f"Unsupported agent: {agent}")
        rule_result = install_rule_block(
            agent,
            scope=scope,
            base_home=base_home,
            base_cwd=base_cwd,
            dry_run=dry_run,
        )
        record = {"agent": agent, "rule": rule_result}
        if include_mcp:
            try:
                mcp_result = install_mcp_config(
                    agent,
                    scope=scope,
                    base_home=base_home,
                    base_cwd=base_cwd,
                    dry_run=dry_run,
                )
                record["mcp"] = mcp_result
            except InitError as exc:
                record["mcp"] = {"installed": False, "reason": str(exc)}
        results.append(record)
    return results


def uninstall(
    agents,
    scope=DEFAULT_SCOPE,
    include_mcp=True,
    base_home=None,
    base_cwd=None,
    dry_run=False,
):
    if "all" in agents:
        agents = list(SUPPORTED_AGENTS)
    if not agents:
        raise InitError("No agents specified")

    results = []
    for agent in agents:
        if agent not in SUPPORTED_AGENTS:
            raise InitError(f"Unsupported agent: {agent}")
        rule_result = uninstall_rule_block(
            agent,
            scope=scope,
            base_home=base_home,
            base_cwd=base_cwd,
            dry_run=dry_run,
        )
        record = {"agent": agent, "rule": rule_result}
        if include_mcp:
            try:
                mcp_result = uninstall_mcp_config(
                    agent,
                    scope=scope,
                    base_home=base_home,
                    base_cwd=base_cwd,
                    dry_run=dry_run,
                )
                record["mcp"] = mcp_result
            except InitError as exc:
                record["mcp"] = {"removed": False, "reason": str(exc)}
        results.append(record)
    return results

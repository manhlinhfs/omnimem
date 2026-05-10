"""Interactive `omnimem quickstart` wizard.

Detects which agent CLIs the user already has, walks them through installing
the OmniMem rule block + MCP registration + lifecycle hooks for each one,
seeds a welcome note, and prints concrete next steps.

The wizard is fully scripted — pass `--yes` to accept every default and run
non-interactively (useful from `install.sh`).
"""

import sys
from pathlib import Path

from omnimem.paths import SOURCE_ROOT


def _supports_unicode(stream):
    encoding = getattr(stream, "encoding", "") or ""
    return "utf" in encoding.lower()


def _tick(stream=None):
    return "✓" if _supports_unicode(stream or sys.stdout) else "[OK]"


def _cross(stream=None):
    return "✗" if _supports_unicode(stream or sys.stdout) else "[--]"


def _arrow(stream=None):
    return "→" if _supports_unicode(stream or sys.stdout) else "->"


def _prompt_yes_no(question, default=True, assume_yes=False, stream=None):
    stream = stream or sys.stdout
    if assume_yes:
        return True
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        stream.write(f"{question} {suffix} ")
        stream.flush()
        try:
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            stream.write("\n")
            return False
        if not line:
            return default
        answer = line.strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False


def detect_agents(home=None):
    """Return ordered list of agent ids whose user-scope config dir exists."""
    base = Path(home) if home else Path.home()
    detected = []
    if (base / ".claude").exists():
        detected.append("claude")
    if (base / ".codex").exists() or (base / "AGENTS.md").exists():
        detected.append("codex")
    if (base / ".gemini").exists():
        detected.append("gemini")
    if (base / ".cursor").exists():
        detected.append("cursor")
    return detected


def _seed_welcome_note(root_dir=SOURCE_ROOT):
    from omnimem.note import create_note, list_notes
    from omnimem.note_index import index_note_record
    from omnimem.vault import ensure_vault_layout

    ensure_vault_layout(root_dir=root_dir)
    if list_notes(root_dir=root_dir, limit=1):
        return None

    body = (
        "Welcome to OmniMem.\n\n"
        "This vault is plain Markdown. You can edit it in Obsidian or any text editor.\n\n"
        "Try these next:\n"
        "- `omnimem note new \"My first decision\" --type decision`\n"
        "- `omnimem note search \"<query>\"`\n"
        "- `omnimem search \"<query>\" --all` (federated across documents + notes + codemap)\n\n"
        "Linked: [[next-steps]].\n"
    )
    record = create_note(
        "OmniMem welcome note",
        body=body,
        note_type="reference",
        tags="welcome,getting-started",
        agent="quickstart",
        root_dir=root_dir,
    )
    try:
        index_note_record(
            record["frontmatter"],
            body,
            record["path"],
            root_dir=root_dir,
        )
    except Exception:
        pass
    return record


def run(
    assume_yes=False,
    install_hooks=True,
    seed_note=True,
    home=None,
    cwd=None,
    stdout=None,
):
    """Run the interactive wizard. Returns a result dict."""
    out = stdout or sys.stdout

    detected = detect_agents(home=home)
    out.write("\n=== OmniMem Quickstart ===\n\n")
    if detected:
        out.write("Detected agent CLIs:\n")
        for agent in detected:
            out.write(f"  {_tick(out)} {agent}\n")
    else:
        out.write(
            "No agent CLI config directories detected (~/.claude, ~/.codex, ~/.gemini, ~/.cursor).\n"
            "OmniMem will still install for whichever agents you choose.\n"
        )

    install_results = []
    hook_results = []

    if not detected and not assume_yes:
        out.write("\nSkipping integration steps because no agents were detected.\n")
        return {
            "detected": [],
            "init": [],
            "hook": [],
            "welcome_note": None,
        }

    targets = detected if detected else []
    if not detected and assume_yes:
        targets = ["claude", "codex", "gemini", "cursor"]
        out.write("\n--yes was passed, installing for all four agents.\n")

    if not _prompt_yes_no(
        f"\n{_arrow(out)} Install OmniMem rule block + MCP server registration for: {', '.join(targets)}?",
        default=True,
        assume_yes=assume_yes,
        stream=out,
    ):
        out.write("Skipped init.\n")
    else:
        from omnimem.init import install as init_install

        try:
            install_results = init_install(
                targets,
                scope="user",
                include_mcp=True,
                base_home=str(home) if home else None,
                base_cwd=str(cwd) if cwd else None,
            )
            out.write(f"  {_tick(out)} Installed init for {len(install_results)} agent(s).\n")
        except Exception as exc:
            out.write(f"  {_cross(out)} init failed: {exc}\n")

    if install_hooks:
        hook_targets = [agent for agent in targets if agent in ("claude", "codex")]
        if hook_targets:
            if _prompt_yes_no(
                f"\n{_arrow(out)} Install lifecycle hooks (SessionStart / Stop / PostToolUse) for: {', '.join(hook_targets)}?",
                default=True,
                assume_yes=assume_yes,
                stream=out,
            ):
                from omnimem.hooks import install as hook_install

                try:
                    hook_results = hook_install(
                        hook_targets,
                        scope="user",
                        base_home=str(home) if home else None,
                        base_cwd=str(cwd) if cwd else None,
                    )
                    out.write(f"  {_tick(out)} Installed hooks for {len(hook_results)} agent(s).\n")
                except Exception as exc:
                    out.write(f"  {_cross(out)} hook installation failed: {exc}\n")
            else:
                out.write("Skipped hook installation.\n")

    welcome_record = None
    if seed_note:
        if _prompt_yes_no(
            f"\n{_arrow(out)} Seed a welcome note in your vault so search has something to find?",
            default=True,
            assume_yes=assume_yes,
            stream=out,
        ):
            try:
                welcome_record = _seed_welcome_note()
                if welcome_record is None:
                    out.write(f"  {_tick(out)} Vault already has notes; skipped seeding.\n")
                else:
                    out.write(f"  {_tick(out)} Seeded note `{welcome_record['slug']}`.\n")
            except Exception as exc:
                out.write(f"  {_cross(out)} seed failed: {exc}\n")
        else:
            out.write("Skipped welcome note.\n")

    out.write("\n=== Next steps ===\n")
    out.write("  1. Restart your agent CLI(s) so the new MCP server and rule block are picked up.\n")
    out.write("  2. Inside the agent, ask any project-specific question. The agent should call `note_search` first.\n")
    out.write("  3. Run `omnimem doctor` if anything looks off.\n")
    out.write("  4. Read QUICKSTART.md for direct CLI usage.\n\n")

    return {
        "detected": detected,
        "init": install_results,
        "hook": hook_results,
        "welcome_note": welcome_record,
    }

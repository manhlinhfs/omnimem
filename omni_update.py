import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from omni_paths import SOURCE_ROOT, detect_install_mode
from omni_version import add_version_argument, get_version, get_version_banner

ROOT_DIR = SOURCE_ROOT


class UpdateError(RuntimeError):
    pass


def run_command(cmd, cwd=None, check=True):
    if cwd is None:
        cwd = ROOT_DIR
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise UpdateError(f"Required command is missing: {cmd[0]}") from exc
    if check and result.returncode != 0:
        raise UpdateError(result.stderr.strip() or result.stdout.strip() or "Command failed")
    return result


def git(*args, root_dir=ROOT_DIR, check=True):
    return run_command(["git", *args], cwd=root_dir, check=check)


def get_current_branch(root_dir=ROOT_DIR):
    return git("rev-parse", "--abbrev-ref", "HEAD", root_dir=root_dir).stdout.strip()


def get_upstream(root_dir=ROOT_DIR):
    result = git(
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{u}",
        root_dir=root_dir,
        check=False,
    )
    if result.returncode != 0:
        raise UpdateError(
            "This branch has no upstream configured. Set a tracked remote branch before running omni_update.py."
        )
    return result.stdout.strip()


def get_head_commit(ref="HEAD", root_dir=ROOT_DIR):
    return git("rev-parse", ref, root_dir=root_dir).stdout.strip()


def get_worktree_status(root_dir=ROOT_DIR):
    return git("status", "--short", root_dir=root_dir).stdout.strip()


def fetch_remote(remote, root_dir=ROOT_DIR):
    git("fetch", "--tags", remote, root_dir=root_dir)


def get_ahead_behind(upstream, root_dir=ROOT_DIR):
    counts = git("rev-list", "--left-right", "--count", f"HEAD...{upstream}", root_dir=root_dir).stdout.strip()
    ahead_str, behind_str = counts.split()
    return int(ahead_str), int(behind_str)


def get_version_for_ref(ref, root_dir=ROOT_DIR):
    result = git("show", f"{ref}:VERSION", root_dir=root_dir, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def get_changed_files(old_ref, new_ref, root_dir=ROOT_DIR):
    output = git("diff", "--name-only", old_ref, new_ref, root_dir=root_dir).stdout.strip()
    if not output:
        return []
    return output.splitlines()


def reinstall_dependencies(root_dir=ROOT_DIR):
    run_command(
        [sys.executable, "-m", "pip", "install", "-r", str(Path(root_dir) / "requirements.txt")],
        cwd=root_dir,
    )


def bootstrap_model(root_dir=ROOT_DIR, allow_model_download=False):
    cmd = [sys.executable, str(Path(root_dir) / "omni_bootstrap.py"), "--offline-only"]
    result = run_command(cmd, cwd=root_dir, check=False)
    if result.returncode == 0:
        return {
            "name": "bootstrap",
            "status": "pass",
            "detail": "Model bootstrap check succeeded in offline mode",
        }

    if allow_model_download or os.getenv("OMNIMEM_ALLOW_MODEL_DOWNLOAD", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        run_command([sys.executable, str(Path(root_dir) / "omni_bootstrap.py")], cwd=root_dir)
        return {
            "name": "bootstrap",
            "status": "pass",
            "detail": "Model bootstrap succeeded with download enabled",
        }

    return {
        "name": "bootstrap",
        "status": "warn",
        "detail": (
            "Model bootstrap refresh did not complete in offline mode. "
            "Run `python3 omni_bootstrap.py` if this clone needs a fresh model download."
        ),
    }


def build_install_mode_guidance(mode):
    if mode == "package_install":
        return (
            "This OmniMem install is running from a Python package, not a git clone. "
            "Self-update is only supported for git clones. Reinstall or upgrade with pip instead, "
            "for example `python -m pip install --upgrade .` from a newer source tree or "
            "`python -m pip install --upgrade git+https://github.com/manhlinhfs/omnimem.git`."
        )
    return (
        "This OmniMem copy is a source tree without git metadata. Self-update is only supported "
        "for tracked git clones. Download a newer source tree or reclone the repository."
    )


def inspect_update_state(root_dir=ROOT_DIR, site_roots=None):
    install_mode_report = detect_install_mode(root_dir=root_dir, site_roots=site_roots)
    report = {
        "tool": "omni_update",
        "current_version": get_version(),
        "install_mode": install_mode_report["mode"],
        "install_mode_detail": install_mode_report["detail"],
        "root_dir": str(Path(root_dir).resolve()),
    }

    if install_mode_report["mode"] != "git_clone":
        report.update(
            {
                "status": "unsupported_install_mode",
                "detail": build_install_mode_guidance(install_mode_report["mode"]),
            }
        )
        return report

    branch = get_current_branch(root_dir=root_dir)
    if branch == "HEAD":
        raise UpdateError("Detached HEAD is not supported. Check out a branch before updating.")

    upstream = get_upstream(root_dir=root_dir)
    remote = upstream.split("/", 1)[0]
    fetch_remote(remote, root_dir=root_dir)

    head = get_head_commit("HEAD", root_dir=root_dir)
    upstream_head = get_head_commit(upstream, root_dir=root_dir)
    ahead, behind = get_ahead_behind(upstream, root_dir=root_dir)
    local_version = get_version()
    upstream_version = get_version_for_ref(upstream, root_dir=root_dir)

    if ahead > 0 and behind > 0:
        status = "diverged"
    elif ahead > 0:
        status = "ahead"
    elif behind > 0:
        status = "update_available"
    else:
        status = "up_to_date"

    report.update(
        {
            "current_version": local_version,
            "upstream_version": upstream_version,
            "branch": branch,
            "upstream": upstream,
            "head": head,
            "upstream_head": upstream_head,
            "ahead": ahead,
            "behind": behind,
            "status": status,
        }
    )
    return report


def perform_update(root_dir=ROOT_DIR, skip_deps=False, skip_bootstrap=False, allow_model_download=False):
    report = inspect_update_state(root_dir=root_dir)
    if report["status"] == "unsupported_install_mode":
        raise UpdateError(report["detail"])

    status = get_worktree_status(root_dir=root_dir)
    if status:
        raise UpdateError(
            "Working tree is not clean. Commit, stash, or remove local changes before running omni_update.py."
        )

    if report["status"] == "diverged":
        raise UpdateError(
            f"Local branch '{report['branch']}' has diverged from {report['upstream']}. Resolve it manually first."
        )
    if report["status"] == "ahead":
        raise UpdateError(
            f"Local branch '{report['branch']}' is ahead of {report['upstream']}. Push or reset it manually first."
        )
    if report["status"] == "up_to_date":
        report["update_performed"] = False
        report["post_update_steps"] = []
        return report

    old_head = report["head"]
    old_version = report["current_version"]
    git("merge", "--ff-only", report["upstream"], root_dir=root_dir)
    new_head = get_head_commit("HEAD", root_dir=root_dir)
    new_version = get_version()
    changed_files = get_changed_files(old_head, new_head, root_dir=root_dir)
    post_update_steps = []

    if "requirements.txt" in changed_files and not skip_deps:
        reinstall_dependencies(root_dir=root_dir)
        post_update_steps.append({"name": "dependencies", "status": "pass", "detail": "requirements.txt reinstalled"})
    elif "requirements.txt" in changed_files:
        post_update_steps.append({"name": "dependencies", "status": "warn", "detail": "requirements.txt changed but reinstall was skipped"})

    if not skip_bootstrap:
        post_update_steps.append(
            bootstrap_model(root_dir=root_dir, allow_model_download=allow_model_download)
        )

    report.update(
        {
            "update_performed": True,
            "previous_head": old_head,
            "previous_version": old_version,
            "head": new_head,
            "current_version": new_version,
            "changed_files": changed_files,
            "post_update_steps": post_update_steps,
            "status": "updated",
        }
    )
    return report


def print_human_report(report):
    print(get_version_banner())
    print(f"Install mode: {report.get('install_mode', 'unknown')}")
    print(f"Install detail: {report.get('install_mode_detail', 'unknown')}")

    if report["status"] == "unsupported_install_mode":
        print(f"Status: {report['status']}")
        print("")
        print(report["detail"])
        return

    print(f"Branch: {report['branch']}")
    print(f"Upstream: {report['upstream']}")
    print(f"Local version: {report.get('current_version')}")
    print(f"Upstream version: {report.get('upstream_version') or 'unknown'}")
    print(f"Local commit: {report.get('head')}")
    print(f"Upstream commit: {report.get('upstream_head')}")
    print(f"Status: {report['status']}")

    if report.get("update_performed"):
        print("")
        print(f"Updated from {report.get('previous_version')} ({report.get('previous_head')})")
        print(f"to {report.get('current_version')} ({report.get('head')})")
        changed_files = report.get("changed_files", [])
        print(f"Changed files: {len(changed_files)}")
        for item in report.get("post_update_steps", []):
            name = item.get("name", "post_update")
            print(f"[{item['status'].upper():4}] {name}: {item['detail']}")
    elif report["status"] == "up_to_date":
        print("")
        print("This clone is already up to date.")
    elif report["status"] == "update_available":
        print("")
        print(f"Update available: behind by {report['behind']} commit(s). Run `python3 omni_update.py` to apply it.")


def main():
    parser = argparse.ArgumentParser(
        description="Update the current OmniMem install safely using fast-forward only semantics"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only inspect whether an update is available",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the update report as JSON",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip reinstalling requirements even if requirements.txt changed",
    )
    parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Skip the post-update model bootstrap check",
    )
    parser.add_argument(
        "--allow-model-download",
        action="store_true",
        help="Allow omni_update.py to download the embedding model if offline bootstrap is insufficient",
    )
    add_version_argument(parser)
    args = parser.parse_args()

    try:
        report = inspect_update_state() if args.check else perform_update(
            skip_deps=args.skip_deps,
            skip_bootstrap=args.skip_bootstrap,
            allow_model_download=args.allow_model_download,
        )
    except UpdateError as exc:
        if args.json:
            print(json.dumps({"tool": "omni_update", "status": "fail", "detail": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}")
        sys.exit(1)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    print_human_report(report)


if __name__ == "__main__":
    main()

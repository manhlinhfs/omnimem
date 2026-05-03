import os
import site
import sys
import sysconfig
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent


def _is_relative_to(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _dedupe_paths(paths):
    unique = []
    seen = set()
    for path in paths:
        if not path:
            continue
        resolved = Path(path).expanduser().resolve()
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        unique.append(resolved)
    return unique


def get_site_package_roots():
    roots = []
    for key in ("purelib", "platlib"):
        value = sysconfig.get_path(key)
        if value:
            roots.append(value)

    try:
        user_site = site.getusersitepackages()
    except Exception:
        user_site = None
    if user_site:
        roots.append(user_site)

    return _dedupe_paths(roots)


def detect_install_mode(root_dir=SOURCE_ROOT, site_roots=None):
    candidate = Path(root_dir).expanduser().resolve()
    if (candidate / ".git").exists():
        return {
            "mode": "git_clone",
            "detail": f"Running from a git clone at {candidate}",
        }

    roots = get_site_package_roots() if site_roots is None else _dedupe_paths(site_roots)
    for site_root in roots:
        if _is_relative_to(candidate, site_root):
            return {
                "mode": "package_install",
                "detail": f"Running from an installed Python package at {candidate}",
            }

    return {
        "mode": "source_tree",
        "detail": f"Running from a source tree without git metadata at {candidate}",
    }


def get_default_user_data_root():
    override = os.getenv("OMNIMEM_HOME")
    if override:
        return Path(override).expanduser()
    # Single neutral location across all OSes. Trades XDG / AppData / Library
    # convention for portability and ease of discovery — users find their
    # vault, db, and models in one obvious place regardless of platform.
    return Path.home() / ".omnimem"


def get_default_user_config_root():
    override = os.getenv("OMNIMEM_CONFIG_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".omnimem"


def _resolve_runtime_config(root_dir=SOURCE_ROOT, site_roots=None, user_data_root=None):
    from omni_config import resolve_runtime_config

    return resolve_runtime_config(
        root_dir=root_dir,
        site_roots=site_roots,
        user_data_root=user_data_root,
    )


def get_runtime_home(root_dir=SOURCE_ROOT, install_mode_report=None, site_roots=None, user_data_root=None):
    if install_mode_report is not None:
        config = _resolve_runtime_config(
            root_dir=root_dir,
            site_roots=site_roots,
            user_data_root=user_data_root,
        )
        return Path(config["values"]["home"]).expanduser()

    config = _resolve_runtime_config(
        root_dir=root_dir,
        site_roots=site_roots,
        user_data_root=user_data_root,
    )
    return Path(config["values"]["home"]).expanduser()


def get_db_dir(root_dir=SOURCE_ROOT, install_mode_report=None, site_roots=None, user_data_root=None):
    config = _resolve_runtime_config(
        root_dir=root_dir,
        site_roots=site_roots,
        user_data_root=user_data_root,
    )
    return Path(config["values"]["db_dir"]).expanduser()


def get_models_root(root_dir=SOURCE_ROOT, install_mode_report=None, site_roots=None, user_data_root=None):
    config = _resolve_runtime_config(
        root_dir=root_dir,
        site_roots=site_roots,
        user_data_root=user_data_root,
    )
    return Path(config["values"]["models_dir"]).expanduser()


def get_bootstrap_command(root_dir=SOURCE_ROOT, install_mode_report=None, site_roots=None):
    report = install_mode_report or detect_install_mode(root_dir=root_dir, site_roots=site_roots)
    if report["mode"] == "package_install":
        return "omnimem bootstrap"
    return f"python {Path(root_dir).expanduser().resolve() / 'omni_bootstrap.py'}"

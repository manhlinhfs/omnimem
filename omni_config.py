import json
import os
import sys
from pathlib import Path

from omni_paths import (
    SOURCE_ROOT,
    _dedupe_paths,
    detect_install_mode,
    get_default_user_config_root,
    get_default_user_data_root,
)

CONFIG_ENV_VAR = "OMNIMEM_CONFIG"
CONFIG_FILE_NAME = "omnimem.json"
USER_CONFIG_FILE_NAME = "config.json"


class ConfigError(RuntimeError):
    pass


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ConfigError(f"Expected a boolean value, got {value!r}")


def _coerce_int(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip())
        except ValueError as exc:
            raise ConfigError(f"Expected an integer value, got {value!r}") from exc
    raise ConfigError(f"Expected an integer value, got {value!r}")


def _coerce_path(value):
    if value is None:
        raise ConfigError("Expected a filesystem path, got null")
    if isinstance(value, (str, os.PathLike)):
        return Path(value).expanduser()
    raise ConfigError(f"Expected a filesystem path, got {value!r}")


def _load_config_payload(path):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Failed to parse JSON config at '{path}': {exc}") from exc

    if not isinstance(payload, dict):
        raise ConfigError(f"Config file '{path}' must contain a top-level JSON object")
    return payload


def get_preferred_config_path(root_dir=SOURCE_ROOT, install_mode_report=None, site_roots=None):
    explicit = os.getenv(CONFIG_ENV_VAR)
    if explicit:
        return Path(explicit).expanduser()

    report = install_mode_report or detect_install_mode(root_dir=root_dir, site_roots=site_roots)
    if report["mode"] == "package_install":
        return get_default_user_config_root() / USER_CONFIG_FILE_NAME
    return Path(root_dir).expanduser().resolve() / CONFIG_FILE_NAME


def get_config_candidates(root_dir=SOURCE_ROOT, install_mode_report=None, site_roots=None):
    explicit = os.getenv(CONFIG_ENV_VAR)
    if explicit:
        return [Path(explicit).expanduser()]

    report = install_mode_report or detect_install_mode(root_dir=root_dir, site_roots=site_roots)
    candidates = []
    if report["mode"] != "package_install":
        candidates.append(Path(root_dir).expanduser().resolve() / CONFIG_FILE_NAME)
    candidates.append(get_default_user_config_root() / USER_CONFIG_FILE_NAME)
    return _dedupe_paths(candidates)


def discover_config(root_dir=SOURCE_ROOT, install_mode_report=None, site_roots=None):
    report = install_mode_report or detect_install_mode(root_dir=root_dir, site_roots=site_roots)
    candidates = get_config_candidates(
        root_dir=root_dir,
        install_mode_report=report,
        site_roots=site_roots,
    )
    preferred_path = get_preferred_config_path(
        root_dir=root_dir,
        install_mode_report=report,
        site_roots=site_roots,
    )

    selected_path = None
    selected_source = "none"
    payload = {}
    error = None

    explicit = os.getenv(CONFIG_ENV_VAR)
    if explicit:
        selected_path = Path(explicit).expanduser()
        selected_source = f"env:{CONFIG_ENV_VAR}"
        if selected_path.exists():
            try:
                payload = _load_config_payload(selected_path)
            except ConfigError as exc:
                error = str(exc)
        return {
            "selected_path": str(selected_path),
            "selected_source": selected_source,
            "preferred_path": str(preferred_path),
            "loaded": error is None and selected_path.exists(),
            "exists": selected_path.exists(),
            "payload": payload,
            "error": error,
            "candidates": [str(path) for path in candidates],
        }

    for candidate in candidates:
        if candidate.exists():
            selected_path = candidate
            if candidate == Path(root_dir).expanduser().resolve() / CONFIG_FILE_NAME:
                selected_source = "repo_local"
            else:
                selected_source = "user_config"
            try:
                payload = _load_config_payload(candidate)
            except ConfigError as exc:
                error = str(exc)
            break

    return {
        "selected_path": str(selected_path) if selected_path else None,
        "selected_source": selected_source,
        "preferred_path": str(preferred_path),
        "loaded": error is None and selected_path is not None,
        "exists": selected_path is not None,
        "payload": payload,
        "error": error,
        "candidates": [str(path) for path in candidates],
    }


def _setting(name, value, source, env_var=None):
    return {
        "name": name,
        "value": value,
        "source": source,
        "env_var": env_var,
    }


def resolve_runtime_config(
    root_dir=SOURCE_ROOT,
    site_roots=None,
    user_data_root=None,
    overrides=None,
    config_report=None,
    ignore_errors=False,
):
    overrides = overrides or {}
    install_mode_report = detect_install_mode(root_dir=root_dir, site_roots=site_roots)
    config_report = config_report or discover_config(
        root_dir=root_dir,
        install_mode_report=install_mode_report,
        site_roots=site_roots,
    )
    if config_report.get("error") and not ignore_errors:
        raise ConfigError(config_report["error"])
    payload = config_report.get("payload") or {}
    config_label = (
        f"config:{config_report['selected_path']}"
        if config_report.get("selected_path")
        else "config"
    )

    if overrides.get("home") is not None:
        home = _coerce_path(overrides["home"])
        home_setting = _setting("home", home, "override")
    elif os.getenv("OMNIMEM_HOME"):
        home = _coerce_path(os.getenv("OMNIMEM_HOME"))
        home_setting = _setting("home", home, "env:OMNIMEM_HOME", env_var="OMNIMEM_HOME")
    elif payload.get("home") is not None:
        home = _coerce_path(payload.get("home"))
        home_setting = _setting("home", home, config_label)
    else:
        if install_mode_report["mode"] == "package_install":
            home = Path(user_data_root).expanduser() if user_data_root is not None else get_default_user_data_root()
            source = "default:package_install"
        else:
            home = Path(root_dir).expanduser().resolve()
            source = f"default:{install_mode_report['mode']}"
        home_setting = _setting("home", home, source)

    if overrides.get("db_dir") is not None:
        db_dir = _coerce_path(overrides["db_dir"])
        db_dir_setting = _setting("db_dir", db_dir, "override")
    elif os.getenv("OMNIMEM_DB_DIR"):
        db_dir = _coerce_path(os.getenv("OMNIMEM_DB_DIR"))
        db_dir_setting = _setting("db_dir", db_dir, "env:OMNIMEM_DB_DIR", env_var="OMNIMEM_DB_DIR")
    elif payload.get("db_dir") is not None:
        db_dir = _coerce_path(payload.get("db_dir"))
        db_dir_setting = _setting("db_dir", db_dir, config_label)
    else:
        db_dir = home / ".omnimem_db"
        db_dir_setting = _setting("db_dir", db_dir, f"derived:{home_setting['source']}")

    if overrides.get("models_dir") is not None:
        models_dir = _coerce_path(overrides["models_dir"])
        models_dir_setting = _setting("models_dir", models_dir, "override")
    elif os.getenv("OMNIMEM_MODELS_DIR"):
        models_dir = _coerce_path(os.getenv("OMNIMEM_MODELS_DIR"))
        models_dir_setting = _setting(
            "models_dir",
            models_dir,
            "env:OMNIMEM_MODELS_DIR",
            env_var="OMNIMEM_MODELS_DIR",
        )
    elif payload.get("models_dir") is not None:
        models_dir = _coerce_path(payload.get("models_dir"))
        models_dir_setting = _setting("models_dir", models_dir, config_label)
    else:
        models_dir = home / ".omnimem_models"
        models_dir_setting = _setting("models_dir", models_dir, f"derived:{home_setting['source']}")

    if overrides.get("allow_model_download") is not None:
        allow_model_download = _coerce_bool(overrides["allow_model_download"])
        allow_model_download_setting = _setting("allow_model_download", allow_model_download, "override")
    elif os.getenv("OMNIMEM_ALLOW_MODEL_DOWNLOAD") is not None:
        allow_model_download = _coerce_bool(os.getenv("OMNIMEM_ALLOW_MODEL_DOWNLOAD"))
        allow_model_download_setting = _setting(
            "allow_model_download",
            allow_model_download,
            "env:OMNIMEM_ALLOW_MODEL_DOWNLOAD",
            env_var="OMNIMEM_ALLOW_MODEL_DOWNLOAD",
        )
    elif payload.get("allow_model_download") is not None:
        allow_model_download = _coerce_bool(payload.get("allow_model_download"))
        allow_model_download_setting = _setting(
            "allow_model_download",
            allow_model_download,
            config_label,
        )
    else:
        allow_model_download = False
        allow_model_download_setting = _setting("allow_model_download", allow_model_download, "default:false")

    if overrides.get("async_extract_timeout_seconds") is not None:
        async_timeout = _coerce_int(overrides["async_extract_timeout_seconds"])
        async_timeout_setting = _setting("async_extract_timeout_seconds", async_timeout, "override")
    elif os.getenv("OMNIMEM_ASYNC_EXTRACT_TIMEOUT") is not None:
        async_timeout = _coerce_int(os.getenv("OMNIMEM_ASYNC_EXTRACT_TIMEOUT"))
        async_timeout_setting = _setting(
            "async_extract_timeout_seconds",
            async_timeout,
            "env:OMNIMEM_ASYNC_EXTRACT_TIMEOUT",
            env_var="OMNIMEM_ASYNC_EXTRACT_TIMEOUT",
        )
    elif payload.get("async_extract_timeout_seconds") is not None:
        async_timeout = _coerce_int(payload.get("async_extract_timeout_seconds"))
        async_timeout_setting = _setting(
            "async_extract_timeout_seconds",
            async_timeout,
            config_label,
        )
    else:
        async_timeout = 20
        async_timeout_setting = _setting("async_extract_timeout_seconds", async_timeout, "default:20")

    settings = {
        "home": home_setting,
        "db_dir": db_dir_setting,
        "models_dir": models_dir_setting,
        "allow_model_download": allow_model_download_setting,
        "async_extract_timeout_seconds": async_timeout_setting,
    }

    return {
        "install_mode": install_mode_report,
        "config": config_report,
        "settings": settings,
        "values": {name: item["value"] for name, item in settings.items()},
    }


def serialize_runtime_config(report):
    config = dict(report.get("config") or {})
    settings = {}
    for name, item in (report.get("settings") or {}).items():
        value = item.get("value")
        if isinstance(value, Path):
            value = str(value)
        settings[name] = {
            "value": value,
            "source": item.get("source"),
            "env_var": item.get("env_var"),
        }
    return {
        "install_mode": report.get("install_mode"),
        "config": config,
        "settings": settings,
    }


def get_allow_model_download(root_dir=SOURCE_ROOT):
    return bool(resolve_runtime_config(root_dir=root_dir)["values"]["allow_model_download"])


def get_async_extract_timeout_seconds(root_dir=SOURCE_ROOT):
    return int(resolve_runtime_config(root_dir=root_dir)["values"]["async_extract_timeout_seconds"])


if __name__ == "__main__":
    report = serialize_runtime_config(resolve_runtime_config())
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    print()

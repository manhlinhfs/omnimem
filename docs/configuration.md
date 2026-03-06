# Configuration

OmniMem v1.7.0 adds a shared JSON config layer so users can move runtime paths without editing code.

## Supported settings

```json
{
  "home": "/absolute/path/to/omnimem-runtime",
  "db_dir": "/absolute/path/to/omnimem-db",
  "models_dir": "/absolute/path/to/omnimem-models",
  "allow_model_download": false,
  "async_extract_timeout_seconds": 20
}
```

## Setting precedence

For runtime settings, OmniMem resolves values in this order:

1. Environment variables
2. Config file values
3. Install-mode defaults

Operation-specific CLI flags such as `--output`, `--overwrite`, and `--force` override only that command invocation.

## Config file discovery

OmniMem checks config files in this order:

1. `OMNIMEM_CONFIG` if it is set
2. `omnimem.json` in the repo root for git-clone or source-tree installs
3. The user config file for package installs or shared user config

Default user config paths:

- Linux: `~/.config/omnimem/config.json`
- macOS: `~/Library/Application Support/omnimem/config.json`
- Windows: `%APPDATA%\\omnimem\\config.json`

## Environment variables

- `OMNIMEM_CONFIG`
- `OMNIMEM_CONFIG_HOME`
- `OMNIMEM_HOME`
- `OMNIMEM_DB_DIR`
- `OMNIMEM_MODELS_DIR`
- `OMNIMEM_ALLOW_MODEL_DOWNLOAD`
- `OMNIMEM_ASYNC_EXTRACT_TIMEOUT`

## Inspect effective config

```bash
./omnimem doctor
./omnimem doctor --json
```

`doctor` now reports which source supplied each runtime setting.

## Example workflow

1. Copy `omnimem.example.json` to `omnimem.json`
2. Edit the paths you want to move
3. Run `./omnimem doctor` to confirm the effective config

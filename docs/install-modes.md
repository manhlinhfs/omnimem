# Install Modes

OmniMem now supports two primary install modes.

## Git clone mode

Use this when you want the repo launchers, local scripts, and built-in self-update flow.

```bash
git clone https://github.com/manhlinhfs/omnimem.git
cd omnimem
./setup.sh
```

Characteristics:
- Runtime data lives inside the repo by default: `.omnimem_db/` and `.omnimem_models/`
- Use `./omnimem ...` from the repo root
- `./omnimem update` is supported

## Package install mode

Use this when you want a normal Python command on your PATH.

```bash
python3 -m pip install .
```

Or install directly from GitHub:

```bash
python3 -m pip install "git+https://github.com/manhlinhfs/omnimem.git@main"
```

Characteristics:
- Runtime data lives in a user data directory instead of `site-packages`
- The command is available as `omnimem`
- `omnimem update` is not supported because installed packages are not tracked git clones

Default runtime data locations for package installs:
- Linux: `~/.local/share/omnimem/`
- macOS: `~/Library/Application Support/omnimem/`
- Windows: `%LOCALAPPDATA%\omnimem\`

## Environment overrides

You can override the default runtime paths with environment variables:
- `OMNIMEM_HOME`
- `OMNIMEM_DB_DIR`
- `OMNIMEM_MODELS_DIR`
- `OMNIMEM_MODEL_DIR`

## Update behavior

- Git clone mode: `omnimem update` performs a fast-forward update on the tracked branch
- Package install mode: reinstall or upgrade with `pip`; OmniMem reports this clearly instead of trying to mutate `site-packages`
- Source tree without `.git`: self-update is also unsupported; download a newer source tree or reclone

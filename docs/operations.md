# Operations

OmniMem v1.7.0 adds runtime operations for backup, export, and restore.

## Backup

Create a compressed runtime snapshot:

```bash
./omnimem backup
./omnimem backup --output /tmp/omnimem-backup.tar.gz
./omnimem backup --no-models
```

By default, backups include:

- the ChromaDB directory
- the local model directory
- the active config file if one is loaded

## Export

Export the collection to a portable JSON file:

```bash
./omnimem export
./omnimem export --output /tmp/omnimem-export.json
```

This format is useful when you want a structured, portable copy of the memories without copying the raw DB files.

## Restore

Restore from either a backup archive or an export JSON file:

```bash
./omnimem restore /tmp/omnimem-backup.tar.gz
./omnimem restore /tmp/omnimem-export.json
./omnimem restore /tmp/omnimem-export.json --force
```

Behavior:

- backup restore copies raw runtime files back into the effective OmniMem paths
- export restore recreates the Chroma collection and re-adds documents with their saved metadata and ids
- `--force` is required when the target already contains data

## Standalone script

The same operations are available through:

```bash
python3 omni_ops.py backup
python3 omni_ops.py export
python3 omni_ops.py restore /path/to/file
```

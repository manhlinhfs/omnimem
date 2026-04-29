# Reindexing

OmniMem v1.8.0 adds a supported reindex workflow for users who already imported files with older chunking strategies.

## Why reindex

Older versions stored imported documents using blank-line chunking. That still works, but the new chunker produces better retrieval behavior for many document and code shapes.

Reindexing lets you rebuild imported chunks in place without wiping the whole collection.

## Dry run first

```bash
./omnimem reindex --dry-run
./omnimem reindex --source handoff.md --dry-run
```

This shows how many import groups and chunks would be rebuilt.

## Apply reindexing

```bash
./omnimem reindex
./omnimem reindex --source handoff.md
```

Behavior:
- imports are grouped by import batch metadata from the current DB
- each group is reconstructed and rechunked using the current strategy
- non-import memories are preserved as-is
- a JSON export backup is created automatically before mutation unless you disable it
- after writing, OmniMem verifies the rebuilt collection before reporting success

## Backup behavior

By default, OmniMem writes a pre-reindex export backup.

You can override the path:

```bash
./omnimem reindex --backup-output /tmp/omnimem-pre-reindex.json
```

Skip the automatic backup only if you have another recent backup:

```bash
./omnimem reindex --skip-backup
```

## Restore if needed

If you want to roll back after reindexing, restore from the generated export file:

```bash
./omnimem restore /tmp/omnimem-pre-reindex.json --force
```

# Warm Runtime Service

OmniMem v1.8.2 uses a local warm runtime service so repeated `search`, `add`, `import`, and `reindex` commands do not need to rebuild the embedding model on every invocation.

## Why it exists

Without the service, each CLI process starts fresh, imports the embedding stack, and rebuilds the embedding function before ChromaDB can work. On a warm machine that startup cost dominates end-to-end latency.

## Default behavior

`./omnimem search ...`, `./omnimem add ...`, `./omnimem import ...`, and `./omnimem reindex ...` now prefer the local service automatically when `search_service_enabled` is true.

If the service is not already running, OmniMem will:

1. Spawn it locally on `127.0.0.1`
2. Wait for the model and collection to finish warming up
3. Send the runtime request over HTTP

If the service cannot be reached, OmniMem falls back to the one-shot direct path so the command still works.

## Commands

```bash
./omnimem serve
./omnimem serve --status
./omnimem add "release note"
./omnimem import ./my-doc.md
./omnimem reindex
./omnimem search "release notes" --full
./omnimem search "release notes" --direct
```

## Config

```json
{
  "search_service_enabled": true,
  "search_service_port": 41733,
  "search_service_startup_timeout_seconds": 20,
  "search_service_request_timeout_seconds": 10
}
```

## Notes

- The service binds only to `127.0.0.1`.
- The first service-backed command still pays the warmup cost once.
- Subsequent search/add/import/reindex calls reuse the already-loaded model and are much faster.
- `--direct` is useful for debugging or benchmarking the old per-process path.

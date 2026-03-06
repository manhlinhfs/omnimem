# Search Service

OmniMem v1.8.1 adds a local warm search service so repeated `search` commands do not need to rebuild the embedding model on every invocation.

## Why it exists

Without the service, every CLI search starts a fresh Python process, imports the embedding stack, and rebuilds the embedding function before ChromaDB can run the query. On a warm machine that startup cost dominates end-to-end latency.

## Default behavior

`./omnimem search ...` now prefers the local service automatically when `search_service_enabled` is true.

If the service is not already running, OmniMem will:

1. Spawn it locally on `127.0.0.1`
2. Wait for the model and collection to finish warming up
3. Send the search request over HTTP

If the service cannot be reached, OmniMem falls back to the one-shot direct path so search still works.

## Commands

```bash
./omnimem serve
./omnimem serve --status
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
- The first service-backed search still pays the warmup cost once.
- Subsequent searches reuse the already-loaded model and are much faster.
- `--direct` is useful for debugging or benchmarking the old path.

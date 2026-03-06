# Search Filters

OmniMem stores metadata alongside each memory. Starting in `v1.5.0`, search can use part of that metadata to narrow vector retrieval before ranking results.

## Supported Filters

- `--source`: exact `source` match
- `--since`: lower timestamp bound
- `--until`: upper timestamp bound
- `--mime-type`: exact MIME type match for imported files

## Accepted Time Formats

- `YYYY-MM-DD`
- ISO-8601 datetime, for example `2026-03-06T12:00:00`
- ISO-8601 datetime with `Z`, for example `2026-03-06T12:00:00Z`

Date-only filters expand automatically:
- `--since 2026-03-06` means `2026-03-06T00:00:00.000000`
- `--until 2026-03-06` means `2026-03-06T23:59:59.999999`

## Examples

Unified CLI:

```bash
./omnimem search "release" --source omnimem --since 2026-03-06
./omnimem search "invoice" --mime-type application/pdf
./omnimem search "doctor" --source omnimem --until 2026-03-07T12:00:00
```

Legacy script:

```bash
python3 omni_search.py "release" --source omnimem --since 2026-03-06
```

## Notes

- Filters can be combined.
- Old memories remain searchable. Records that do not contain a filtered field simply will not match that specific filter.
- Tag filtering is intentionally postponed because tags are still stored as a normalized scalar string, not as a richer query structure.

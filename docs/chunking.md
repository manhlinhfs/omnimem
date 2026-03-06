# Chunking

OmniMem v1.8.0 replaces blank-line chunking with a structure-aware chunker.

## What changed

Instead of splitting imported content on every empty line, OmniMem now:

1. Detects a chunking profile from MIME type, file extension, and text shape
2. Builds logical blocks before chunking
3. Packs those blocks toward a target token budget
4. Adds overlap between neighboring chunks to preserve retrieval context

## Chunking profiles

### Prose
Used for markdown, plain text, PDF, and most document extracts.

Behavior:
- respects headings when they are present
- keeps lists, tables, paragraphs, and fenced blocks together when possible
- splits oversized paragraphs by sentence boundaries

Default settings:
- `chunk_target_tokens = 420`
- `chunk_overlap_tokens = 70`

### Code
Used for common source-code file extensions and code-like MIME types.

Behavior:
- groups code by declaration-like boundaries and blank-line segments
- preserves nearby comment blocks when they describe the next declaration
- splits oversized blocks by lines instead of sentence heuristics

Default settings:
- `code_chunk_target_tokens = 260`
- `code_chunk_overlap_tokens = 40`

### OCR
Used for noisy short-line extracts such as OCR-heavy content.

Behavior:
- keeps chunk targets smaller than prose
- uses a larger overlap to preserve continuity across fragmented lines

Default settings:
- `ocr_chunk_target_tokens = 320`
- `ocr_chunk_overlap_tokens = 90`

## Metadata added to imported chunks

New import chunks now include:
- `chunk_profile`
- `chunk_strategy`
- `chunk_target_tokens`
- `chunk_overlap_tokens`
- `chunk_tokens`
- `chunk_chars`
- `import_group_id`
- `section_path`
- `source_path` when available

## Tuning chunk sizes

Set values in `omnimem.json` or through environment variables.

Example:

```json
{
  "chunk_target_tokens": 480,
  "chunk_overlap_tokens": 80,
  "code_chunk_target_tokens": 240,
  "code_chunk_overlap_tokens": 32
}
```

Inspect the effective values with:

```bash
./omnimem doctor
./omnimem doctor --json
```

# OmniMem Notes (Second Brain)

OmniMem ships a structured note module for any AI coding agent. Notes live as plain Markdown files inside the OmniMem vault and are mirrored into a dedicated ChromaDB collection (`omnimem_notes`) for semantic search.

The vault is portable: you can read and edit notes with any Markdown editor (Obsidian, VS Code, vim) and OmniMem will pick up your edits on the next `note reindex`.

## Vault layout

```
$OMNIMEM_HOME/
└── vault/
    ├── notes/                # one Markdown file per note
    ├── conversations/        # imported agent transcripts
    └── attachments/          # binary files referenced by notes
```

`$OMNIMEM_HOME` defaults to `~/.local/share/omnimem` on Linux, `~/Library/Application Support/omnimem` on macOS, or `%LOCALAPPDATA%\omnimem` on Windows. Override with the `OMNIMEM_HOME` environment variable or in `omnimem.json`.

## Frontmatter schema

```yaml
---
id: 5f2a3e1b-4c8d-4f1a-9b2e-7c6d5e4f3a2b   # uuid4, immutable
slug: auth-decision-fastapi                # stable kebab-case identifier
title: Why we chose FastAPI for auth
created_at: 2026-04-30T10:15:00.000000
updated_at: 2026-04-30T10:15:00.000000
type: decision                              # note | decision | log | reference | conversation
tags: [auth, backend, fastapi]
links: [auth-flow-pattern, jwt-rotation]    # auto-rebuilt from the body
source: omnimem-cli
agent: claude-code                          # optional
project: omnimem                            # optional
---
```

`links` is regenerated on every save by parsing `[[slug]]` and `[[slug|Display]]` references in the body. Manual edits to `links` in frontmatter are non-authoritative.

## CLI reference

### Create

```bash
omnimem note new "Why we chose FastAPI" \
  --type decision \
  --tags auth,backend \
  --body "Pros: speed, types. Related: [[auth-flow-pattern]]."
```

Read the body from stdin (handy for agents):

```bash
echo "Body content here" | omnimem note new "Some title" --body -
```

### Read / update / delete

```bash
omnimem note show <slug-or-id>
omnimem note update <slug-or-id> --title "New title" --add-tag urgent --rm-tag draft
omnimem note rm <slug-or-id>
```

### List and filter

```bash
omnimem note list --type decision --tag auth --since 2026-04-01 --limit 20
```

### Search (semantic)

```bash
omnimem note search "fastapi auth" --full --limit 5
```

### Linking

```bash
omnimem note link source-slug target-slug      # appends [[target-slug]] in body
omnimem note unlink source-slug target-slug    # removes wikilinks pointing at target
omnimem note backlinks <slug-or-id>            # reverse lookup
omnimem note graph --root <slug>               # adjacency dump as JSON
```

### Reindex

```bash
omnimem note reindex --dry-run     # show what would be rebuilt
omnimem note reindex               # rebuild the omnimem_notes collection from disk
```

### Temporal queries (`--at-date`)

`note list` and `note search` accept `--at-date YYYY-MM-DD` to restrict results to notes created at or before that day. Useful when reconstructing project state at a specific moment:

```bash
omnimem note list --at-date 2026-04-15
omnimem note search "auth decision" --at-date 2026-03-31
```

The cutoff is end-of-day in the user's local time. A full ISO datetime (e.g. `2026-04-01T12:00:00`) is also accepted.

### Canvas export

```bash
omnimem note canvas /path/to/graph.canvas
omnimem note canvas /path/to/subgraph.canvas --root <slug> --depth 2
```

Generates an Obsidian Canvas JSON file with one node per note and one edge per wikilink. With `--root`, the export is restricted to slugs reachable from the root within `--depth` hops.

## Wikilink convention

- `[[slug]]` — link by slug (preferred).
- `[[slug|Display Title]]` — link by slug, render with a custom display string.
- Wikilinks resolve by slug, not title, so renaming a title does not break links. Use `omnimem note update --title` to rename safely.

## Conflict policy

When the body and frontmatter disagree (for example, `links` in frontmatter is out of date with the body), **the body wins**. OmniMem regenerates `links` from `[[...]]` references on the next save or `omnimem note reindex`.

## Federated search

`omnimem mcp serve` exposes a `search_all` tool that ranks results from `omnimem_notes` (your structured notes) and `omnimem_core` (imported documents) together, so an agent can ask one question and let OmniMem pick the right collection.

For raw CLI access today, run both:

```bash
omnimem note search "<query>"     # structured notes
omnimem search "<query>"          # imported documents
```

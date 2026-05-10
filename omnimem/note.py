"""Note module: filesystem-level CRUD for OmniMem second brain notes.

This module is the source of truth for the vault on disk. ChromaDB indexing of
notes is layered on top in a separate module so the markdown vault stays
authoritative and human-editable.
"""

import datetime
import re
import uuid
from pathlib import Path

import yaml

from omnimem.metadata import current_timestamp, normalize_tags
from omnimem.paths import SOURCE_ROOT
from omnimem.vault import (
    DEFAULT_NOTE_TYPE,
    NOTE_TYPES,
    list_existing_note_slugs,
    list_note_paths,
    note_path_for_slug,
    slugify,
    unique_slug,
)

FRONTMATTER_DELIMITER = "---"
_FRONTMATTER_PATTERN = re.compile(
    r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z",
    re.DOTALL,
)
_WIKILINK_PATTERN = re.compile(r"\[\[([^\]\|]+)(?:\|([^\]]+))?\]\]")


class NoteError(RuntimeError):
    pass


def _now_iso():
    return current_timestamp()


def _coerce_tag_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        normalized = normalize_tags(",".join(str(item) for item in value))
    else:
        normalized = normalize_tags(value)
    if not normalized:
        return []
    return normalized.split(",")


def _coerce_link_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        items = [str(item).strip() for item in value]
    else:
        items = [part.strip() for part in str(value).split(",")]
    seen = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return seen


def parse_frontmatter(text):
    """Split a markdown document into (frontmatter_dict, body_string).

    Returns ({}, text) when the document has no YAML frontmatter block.
    """
    if not text:
        return {}, ""

    match = _FRONTMATTER_PATTERN.match(text)
    if not match:
        return {}, text

    raw_yaml, body = match.group(1), match.group(2)
    try:
        loaded = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError as exc:
        raise NoteError(f"Invalid YAML frontmatter: {exc}") from exc
    if not isinstance(loaded, dict):
        raise NoteError("Frontmatter must be a YAML mapping")
    return loaded, body


def serialize_frontmatter(data):
    """Render a frontmatter dict as a YAML block bordered by ---."""
    yaml_text = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()
    return f"{FRONTMATTER_DELIMITER}\n{yaml_text}\n{FRONTMATTER_DELIMITER}\n"


def serialize_note(frontmatter, body):
    block = serialize_frontmatter(frontmatter)
    body_text = body or ""
    if not body_text.endswith("\n"):
        body_text += "\n"
    return f"{block}\n{body_text}"


def extract_wikilinks(body):
    """Return the ordered, deduplicated list of slug references found in body."""
    if not body:
        return []
    seen = []
    for match in _WIKILINK_PATTERN.finditer(body):
        target = match.group(1).strip()
        if not target:
            continue
        if target not in seen:
            seen.append(target)
    return seen


def build_frontmatter(
    *,
    note_id,
    slug,
    title,
    note_type=DEFAULT_NOTE_TYPE,
    tags=None,
    links=None,
    source="omnimem-cli",
    agent=None,
    project=None,
    created_at=None,
    updated_at=None,
    extra=None,
):
    if note_type not in NOTE_TYPES:
        raise NoteError(
            f"Unsupported note type '{note_type}'. Allowed: {', '.join(NOTE_TYPES)}"
        )

    timestamp = updated_at or _now_iso()
    creation_timestamp = created_at or timestamp

    frontmatter = {
        "id": note_id,
        "slug": slug,
        "title": title,
        "created_at": creation_timestamp,
        "updated_at": timestamp,
        "type": note_type,
        "tags": _coerce_tag_list(tags),
        "links": _coerce_link_list(links),
        "source": source,
    }
    if agent:
        frontmatter["agent"] = agent
    if project:
        frontmatter["project"] = project

    if extra:
        for key, value in extra.items():
            if key in frontmatter:
                continue
            frontmatter[key] = value

    return frontmatter


def create_note(
    title,
    body=None,
    *,
    note_type=DEFAULT_NOTE_TYPE,
    tags=None,
    source="omnimem-cli",
    agent=None,
    project=None,
    root_dir=SOURCE_ROOT,
    note_id=None,
):
    """Create a new note on disk and return its frontmatter + path."""
    if not title or not str(title).strip():
        raise NoteError("Note title cannot be empty")

    base_slug = slugify(title)
    existing = list_existing_note_slugs(root_dir=root_dir)
    slug = unique_slug(base_slug, existing)

    body_text = body or ""
    body_links = extract_wikilinks(body_text)

    new_id = note_id or str(uuid.uuid4())
    timestamp = _now_iso()
    frontmatter = build_frontmatter(
        note_id=new_id,
        slug=slug,
        title=str(title).strip(),
        note_type=note_type,
        tags=tags,
        links=body_links,
        source=source,
        agent=agent,
        project=project,
        created_at=timestamp,
        updated_at=timestamp,
    )

    path = note_path_for_slug(slug, root_dir=root_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise NoteError(f"Note file already exists: {path}")

    path.write_text(serialize_note(frontmatter, body_text), encoding="utf-8")
    return {
        "id": new_id,
        "slug": slug,
        "path": str(path),
        "frontmatter": frontmatter,
    }


def read_note(slug_or_id, root_dir=SOURCE_ROOT):
    path = _resolve_note_path(slug_or_id, root_dir=root_dir)
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    return {
        "frontmatter": frontmatter,
        "body": body,
        "path": str(path),
    }


def write_note(slug, frontmatter, body, root_dir=SOURCE_ROOT):
    """Persist an updated note. Rewrites `links` from the body before saving."""
    if frontmatter.get("slug") != slug:
        raise NoteError("Frontmatter slug must match the target slug")

    refreshed_links = extract_wikilinks(body or "")
    frontmatter = dict(frontmatter)
    frontmatter["links"] = refreshed_links
    frontmatter["updated_at"] = _now_iso()

    path = note_path_for_slug(slug, root_dir=root_dir)
    if not path.exists():
        raise NoteError(f"Note not found: {path}")

    path.write_text(serialize_note(frontmatter, body or ""), encoding="utf-8")
    return {
        "id": frontmatter.get("id"),
        "slug": slug,
        "path": str(path),
        "frontmatter": frontmatter,
    }


def delete_note(slug_or_id, root_dir=SOURCE_ROOT):
    path = _resolve_note_path(slug_or_id, root_dir=root_dir)
    path.unlink()
    return {"deleted": True, "path": str(path)}


def list_notes(
    root_dir=SOURCE_ROOT,
    note_type=None,
    tag=None,
    since=None,
    until=None,
    at_date=None,
    limit=None,
):
    """Enumerate notes with optional filtering. Sorted by updated_at desc.

    Time filters operate on `updated_at` for `since` / `until` and on
    `created_at` for `at_date` (only notes created at or before `at_date` are
    returned, so the result reflects the vault state as of that day).
    """
    records = []
    at_date_eod = _coerce_at_date_upper_bound(at_date)
    for path in list_note_paths(root_dir=root_dir):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            frontmatter, _body = parse_frontmatter(text)
        except NoteError:
            continue
        if note_type and frontmatter.get("type") != note_type:
            continue
        if tag and tag not in (frontmatter.get("tags") or []):
            continue
        if since and (frontmatter.get("updated_at") or "") < since:
            continue
        if until and (frontmatter.get("updated_at") or "") > until:
            continue
        if at_date_eod and (frontmatter.get("created_at") or "") > at_date_eod:
            continue
        records.append(
            {
                "id": frontmatter.get("id"),
                "slug": frontmatter.get("slug"),
                "title": frontmatter.get("title"),
                "type": frontmatter.get("type"),
                "tags": frontmatter.get("tags") or [],
                "created_at": frontmatter.get("created_at"),
                "updated_at": frontmatter.get("updated_at"),
                "path": str(path),
            }
        )

    records.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
    if limit is not None:
        records = records[: int(limit)]
    return records


def _coerce_at_date_upper_bound(at_date):
    """Translate `--at-date YYYY-MM-DD` into an end-of-day ISO timestamp."""
    if not at_date:
        return None
    raw = str(at_date).strip()
    if not raw:
        return None
    if "T" in raw:
        return raw
    return f"{raw}T23:59:59.999999"


def find_backlinks(slug, root_dir=SOURCE_ROOT):
    """Return notes whose body links to the given slug."""
    backlinks = []
    for path in list_note_paths(root_dir=root_dir):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            frontmatter, body = parse_frontmatter(text)
        except NoteError:
            continue
        targets = extract_wikilinks(body or "")
        if slug in targets:
            backlinks.append(
                {
                    "id": frontmatter.get("id"),
                    "slug": frontmatter.get("slug"),
                    "title": frontmatter.get("title"),
                    "path": str(path),
                }
            )
    return backlinks


def add_link(from_slug, to_slug, root_dir=SOURCE_ROOT):
    """Append `[[to_slug]]` to the source note body when not already linked."""
    record = read_note(from_slug, root_dir=root_dir)
    body = record["body"] or ""
    if to_slug in extract_wikilinks(body):
        return write_note(from_slug, record["frontmatter"], body, root_dir=root_dir)
    appended_body = body
    if not appended_body.endswith("\n"):
        appended_body += "\n"
    appended_body += f"\nLinked: [[{to_slug}]]\n"
    return write_note(from_slug, record["frontmatter"], appended_body, root_dir=root_dir)


def remove_link(from_slug, to_slug, root_dir=SOURCE_ROOT):
    """Strip wiki references to `to_slug` from the source note body."""
    record = read_note(from_slug, root_dir=root_dir)
    body = record["body"] or ""
    pattern = re.compile(
        r"\[\[" + re.escape(to_slug) + r"(?:\|[^\]]+)?\]\]"
    )
    new_body = pattern.sub("", body)
    return write_note(from_slug, record["frontmatter"], new_body, root_dir=root_dir)


def _resolve_note_path(slug_or_id, root_dir=SOURCE_ROOT):
    direct = note_path_for_slug(slug_or_id, root_dir=root_dir)
    if direct.exists():
        return direct

    for path in list_note_paths(root_dir=root_dir):
        try:
            frontmatter, _body = parse_frontmatter(path.read_text(encoding="utf-8"))
        except (OSError, NoteError):
            continue
        if frontmatter.get("id") == slug_or_id or frontmatter.get("slug") == slug_or_id:
            return path

    raise NoteError(f"Note not found: {slug_or_id}")

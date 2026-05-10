"""Vault layout, slug generation, and filesystem helpers for OmniMem notes."""

import re
import unicodedata
from pathlib import Path

from omnimem.paths import SOURCE_ROOT, get_runtime_home

VAULT_DIRNAME = "vault"
NOTES_DIRNAME = "notes"
CONVERSATIONS_DIRNAME = "conversations"
ATTACHMENTS_DIRNAME = "attachments"

NOTE_TYPES = ("note", "decision", "log", "reference", "conversation")
DEFAULT_NOTE_TYPE = "note"

_SLUG_INVALID_CHARS = re.compile(r"[^a-z0-9]+")
_SLUG_TRIM_DASHES = re.compile(r"^-+|-+$")
_MAX_SLUG_LENGTH = 80

# Letters that NFKD cannot decompose to ASCII but have a clear ASCII fold.
# Extend conservatively: only add characters with widely-accepted ASCII forms.
_ASCII_FOLD_MAP = {
    "Đ": "D",  # Đ
    "đ": "d",  # đ
    "ß": "ss", # ß
    "æ": "ae", # æ
    "Æ": "AE", # Æ
    "œ": "oe", # œ
    "Œ": "OE", # Œ
    "ø": "o",  # ø
    "Ø": "O",  # Ø
    "ł": "l",  # ł
    "Ł": "L",  # Ł
}


def _ascii_fold(text):
    return "".join(_ASCII_FOLD_MAP.get(ch, ch) for ch in text)


def get_vault_root(root_dir=SOURCE_ROOT):
    return Path(get_runtime_home(root_dir=root_dir)) / VAULT_DIRNAME


def get_notes_dir(root_dir=SOURCE_ROOT):
    return get_vault_root(root_dir=root_dir) / NOTES_DIRNAME


def get_conversations_dir(root_dir=SOURCE_ROOT):
    return get_vault_root(root_dir=root_dir) / CONVERSATIONS_DIRNAME


def get_attachments_dir(root_dir=SOURCE_ROOT):
    return get_vault_root(root_dir=root_dir) / ATTACHMENTS_DIRNAME


def ensure_vault_layout(root_dir=SOURCE_ROOT):
    """Create the vault directory tree if missing. Idempotent."""
    notes = get_notes_dir(root_dir=root_dir)
    conversations = get_conversations_dir(root_dir=root_dir)
    attachments = get_attachments_dir(root_dir=root_dir)
    for directory in (notes, conversations, attachments):
        directory.mkdir(parents=True, exist_ok=True)
    return {
        "vault": str(get_vault_root(root_dir=root_dir)),
        "notes": str(notes),
        "conversations": str(conversations),
        "attachments": str(attachments),
    }


def slugify(text):
    """Convert an arbitrary title into a stable kebab-case slug.

    Normalizes Unicode to ASCII where possible, lowercases, replaces any run of
    non-alphanumeric characters with a single dash, trims leading/trailing
    dashes, and caps the length.
    """
    if text is None:
        raise ValueError("slugify requires a non-empty title")

    raw = str(text).strip()
    if not raw:
        raise ValueError("slugify requires a non-empty title")

    folded = _ascii_fold(raw)
    decomposed = unicodedata.normalize("NFKD", folded)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower() if ascii_only else raw.lower()

    slug = _SLUG_INVALID_CHARS.sub("-", lowered)
    slug = _SLUG_TRIM_DASHES.sub("", slug)
    slug = slug[:_MAX_SLUG_LENGTH]
    slug = _SLUG_TRIM_DASHES.sub("", slug)

    if not slug:
        slug = "untitled"
    return slug


def unique_slug(base_slug, existing_slugs):
    """Append a numeric suffix to disambiguate from existing slugs."""
    if base_slug not in existing_slugs:
        return base_slug

    counter = 2
    while True:
        candidate = f"{base_slug}-{counter}"
        if candidate not in existing_slugs:
            return candidate
        counter += 1


def note_path_for_slug(slug, root_dir=SOURCE_ROOT):
    return get_notes_dir(root_dir=root_dir) / f"{slug}.md"


def list_existing_note_slugs(root_dir=SOURCE_ROOT):
    notes_dir = get_notes_dir(root_dir=root_dir)
    if not notes_dir.exists():
        return set()
    return {path.stem for path in notes_dir.glob("*.md")}


def list_note_paths(root_dir=SOURCE_ROOT):
    notes_dir = get_notes_dir(root_dir=root_dir)
    if not notes_dir.exists():
        return []
    return sorted(notes_dir.glob("*.md"))

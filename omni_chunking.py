import os
import re
import uuid
from pathlib import Path

from omni_config import get_chunk_settings_for_profile
from omni_metadata import build_base_metadata, coerce_metadata_value, normalize_mime_type

CHUNK_STRATEGY_VERSION = "v2"
CODE_PROFILE = "code"
PROSE_PROFILE = "prose"
OCR_PROFILE = "ocr"

CODE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".m",
    ".mm",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".scala",
    ".sh",
    ".sql",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
}
CODE_MIME_PREFIXES = (
    "text/x-",
    "application/x-",
)
CODE_MIME_EXACT = {
    "application/javascript",
    "application/json",
    "application/sql",
    "text/css",
    "text/html",
    "text/javascript",
    "text/x-python",
}
DECLARATION_RE = re.compile(
    r"^\s*(async\s+def|def|class|function|interface|struct|enum|impl|func|package|module|namespace|export\s+(async\s+)?function)\b"
)
LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def normalize_newlines(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def estimate_tokens(text):
    count = len(TOKEN_RE.findall(text or ""))
    return max(1, count)


def detect_chunk_profile(mime_type=None, file_path=None, content=None):
    normalized_mime_type = normalize_mime_type(mime_type)
    suffix = Path(file_path).suffix.lower() if file_path else ""

    if suffix in CODE_EXTENSIONS:
        return CODE_PROFILE
    if normalized_mime_type in CODE_MIME_EXACT:
        return CODE_PROFILE
    if normalized_mime_type and normalized_mime_type.startswith(CODE_MIME_PREFIXES):
        return CODE_PROFILE
    if normalized_mime_type and normalized_mime_type.startswith("image/"):
        return OCR_PROFILE

    text = content or ""
    lines = [line for line in normalize_newlines(text).splitlines() if line.strip()]
    if lines:
        average_line_length = sum(len(line.strip()) for line in lines) / len(lines)
        if average_line_length < 48 and len(lines) > 25:
            return OCR_PROFILE
    return PROSE_PROFILE


def _section_path_to_string(section_stack):
    parts = [part for part in section_stack if part]
    return " > ".join(parts) if parts else None


def _make_block(text, kind, section_path=None):
    cleaned = text.strip()
    if not cleaned:
        return None
    return {
        "text": cleaned,
        "kind": kind,
        "section_path": section_path,
    }


def _build_prose_blocks(text):
    lines = normalize_newlines(text).split("\n")
    section_stack = []
    blocks = []
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        heading_match = HEADING_RE.match(stripped)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            section_stack = section_stack[: level - 1]
            section_stack.append(heading_text)
            block = _make_block(stripped, "heading", _section_path_to_string(section_stack))
            if block:
                blocks.append(block)
            index += 1
            continue

        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence_lines = [line]
            fence_marker = stripped[:3]
            index += 1
            while index < len(lines):
                fence_lines.append(lines[index])
                if lines[index].strip().startswith(fence_marker):
                    index += 1
                    break
                index += 1
            block = _make_block("\n".join(fence_lines), "fence", _section_path_to_string(section_stack))
            if block:
                blocks.append(block)
            continue

        if LIST_RE.match(stripped):
            list_lines = [line]
            index += 1
            while index < len(lines):
                candidate = lines[index]
                candidate_stripped = candidate.strip()
                if not candidate_stripped:
                    break
                if LIST_RE.match(candidate_stripped) or candidate.startswith("  ") or candidate.startswith("\t"):
                    list_lines.append(candidate)
                    index += 1
                    continue
                break
            block = _make_block("\n".join(list_lines), "list", _section_path_to_string(section_stack))
            if block:
                blocks.append(block)
            continue

        if "|" in stripped:
            table_lines = [line]
            index += 1
            while index < len(lines):
                candidate = lines[index]
                candidate_stripped = candidate.strip()
                if not candidate_stripped or "|" not in candidate_stripped:
                    break
                table_lines.append(candidate)
                index += 1
            block = _make_block("\n".join(table_lines), "table", _section_path_to_string(section_stack))
            if block:
                blocks.append(block)
            continue

        paragraph_lines = [line]
        index += 1
        while index < len(lines):
            candidate = lines[index]
            candidate_stripped = candidate.strip()
            if not candidate_stripped:
                break
            if HEADING_RE.match(candidate_stripped):
                break
            if candidate_stripped.startswith("```") or candidate_stripped.startswith("~~~"):
                break
            if LIST_RE.match(candidate_stripped):
                break
            paragraph_lines.append(candidate)
            index += 1
        block = _make_block("\n".join(paragraph_lines), "paragraph", _section_path_to_string(section_stack))
        if block:
            blocks.append(block)

    return blocks


def _split_code_segments(text):
    lines = normalize_newlines(text).split("\n")
    segments = []
    current = []
    for line in lines:
        if not line.strip():
            if current:
                segments.append("\n".join(current).strip())
                current = []
            continue
        current.append(line)
    if current:
        segments.append("\n".join(current).strip())
    return [segment for segment in segments if segment]


def _build_code_blocks(text):
    segments = _split_code_segments(text)
    blocks = []
    index = 0
    while index < len(segments):
        segment = segments[index]
        if index + 1 < len(segments):
            next_segment = segments[index + 1]
            comment_only = all(
                line.strip().startswith(("#", "//", "/*", "*", "--"))
                for line in segment.splitlines()
                if line.strip()
            )
            if comment_only and DECLARATION_RE.match(next_segment.splitlines()[0].strip()):
                segment = segment + "\n\n" + next_segment
                index += 1
        kind = "code_block"
        if DECLARATION_RE.match(segment.splitlines()[0].strip()):
            kind = "code_decl"
        blocks.append({"text": segment, "kind": kind, "section_path": None})
        index += 1
    return blocks


def build_blocks(text, profile):
    if profile == CODE_PROFILE:
        return _build_code_blocks(text)
    return _build_prose_blocks(text)


def _split_prose_text(text, target_tokens):
    sentences = [item.strip() for item in SENTENCE_SPLIT_RE.split(text.strip()) if item.strip()]
    if len(sentences) <= 1:
        sentences = [line.strip() for line in text.splitlines() if line.strip()]
    if len(sentences) <= 1:
        return [text.strip()]

    chunks = []
    current = []
    current_tokens = 0
    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence)
        if current and current_tokens + sentence_tokens > target_tokens:
            chunks.append(" ".join(current).strip())
            current = [sentence]
            current_tokens = sentence_tokens
        else:
            current.append(sentence)
            current_tokens += sentence_tokens
    if current:
        chunks.append(" ".join(current).strip())
    return [chunk for chunk in chunks if chunk]


def _split_code_text(text, target_tokens):
    lines = [line.rstrip() for line in normalize_newlines(text).splitlines() if line.strip()]
    if not lines:
        return []

    chunks = []
    current = []
    current_tokens = 0
    for line in lines:
        line_tokens = estimate_tokens(line)
        if current and current_tokens + line_tokens > target_tokens:
            chunks.append("\n".join(current).strip())
            current = [line]
            current_tokens = line_tokens
        else:
            current.append(line)
            current_tokens += line_tokens
    if current:
        chunks.append("\n".join(current).strip())
    return [chunk for chunk in chunks if chunk]


def split_oversized_block(text, target_tokens, profile):
    if profile == CODE_PROFILE:
        return _split_code_text(text, target_tokens)
    return _split_prose_text(text, target_tokens)


def _collect_section_path(blocks):
    seen = []
    for block in blocks:
        section_path = block.get("section_path")
        if section_path and section_path not in seen:
            seen.append(section_path)
    return seen[-1] if seen else None


def _tail_overlap(text, overlap_tokens, profile):
    if overlap_tokens <= 0:
        return ""

    if profile == CODE_PROFILE:
        lines = [line for line in normalize_newlines(text).splitlines() if line.strip()]
        selected = []
        token_count = 0
        for line in reversed(lines):
            selected.append(line)
            token_count += estimate_tokens(line)
            if token_count >= overlap_tokens:
                break
        return "\n".join(reversed(selected)).strip()

    sentences = [item.strip() for item in SENTENCE_SPLIT_RE.split(text.strip()) if item.strip()]
    if not sentences:
        lines = [line.strip() for line in normalize_newlines(text).splitlines() if line.strip()]
        sentences = lines
    selected = []
    token_count = 0
    for sentence in reversed(sentences):
        selected.append(sentence)
        token_count += estimate_tokens(sentence)
        if token_count >= overlap_tokens:
            break
    return " ".join(reversed(selected)).strip()


def chunk_document(content, mime_type=None, file_path=None, root_dir=None, config_values=None):
    normalized_content = normalize_newlines(content or "").strip()
    if not normalized_content:
        return {
            "profile": PROSE_PROFILE,
            "target_tokens": 0,
            "overlap_tokens": 0,
            "chunks": [],
        }

    profile = detect_chunk_profile(mime_type=mime_type, file_path=file_path, content=normalized_content)
    if config_values is None:
        if root_dir is None:
            target_tokens, overlap_tokens = get_chunk_settings_for_profile(profile)
        else:
            target_tokens, overlap_tokens = get_chunk_settings_for_profile(profile, root_dir=root_dir)
    else:
        if profile == CODE_PROFILE:
            target_tokens = int(config_values["code_chunk_target_tokens"])
            overlap_tokens = int(config_values["code_chunk_overlap_tokens"])
        elif profile == OCR_PROFILE:
            target_tokens = int(config_values["ocr_chunk_target_tokens"])
            overlap_tokens = int(config_values["ocr_chunk_overlap_tokens"])
        else:
            target_tokens = int(config_values["chunk_target_tokens"])
            overlap_tokens = int(config_values["chunk_overlap_tokens"])

    blocks = build_blocks(normalized_content, profile)
    if not blocks:
        blocks = [{"text": normalized_content, "kind": "raw", "section_path": None}]

    base_chunks = []
    current_blocks = []
    current_tokens = 0
    for block in blocks:
        block_tokens = estimate_tokens(block["text"])
        if block_tokens > target_tokens:
            if current_blocks:
                chunk_text = "\n\n".join(item["text"] for item in current_blocks).strip()
                base_chunks.append(
                    {
                        "text": chunk_text,
                        "section_path": _collect_section_path(current_blocks),
                    }
                )
                current_blocks = []
                current_tokens = 0
            for piece in split_oversized_block(block["text"], target_tokens, profile):
                base_chunks.append({"text": piece, "section_path": block.get("section_path")})
            continue

        if current_blocks and current_tokens + block_tokens > target_tokens:
            chunk_text = "\n\n".join(item["text"] for item in current_blocks).strip()
            base_chunks.append(
                {
                    "text": chunk_text,
                    "section_path": _collect_section_path(current_blocks),
                }
            )
            current_blocks = []
            current_tokens = 0

        current_blocks.append(block)
        current_tokens += block_tokens

    if current_blocks:
        chunk_text = "\n\n".join(item["text"] for item in current_blocks).strip()
        base_chunks.append(
            {
                "text": chunk_text,
                "section_path": _collect_section_path(current_blocks),
            }
        )

    chunks = []
    for index, chunk in enumerate(base_chunks):
        chunk_text = chunk["text"]
        if index > 0:
            overlap_text = _tail_overlap(base_chunks[index - 1]["text"], overlap_tokens, profile)
            if overlap_text:
                chunk_text = f"{overlap_text}\n\n{chunk_text}".strip()
        chunks.append(
            {
                "text": chunk_text,
                "section_path": chunk.get("section_path"),
                "chunk_tokens": estimate_tokens(chunk_text),
                "chunk_chars": len(chunk_text),
                "chunk_index": index,
            }
        )

    return {
        "profile": profile,
        "target_tokens": target_tokens,
        "overlap_tokens": overlap_tokens,
        "chunks": chunks,
    }


def build_import_records(
    content,
    mime_type,
    source_name,
    doc_metadata=None,
    file_path=None,
    timestamp=None,
    import_group_id=None,
    root_dir=None,
    config_values=None,
    reindexed_from_chunk_count=None,
):
    normalized_mime_type = normalize_mime_type(mime_type) or "unknown"
    doc_metadata = doc_metadata or {}
    chunk_plan = chunk_document(
        content,
        mime_type=normalized_mime_type,
        file_path=file_path,
        root_dir=root_dir,
        config_values=config_values,
    )

    timestamp = timestamp or doc_metadata.get("timestamp")
    import_group_id = import_group_id or str(uuid.uuid4())
    source_path = str(Path(file_path).expanduser()) if file_path else doc_metadata.get("source_path")

    documents = []
    metadatas = []
    ids = []
    for chunk in chunk_plan["chunks"]:
        meta = build_base_metadata(
            source=source_name,
            timestamp=timestamp,
            record_kind="import_chunk",
            chunk_index=chunk["chunk_index"],
            mime_type=normalized_mime_type,
            chunk_profile=chunk_plan["profile"],
            chunk_strategy=CHUNK_STRATEGY_VERSION,
            chunk_target_tokens=chunk_plan["target_tokens"],
            chunk_overlap_tokens=chunk_plan["overlap_tokens"],
            chunk_tokens=chunk["chunk_tokens"],
            chunk_chars=chunk["chunk_chars"],
            import_group_id=import_group_id,
            section_path=chunk.get("section_path"),
            source_path=source_path,
            reindexed_from_chunk_count=reindexed_from_chunk_count,
        )
        for key, value in doc_metadata.items():
            if key in meta:
                continue
            meta[key] = coerce_metadata_value(value)
        documents.append(chunk["text"])
        metadatas.append(meta)
        ids.append(str(uuid.uuid4()))

    return {
        "documents": documents,
        "metadatas": metadatas,
        "ids": ids,
        "profile": chunk_plan["profile"],
        "target_tokens": chunk_plan["target_tokens"],
        "overlap_tokens": chunk_plan["overlap_tokens"],
        "import_group_id": import_group_id,
    }

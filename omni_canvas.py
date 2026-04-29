"""Obsidian Canvas export for OmniMem notes.

Generates a `.canvas` JSON file (the Obsidian Canvas spec) capturing the note
graph: one node per note, one edge per wikilink. Layout is a deterministic
spiral so the export is stable across runs and reasonable for vaults up to a
few hundred notes.
"""

import json
import math
from pathlib import Path

from omni_note import extract_wikilinks, list_notes, parse_frontmatter
from omni_paths import SOURCE_ROOT
from omni_vault import list_note_paths

NODE_WIDTH = 240
NODE_HEIGHT = 80
SPIRAL_GAP = 60


class CanvasError(RuntimeError):
    pass


def _spiral_position(index):
    """Return (x, y) for the i-th node arranged on a square spiral.

    Yields a layout where adjacent slugs sit close together but the canvas
    fills outward — easier to read than a fixed grid for sparse graphs.
    """
    if index == 0:
        return (0, 0)
    layer = math.ceil((math.sqrt(index + 1) - 1) / 2)
    if layer == 0:
        return (0, 0)
    leg = max(1, 2 * layer)
    perimeter_start = (2 * layer - 1) ** 2
    offset = index - perimeter_start
    side = offset // leg
    along = offset % leg

    step = NODE_WIDTH + SPIRAL_GAP
    if side == 0:
        x = layer * step
        y = (-layer + along) * (NODE_HEIGHT + SPIRAL_GAP)
    elif side == 1:
        x = (layer - along) * step
        y = layer * (NODE_HEIGHT + SPIRAL_GAP)
    elif side == 2:
        x = -layer * step
        y = (layer - along) * (NODE_HEIGHT + SPIRAL_GAP)
    else:
        x = (-layer + along) * step
        y = -layer * (NODE_HEIGHT + SPIRAL_GAP)
    return (x, y)


def _build_node(index, slug, title, path=None):
    x, y = _spiral_position(index)
    text = f"# {title}\n[[{slug}]]" if title else f"[[{slug}]]"
    node = {
        "id": slug,
        "type": "text",
        "x": x,
        "y": y,
        "width": NODE_WIDTH,
        "height": NODE_HEIGHT,
        "text": text,
    }
    if path:
        node["file"] = str(path)
    return node


def collect_graph(root_dir=SOURCE_ROOT, root_slug=None, depth=None):
    """Return (nodes, edges) for the canvas export.

    When `root_slug` is set, the graph is restricted to slugs reachable from
    that note within `depth` hops (default: unlimited).
    """
    nodes = []
    seen_slugs = []
    edges_seen = set()
    edges = []

    notes_meta = {}
    for path in list_note_paths(root_dir=root_dir):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            frontmatter, body = parse_frontmatter(text)
        except Exception:
            continue
        slug = frontmatter.get("slug")
        if not slug:
            continue
        notes_meta[slug] = {
            "title": frontmatter.get("title") or slug,
            "path": str(path),
            "links": extract_wikilinks(body or ""),
        }

    if root_slug:
        if root_slug not in notes_meta:
            raise CanvasError(f"Root slug not in vault: {root_slug}")
        frontier = [(root_slug, 0)]
        visited = set()
        while frontier:
            current, current_depth = frontier.pop(0)
            if current in visited:
                continue
            visited.add(current)
            seen_slugs.append(current)
            if depth is not None and current_depth >= int(depth):
                continue
            for target in notes_meta.get(current, {}).get("links", []):
                if target in notes_meta and target not in visited:
                    frontier.append((target, current_depth + 1))
    else:
        seen_slugs = sorted(notes_meta.keys())

    for index, slug in enumerate(seen_slugs):
        meta = notes_meta[slug]
        nodes.append(_build_node(index, slug, meta["title"], meta["path"]))
        for target in meta["links"]:
            if target in seen_slugs:
                key = (slug, target)
                if key in edges_seen:
                    continue
                edges_seen.add(key)
                edges.append(
                    {
                        "id": f"{slug}->{target}",
                        "fromNode": slug,
                        "fromSide": "right",
                        "toNode": target,
                        "toSide": "left",
                    }
                )

    return nodes, edges


def export_canvas(output_path, root_dir=SOURCE_ROOT, root_slug=None, depth=None):
    nodes, edges = collect_graph(root_dir=root_dir, root_slug=root_slug, depth=depth)
    payload = {"nodes": nodes, "edges": edges}
    target = Path(output_path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "output": str(target),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "root": root_slug,
        "depth": depth,
    }

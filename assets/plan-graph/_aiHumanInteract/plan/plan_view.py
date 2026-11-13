"""Render a Plan Graph payload as a self-contained HTML reader view.

The caller (``build_graph.py``) owns discovery, validation, and file output.
This module only computes the deterministic layout and returns the page text.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field

NODE_W = 240
NODE_H = 68
ACCENT_W = 7
CARD_STROKE = 1.5
GAP_X = 56
PARENT_CHILD_GAP = 64
LEAF_GAP = 16
SIBLING_GAP_Y = 20
ROOT_GAP = 110
MARGIN = 72

LEVEL_Z = {"long-term": 48, "mid-term": 32, "short-term": 16, "work-package": 0}
DEPTH_X = 0.35

STATUS_STYLE = {
    "done": ("#EDF7F0", "#A7CEB4", "#234B36"),
    "in_progress": ("#FFF4E8", "#E7BA91", "#80512A"),
    "proposed": ("#EFF5FC", "#B3C9E2", "#31577D"),
    "blocked": ("#FCEEEE", "#E0ACAC", "#873F3F"),
    "superseded": ("#F1F2F4", "#C9CDD2", "#777D85"),
}
SECONDARY_TEXT = "#78838D"
LEVEL_TAG = {
    "long-term": "LT",
    "mid-term": "MT",
    "short-term": "ST",
    "work-package": "WP",
}
LEVEL_COLOR = {
    "long-term": "#7766A6",
    "mid-term": "#6487AD",
    "short-term": "#6F9DA2",
    "work-package": "#A4ADB7",
}


@dataclass
class PlanNode:
    node_id: str
    title: str
    level: str
    status: str
    parent: str | None
    children: list["PlanNode"] = field(default_factory=list)
    detail: dict = field(default_factory=dict)


@dataclass
class Block:
    width: float
    height: float
    items: list[tuple[PlanNode, float, float]]
    root_x: float = 0.0
    root_y: float = 0.0


def load_nodes(payload: dict) -> list[PlanNode]:
    nodes = [
        PlanNode(
            node_id=raw["id"],
            title=raw.get("title", raw["id"]),
            level=raw.get("level", ""),
            status=raw.get("status", ""),
            parent=raw.get("parent"),
            detail=raw,
        )
        for raw in payload["nodes"]
    ]
    by_id = {node.node_id: node for node in nodes}
    roots: list[PlanNode] = []
    for node in nodes:
        if node.parent and node.parent in by_id:
            by_id[node.parent].children.append(node)
        else:
            roots.append(node)
    for node in nodes:
        node.children.sort(key=lambda item: item.node_id)
    roots.sort(key=lambda item: item.node_id)
    return roots


def group_children(children: list[PlanNode]) -> list[list[PlanNode]]:
    """Group consecutive leaf siblings; runs of 3+ become one stacked group."""
    groups: list[list[PlanNode]] = []
    index = 0
    while index < len(children):
        if children[index].children:
            groups.append([children[index]])
            index += 1
            continue
        end = index
        while end < len(children) and not children[end].children:
            end += 1
        run = children[index:end]
        if len(run) >= 3:
            groups.append(run)
        else:
            groups.extend([leaf] for leaf in run)
        index = end
    return groups


def layout_subtree(node: PlanNode, direction: str = "down") -> Block:
    if not node.children:
        return Block(NODE_W, NODE_H, [(node, 0.0, 0.0)], 0.0, 0.0)

    if direction == "right":
        blocks = [layout_subtree(child, direction) for child in node.children]
        total_height = sum(block.height for block in blocks) + SIBLING_GAP_Y * (len(blocks) - 1)
        max_width = max(block.width for block in blocks)
        items: list[tuple[PlanNode, float, float]] = []
        child_centers: list[float] = []
        y = 0.0
        for block in blocks:
            child_centers.append(y + block.root_y + NODE_H / 2)
            for child, bx, by in block.items:
                items.append((child, NODE_W + GAP_X + bx, y + by))
            y += block.height + SIBLING_GAP_Y
        parent_y = (child_centers[0] + child_centers[-1]) / 2 - NODE_H / 2
        items.append((node, 0.0, parent_y))
        return Block(
            NODE_W + GAP_X + max_width, max(NODE_H, total_height), items, 0.0, parent_y
        )

    groups = group_children(node.children)
    blocks: list[Block] = []
    for group in groups:
        if len(group) >= 3:  # stacked leaf run
            height = len(group) * NODE_H + (len(group) - 1) * LEAF_GAP
            items = [(leaf, 0.0, i * (NODE_H + LEAF_GAP)) for i, leaf in enumerate(group)]
            blocks.append(Block(NODE_W, height, items))
        else:
            blocks.append(layout_subtree(group[0], direction))

    total_width = sum(block.width for block in blocks) + GAP_X * (len(blocks) - 1)
    children_height = max(block.height for block in blocks)

    items = []
    child_centers = []
    x = 0.0
    for block in blocks:
        child_centers.append(x + block.root_x + NODE_W / 2)
        for child, bx, by in block.items:
            items.append((child, x + bx, NODE_H + PARENT_CHILD_GAP + by))
        x += block.width + GAP_X
    parent_x = (child_centers[0] + child_centers[-1]) / 2 - NODE_W / 2
    items.append((node, parent_x, 0.0))
    return Block(
        total_width,
        NODE_H + PARENT_CHILD_GAP + children_height,
        items,
        parent_x,
        0.0,
    )


def layout_forest(
    roots: list[PlanNode], direction: str = "down"
) -> tuple[list[tuple[PlanNode, float, float]], float, float]:
    placed: list[tuple[PlanNode, float, float]] = []
    blocks = [layout_subtree(root, direction) for root in roots]
    width = max((block.width for block in blocks), default=NODE_W)
    height = sum(block.height for block in blocks) + ROOT_GAP * max(0, len(blocks) - 1)
    y = 0.0
    for block in blocks:
        if direction == "right":
            offset_x = 0.0
        else:
            offset_x = (width - block.width) / 2
        for node, x, by in block.items:
            placed.append((node, offset_x + x + MARGIN, y + by + MARGIN))
        y += block.height + ROOT_GAP
    return placed, width + MARGIN * 2, height + MARGIN * 2


def _text_width(text: str) -> float:
    return sum(12.5 if ord(char) > 0x2E80 else 6.9 for char in text)


def wrap_title(title: str, max_width: float = 212, max_lines: int = 2) -> list[str]:
    lines: list[str] = []
    current = ""
    index = 0
    while index < len(title):
        char = title[index]
        if _text_width(current + char) <= max_width:
            current += char
            index += 1
            continue
        if len(lines) == max_lines - 1:
            break
        cut = current.rfind(" ")
        if cut > 0 and len(current) - cut <= 14:
            lines.append(current[:cut].rstrip())
            current = current[cut + 1 :] + char
        else:
            lines.append(current.rstrip())
            current = char
        index += 1
    if len(lines) < max_lines:
        lines.append(current.rstrip())
    if index < len(title) and lines:
        lines[-1] = lines[-1].rstrip() + "…"
    return [line for line in lines if line][:max_lines]


def edge_markup(
    placed: list[tuple[PlanNode, float, float, float]], direction: str = "down"
) -> str:
    """Parent-child connectors. A stacked leaf run is reached along a spine."""
    pos = {node.node_id: (x, y) for node, x, y, _ in placed}
    children: dict[str, list[tuple[PlanNode, float, float]]] = {}
    for node, x, y, _ in placed:
        if node.parent and node.parent in pos:
            children.setdefault(node.parent, []).append((node, x, y))

    parts: list[str] = []
    for parent_id, kids in children.items():
        px, py = pos[parent_id]
        if direction == "right":
            pbx, pby = px + NODE_W, py + NODE_H / 2
            midx = pbx + GAP_X / 2
            for child, cx, cy in kids:
                ccy = cy + NODE_H / 2
                parts.append(
                    f'<path class="edge" data-to="{child.node_id}" data-from="{parent_id}" '
                    f'd="M {pbx:.1f} {pby:.1f} H {midx:.1f} '
                    f'V {ccy:.1f} H {cx:.1f}"/>'
                )
            continue

        pbx, pby = px + NODE_W / 2, py + NODE_H
        midy = pby + PARENT_CHILD_GAP / 2
        columns: dict[float, list[tuple[PlanNode, float, float]]] = {}
        for child, cx, cy in kids:
            columns.setdefault(round(cx, 1), []).append((child, cx, cy))
        for column_x, members in columns.items():
            stacked = len(members) >= 3 and all(not item[0].children for item in members)
            if stacked:
                spine = column_x - 14
                for child, cx, cy in members:
                    center = cy + NODE_H / 2
                    parts.append(
                        f'<path class="edge" data-to="{child.node_id}" data-from="{parent_id}" '
                        f'd="M {pbx:.1f} {pby:.1f} V {midy:.1f} H {spine:.1f} '
                        f'V {center:.1f} H {cx:.1f}"/>'
                    )
            else:
                for child, cx, cy in members:
                    parts.append(
                        f'<path class="edge" data-to="{child.node_id}" data-from="{parent_id}" '
                        f'd="M {pbx:.1f} {pby:.1f} V {midy:.1f} '
                        f'H {cx + NODE_W / 2:.1f} V {cy:.1f}"/>'
                    )
    return '<g id="edge-layer">' + "".join(parts) + "</g>"


CARD_MARK_STYLE = {
    "supersedes": ("↓", 56),
    "conflicts_with": ("✕", 48),
    "alternative_of": ("→", 48),
}
CARD_MARK_FILL = "#212529"
CARD_MARK_OPACITY = 0.18


def card_mark_markup(
    placed: list[tuple[PlanNode, float, float, float]], edges: list[dict]
) -> str:
    """Large watermark marks on the referenced card, shown with its owner."""
    pos = {node.node_id: (x, y) for node, x, y, _ in placed}
    parts: list[str] = []
    for edge in edges:
        relation = edge.get("relationship")
        if relation not in CARD_MARK_STYLE:
            continue
        source, target = edge.get("from"), edge.get("to")
        if source not in pos or target not in pos:
            continue
        tx, ty = pos[target]
        cx = tx + NODE_W / 2
        cy = ty + NODE_H / 2
        glyph, size = CARD_MARK_STYLE[relation]
        body = (
            f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" '
            f'dominant-baseline="central" fill="{CARD_MARK_FILL}" fill-opacity="{CARD_MARK_OPACITY}" '
            f'font-size="{size}" font-weight="700">{glyph}</text>'
        )
        if relation == "alternative_of":
            body += (
                f'<text x="{cx:.1f}" y="{cy + 30:.1f}" text-anchor="middle" '
                f'fill="{CARD_MARK_FILL}" fill-opacity="{CARD_MARK_OPACITY}" font-size="10" '
                f'font-weight="600">alt</text>'
            )
        parts.append(
            f'<g class="card-mark" data-owner="{source}" data-target="{target}" '
            f'data-relation="{relation}" style="display:none">{body}</g>'
        )
    return '<g id="card-mark-layer">' + "".join(parts) + "</g>"


def ground_of(px: float, py: float, z: float) -> tuple[float, float]:
    return px - z * DEPTH_X, py + z


def ground_markup(placed: list[tuple[PlanNode, float, float, float]]) -> str:
    """Ground shadows, then the extruded side face under each raised card."""
    parts: list[str] = []
    for node, px, py, z in placed:
        gx, gy = ground_of(px, py, z)
        parts.append(
            f'<ellipse class="shadow" data-id="{html.escape(node.node_id)}" '
            f'cx="{gx + NODE_W / 2:.1f}" cy="{gy + NODE_H:.1f}" '
            f'rx="{NODE_W / 2 - 2:.1f}" ry="5" fill="#000" opacity="0.05"/>'
        )
    for node, px, py, z in placed:
        if z <= 0:
            continue
        gx, gy = ground_of(px, py, z)
        parts.append(
            f'<path class="side" data-id="{html.escape(node.node_id)}" '
            f'd="M {px:.1f} {py + NODE_H:.1f} '
            f'L {px + NODE_W:.1f} {py + NODE_H:.1f} '
            f'L {gx + NODE_W:.1f} {gy + NODE_H:.1f} '
            f'L {gx:.1f} {gy + NODE_H:.1f} Z" '
            f'fill="#E1E5E8" stroke="#D5DADF" stroke-width="0.8"/>'
        )
    return '<g id="ground-layer">' + "".join(parts) + "</g>"


def card_outline(
    x: float, y: float, width: float, height: float, radius: float = 5, notch: float = ACCENT_W
) -> str:
    """Top, right and bottom edges only; the accent strip owns the left edge."""
    return (
        f"M {x + notch:.1f} {y:.1f} H {x + width - radius:.1f} "
        f"Q {x + width:.1f} {y:.1f} {x + width:.1f} {y + radius:.1f} "
        f"V {y + height - radius:.1f} "
        f"Q {x + width:.1f} {y + height:.1f} {x + width - radius:.1f} {y + height:.1f} "
        f"H {x + notch:.1f}"
    )


def card_path(x: float, y: float, width: float, height: float, radius: float = 5) -> str:
    """Rounded on the right, square on the left so the accent bar aligns."""
    return (
        f"M {x:.1f} {y:.1f} H {x + width - radius:.1f} "
        f"Q {x + width:.1f} {y:.1f} {x + width:.1f} {y + radius:.1f} "
        f"V {y + height - radius:.1f} "
        f"Q {x + width:.1f} {y + height:.1f} {x + width - radius:.1f} {y + height:.1f} "
        f"H {x:.1f} Z"
    )


def halo_markup(placed: list[tuple[PlanNode, float, float, float]]) -> str:
    parts = [
        f'<rect class="halo" data-id="{html.escape(node.node_id)}" '
        f'x="{x - 10:.1f}" y="{y - 10:.1f}" width="{NODE_W + 20}" height="{NODE_H + 20}" rx="14"/>'
        for node, x, y, _ in placed
    ]
    return '<g id="halo-layer">' + "".join(parts) + "</g>"


def svg_markup(placed: list[tuple[PlanNode, float, float, float]]) -> str:
    parts: list[str] = []
    for node, x, y, _ in placed:
        fill, stroke, text = STATUS_STYLE.get(node.status, ("#ffffff", "#adb5bd", "#212529"))
        dashed = ' stroke-dasharray="5 3"' if node.status == "superseded" else ""
        level_color = LEVEL_COLOR.get(node.level, "#868e96")
        parts.append(
            f'<g class="node" data-id="{html.escape(node.node_id)}">'
            f'<title>{html.escape(node.title)}</title>'
            f'<path class="card" d="{card_path(x, y, NODE_W, NODE_H)}" fill="{fill}"/>'
            f'<rect class="accent" x="{x:.1f}" y="{y - CARD_STROKE / 2:.1f}" width="{ACCENT_W}" '
            f'height="{NODE_H + CARD_STROKE}" fill="{level_color}"/>'
            f'<path class="card-outline" d="{card_outline(x, y, NODE_W, NODE_H)}" '
            f'fill="none" stroke="{stroke}" stroke-width="{CARD_STROKE}"{dashed}/>'
            f'<path class="card-select" d="{card_path(x, y, NODE_W, NODE_H)}" fill="none"/>'
            f'<text x="{x + 14:.1f}" y="{y + 20:.1f}" class="id" fill="{SECONDARY_TEXT}">{html.escape(node.node_id)}</text>'
            f'<text x="{x + NODE_W - 10:.1f}" y="{y + 20:.1f}" class="tag" text-anchor="end" '
            f'fill="{level_color}">{LEVEL_TAG.get(node.level, "")}</text>'
        )
        for line_index, line in enumerate(wrap_title(node.title)):
            parts.append(
                f'<text x="{x + 14:.1f}" y="{y + 41 + line_index * 17:.1f}" '
                f'class="title" fill="{text}">{html.escape(line)}</text>'
            )
        parts.append("</g>")
    return '<g id="node-layer">' + "".join(parts) + "</g>"


HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Plan tree — {title}</title>
<style>
  :root {{ color-scheme: light; }}
  html, body {{ margin: 0; height: 100%; background: #F6F6F4;
    font-family: "WenQuanYi Micro Hei", "Noto Sans CJK SC", "Segoe UI", sans-serif; }}
  #canvas {{ width: 100%; height: 100%; display: block; cursor: grab;
    user-select: none; -webkit-user-select: none; touch-action: none; }}
  #canvas text {{ user-select: none; -webkit-user-select: none; }}
  #canvas.dragging {{ cursor: grabbing; }}
  .id {{ font-size: 11px; font-weight: 500; letter-spacing: .02em; }}
  .title {{ font-size: 13px; font-weight: 600; }}
  .tag {{ font-size: 10px; font-weight: 600; letter-spacing: .08em; opacity: .8; }}
  .node:hover .card {{ filter: brightness(.97); }}
  #hud {{ position: fixed; left: 16px; top: 16px; background: rgba(255,255,255,.94);
    border: 1px solid #dee2e6; border-radius: 10px; padding: 12px 14px;
    font-size: 12px; line-height: 1.6; box-shadow: 0 2px 8px rgba(0,0,0,.06); }}
  #hud b {{ font-size: 13px; }}
  #hud .swatch {{ display: inline-block; width: 9px; height: 9px; border-radius: 50%; }}
  #filters {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 7px 0 2px; max-width: 340px; }}
  .filter {{ display: inline-flex; align-items: center; gap: 5px; border: 1px solid #dee2e6;
    background: #fff; border-radius: 999px; padding: 2px 8px; font: inherit; font-size: 11px;
    color: #495057; cursor: pointer; }}
  .filter b {{ font-weight: 600; color: #212529; }}
  .filter.active {{ border-color: #5078B8; background: #E8F0FB; }}
  #search-open {{ margin-top: 7px; border: 1px solid #ced4da; background: #fff;
    border-radius: 6px; padding: 3px 8px; font: inherit; font-size: 11px;
    color: #495057; cursor: pointer; }}
  #search-open kbd {{ font: inherit; font-size: 10px; color: #868e96; }}
  #search-chip {{ display: flex; align-items: center; gap: 6px; margin-top: 7px;
    padding: 3px 8px; border-radius: 6px; background: #E8F0FB; color: #31577D;
    font-size: 11px; }}
  #search-chip[hidden] {{ display: none; }}
  #search-clear {{ border: 0; background: none; color: #31577D; cursor: pointer;
    font-size: 14px; line-height: 1; padding: 0 2px; }}
  #search-surface {{ position: fixed; left: 50%; bottom: 24px; transform: translateX(-50%);
    width: min(760px, calc(100vw - 48px)); z-index: 40; border-radius: 16px;
    background: rgba(255,255,255,.82); backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px); box-shadow: 0 18px 50px rgba(0,0,0,.18);
    border: 1px solid rgba(255,255,255,.75); padding: 8px; box-sizing: border-box; }}
  #search-surface[hidden] {{ display: none; }}
  #search-results {{ max-height: min(44vh, 420px); overflow-y: auto; padding: 2px; }}
  .search-result {{ display: flex; gap: 8px; align-items: baseline; padding: 7px 10px;
    border-radius: 8px; cursor: pointer; font-size: 12px; }}
  .search-result:hover, .search-result.active {{ background: rgba(80,120,184,.12); }}
  .search-result .rid {{ font-weight: 600; color: #495057; }}
  .search-result .rtitle {{ color: #27313B; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; }}
  .search-result .rstatus {{ margin-left: auto; color: #868e96; font-size: 10px;
    white-space: nowrap; }}
  .search-empty {{ padding: 12px 10px; color: #868e96; font-size: 11px; }}
  .dot {{ width: 8px; height: 8px; border-radius: 50%; flex: none; }}
  .dot-done {{ background: #A7CEB4; }}
  .dot-in_progress {{ background: #E7BA91; }}
  .dot-proposed {{ background: #B3C9E2; }}
  .dot-blocked {{ background: #E0ACAC; }}
  .dot-superseded {{ background: #C9CDD2; }}
  #search-box {{ display: flex; gap: 10px; align-items: center; margin-top: 6px; }}
  #search {{ flex: 1; box-sizing: border-box; padding: 7px 10px; border-radius: 8px;
    border: 1px solid #fff; background: #fff; font: inherit; font-size: 12px;
    color: #27313B; box-shadow: 0 0 0 2px rgba(255,255,255,.9),
    0 0 18px rgba(80,120,184,.35); }}
  #search:focus {{ outline: none; box-shadow: 0 0 0 2px #fff, 0 0 22px rgba(80,120,184,.55); }}
  #search-help {{ color: #868e96; font-size: 10px; white-space: nowrap; }}
  #hud .hint {{ color: #868e96; margin-top: 6px; }}
  #panel {{ position: fixed; top: 0; right: 0; width: 380px; height: 100%;
    background: #fff; border-left: 1px solid #dee2e6; box-shadow: -4px 0 16px rgba(0,0,0,.08);
    display: flex; flex-direction: column; box-sizing: border-box;
    font-size: 12px; line-height: 1.65; }}
  #panel[hidden] {{ display: none; }}
  #panel-head {{ flex: none; position: relative; padding: 16px 18px 10px;
    border-bottom: 1px solid #e9ecef; }}
  #panel-head.status-done {{ background: #EDF7F0; border-bottom-color: #A7CEB4; }}
  #panel-head.status-in_progress {{ background: #FFF4E8; border-bottom-color: #E7BA91; }}
  #panel-head.status-proposed {{ background: #EFF5FC; border-bottom-color: #B3C9E2; }}
  #panel-head.status-blocked {{ background: #FCEEEE; border-bottom-color: #E0ACAC; }}
  #panel-head.status-superseded {{ background: #F1F2F4; border-bottom-color: #C9CDD2; }}
  #panel-head.status-done h3 {{ color: #234B36; }}
  #panel-head.status-in_progress h3 {{ color: #80512A; }}
  #panel-head.status-proposed h3 {{ color: #31577D; }}
  #panel-head.status-blocked h3 {{ color: #873F3F; }}
  #panel-head.status-superseded h3 {{ color: #777D85; }}
  #panel-resizer {{ position: absolute; left: -7px; top: 0; bottom: 0; width: 14px;
    cursor: col-resize; z-index: 2; }}
  #panel-resizer::after {{ content: ""; position: absolute; left: 6px; top: 50%;
    width: 2px; height: 56px; margin-top: -28px; border-radius: 1px; background: #CED4DA; }}
  #panel-resizer:hover {{ background: rgba(80,120,184,.08); }}
  #panel-resizer:hover::after, #panel-resizer.dragging::after {{ background: #5078B8; }}
  body.resizing {{ user-select: none; cursor: col-resize; }}
  #shade {{ opacity: 0; pointer-events: none; transition: opacity .3s ease; }}
  #shade.on {{ opacity: .45; pointer-events: auto; }}
  #panel-body {{ flex: 1; min-height: 0; overflow-y: auto; padding: 12px 18px 20px; }}
  #panel h3 {{ margin: 0 26px 4px 0; font-size: 14px; line-height: 1.4; }}
  #panel .meta {{ color: #868e96; margin-bottom: 6px; }}
  #panel h4 {{ margin: 16px 0 4px; font-size: 10px; text-transform: uppercase;
    letter-spacing: .08em; color: #868e96; }}
  #panel ul {{ margin: 0; padding-left: 16px; }}
  #panel li {{ margin: 2px 0; }}
  #panel code {{ background: #f1f3f5; padding: 1px 4px; border-radius: 3px;
    font-size: 11px; word-break: break-all; }}
  #panel .kind {{ color: #495057; margin-top: 6px; font-size: 11px; }}
  #panel .rel-summary {{ margin-top: 6px; font-size: 10px; color: #495057;
    display: flex; flex-wrap: wrap; gap: 4px 10px; }}
  #panel .rel-summary b {{ font-weight: 600; }}
  #panel .rel-block {{ margin-top: 4px; }}
  #panel .rel-row {{ display: flex; gap: 8px; margin: 3px 0; font-size: 11px;
    line-height: 1.5; }}
  #panel .rel-label {{ flex: none; width: 84px; color: #868e96; }}
  #panel .rel-values {{ flex: 1; min-width: 0; }}
  #panel .rel-link {{ display: inline-flex; align-items: baseline; gap: 5px;
    color: #31577D; text-decoration: none; margin: 0 8px 2px 0; }}
  #panel .rel-link:hover {{ text-decoration: underline; }}
  #panel .rel-empty {{ color: #adb5bd; }}
  #close {{ position: absolute; right: 12px; top: 10px; border: 0; background: none;
    font-size: 20px; line-height: 1; cursor: pointer; color: #868e96; }}
  .edge {{ fill: none; stroke: #B8C0C9; stroke-width: 1.2; stroke-linejoin: round;
    stroke-linecap: round; transition: stroke .12s ease, stroke-width .12s ease; }}
  .edge.hot {{ stroke: #5078B8; stroke-width: 2.2; }}
  .card-mark {{ pointer-events: none; }}
  .halo {{ fill: transparent; pointer-events: none; }}
  .halo.on {{ fill: #DCEBFA; filter: blur(4px); }}
  .node {{ cursor: pointer; }}
  .card-outline, .card-select {{ pointer-events: none; }}
  .card-select {{ display: none; }}
  .node.selected .card-outline {{ display: none; }}
  .node.selected .card-select {{ display: inline; stroke: #5078B8; stroke-width: 2.5;
    filter: drop-shadow(0 0 4px rgba(80,120,184,.35)); }}
  #reset, #fit, #overview {{ margin-top: 6px; border: 1px solid #ced4da;
    background: #fff; border-radius: 6px; padding: 3px 8px; font-size: 11px;
    cursor: pointer; }}
</style>
</head>
<body>
<svg id="canvas" xmlns="http://www.w3.org/2000/svg">
  <g id="scene">{body}</g>
  <rect id="shade" width="100%" height="100%" fill="#1B1B1B"/>
  <g id="top-layer"></g>
</svg>
<div id="hud">
  <b>{title}</b>
  <div id="filters">{filters}<button id="filter-all" class="filter filter-all">全选</button></div>
  <button id="search-open" type="button">搜索 <kbd>Ctrl/⌘K</kbd></button>
  <div id="search-chip" hidden><span id="search-chip-text"></span><button id="search-clear" aria-label="clear search">×</button></div>
  <div class="hint">点击节点查看详情 · Ctrl/⌘K 搜索 · 点状态筛选 · 滚轮缩放 · 拖拽平移</div>
  <button id="reset">100%</button>
  <button id="fit">适应宽度</button>
  <button id="overview">全览</button>
</div>
<div id="search-surface" hidden>
  <div id="search-results"></div>
  <div id="search-box">
    <input id="search" type="search" placeholder="搜索 plan 文本…" autocomplete="off"/>
    <div id="search-help">↑↓ 选择 · Enter 打开 · Esc 关闭</div>
  </div>
</div>
<aside id="panel" hidden>
  <div id="panel-resizer" role="separator" aria-orientation="vertical"
       aria-label="resize detail panel" tabindex="0"></div>
  <div id="panel-head">
    <button id="close" aria-label="close">×</button>
  </div>
  <div id="panel-body"></div>
</aside>
<script>
  const DETAILS = {details};
  const RELATIONS = {relations};
  const svg = document.getElementById('canvas');
  const scene = document.getElementById('scene');
  const topLayer = document.getElementById('top-layer');
  const shade = document.getElementById('shade');
  const nodeLayer = document.getElementById('node-layer');
  const haloLayer = document.getElementById('halo-layer');
  const groundLayer = document.getElementById('ground-layer');
  const W = {width}, H = {height};
  let k = 1, tx = 0, ty = 0, dragging = false, lastX = 0, lastY = 0, moved = false;
  const panel = document.getElementById('panel');
  const panelHead = document.getElementById('panel-head');
  const panelBody = document.getElementById('panel-body');
  const resizer = document.getElementById('panel-resizer');
  const PANEL_MIN = 300, PANEL_MAX = 900, PANEL_DEFAULT = 380;
  let resizingPanel = false;
  let selectedId = null;

  function setPanelWidth(width) {{
    const max = Math.max(PANEL_MIN, Math.min(PANEL_MAX, window.innerWidth - 240));
    const clamped = Math.max(PANEL_MIN, Math.min(width, max));
    panel.style.width = clamped + 'px';
    try {{ localStorage.setItem('ptm-plan-panel-width', String(clamped)); }} catch (error) {{}}
  }}

  function endResize() {{
    if (!resizingPanel) return;
    resizingPanel = false;
    resizer.classList.remove('dragging');
    document.body.classList.remove('resizing');
  }}

  resizer.addEventListener('pointerdown', (event) => {{
    resizingPanel = true;
    resizer.classList.add('dragging');
    document.body.classList.add('resizing');
    resizer.setPointerCapture(event.pointerId);
    event.preventDefault();
  }});
  resizer.addEventListener('pointermove', (event) => {{
    if (!resizingPanel) return;
    setPanelWidth(window.innerWidth - event.clientX);
  }});
  resizer.addEventListener('pointerup', endResize);
  resizer.addEventListener('pointercancel', endResize);
  resizer.addEventListener('dblclick', () => setPanelWidth(PANEL_DEFAULT));
  resizer.addEventListener('keydown', (event) => {{
    const current = panel.getBoundingClientRect().width;
    if (event.key === 'ArrowLeft') {{ setPanelWidth(current + 24); event.preventDefault(); }}
    if (event.key === 'ArrowRight') {{ setPanelWidth(current - 24); event.preventDefault(); }}
  }});
  try {{
    const saved = Number(localStorage.getItem('ptm-plan-panel-width'));
    if (saved) setPanelWidth(saved);
  }} catch (error) {{}}
  window.addEventListener('resize', () => {{
    if (!panel.hidden) setPanelWidth(panel.getBoundingClientRect().width);
  }});
  const nodeById = new Map([...document.querySelectorAll('.node')].map(g => [g.dataset.id, g]));
  const haloById = new Map([...document.querySelectorAll('.halo')].map(h => [h.dataset.id, h]));
  const edgeLayer = document.getElementById('edge-layer');
  const hotLayer = document.getElementById('hot-layer');
  function clearHot() {
    hotLayer.querySelectorAll('.edge').forEach(path => {
      path.classList.remove('hot');
      edgeLayer.appendChild(path);
    });
  }

  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function revealPanel() {
    if (reduceMotion) return;
    const items = [
      ...panelHead.querySelectorAll('h3, .meta'),
      ...panelBody.children,
    ];
    items.forEach((item, index) => {
      item.animate(
        [
          { opacity: 0, transform: 'translateY(-6px)' },
          { opacity: 1, transform: 'translateY(0)' },
        ],
        {
          duration: 320,
          delay: Math.min(index * 28, 280),
          easing: 'cubic-bezier(.2, .7, .3, 1)',
          fill: 'both',
        }
      );
    });
  }

  function show(id) {
    const d = DETAILS[id];
    if (!d) return;
    selectedId = id;
    panelHead.className = 'status-' + d.status;
    document.querySelectorAll('.node.selected').forEach(n => n.classList.remove('selected'));
    nodeById.get(id)?.classList.add('selected');
    clearHot();
    document.querySelectorAll('.halo.on').forEach(h => h.classList.remove('on'));
    haloById.get(id)?.classList.add('on');
    let cursor = id;
    while (cursor && DETAILS[cursor]) {
      edgeLayer.querySelectorAll('.edge[data-to="' + cursor + '"]').forEach(p => {
        p.classList.add('hot');
        hotLayer.appendChild(p);
      });
      cursor = DETAILS[cursor].parent;
    }
    panelBody.replaceChildren();
    [...panelHead.children].forEach(child => { if (child.id !== 'close') child.remove(); });
    panelHead.append(el('h3', null, d.id + ' · ' + d.title));
    panelHead.append(el('div', 'meta', d.level + ' · ' + d.status + ' · updated ' + d.updated + (d.parent ? ' · parent ' + d.parent : '')));
    panelHead.append(renderRelationSummary(id));
    panelBody.append(renderRelations(id));
    panelBody.scrollTop = 0;
    if (d.objective) {
      panelBody.append(el('h4', null, 'Objective'));
      panelBody.append(el('p', null, d.objective));
    }
    for (const [label, key] of [['Deliverables', 'deliverables'], ['Acceptance', 'acceptance']]) {
      if (Array.isArray(d[key]) && d[key].length) {
        panelBody.append(el('h4', null, label));
        const ul = document.createElement('ul');
        d[key].forEach(x => ul.append(el('li', null, x)));
        panelBody.append(ul);
      }
    }
    const links = d.links || {};
    const kinds = Object.keys(links);
    if (kinds.length) {
      panelBody.append(el('h4', null, 'Links'));
      for (const kind of kinds) {
        panelBody.append(el('div', 'kind', kind));
        const ul = document.createElement('ul');
        const items = Array.isArray(links[kind]) ? links[kind] : [links[kind]];
        items.forEach(x => {
          const li = document.createElement('li');
          const code = document.createElement('code');
          code.textContent = x;
          li.append(code);
          ul.append(li);
        });
        panelBody.append(ul);
      }
    }
    if (Array.isArray(d.evidence) && d.evidence.length) {
      panelBody.append(el('h4', null, 'Evidence'));
      const ul = document.createElement('ul');
      d.evidence.forEach(x => {
        const li = document.createElement('li');
        const code = document.createElement('code');
        code.textContent = x;
        li.append(code);
        ul.append(li);
      });
      panelBody.append(ul);
    }
    document.querySelectorAll('.card-mark').forEach(mark => {
      mark.style.display = mark.dataset.owner === id ? '' : 'none';
    });
    panel.hidden = false;
    revealPanel();
    history.replaceState(null, '', '#' + encodeURIComponent(id));
  }
  function hidePanel() {
    selectedId = null;
    panel.hidden = true;
    document.querySelectorAll('.node.selected').forEach(n => n.classList.remove('selected'));
    document.querySelectorAll('.halo.on').forEach(h => h.classList.remove('on'));
    clearHot();
    document.querySelectorAll('.card-mark').forEach(mark => { mark.style.display = 'none'; });
    history.replaceState(null, '', location.pathname + location.search);
  }
  const filterButtons = [...document.querySelectorAll('.filter[data-status]')];
  const activeStatuses = new Set();
  const searchInput = document.getElementById('search');
  const searchSurface = document.getElementById('search-surface');
  const searchResults = document.getElementById('search-results');
  const searchChip = document.getElementById('search-chip');
  const searchChipText = document.getElementById('search-chip-text');
  let queryTokens = [];
  let searchMatches = [];
  let searchIndex = -1;
  const searchText = new Map(Object.entries(DETAILS).map(([id, detail]) => {
    const links = Object.values(detail.links || {}).flatMap(value =>
      Array.isArray(value) ? value : [value]
    );
    return [id, [
      detail.id, detail.title, detail.level, detail.status, detail.updated,
      detail.parent, detail.source, detail.objective,
      ...(detail.deliverables || []), ...(detail.acceptance || []),
      ...(detail.evidence || []), ...links,
    ].join(' ').toLowerCase()];
  }));

  function nodeMatches(id) {
    const detail = DETAILS[id];
    if (!detail) return false;
    if (activeStatuses.size > 0 && !activeStatuses.has(detail.status)) return false;
    if (queryTokens.length > 0) {
      const haystack = searchText.get(id) || '';
      if (!queryTokens.every(token => haystack.includes(token))) return false;
    }
    return true;
  }

  function renderSearchResults() {
    searchMatches = Object.keys(DETAILS).filter(nodeMatches).sort().slice(0, 50);
    searchIndex = -1;
    searchResults.replaceChildren();
    if (queryTokens.length === 0) {
      const hint = document.createElement('div');
      hint.className = 'search-empty';
      hint.textContent = '输入关键词，匹配 id、标题、objective、deliverables、acceptance、links…';
      searchResults.append(hint);
      return;
    }
    if (searchMatches.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'search-empty';
      empty.textContent = '没有匹配的 plan';
      searchResults.append(empty);
      return;
    }
    for (const id of searchMatches) {
      const detail = DETAILS[id];
      const row = document.createElement('div');
      row.className = 'search-result';
      row.dataset.id = id;
      const dot = document.createElement('span');
      dot.className = 'dot dot-' + detail.status;
      const rid = document.createElement('span');
      rid.className = 'rid';
      rid.textContent = id;
      const title = document.createElement('span');
      title.className = 'rtitle';
      title.textContent = detail.title;
      const status = document.createElement('span');
      status.className = 'rstatus';
      status.textContent = detail.status + ' · ' + detail.level;
      row.append(dot, rid, title, status);
      row.addEventListener('click', () => openResult(id));
      searchResults.append(row);
    }
  }

  function openSearch() {
    searchSurface.hidden = false;
    renderSearchResults();
    searchInput.focus();
    searchInput.select();
  }

  function closeSearch() {
    searchSurface.hidden = true;
  }

  function openResult(id) {
    closeSearch();
    show(id);
  }

  function updateSearchChrome() {
    const value = searchInput.value.trim();
    searchChip.hidden = !value;
    searchChipText.textContent = value ? '搜索：' + value : '';
  }

  function relationCounts(rel) {
    const count = (list, type) => (list || []).filter(item => item.type === type).length;
    return {
      parent: (rel.parent ? 1 : 0) + (rel.children || []).length,
      depends: count(rel.in, 'prerequisite_for') + count(rel.out, 'prerequisite_for'),
      enables: count(rel.in, 'enables') + count(rel.out, 'enables'),
      validates: count(rel.in, 'validates') + count(rel.out, 'validates'),
      supersedes: count(rel.in, 'supersedes') + count(rel.out, 'supersedes'),
      conflicts: count(rel.in, 'conflicts_with') + count(rel.out, 'conflicts_with'),
      alternative: count(rel.in, 'alternative_of') + count(rel.out, 'alternative_of'),
    };
  }

  function renderRelationSummary(id) {
    const counts = relationCounts(RELATIONS[id] || {});
    const labels = {
      parent: 'parent', depends: 'depends', enables: 'enables',
      validates: 'validates', supersedes: 'supersedes',
      conflicts: 'conflicts', alternative: 'alternative',
    };
    const summary = el('div', 'rel-summary');
    let any = false;
    for (const [key, label] of Object.entries(labels)) {
      if (!counts[key]) continue;
      any = true;
      const item = el('span', null, label + ' ');
      item.append(el('b', null, String(counts[key])));
      summary.append(item);
    }
    if (!any) summary.textContent = 'no relations';
    return summary;
  }

  function relationLink(targetId) {
    const detail = DETAILS[targetId] || { status: 'superseded', title: targetId };
    const link = document.createElement('a');
    link.className = 'rel-link';
    link.href = '#' + encodeURIComponent(targetId);
    link.dataset.id = targetId;
    const dot = document.createElement('span');
    dot.className = 'dot dot-' + detail.status;
    link.append(dot, document.createTextNode(targetId + ' · ' + detail.title));
    return link;
  }

  function relationRow(label, targets, emptyText = 'none') {
    const row = el('div', 'rel-row');
    const name = el('span', 'rel-label', label);
    const values = el('span', 'rel-values');
    if (!targets.length) {
      values.append(el('span', 'rel-empty', emptyText));
    } else {
      targets.forEach(target => values.append(relationLink(target)));
    }
    row.append(name, values);
    return row;
  }

  function renderRelations(id) {
    const rel = RELATIONS[id] || {};
    const block = el('div', 'rel-block');
    block.append(el('h4', null, 'Relations'));
    const outgoing = type => (rel.out || []).filter(item => item.type === type).map(item => item.target);
    const incoming = type => (rel.in || []).filter(item => item.type === type).map(item => item.target);
    block.append(relationRow('Parent/children', [], 'see the graph'));
    block.append(relationRow('Depends on', incoming('prerequisite_for')));
    block.append(relationRow('Required by', outgoing('prerequisite_for')));
    block.append(relationRow('Enables', outgoing('enables')));
    block.append(relationRow('Enabled by', incoming('enables')));
    block.append(relationRow('Validates', outgoing('validates')));
    block.append(relationRow('Validated by', incoming('validates')));
    block.append(relationRow('Supersedes', outgoing('supersedes')));
    block.append(relationRow('Superseded by', incoming('supersedes')));
    const conflicts = [...new Set([...outgoing('conflicts_with'), ...incoming('conflicts_with')])];
    block.append(relationRow('Conflicts with', conflicts));
    block.append(relationRow('Alternative of', outgoing('alternative_of')));
    block.append(relationRow('Has alternative', incoming('alternative_of')));
    return block;
  }

  function navigateTo(id) {
    activeStatuses.clear();
    filterButtons.forEach(button => button.classList.remove('active'));
    searchInput.value = '';
    queryTokens = [];
    applyFilter(false);
    closeSearch();
    show(id);
  }

  function clearTop() {
    topLayer.querySelectorAll('.node').forEach(el => nodeLayer.appendChild(el));
    topLayer.querySelectorAll('.halo').forEach(el => haloLayer.appendChild(el));
    topLayer.querySelectorAll('.side').forEach(el => groundLayer.appendChild(el));
  }

  function applyFilter(pulse = true) {
    const wasFiltering = shade.classList.contains('on');
    clearTop();
    const filtering = activeStatuses.size > 0 || queryTokens.length > 0;
    shade.classList.toggle('on', filtering);
    if (filtering && wasFiltering && pulse) {
      shade.animate(
        [{ opacity: 0.32 }, { opacity: 0.45 }],
        { duration: 300, easing: 'ease-out' }
      );
    }
    if (filtering) {
      const halos = [...document.querySelectorAll('.halo')].filter(el => nodeMatches(el.dataset.id));
      const nodes = [...document.querySelectorAll('.node')].filter(el => nodeMatches(el.dataset.id));
      halos.forEach(el => topLayer.appendChild(el));
      nodes.forEach(el => topLayer.appendChild(el));
    }
    if (selectedId && !nodeMatches(selectedId)) hidePanel();
    if (!searchSurface.hidden) renderSearchResults();
    updateSearchChrome();
  }

  filterButtons.forEach(button => {
    button.addEventListener('click', () => {
      const status = button.dataset.status;
      if (activeStatuses.has(status)) activeStatuses.delete(status);
      else activeStatuses.add(status);
      button.classList.toggle('active', activeStatuses.has(status));
      applyFilter();
    });
  });

  searchInput.addEventListener('input', () => {
    queryTokens = searchInput.value.toLowerCase().split(/\\s+/).filter(Boolean);
    applyFilter(false);
  });
  searchInput.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      if (searchMatches.length === 0) return;
      event.preventDefault();
      const delta = event.key === 'ArrowDown' ? 1 : -1;
      searchIndex = (searchIndex + delta + searchMatches.length) % searchMatches.length;
      [...searchResults.querySelectorAll('.search-result')].forEach((row, index) => {
        row.classList.toggle('active', index === searchIndex);
      });
      const active = searchResults.querySelector('.search-result.active');
      if (active) active.scrollIntoView({ block: 'nearest' });
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      const target = searchIndex >= 0 ? searchMatches[searchIndex] : searchMatches[0];
      if (target) openResult(target);
    }
  });

  document.getElementById('search-open').addEventListener('click', openSearch);
  document.getElementById('search-clear').addEventListener('click', () => {
    searchInput.value = '';
    queryTokens = [];
    applyFilter(false);
    searchInput.focus();
  });

  document.getElementById('filter-all').addEventListener('click', () => {
    activeStatuses.clear();
    filterButtons.forEach(button => button.classList.remove('active'));
    searchInput.value = '';
    queryTokens = [];
    applyFilter();
  });

  svg.addEventListener('click', (event) => {
    if (moved) { moved = false; return; }
    const g = event.target.closest('.node');
    if (g) show(g.dataset.id);
  });
  document.getElementById('close').addEventListener('click', hidePanel);
  panelBody.addEventListener('click', (event) => {
    const link = event.target.closest('a.rel-link');
    if (!link) return;
    event.preventDefault();
    navigateTo(link.dataset.id);
  });
  document.addEventListener('keydown', (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      if (searchSurface.hidden) openSearch();
      else closeSearch();
      return;
    }
    if (event.key === 'Escape') {
      if (!searchSurface.hidden) {
        closeSearch();
        event.preventDefault();
        return;
      }
      hidePanel();
    }
  });

  function apply() {{
    const transform = `translate(${{tx}} ${{ty}}) scale(${{k}})`;
    scene.setAttribute('transform', transform);
    topLayer.setAttribute('transform', transform);
  }}
  function fitWidth() {{
    const r = svg.getBoundingClientRect();
    k = Math.min(1, (r.width - 40) / W);
    tx = (r.width - W * k) / 2;
    ty = 20;
    apply();
  }}
  function actualSize() {{
    const r = svg.getBoundingClientRect();
    k = 1;
    tx = Math.max(20, (r.width - W) / 2);
    ty = 20;
    apply();
  }}
  function overview() {{
    const r = svg.getBoundingClientRect();
    k = Math.min(1, (r.width - 40) / W, (r.height - 40) / H);
    tx = (r.width - W * k) / 2;
    ty = Math.max(20, (r.height - H * k) / 2);
    apply();
  }}
  svg.addEventListener('wheel', (event) => {{
    event.preventDefault();
    const r = svg.getBoundingClientRect();
    const mx = event.clientX - r.left, my = event.clientY - r.top;
    const next = Math.min(3, Math.max(0.12, k * Math.exp(-event.deltaY * 0.0015)));
    tx = mx - (mx - tx) * (next / k);
    ty = my - (my - ty) * (next / k);
    k = next;
    apply();
  }}, {{ passive: false }});
  svg.addEventListener('pointerdown', (event) => {{
    event.preventDefault();
    const selection = window.getSelection();
    if (selection) selection.removeAllRanges();
    dragging = true; moved = false; lastX = event.clientX; lastY = event.clientY;
    svg.classList.add('dragging');
  }});
  svg.addEventListener('pointermove', (event) => {{
    if (!dragging) return;
    if (Math.abs(event.clientX - lastX) + Math.abs(event.clientY - lastY) > 3) moved = true;
    tx += event.clientX - lastX; ty += event.clientY - lastY;
    lastX = event.clientX; lastY = event.clientY; apply();
  }});
  svg.addEventListener('pointerup', () => {{ dragging = false; svg.classList.remove('dragging'); }});
  svg.addEventListener('pointercancel', () => {{ dragging = false; svg.classList.remove('dragging'); }});
  svg.addEventListener('dblclick', overview);
  document.getElementById('reset').addEventListener('click', actualSize);
  document.getElementById('fit').addEventListener('click', fitWidth);
  document.getElementById('overview').addEventListener('click', overview);
  overview();
  const initial = decodeURIComponent(location.hash.slice(1));
  if (initial && DETAILS[initial]) show(initial);
</script>
</body>
</html>
"""


def render_html(payload: dict, title: str) -> str:
    roots = load_nodes(payload)
    placed, _, _ = layout_forest(roots, "down")
    projected: list[tuple[PlanNode, float, float, float]] = []
    for node, x, y in placed:
        z = LEVEL_Z.get(node.level, 0)
        projected.append((node, x + z * DEPTH_X, y - z, z))
    min_x = min(min(px - z * DEPTH_X, px - 10) for _, px, py, z in projected)
    max_x = max(px + NODE_W + 10 for _, px, py, z in projected)
    min_y = min(py - 10 for _, px, py, z in projected)
    max_y = max(py + NODE_H + z for _, px, py, z in projected)
    shift_x = 24 - min_x
    shift_y = 24 - min_y
    projected = [
        (node, px + shift_x, py + shift_y, z) for node, px, py, z in projected
    ]
    width = (max_x - min_x) + 48
    height = (max_y - min_y) + 48

    body = (
        ground_markup(projected)
        + halo_markup(projected)
        + edge_markup(projected, "down")
        + svg_markup(projected)
        + card_mark_markup(projected, payload.get("edges", []))
        + '<g id="hot-layer"></g>'
    )
    details = {
        node.node_id: {
            "id": node.node_id,
            "title": node.title,
            "level": node.level,
            "status": node.status,
            "updated": node.detail.get("updated", ""),
            "parent": node.parent,
            "source": node.detail.get("source", ""),
            "objective": node.detail.get("objective", ""),
            "deliverables": node.detail.get("deliverables", []),
            "acceptance": node.detail.get("acceptance", []),
            "links": node.detail.get("links", {}),
            "evidence": node.detail.get("evidence", []),
        }
        for node, _, _, _ in projected
    }

    relations: dict[str, dict] = {
        node_id: {"parent": detail["parent"], "children": [], "out": [], "in": []}
        for node_id, detail in details.items()
    }
    for node_id, detail in details.items():
        parent = detail["parent"]
        if parent in relations:
            relations[parent]["children"].append(node_id)
    for edge in payload.get("edges", []):
        relation = edge.get("relationship")
        if relation == "decomposes_to":
            continue
        source, target = edge.get("from"), edge.get("to")
        if source in relations and target in relations:
            relations[source]["out"].append({"type": relation, "target": target})
            relations[target]["in"].append({"type": relation, "target": source})
    for entry in relations.values():
        entry["children"].sort()
        entry["out"].sort(key=lambda item: (item["type"], item["target"]))
        entry["in"].sort(key=lambda item: (item["type"], item["target"]))

    counts: dict[str, int] = {}
    for node, _, _, _ in projected:
        counts[node.status] = counts.get(node.status, 0) + 1
    labels = {
        "done": "done",
        "in_progress": "in progress",
        "proposed": "proposed",
        "blocked": "blocked",
        "superseded": "superseded",
    }
    filter_html = "".join(
        (
            f'<button class="filter" data-status="{status}" title="filter {labels[status]}">'
            f'<span class="swatch" style="background:{STATUS_STYLE[status][0]};'
            f'border:1px solid {STATUS_STYLE[status][1]}"></span>'
            f'{labels[status]} <b>{counts[status]}</b></button>'
        )
        for status in ("done", "in_progress", "proposed", "blocked", "superseded")
        if counts.get(status)
    )

    page = HTML.replace("{{", "{").replace("}}", "}")
    return (
        page.replace("{title}", title)
        .replace("{filters}", filter_html)
        .replace("{width}", f"{width:.0f}")
        .replace("{height}", f"{height:.0f}")
        .replace("{body}", body)
        .replace("{details}", json.dumps(details, ensure_ascii=False).replace("</", "<\\/"))
        .replace("{relations}", json.dumps(relations, ensure_ascii=False).replace("</", "<\\/"))
    )

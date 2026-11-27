#!/usr/bin/env python3
"""Render a self-contained interactive Four-Graph Studio (`_aiHumanInteract/studio/index.html`).

Refined v2 after visual critique:
- Progressive Hebbian disclosure (calm whisper top-backbone in idle overview, vivid full
  synaptic fan-out on hover, node selection, or Dual-Path Spreading Probe; optional full mesh).
- Direction-aware orthogonal & spine routing (stacked WP spine on left channel, upward imports
  routed cleanly around outer channel without cutting through cards, deduplicated parallel edges).
- Responsive topbar & automatic smooth viewport refit when the right-hand inspector opens/resizes.
- Top-docked Dual-Path command search (`⌘K`) that never occludes bottom controls or lower canvas.
"""

from __future__ import annotations

import html
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


CARD_W = 264
CARD_H = 78
GAP_X = 56
GAP_Y = 66
LEAF_GAP = 24

LEVEL_Z = {"long-term": 36, "mid-term": 24, "short-term": 12, "work-package": 0}
DEPTH_X = 0.34

LANG_BADGE = {
    "python": "PY",
    "typescript": "TS",
    "javascript": "JS",
    "vue": "VUE",
    "shell": "SH",
    "unknown": "FILE",
}
ROLE_BADGE = {
    "entrypoint": "ENTRY",
    "module": "MODULE",
    "test": "TEST",
    "planned_target": "PLANNED",
}

GRAPH_ACCENT = {
    "intent": "#6E5DC6",
    "specs": "#2C6B67",
    "plan_lt": "#7766A6",
    "plan_mt": "#6487AD",
    "plan_st": "#6F9DA2",
    "plan_wp": "#9AA5B1",
    "knowledge_debt": "#C88A2E",
    "scripts": "#3B7A8C",
}

SPEC_KIND_TAG = {
    "invariant": "INVARIANT",
    "glossary": "GLOSSARY",
    "standard": "STANDARD",
    "contract": "CONTRACT",
}

STATUS_PALETTE = {
    "proposed": ("#EFF5FC", "#B3C9E2", "#2B4F73"),
    "ready": ("#EAF7F5", "#9CCFC7", "#1F5A52"),
    "in_progress": ("#FFF4E8", "#E7BA91", "#7D4E27"),
    "blocked": ("#FCEEEE", "#E0ACAC", "#873F3F"),
    "done": ("#EDF7F0", "#A7CEB4", "#234B36"),
    "superseded": ("#F1F2F4", "#C9CDD2", "#777D85"),
    "exploring": ("#F4F1FC", "#C5B8EA", "#4A3880"),
    "clarified": ("#EDF6FA", "#A5CBE0", "#23516B"),
    "crystallized": ("#EDF7F0", "#A7CEB4", "#234B36"),
    "reopened": ("#FFF2EC", "#E6B098", "#8A4224"),
    "enforced": ("#EBF6F4", "#8EC4BA", "#184A43"),
    "draft": ("#F2F5F8", "#BCC6D2", "#3E4C59"),
    "deprecated": ("#F5F2EE", "#D3C5B4", "#6E5A44"),
    "open": ("#FDF6E7", "#E2C285", "#7A5213"),
    "affirmed": ("#EDF7F0", "#A7CEB4", "#234B36"),
    "rejected": ("#FCEEEE", "#DF9F9F", "#873535"),
    "clean": ("#F3F7F9", "#B8CCD6", "#264A5A"),
    "modified": ("#FFF6EA", "#E4BE8E", "#7A4E1D"),
    "untracked": ("#EFF5FC", "#B3C9E2", "#2B4F73"),
    "planned_missing": ("#FCEEEE", "#E0ACAC", "#873F3F"),
}


@dataclass
class TreeItem:
    nid: str
    parent: str | None
    level: str
    children: list["TreeItem"] = field(default_factory=list)


def _text_w(text: str) -> float:
    return sum(12.3 if ord(ch) > 0x2E80 else 6.6 for ch in text)


def _wrap(text: str, max_w: float = 234, max_lines: int = 2) -> list[str]:
    lines: list[str] = []
    cur = ""
    idx = 0
    while idx < len(text):
        ch = text[idx]
        if _text_w(cur + ch) <= max_w:
            cur += ch
            idx += 1
            continue
        if len(lines) == max_lines - 1:
            break
        cut = max(cur.rfind(" "), cur.rfind("("), cur.rfind("（"))
        if cut > 4 and len(cur) - cut <= 18:
            lines.append(cur[:cut].rstrip())
            cur = cur[cut:].lstrip() + ch
        else:
            lines.append(cur.rstrip())
            cur = ch
        idx += 1
    if len(lines) < max_lines and cur:
        lines.append(cur.rstrip())
    if idx < len(text) and lines:
        lines[-1] = lines[-1].rstrip(" .·(") + "…"
    return lines[:max_lines]


def _layout_tree(
    items: list[TreeItem],
    *,
    stack_threshold: int = 3,
) -> tuple[dict[str, tuple[float, float]], float, float, set[str]]:
    """Stepped architectural tree layout; also returns IDs placed inside vertical leaf stacks."""
    by_id = {it.nid: it for it in items}
    roots: list[TreeItem] = []
    for it in items:
        if it.parent and it.parent in by_id:
            by_id[it.parent].children.append(it)
        else:
            roots.append(it)
    for it in items:
        it.children.sort(key=lambda c: c.nid)
    roots.sort(key=lambda r: r.nid)
    stacked_ids: set[str] = set()

    def sub(node: TreeItem) -> tuple[float, float, list[tuple[str, float, float]], float]:
        if not node.children:
            return CARD_W, CARD_H, [(node.nid, 0.0, 0.0)], 0.0
        groups: list[list[TreeItem]] = []
        i = 0
        while i < len(node.children):
            if node.children[i].children:
                groups.append([node.children[i]])
                i += 1
                continue
            j = i
            while j < len(node.children) and not node.children[j].children:
                j += 1
            run = node.children[i:j]
            if len(run) >= stack_threshold:
                groups.append(run)
                for lf in run:
                    stacked_ids.add(lf.nid)
            else:
                groups.extend([[leaf] for leaf in run])
            i = j

        blocks: list[tuple[float, float, list[tuple[str, float, float]], float]] = []
        for grp in groups:
            if len(grp) >= stack_threshold:
                h = len(grp) * CARD_H + (len(grp) - 1) * LEAF_GAP
                pts = [(lf.nid, 0.0, k * (CARD_H + LEAF_GAP)) for k, lf in enumerate(grp)]
                blocks.append((CARD_W, h, pts, 0.0))
            else:
                blocks.append(sub(grp[0]))

        tot_w = sum(b[0] for b in blocks) + GAP_X * (len(blocks) - 1)
        ch_h = max(b[1] for b in blocks)
        placed: list[tuple[str, float, float]] = []
        centers: list[float] = []
        cx = 0.0
        for bw, _, bpts, broot_x in blocks:
            centers.append(cx + broot_x + CARD_W / 2)
            for cid, bx, by in bpts:
                placed.append((cid, cx + bx, CARD_H + GAP_Y + by))
            cx += bw + GAP_X
        px = (centers[0] + centers[-1]) / 2 - CARD_W / 2
        placed.append((node.nid, px, 0.0))
        return tot_w, CARD_H + GAP_Y + ch_h, placed, px

    if not roots:
        return {}, 0.0, 0.0, stacked_ids

    rblocks = [sub(r) for r in roots]
    coords: dict[str, tuple[float, float]] = {}
    cur_x = 0.0
    max_h = 0.0
    for bw, bh, bpts, _ in rblocks:
        for nid, x, y in bpts:
            coords[nid] = (cur_x + x, y)
        cur_x += bw + GAP_X * 1.5
        max_h = max(max_h, bh)
    total_w = max(CARD_W, cur_x - GAP_X * 1.5)
    return coords, total_w, max_h, stacked_ids


def _layout_scripts(
    script_nodes: list[dict[str, Any]],
    script_edges: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, tuple[float, float]], float, float, list[dict[str, Any]]]:
    """Sugiyama-style topological DAG layout for the Scripts Graph.

    Places Callers strictly ABOVE Callees so every `imports`/`invokes` arrow flows
    naturally downward without upward detours or knots:
      - Row 0 (top)      : Test suites (`role == "test"`)
      - Rows 1..K        : Connected modules ranked top-down by longest dependency path
                           with 2-pass barycenter crossing minimization
      - Bottom row       : Planned / missing target modules (if any)
      - Dedicated right column: Standalone scripts/configs with 0 internal edges
    """
    if not script_nodes:
        return {}, 0.0, 0.0, []

    node_by_id = {n["id"]: n for n in script_nodes}
    dep_rels = {"imports", "invokes"}
    adj: dict[str, set[str]] = {n["id"]: set() for n in script_nodes}
    radj: dict[str, set[str]] = {n["id"]: set() for n in script_nodes}
    for e in script_edges or []:
        if e.get("relationship") not in dep_rels:
            continue
        u, v = e.get("from"), e.get("to")
        if u in node_by_id and v in node_by_id and u != v:
            adj[u].add(v)
            radj[v].add(u)

    tests: list[dict[str, Any]] = []
    planned: list[dict[str, Any]] = []
    connected: list[dict[str, Any]] = []
    standalone: list[dict[str, Any]] = []

    for s in sorted(script_nodes, key=lambda n: (-n.get("centrality", 0.0), n["path"])):
        sid = s["id"]
        if s.get("status") == "planned_missing" or s.get("role") == "planned_target":
            planned.append(s)
        elif s.get("role") == "test":
            tests.append(s)
        elif adj[sid] or radj[sid]:
            connected.append(s)
        else:
            standalone.append(s)

    # Compute topological rank on `connected` modules so every edge u -> v satisfies rank[v] > rank[u].
    conn_ids = {s["id"] for s in connected}
    rank: dict[str, int] = {sid: 0 for sid in conn_ids}
    # Cap iterations at len(conn_ids) so cyclic codebases converge deterministically.
    for _ in range(len(conn_ids)):
        changed = False
        for u in conn_ids:
            for v in adj[u]:
                if v in conn_ids and rank[v] < rank[u] + 1:
                    rank[v] = rank[u] + 1
                    changed = True
        if not changed:
            break

    # Tighten root callers downward to sit 1 layer directly above their highest callee
    # so edges stay short (e.g. a controller calling a deep leaf sits near it).
    for u in conn_ids:
        if not any(p in conn_ids for p in radj[u]):
            callees = [v for v in adj[u] if v in conn_ids]
            if callees:
                rank[u] = max(0, min(rank[v] for v in callees) - 1)

    max_rank = max(rank.values(), default=-1)
    dag_layers: list[tuple[str, str, list[dict[str, Any]]]] = []
    if tests:
        dag_layers.append(("TESTS · 测试守门", "test", tests))

    if max_rank >= 0:
        buckets: list[list[dict[str, Any]]] = [[] for _ in range(max_rank + 1)]
        for s in connected:
            buckets[rank[s["id"]]].append(s)
        non_empty = [b for b in buckets if b]
        n_layers = len(non_empty)
        for idx, bucket in enumerate(non_empty):
            if n_layers == 1:
                label = "MODULES · 核心模块"
            elif idx == 0:
                label = "ENTRY · 入口与顶层"
            elif idx == n_layers - 1:
                label = "CORE LIBS · 底层核心库"
            elif idx == 1 and n_layers >= 4:
                label = "ORCHESTRATION · 应用编排"
            else:
                label = f"LAYER {idx + 1} · 组件与模块"
            dag_layers.append((label, "dag", bucket))

    if planned:
        dag_layers.append(("PLANNED · 规划目标", "planned", planned))

    # 2-pass Barycenter ordering across layers to minimize edge crossings and align caller/callee columns.
    order_pos: dict[str, float] = {}
    for _, _, nodes in dag_layers:
        nodes.sort(key=lambda n: (-n.get("centrality", 0.0), n["path"]))
        for i, n in enumerate(nodes):
            order_pos[n["id"]] = float(i)

    def _barycenter_sort(layer_nodes: list[dict[str, Any]], use_parents: bool) -> None:
        scored: list[tuple[float, float, str, dict[str, Any]]] = []
        for idx, n in enumerate(layer_nodes):
            nid = n["id"]
            nbrs = [p for p in (radj[nid] if use_parents else adj[nid]) if p in order_pos]
            if nbrs:
                avg = sum(order_pos[p] for p in nbrs) / len(nbrs)
            else:
                avg = float(idx) + 0.01
            scored.append((avg, -n.get("centrality", 0.0), n["path"], n))
        scored.sort(key=lambda item: (item[0], item[1], item[2]))
        layer_nodes[:] = [item[3] for item in scored]
        for i, n in enumerate(layer_nodes):
            order_pos[n["id"]] = float(i)

    for _ in range(2):
        for li in range(1, len(dag_layers)):
            _barycenter_sort(dag_layers[li][2], use_parents=True)
        for li in range(len(dag_layers) - 2, -1, -1):
            _barycenter_sort(dag_layers[li][2], use_parents=False)

    scr_gap_x = 64.0
    scr_gap_y = 74.0
    max_per_row = 4
    band_pad_x = 24.0
    band_pad_top = 30.0
    band_pad_bot = 18.0

    max_cols = max((min(max_per_row, len(nodes)) for _, _, nodes in dag_layers), default=1)
    dag_w = max_cols * CARD_W + max(0, max_cols - 1) * scr_gap_x if dag_layers else 0.0

    coords: dict[str, tuple[float, float]] = {}
    bands: list[dict[str, Any]] = []
    cur_y = 0.0

    for label, kind, nodes in dag_layers:
        cols = min(max_per_row, len(nodes))
        rows = math.ceil(len(nodes) / cols)
        band_y = cur_y
        inner_y = cur_y + band_pad_top
        for r in range(rows):
            row_nodes = nodes[r * cols : (r + 1) * cols]
            row_w = len(row_nodes) * CARD_W + max(0, len(row_nodes) - 1) * scr_gap_x
            x_pad = (dag_w - row_w) / 2.0
            for c, s in enumerate(row_nodes):
                coords[s["id"]] = (
                    round(x_pad + c * (CARD_W + scr_gap_x), 1),
                    round(inner_y + r * (CARD_H + 28.0), 1),
                )
        inner_h = rows * CARD_H + max(0, rows - 1) * 28.0
        band_h = band_pad_top + inner_h + band_pad_bot
        bands.append({
            "label": label,
            "kind": kind,
            "x": round(-band_pad_x, 1),
            "y": round(band_y, 1),
            "w": round(dag_w + band_pad_x * 2, 1),
            "h": round(band_h, 1),
        })
        cur_y += band_h + (scr_gap_y - band_pad_top - band_pad_bot + 26.0)

    dag_h = max(CARD_H, cur_y - (scr_gap_y - band_pad_top - band_pad_bot + 26.0)) if dag_layers else 0.0

    total_w = dag_w
    total_h = dag_h

    if standalone:
        st_x = (dag_w + band_pad_x * 2 + 56.0) if dag_layers else 0.0
        st_cols = 1 if len(standalone) <= 5 else 2
        st_rows = math.ceil(len(standalone) / st_cols)
        st_inner_w = st_cols * CARD_W + max(0, st_cols - 1) * 32.0
        st_inner_h = st_rows * CARD_H + max(0, st_rows - 1) * 26.0
        for idx, s in enumerate(standalone):
            c, r = idx % st_cols, idx // st_cols
            coords[s["id"]] = (
                round(st_x + c * (CARD_W + 32.0), 1),
                round(band_pad_top + r * (CARD_H + 26.0), 1),
            )
        st_band_h = band_pad_top + st_inner_h + band_pad_bot
        bands.append({
            "label": "STANDALONE · 独立脚本与配置",
            "kind": "standalone",
            "x": round(st_x - band_pad_x, 1),
            "y": 0.0,
            "w": round(st_inner_w + band_pad_x * 2, 1),
            "h": round(st_band_h, 1),
        })
        total_w = st_x + st_inner_w + band_pad_x
        total_h = max(total_h, st_band_h)

    return coords, max(CARD_W, total_w), max(CARD_H, total_h), bands


def _compute_all_layouts(federated: Mapping[str, Any]) -> tuple[dict[str, Any], set[str]]:
    intent_nodes = federated.get("intent", {}).get("nodes", [])
    spec_nodes = federated.get("specs", {}).get("nodes", [])
    plan_nodes = federated.get("plan", {}).get("nodes", [])
    kd_nodes = federated.get("knowledge_debt", {}).get("nodes", [])
    script_nodes = federated.get("scripts", {}).get("nodes", [])

    int_items = [
        TreeItem(
            nid=n["id"],
            parent=n.get("parent"),
            level="intent",
        )
        for n in intent_nodes
    ]
    int_pos, int_w, int_h, int_stacked = _layout_tree(int_items, stack_threshold=3)

    spec_items = [
        TreeItem(
            nid=n["id"],
            parent=n.get("parent"),
            level="spec",
        )
        for n in spec_nodes
    ]
    spec_pos, spec_w, spec_h, spec_stacked = _layout_tree(spec_items, stack_threshold=5)

    kd_pos: dict[str, tuple[float, float]] = {}
    cols_kd = max(1, min(3, len(kd_nodes)))
    for idx, k in enumerate(kd_nodes):
        c, r = idx % cols_kd, idx // cols_kd
        kd_pos[k["id"]] = (c * (CARD_W + 40), r * (CARD_H + 28))
    kd_w = cols_kd * CARD_W + max(0, cols_kd - 1) * 40 if kd_nodes else 0.0
    kd_h = (math.ceil(len(kd_nodes) / cols_kd) * (CARD_H + 28) - 28) if kd_nodes else 0.0

    plan_items = [
        TreeItem(nid=n["id"], parent=n.get("parent"), level=n["level"])
        for n in plan_nodes
    ]
    plan_base_pos, plan_w, plan_h, plan_stacked = _layout_tree(plan_items, stack_threshold=3)
    # Note: apply 2.5D vertical lift (`y - z`), keeping horizontal `x` aligned so parent->child vertical stems stay 100% plumb without 4px kinks!
    plan_pos: dict[str, tuple[float, float]] = {}
    for n in plan_nodes:
        bx, by = plan_base_pos.get(n["id"], (0.0, 0.0))
        z = LEVEL_Z.get(n["level"], 0)
        plan_pos[n["id"]] = (bx, by - z * 0.55)

    script_edges = federated.get("scripts", {}).get("edges", [])
    scr_pos, scr_w, scr_h, scr_bands = _layout_scripts(script_nodes, script_edges)

    margin = 86.0
    band_gap_x = 124.0
    stratum_gap_y = 124.0

    epistemic_w = int_w + (band_gap_x + kd_w if kd_w > 0 and int_w > 0 else kd_w)
    epistemic_h = max(int_h, kd_h, CARD_H)
    normative_w = max(spec_w, CARD_W) if spec_nodes else 0.0
    normative_h = max(spec_h, CARD_H) if spec_nodes else 0.0
    pragmatic_w = plan_w + (band_gap_x + scr_w if scr_w > 0 and plan_w > 0 else scr_w)
    pragmatic_h = max(plan_h + 44, scr_h, CARD_H)

    overview_inner_w = max(epistemic_w, normative_w, pragmatic_w, 720.0)
    epistemic_top = margin + 48.0
    if spec_nodes:
        normative_top = epistemic_top + epistemic_h + stratum_gap_y
        pragmatic_top = normative_top + normative_h + stratum_gap_y
    else:
        normative_top = epistemic_top
        pragmatic_top = epistemic_top + epistemic_h + stratum_gap_y

    overview_pos: dict[str, tuple[float, float]] = {}
    ep_start_x = margin + (overview_inner_w - epistemic_w) / 2
    for nid, (x, y) in int_pos.items():
        overview_pos[nid] = (round(ep_start_x + x, 1), round(epistemic_top + y, 1))
    kd_offset_x = ep_start_x + (int_w + band_gap_x if int_w > 0 else 0.0)
    for nid, (x, y) in kd_pos.items():
        overview_pos[nid] = (round(kd_offset_x + x, 1), round(epistemic_top + y, 1))

    if spec_nodes:
        nm_start_x = margin + (overview_inner_w - normative_w) / 2
        for nid, (x, y) in spec_pos.items():
            overview_pos[nid] = (round(nm_start_x + x, 1), round(normative_top + 18.0 + y, 1))

    pr_start_x = margin + (overview_inner_w - pragmatic_w) / 2
    for nid, (x, y) in plan_pos.items():
        overview_pos[nid] = (round(pr_start_x + x, 1), round(pragmatic_top + 32.0 + y, 1))
    scr_offset_x = pr_start_x + (plan_w + band_gap_x if plan_w > 0 else 0.0)
    for nid, (x, y) in scr_pos.items():
        overview_pos[nid] = (round(scr_offset_x + x, 1), round(pragmatic_top + 20.0 + y, 1))

    def _shift(
        pos_map: dict[str, tuple[float, float]],
        w: float,
        h: float,
        bands: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        pad = 84.0
        out: dict[str, Any] = {
            "positions": {
                k: [round(v[0] + pad, 1), round(v[1] + pad + 26.0, 1)]
                for k, v in pos_map.items()
            },
            "width": round(max(w, 480.0) + pad * 2, 1),
            "height": round(max(h, 300.0) + pad * 2 + 40.0, 1),
        }
        if bands:
            out["bands"] = [
                {
                    **b,
                    "x": round(b["x"] + pad, 1),
                    "y": round(b["y"] + pad + 26.0, 1),
                }
                for b in bands
            ]
        return out

    strata_dict: dict[str, Any] = {
        "epistemic": {
            "x": round(margin - 32, 1),
            "y": round(margin, 1),
            "w": round(overview_inner_w + 64, 1),
            "h": round(epistemic_h + 78, 1),
        },
        "pragmatic": {
            "x": round(margin - 32, 1),
            "y": round(pragmatic_top - 30, 1),
            "w": round(overview_inner_w + 64, 1),
            "h": round(pragmatic_h + 76, 1),
        },
    }
    if spec_nodes:
        strata_dict["normative"] = {
            "x": round(margin - 32, 1),
            "y": round(normative_top - 26, 1),
            "w": round(overview_inner_w + 64, 1),
            "h": round(normative_h + 70, 1),
        }

    layouts = {
        "overview": {
            "positions": {k: [v[0], v[1]] for k, v in overview_pos.items()},
            "width": round(overview_inner_w + margin * 2, 1),
            "height": round(pragmatic_top + pragmatic_h + margin, 1),
            "strata": strata_dict,
        },
        "intent": _shift(int_pos, int_w, int_h),
        "specs": _shift(spec_pos, spec_w, spec_h),
        "plan": _shift(plan_pos, plan_w, plan_h + 44),
        "knowledge_debt": _shift(kd_pos, kd_w, kd_h),
        "scripts": _shift(scr_pos, scr_w, scr_h, scr_bands),
    }
    return layouts, (int_stacked | spec_stacked | plan_stacked)


def _deduplicate_structural_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep ONLY Parent/Children tree edges on Intent, Spec & Plan canvases, plus AST imports/invokes on Scripts."""
    canvas_rels = {"decomposes_to", "decomposes_intent", "decomposes_spec", "imports", "invokes"}
    priority = {
        "decomposes_to": 1,
        "decomposes_intent": 1,
        "decomposes_spec": 1,
        "imports": 1,
        "invokes": 2,
    }
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for e in edges:
        rel = e["relationship"]
        if rel not in canvas_rels:
            continue
        u, v = e["from"], e["to"]
        pair = (u, v)
        if pair not in grouped or priority.get(rel, 9) < priority.get(grouped[pair]["relationship"], 9):
            grouped[pair] = dict(e)
    return list(grouped.values())


def _build_explicit_relations(federated: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Build bidirectional agent-curated relation records for every Intent, Spec, and Plan node."""
    relations: dict[str, dict[str, Any]] = {}
    for graph_key in ("intent", "specs", "plan"):
        gnodes = federated.get(graph_key, {}).get("nodes", [])
        gedges = federated.get(graph_key, {}).get("edges", [])
        for n in gnodes:
            relations[n["id"]] = {
                "parent": n.get("parent"),
                "children": [],
                "depends_on": [],
                "required_by": [],
                "enables": [],
                "enabled_by": [],
                "validates": [],
                "validated_by": [],
                "supersedes": [],
                "superseded_by": [],
                "conflicts_with": [],
                "alternative_of": [],
                "has_alternative": [],
                "refines": [],
                "constrains": [],
            }
        for n in gnodes:
            p = n.get("parent")
            if p and p in relations:
                relations[p]["children"].append(n["id"])
        for e in gedges:
            rel = e.get("relationship")
            u, v = e.get("from"), e.get("to")
            if u not in relations or v not in relations:
                continue
            if rel == "prerequisite_for":
                relations[v]["depends_on"].append(u)
                relations[u]["required_by"].append(v)
            elif rel == "enables":
                relations[u]["enables"].append(v)
                relations[v]["enabled_by"].append(u)
            elif rel == "validates":
                relations[u]["validates"].append(v)
                relations[v]["validated_by"].append(u)
            elif rel == "supersedes":
                relations[u]["supersedes"].append(v)
                relations[v]["superseded_by"].append(u)
            elif rel == "conflicts_with":
                relations[u]["conflicts_with"].append(v)
                relations[v]["conflicts_with"].append(u)
            elif rel == "alternative_of":
                relations[u]["alternative_of"].append(v)
                relations[v]["has_alternative"].append(u)
            elif rel in ("refines", "constrains"):
                relations[u][rel].append(v)

    for entry in relations.values():
        for k, val in list(entry.items()):
            if isinstance(val, list):
                entry[k] = sorted(set(val))
    return relations


def _passive_icon_badges(rel_entry: Mapping[str, Any] | None) -> list[dict[str, str]]:
    """Compact corner micro-stamps for Supersedes/Superseded, Conflicts, and Alternatives."""
    if not rel_entry:
        return []
    badges: list[dict[str, str]] = []
    sup_out = rel_entry.get("supersedes") or []
    sup_in = rel_entry.get("superseded_by") or []
    if sup_out or sup_in:
        if sup_out and not sup_in:
            badges.append({
                "glyph": "↑",
                "tone": "sup-up",
                "tip": f"替代 (Supersedes): {', '.join(sup_out)}",
            })
        elif sup_in and not sup_out:
            badges.append({
                "glyph": "↓",
                "tone": "sup-down",
                "tip": f"被替代于 (Superseded by): {', '.join(sup_in)}",
            })
        else:
            badges.append({
                "glyph": "↕",
                "tone": "sup-up",
                "tip": f"替代 {', '.join(sup_out)} · 被替代于 {', '.join(sup_in)}",
            })
    conf = rel_entry.get("conflicts_with") or []
    if conf:
        badges.append({
            "glyph": "✕",
            "tone": "conflict",
            "tip": f"冲突 (Conflicts with): {', '.join(conf)}",
        })
    alt_of = rel_entry.get("alternative_of") or []
    has_alt = rel_entry.get("has_alternative") or []
    if alt_of or has_alt:
        glyph = "◎" if has_alt and not alt_of else "⇄"
        parts = []
        if alt_of:
            parts.append(f"备选基线: {', '.join(alt_of)}")
        if has_alt:
            parts.append(f"拥有备选: {', '.join(has_alt)}")
        badges.append({
            "glyph": glyph,
            "tone": "alt",
            "tip": " · ".join(parts),
        })
    return badges


def _collect_prototype_svgs(
    repo_root: Path,
    intent_nodes: list[dict[str, Any]],
    eval_nodes: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    svgs: dict[str, str] = {}
    refs: list[str] = []
    for inode in intent_nodes:
        for alt in inode.get("implementation_alternatives", []):
            if isinstance(alt, dict) and alt.get("prototype"):
                refs.append(str(alt["prototype"]))
        for c in inode.get("concepts", []):
            if isinstance(c, dict) and c.get("prototype"):
                refs.append(str(c["prototype"]))
    for enode in eval_nodes or []:
        for eref in enode.get("evidence_refs", []):
            refs.append(str(eref))
    for ref in refs:
        if ref in svgs or not ref.endswith(".svg"):
            continue
        target = (repo_root / ref).resolve()
        try:
            target.relative_to(repo_root.resolve())
        except ValueError:
            continue
        if target.is_file() and target.stat().st_size <= 120_000:
            svgs[ref] = target.read_text(encoding="utf-8", errors="replace")
    return svgs


STUDIO_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>PtM Curated Studio — {title}</title>
<style>
  :root {
    color-scheme: light;
    --paper: #F6F6F4;
    --surface: rgba(255, 255, 255, 0.94);
    --ink: #232D37;
    --muted: #74808B;
    --line: #DDE2E7;
    --focus: #3E68A8;
    --panel-w: 430px;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; height: 100%; overflow: hidden;
    background: var(--paper); color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans CJK SC", "Segoe UI", sans-serif;
  }
  #canvas {
    width: 100%; height: 100%; display: block;
    cursor: grab; user-select: none; -webkit-user-select: none; touch-action: none;
  }
  #canvas.dragging { cursor: grabbing; }
  #canvas text { user-select: none; -webkit-user-select: none; }

  /* Responsive Top Bar — shifts left smoothly when right inspector opens */
  #topbar {
    position: fixed; top: 14px; left: 16px; right: 16px; z-index: 30;
    display: flex; align-items: center; justify-content: space-between; gap: 10px;
    pointer-events: none; transition: right .2s ease;
  }
  body.panel-open #topbar { right: calc(var(--panel-w) + 16px); }

  .bar-cluster {
    pointer-events: auto;
    display: flex; align-items: center; gap: 5px; flex-wrap: wrap;
    background: var(--surface); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--line); border-radius: 11px; padding: 5px 9px;
    box-shadow: 0 3px 14px rgba(24, 34, 44, 0.055);
  }
  .brand {
    font-size: 12.5px; font-weight: 700; padding: 0 5px 0 2px;
    color: #1F2933; display: flex; align-items: center; gap: 6px;
  }
  .brand-badge {
    font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 5px;
    background: #ECEAE4; color: #52606D;
  }
  .sep { width: 1px; height: 17px; background: var(--line); margin: 0 2px; }
  .lens-btn {
    border: 1px solid transparent; background: transparent; color: #4A5562;
    font: inherit; font-size: 11px; font-weight: 500; padding: 3.5px 7.5px;
    border-radius: 7px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;
    white-space: nowrap; transition: background .14s ease, color .14s ease;
  }
  .lens-btn:hover { background: #EFECE6; color: #1F2933; }
  .lens-btn.active { background: #232D37; color: #FFFFFF; font-weight: 600; }
  .lens-btn .cnt {
    font-size: 9.5px; opacity: 0.82; font-variant-numeric: tabular-nums;
    padding: 0 4px; border-radius: 4px; background: rgba(120,130,140,0.14);
  }
  .lens-btn.active .cnt { background: rgba(255,255,255,0.22); opacity: 1; }

  .toggle-pill {
    border: 1px solid var(--line); background: #FFFFFF; color: #52606D;
    font: inherit; font-size: 11px; font-weight: 500; padding: 3.5px 8.5px;
    border-radius: 999px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;
    white-space: nowrap;
  }
  .toggle-pill.on { border-color: #C88A2E; background: #FDF6E7; color: #7A5213; font-weight: 600; }
  .toggle-pill.cross-on { border-color: #6E5DC6; background: #F3F1FC; color: #44338A; font-weight: 600; }
  .toggle-pill.verify-on { border-color: #6CA888; background: #ECF7F0; color: #1B5E37; font-weight: 600; }
  .toggle-pill.verify-attn { border-color: #DF8A52; background: #FFF1E6; color: #8F3D14; font-weight: 700; }
  .toggle-pill:disabled { opacity: 0.42; cursor: default; }

  /* Legend Strip */
  #legend {
    position: fixed; left: 16px; bottom: 58px; z-index: 24;
    background: rgba(255,255,255,0.88); border: 1px solid var(--line);
    border-radius: 8px; padding: 5px 10px; font-size: 10.5px; color: #52606D;
    display: flex; align-items: center; gap: 12px; pointer-events: none;
  }
  .leg-item { display: inline-flex; align-items: center; gap: 5px; }
  .leg-line { width: 16px; height: 0; border-top: 1.6px solid #9AA5B1; }
  .leg-line.cross { border-top: 1.6px dashed #6E5DC6; }
  .leg-line.hebb { border-top: 2px dotted #C88A2E; }

  /* Bottom Controls */
  #bottombar {
    position: fixed; left: 16px; bottom: 14px; z-index: 28;
    display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
    background: var(--surface); backdrop-filter: blur(12px);
    border: 1px solid var(--line); border-radius: 10px; padding: 5px 9px;
    box-shadow: 0 3px 12px rgba(24, 34, 44, 0.06); font-size: 11px;
  }
  .ctrl-btn {
    border: 1px solid #D3D9DF; background: #FFF; color: #3E4C59;
    border-radius: 6px; padding: 3px 8px; font: inherit; font-size: 11px; cursor: pointer;
  }
  .ctrl-btn:hover { background: #F5F7F9; }
  .ctrl-btn kbd { font-size: 10px; color: #82909D; font-family: inherit; }
  #probe-banner {
    display: none; align-items: center; gap: 6px; padding: 3px 9px;
    border-radius: 6px; background: #FDF6E7; border: 1px solid #E2C285; color: #7A5213;
    font-weight: 600;
  }
  #probe-banner.on { display: inline-flex; }
  #probe-clear { border: 0; background: none; color: #7A5213; cursor: pointer; font-size: 13px; padding: 0 2px; }

  /* Top-Docked Dual-Path Command Surface — never collides with bottom HUD or lower canvas */
  #search-surface {
    position: fixed; left: 50%; top: 64px; transform: translateX(-50%);
    width: min(680px, calc(100vw - 48px)); z-index: 45;
    background: rgba(255,255,255,0.96); backdrop-filter: blur(16px);
    border: 1px solid #CFD6DE; border-radius: 13px; padding: 10px;
    box-shadow: 0 16px 44px rgba(15, 23, 32, 0.16);
    transition: left .2s ease;
  }
  body.panel-open #search-surface { left: calc((100vw - var(--panel-w)) / 2); width: min(640px, calc(100vw - var(--panel-w) - 40px)); }
  #search-surface[hidden] { display: none; }
  .s-box { display: flex; align-items: center; gap: 8px; padding-bottom: 7px; border-bottom: 1px solid #EBEEF2; }
  #search-input {
    flex: 1; border: 1px solid #CBD2D9; border-radius: 8px; padding: 6px 11px;
    font: inherit; font-size: 12.5px; color: #1F2933; background: #FFF;
  }
  #search-input:focus { outline: none; border-color: var(--focus); box-shadow: 0 0 0 3px rgba(62,104,168,0.16); }
  #search-results { max-height: 240px; overflow-y: auto; padding-top: 6px; }
  .s-row {
    display: flex; align-items: center; gap: 8px; padding: 6px 9px;
    border-radius: 7px; cursor: pointer; font-size: 12px;
  }
  .s-row:hover { background: #EEF3FA; }
  .s-badge {
    font-size: 9.5px; font-weight: 700; padding: 1px 6px; border-radius: 4px;
    text-transform: uppercase; letter-spacing: 0.04em; flex: none; white-space: nowrap;
  }
  .s-badge.base { background: #E6EFFA; color: #2B5488; }
  .s-badge.flip { background: #FDF3DC; color: #8C5811; border: 1px solid #E9C77B; }
  .s-badge.thr { background: #ECF7F4; color: #19574E; border: 1px solid #96CFC5; }
  .s-id { font-weight: 600; color: #3E4C59; font-family: ui-monospace, SFMono-Regular, monospace; font-size: 11px; flex: none; }
  .s-title { color: #1F2933; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
  .s-via { font-size: 10.5px; color: #8C5811; white-space: nowrap; flex: none; }

  /* Right Curated Reasoning & Detail Inspector */
  #panel {
    position: fixed; top: 0; right: 0; width: var(--panel-w); height: 100%; z-index: 35;
    background: #FFFFFF; border-left: 1px solid var(--line);
    box-shadow: -6px 0 24px rgba(15, 23, 32, 0.08);
    display: flex; flex-direction: column; font-size: 12.5px; line-height: 1.58;
  }
  #panel[hidden] { display: none; }
  #panel-resizer {
    position: absolute; left: -6px; top: 0; bottom: 0; width: 12px; cursor: col-resize; z-index: 2;
  }
  #panel-head {
    padding: 16px 18px 12px; border-bottom: 1px solid #E9ECEF; position: relative;
  }
  #panel-close {
    position: absolute; top: 11px; right: 13px; border: 0; background: none;
    font-size: 20px; color: #7B8794; cursor: pointer; line-height: 1;
  }
  .p-kicker {
    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
    color: #616E7C; margin-bottom: 4px;
  }
  #panel-head h2 { margin: 0 24px 5px 0; font-size: 14.5px; line-height: 1.38; color: #1F2933; }
  .p-meta { font-size: 11px; color: #616E7C; }
  .p-actions { margin-top: 9px; display: flex; gap: 6px; flex-wrap: wrap; }
  .p-btn {
    border: 1px solid #CBD2D9; background: #FFF; color: #232D37;
    font: inherit; font-size: 11px; font-weight: 600; padding: 4px 9px;
    border-radius: 6px; cursor: pointer;
  }
  .p-btn:hover { background: #F5F7F9; }
  .p-btn.hebb { border-color: #DFB56B; background: #FDF6E7; color: #7A5213; }
  .p-btn.warn { border-color: #DF9F9F; background: #FCEEEE; color: #873535; }
  .p-btn.warn.active { background: #873535; color: #FFF; }

  #panel-body { flex: 1; overflow-y: auto; padding: 12px 18px 28px; }
  .sec-title {
    margin: 15px 0 6px; font-size: 10.5px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.08em; color: #7B8794;
  }
  .quote-box {
    background: #F8F7F4; border-left: 3px solid #6E5DC6; padding: 8px 11px;
    border-radius: 0 7px 7px 0; font-size: 12px; color: #2E3842; margin: 5px 0;
  }
  .concept-card {
    border: 1px solid #E4E7EB; border-radius: 8px; padding: 9px 11px; margin: 7px 0;
    background: #FCFCFB;
  }
  .concept-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; font-weight: 600; font-size: 12.5px; }
  .variant-list { margin: 6px 0 0; padding: 0; list-style: none; }
  .variant-item {
    padding: 5px 8px; margin: 4px 0; border-radius: 6px; font-size: 11.5px;
    border: 1px solid #EBEEF2; background: #FFF; display: flex; justify-content: space-between; align-items: center; gap: 10px;
  }
  .variant-item .v-status { white-space: nowrap; flex-shrink: 0; font-size: 10.5px; color: #616E7C; }
  .variant-item.chosen { border-color: #8FC4B9; background: #EDF8F5; color: #194D44; font-weight: 600; }
  .variant-item.chosen .v-status { color: #194D44; font-weight: 700; }
  .proto-frame {
    margin-top: 8px; border: 1px solid #DDE2E7; border-radius: 8px; padding: 7px;
    background: #F9F9F7;
  }
  .proto-frame svg { width: 100%; height: auto; display: block; border-radius: 4px; }
  .triage-grid { display: flex; flex-direction: column; gap: 6px; margin-top: 6px; }
  .triage-opt {
    border: 1px solid #DDE2E7; border-radius: 7px; padding: 7px 10px; cursor: pointer;
    background: #FFF; text-align: left; font: inherit; font-size: 11.5px; transition: all .12s ease;
  }
  .triage-opt:hover { border-color: #9AA5B1; }
  .triage-opt.selected-agree { border-color: #88C49C; background: #EDF7F0; }
  .triage-opt.selected-proto { border-color: #E2C285; background: #FDF6E7; }
  .triage-opt.selected-reject { border-color: #DF9F9F; background: #FCEEEE; }
  .cmd-preview {
    margin-top: 8px; padding: 8px 10px; background: #1F2933; color: #E4E7EB;
    border-radius: 6px; font-family: ui-monospace, SFMono-Regular, monospace; font-size: 11px;
    word-break: break-all;
  }
  .chip-wrap { display: flex; flex-direction: column; gap: 5px; margin-top: 4px; }
  .chip-link {
    display: flex; align-items: baseline; justify-content: space-between; gap: 8px;
    padding: 5px 9px; border-radius: 7px; border: 1px solid #E1E6EB;
    background: #F9FAFB; color: #24476B; font-size: 11.5px; text-decoration: none; cursor: pointer;
    line-height: 1.4;
  }
  .chip-link:hover { background: #EDF2F8; border-color: #B3C9E2; }
  .chip-link.hebb { border-color: #EAD29E; background: #FDF9F0; color: #7A5213; }
  .chip-meta { font-size: 10.5px; font-family: ui-monospace, SFMono-Regular, monospace; opacity: 0.78; white-space: nowrap; flex-shrink: 0; }

  /* Agent-Curated Explicit Relations Table & Summary */
  .rel-summary {
    margin-top: 7px; font-size: 10.5px; color: #4A5562;
    display: flex; flex-wrap: wrap; gap: 4px 8px;
  }
  .rel-summary span {
    background: rgba(255,255,255,0.68); border: 1px solid rgba(130,145,160,0.28);
    border-radius: 999px; padding: 1px 7px;
  }
  .rel-summary b { font-weight: 700; color: #1F2933; }
  .rel-summary span.hebb-cnt { border-color: #E2C285; background: #FDF6E7; color: #7A5213; }
  .rel-summary span.ver-ok { border-color: #84C39B; background: #E6F5EC; color: #185A34; font-weight: 600; }
  .rel-summary span.ver-warn { border-color: #E0AE58; background: #FFF3DF; color: #8A530B; font-weight: 600; }
  .rel-summary span.ver-fail { border-color: #E09494; background: #FDECEC; color: #962828; font-weight: 600; }
  .rel-summary span.eval-ok { border-color: #AEB8E8; background: #EEF1FC; color: #364584; font-weight: 600; }
  .rel-summary span.eval-warn { border-color: #E5A882; background: #FFF0E6; color: #8F3D14; font-weight: 600; }
  .rel-summary span.thr-cnt { border-color: #96CFC5; background: #EBF7F5; color: #19574E; font-weight: 600; }

  /* Disentangled Episodic Topic Threads (Turn -> Span -> Thread) */
  .thr-card {
    border: 1px solid #D8E3E1; border-radius: 9px; padding: 9px 11px;
    background: #FBFDFC; margin: 6px 0;
  }
  .thr-card.active {
    border-color: #88C4B8; background: #F6FBF9;
  }
  .thr-capsule {
    margin-top: 5px; padding: 6.5px 9px; border-radius: 6px;
    background: #EFF6F4; border-left: 3px solid #2C6B67;
    font-size: 11.5px; color: #1F3A37; line-height: 1.46;
  }
  .thr-details { margin-top: 6px; }
  .thr-details summary {
    cursor: pointer; font-size: 11px; font-weight: 600; color: #2A5C56;
    user-select: none; padding: 2px 0;
  }
  .thr-details summary:hover { color: #163C38; }
  .span-item {
    margin-top: 7px; padding: 7px 9px; border-radius: 7px;
    background: #FFFFFF; border: 1px solid #E3E8EC; font-size: 11.3px; line-height: 1.46;
  }
  .span-prov {
    display: flex; align-items: center; justify-content: space-between; gap: 6px;
    font-size: 10px; font-family: ui-monospace, SFMono-Regular, monospace;
    color: #616E7C; margin-bottom: 4px;
  }
  .span-prov-badge {
    background: #EDF2F7; border: 1px solid #CBD5E0; color: #334E68;
    padding: 0.5px 5px; border-radius: 4px; font-weight: 600;
  }
  .span-u { color: #1F2933; margin-bottom: 4px; }
  .span-u b { color: #5243AA; }
  .span-a { color: #334E68; padding-top: 4px; border-top: 1px dashed #E6EBF0; }
  .span-a b { color: #1F5A52; }

  /* Dual-Track Formal Verification & Substantive Evaluation Inspector Cards */
  .ver-card, .eval-card {
    border: 1px solid #DCE3EA; border-radius: 9px; padding: 9px 11px;
    background: #FAFBFD; margin: 6px 0;
  }
  .eval-card.concerns, .eval-card.fail {
    border-color: #E6B596; background: #FFFDFB;
  }
  .ver-head {
    display: flex; align-items: center; justify-content: space-between; gap: 8px;
    font-weight: 700; font-size: 12px; color: #1F2933;
  }
  .ver-pill {
    font-size: 10px; font-weight: 700; padding: 1.5px 7px; border-radius: 999px;
    white-space: nowrap; flex: none;
  }
  .ver-pill.verified, .ver-pill.pass, .ver-pill.selected_winner {
    background: #E6F5EC; border: 1px solid #84C39B; color: #185A34;
  }
  .ver-pill.stale, .ver-pill.concerns {
    background: #FFF1E4; border: 1px solid #E3AC72; color: #8A4510;
  }
  .ver-pill.failing, .ver-pill.fail {
    background: #FDECEC; border: 1px solid #E09494; color: #962828;
  }
  .ver-pill.partial {
    background: #EBF3F9; border: 1px solid #A3C2DC; color: #265077;
  }
  .ver-pill.unverified, .ver-pill.noted {
    background: #F1F3F5; border: 1px solid #CBD2D9; color: #52606D;
  }
  .eval-persp {
    margin-top: 4px; font-size: 11px; color: #4A5562;
    display: flex; flex-wrap: wrap; gap: 6px; align-items: center;
  }
  .eval-persp-tag {
    background: #EEF1FC; border: 1px solid #C6CEF0; color: #344382;
    padding: 1px 6px; border-radius: 4px; font-size: 10.5px; font-weight: 600;
  }
  .qual-row {
    padding: 4.5px 8px; border-radius: 6px; font-size: 11px; line-height: 1.42;
    margin-top: 4px; display: flex; align-items: flex-start; gap: 6px;
  }
  .qual-row.preserved { background: #EDF7F0; border: 1px solid #B8DCC4; color: #1E462E; }
  .qual-row.risk { background: #FFF2E8; border: 1px solid #E8B490; color: #883812; font-weight: 500; }

  .rel-card {
    border: 1px solid #E2E7EC; border-radius: 9px; padding: 8px 11px;
    background: #FAFBFD; margin-top: 5px;
  }
  .rel-group-sep {
    height: 1px; background: #EBEEF2; margin: 6px 0;
  }
  .rel-row {
    display: flex; align-items: flex-start; gap: 8px; margin: 3.5px 0;
    font-size: 11.5px; line-height: 1.48;
  }
  .rel-label {
    flex: none; width: 108px; color: #6E7A86; font-size: 11px; font-weight: 500;
    display: inline-flex; align-items: center; gap: 4px;
  }
  .rel-ico {
    display: inline-flex; align-items: center; justify-content: center;
    width: 15px; height: 15px; border-radius: 4px; font-size: 10px; font-weight: 800;
    flex: none;
  }
  .rel-ico.sup-down { background: #ECEFF2; color: #36414C; border: 1px solid #BFC6CE; }
  .rel-ico.sup-up { background: #E6F0FA; color: #1E4976; border: 1px solid #9EC0E2; }
  .rel-ico.conflict { background: #FDECEC; color: #9B2C2C; border: 1px solid #E5A1A1; }
  .rel-ico.alt { background: #F1EEFC; color: #44338A; border: 1px solid #BEB3EC; }
  .rel-values { flex: 1; min-width: 0; display: flex; flex-wrap: wrap; gap: 4px 6px; }
  .rel-empty { color: #B0BAC4; font-size: 11px; }
  .rel-graph-hint { color: #52606D; font-size: 11px; }
  .rel-pill {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 1.5px 7px; border-radius: 5px; border: 1px solid #DCE3EA;
    background: #FFFFFF; color: #24476B; text-decoration: none; font-size: 11px;
    cursor: pointer; max-width: 100%;
  }
  .rel-pill:hover { background: #EDF3FA; border-color: #9EC0E2; }
  .rel-pill .p-txt { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .s-dot { width: 7px; height: 7px; border-radius: 50%; flex: none; border: 1px solid rgba(0,0,0,0.12); }

  /* Spec Graph 4-Pillar Inspector Cards */
  .rule-list { display: flex; flex-direction: column; gap: 5px; margin-top: 5px; }
  .rule-row {
    padding: 5.5px 9px; border-radius: 7px; font-size: 11.5px; line-height: 1.45;
    display: flex; align-items: flex-start; gap: 6px;
  }
  .rule-row.do { background: #EDF7F0; border: 1px solid #B5DAC0; color: #1E462E; }
  .rule-row.dont { background: #FDEEEE; border: 1px solid #E6B0B0; color: #802828; }
  .rule-tag { font-weight: 800; font-size: 10px; white-space: nowrap; margin-top: 1px; }
  .alias-wrap { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
  .term-canon {
    display: inline-flex; align-items: center; gap: 5px; padding: 3px 9px;
    border-radius: 6px; background: #EBF6F4; border: 1px solid #8EC4BA;
    color: #184A43; font-weight: 700; font-size: 11.5px; font-family: ui-monospace, SFMono-Regular, monospace;
  }
  .term-forbid {
    display: inline-flex; align-items: center; gap: 4px; padding: 2.5px 8px;
    border-radius: 6px; background: #FDEEEE; border: 1px solid #E5A6A6;
    color: #8A2C2C; font-size: 11px; text-decoration: line-through;
    font-family: ui-monospace, SFMono-Regular, monospace;
  }
  .contract-sig {
    margin-top: 5px; padding: 8px 10px; border-radius: 7px;
    background: #F4F6F8; border: 1px solid #CFD7DF; color: #1F2933;
    font-family: ui-monospace, SFMono-Regular, monospace; font-size: 11px; line-height: 1.5;
    word-break: break-word;
  }

  /* SVG Scene Styling */
  .stratum-box { fill: rgba(255,255,255,0.48); stroke: #DDDAD2; stroke-width: 1.2; stroke-dasharray: 6 4; }
  .stratum-box.normative { fill: rgba(235, 246, 244, 0.42); stroke: #B6D4CE; }
  .stratum-label { font-size: 11px; font-weight: 700; letter-spacing: 0.08em; fill: #6E7A86; }
  .stratum-sub { font-size: 10.5px; fill: #9AA5B1; }

  .script-band { fill: rgba(255, 255, 255, 0.56); stroke: #DFE4EA; stroke-width: 1; rx: 12; }
  .script-band.test { fill: rgba(238, 246, 252, 0.55); stroke: #CBE0F0; }
  .script-band.standalone { fill: rgba(247, 246, 242, 0.72); stroke: #DCD8CE; stroke-dasharray: 5 4; }
  .script-band-label { font-size: 9.8px; font-weight: 700; letter-spacing: 0.07em; fill: #738291; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }

  .struct-edge { fill: none; stroke: #B0BAC4; stroke-width: 1.35; stroke-linecap: round; stroke-linejoin: round; }
  .struct-edge.script-import { stroke: #4A6480; stroke-width: 1.65; opacity: 0.90; }
  .struct-edge.script-test { stroke: #7B9EC0; stroke-width: 1.25; stroke-dasharray: 4 3; opacity: 0.72; }
  .struct-edge.script-invoke { stroke: #1E7E74; stroke-width: 1.45; stroke-dasharray: 5 3; opacity: 0.85; }
  .struct-edge.script-back { stroke: #C93B3B; stroke-width: 1.65; stroke-dasharray: 5 3; opacity: 0.88; }
  .cross-edge { fill: none; stroke: #7C69C8; stroke-width: 1.2; stroke-dasharray: 5 4; opacity: 0.28; transition: opacity .15s ease; }
  .hebb-edge { fill: none; stroke: #C88A2E; stroke-dasharray: 2 4; opacity: 0.0; pointer-events: none; transition: opacity .15s ease; }
  .hebb-edge.backbone { opacity: 0.20; }
  .hebb-edge.mesh-all { opacity: 0.34; }
  .card-mark { pointer-events: none; }

  .edge-hot { stroke: #3B66A8 !important; stroke-width: 2.25 !important; opacity: 0.96 !important; }
  .edge-hebb-hot { stroke: #C07415 !important; opacity: 0.92 !important; stroke-dasharray: none !important; }
  .edge-blast { stroke: #C93B3B !important; stroke-width: 2.35 !important; opacity: 0.96 !important; stroke-dasharray: 6 3 !important; }

  .g-node { cursor: pointer; transition: opacity .16s ease; }
  .g-node.dimmed { opacity: 0.20; }
  .g-node:hover .card-bg { filter: brightness(0.975); }
  .card-sel { display: none; fill: none; stroke: #3B66A8; stroke-width: 2.4; pointer-events: none; }
  .g-node.selected .card-sel { display: inline; }
  .halo-ring { fill: none; pointer-events: none; opacity: 0; }
  .g-node.probe-base .halo-ring { opacity: 1; stroke: #3E68A8; stroke-width: 3; }
  .g-node.probe-flip .halo-ring { opacity: 1; stroke: #D48817; stroke-width: 3.2; stroke-dasharray: 6 3; }
  .g-node.blast-hit .halo-ring { opacity: 1; stroke: #C93B3B; stroke-width: 3.2; }
  .g-node.verify-attn-hit .halo-ring { opacity: 1; stroke: #D96B27; stroke-width: 3; stroke-dasharray: 5 3; }
  .n-id { font-size: 10.5px; font-weight: 600; fill: #6E7A86; font-family: ui-monospace, SFMono-Regular, monospace; }
  .n-tag { font-size: 9.5px; font-weight: 700; letter-spacing: 0.06em; }
  .n-title { font-size: 12.5px; font-weight: 600; }
  .n-sub { font-size: 10px; fill: #616E7C; }
  .micro-glyph-txt { font-size: 9.5px; font-weight: 800; pointer-events: none; }
  .medallion-txt { font-size: 8.4px; font-weight: 700; pointer-events: none; letter-spacing: 0.01em; }
  .stamp-pill-txt { font-size: 10px; font-weight: 700; letter-spacing: 0.02em; }
</style>
</head>
<body>

<div id="topbar">
  <div class="bar-cluster">
    <div class="brand">
      <span>Paths to Modernity</span>
      <span class="brand-badge">{embed_badge}</span>
    </div>
    <span class="sep"></span>
    <button class="lens-btn active" data-lens="overview">0 · 三层总览 <span class="cnt">{total_count}</span></button>
    <button class="lens-btn" data-lens="intent">1 · 意图图谱 <span class="cnt">{intent_count}</span></button>
    <button class="lens-btn" data-lens="specs">2 · 规范契约 <span class="cnt">{spec_count}</span></button>
    <button class="lens-btn" data-lens="plan">3 · 规划树 2.5D <span class="cnt">{plan_count}</span></button>
    <button class="lens-btn" data-lens="knowledge_debt">4 · 知识债书签 <span class="cnt">{kd_count}</span></button>
    <button class="lens-btn" data-lens="scripts">5 · 脚本依赖图 <span class="cnt">{scripts_count}</span></button>
  </div>
  <div class="bar-cluster">
    <button id="toggle-verify" class="toggle-pill verify-on" type="button" title="点击切换：双轨徽章 / 聚焦待测与存疑 / 隐藏">✓ 双轨验证: 徽章</button>
    <button id="toggle-cross" class="toggle-pill cross-on" type="button">跨域连线</button>
    <button id="toggle-hebbian" class="toggle-pill on" type="button" title="点击切换：智能聚焦 / 全局网格 / 隐藏">⚡ 赫布: 智能聚焦</button>
  </div>
</div>

<div id="legend">
  <span class="leg-item"><span class="leg-line"></span>Parent / Children 树结构线</span>
  <span class="leg-item"><span class="rel-ico alt">⇄</span><span class="rel-ico sup-down">↓</span><span class="rel-ico conflict">✕</span>备选·替代·冲突</span>
  <span class="leg-item"><span class="ver-pill verified" style="padding:0 5px;font-size:9.5px;">✓实测</span><span class="ver-pill concerns" style="padding:0 5px;font-size:9.5px;">⚠存疑/◈评鉴</span>形式+内容双轨验证</span>
  <span id="leg-cross" class="leg-item"><span class="leg-line cross"></span>跨域溯源边</span>
  <span class="leg-item"><span class="leg-line hebb"></span>Hebbian 突触</span>
</div>

<svg id="canvas" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="arr-struct" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 1.5 L 8.5 5 L 0 8.5 z" fill="#9AA5B1"/>
    </marker>
    <marker id="arr-cross" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5.5" markerHeight="5.5" orient="auto">
      <path d="M 0 1.5 L 8.5 5 L 0 8.5 z" fill="#7C69C8"/>
    </marker>
  </defs>
  <g id="viewport">
    <g id="stratum-layer"></g>
    <g id="ground-layer"></g>
    <g id="hebbian-layer"></g>
    <g id="cross-layer"></g>
    <g id="struct-layer"></g>
    <g id="node-layer"></g>
    <g id="card-mark-layer"></g>
  </g>
</svg>

<div id="bottombar">
  <button id="open-search" class="ctrl-btn" type="button">双路检索 / 激活扩散 <kbd>⌘K</kbd></button>
  <div id="probe-banner"><span id="probe-label"></span><button id="probe-clear" title="清除激活探针">×</button></div>
  <span class="sep"></span>
  <button id="btn-overview" class="ctrl-btn" type="button">全览适配</button>
  <button id="btn-100" class="ctrl-btn" type="button">100%</button>
</div>

<div id="search-surface" hidden>
  <div class="s-box">
    <input id="search-input" type="search" placeholder="输入概念、意图、术语或文件名 — 实时运行 Base 匹配 + 赫布激活扩散 (Flip)…" autocomplete="off"/>
    <span style="font-size:10.5px;color:#7B8794;white-space:nowrap;">Esc 关闭</span>
  </div>
  <div id="search-results"></div>
</div>

<aside id="panel" hidden>
  <div id="panel-resizer"></div>
  <div id="panel-head">
    <button id="panel-close" aria-label="关闭详情">×</button>
    <div id="p-kicker" class="p-kicker"></div>
    <h2 id="p-title"></h2>
    <div id="p-meta" class="p-meta"></div>
    <div id="p-rel-summary" class="rel-summary"></div>
    <div id="p-actions" class="p-actions"></div>
  </div>
  <div id="panel-body"></div>
</aside>

<script>
const DATA = {studio_payload};
const svg = document.getElementById('canvas');
const vp = document.getElementById('viewport');
const stratumLayer = document.getElementById('stratum-layer');
const groundLayer = document.getElementById('ground-layer');
const hebbLayer = document.getElementById('hebbian-layer');
const crossLayer = document.getElementById('cross-layer');
const structLayer = document.getElementById('struct-layer');
const nodeLayer = document.getElementById('node-layer');
const cardMarkLayer = document.getElementById('card-mark-layer');
const panelEl = document.getElementById('panel');

const CARD_W = 264, CARD_H = 78;
const STACKED_IDS = new Set(DATA.stacked_ids || []);
const RELATIONS = DATA.relations || {};

const STAMP_SPECS = {
  supersedes:      { glyph: '↓', label: '↓ 被替代',   fill: '#ECEFF2', stroke: '#7B8794', text: '#2E3842', wm: '#3E4C59' },
  superseded_by:   { glyph: '↑', label: '↑ 替代方',   fill: '#E6F0FA', stroke: '#4A80B8', text: '#1A4473', wm: '#2B5B8E' },
  conflicts_with:  { glyph: '✕', label: '✕ 冲突',     fill: '#FDECEC', stroke: '#D65A5A', text: '#962828', wm: '#B83232' },
  alternative_of:  { glyph: '◎', label: '◎ 对照基线', fill: '#F1EEFC', stroke: '#8470D6', text: '#3F2E88', wm: '#5B46B2' },
  has_alternative: { glyph: '⇄', label: '⇄ 备选方案', fill: '#F1EEFC', stroke: '#8470D6', text: '#3F2E88', wm: '#5B46B2' }
};
const MICRO_TONES = {
  'sup-up':   { fill: '#E6F0FA', stroke: '#9EC0E2', text: '#1E4976' },
  'sup-down': { fill: '#ECEFF2', stroke: '#BFC6CE', text: '#36414C' },
  'conflict': { fill: '#FDECEC', stroke: '#E5A1A1', text: '#9B2C2C' },
  'alt':      { fill: '#F1EEFC', stroke: '#BEB3EC', text: '#44338A' }
};
const MEDALLION_SPECS = {
  verified:        { label: '✓ 实测', fill: '#E6F5EC', stroke: '#84C39B', text: '#185A34' },
  stale:           { label: '⟳ 待测', fill: '#FFF3DF', stroke: '#E0AE58', text: '#8A530B' },
  failing:         { label: '✕ 失败', fill: '#FDECEC', stroke: '#E09494', text: '#962828' },
  partial:         { label: '◐ 部分', fill: '#EBF3F9', stroke: '#A3C2DC', text: '#265077' },
  unverified:      { label: '○ 未测', fill: '#F3F4F6', stroke: '#CBD2D9', text: '#52606D' },
  eval_ok:         { label: '◈ 评鉴', fill: '#EEF1FC', stroke: '#AEB8E8', text: '#364584' },
  eval_warn:       { label: '⚠ 存疑', fill: '#FFF0E6', stroke: '#E5A882', text: '#8F3D14' }
};
let currentLens = 'overview';
let hebbianMode = 'focus'; // 'focus' | 'all' | 'off'
let verifyMode = 'badges'; // 'badges' | 'attention' | 'off'
let showCross = true;
let selectedId = null;
let hoveredId = null;
let blastKdId = null;
let probeActive = false;
let k = 1, tx = 0, ty = 0, dragging = false, lx = 0, ly = 0, moved = false;

const nodesById = new Map(DATA.nodes.map(n => [n.id, n]));
const synapsesByNode = new Map();
DATA.synapses.forEach(s => {
  if (!synapsesByNode.has(s.from)) synapsesByNode.set(s.from, []);
  if (!synapsesByNode.has(s.to)) synapsesByNode.set(s.to, []);
  synapsesByNode.get(s.from).push({ target: s.to, weight: s.weight, coactivations: s.coactivations });
  synapsesByNode.get(s.to).push({ target: s.from, weight: s.weight, coactivations: s.coactivations });
});

function svgEl(tag, attrs = {}, text = null) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, val] of Object.entries(attrs)) el.setAttribute(key, String(val));
  if (text !== null) el.textContent = text;
  return el;
}

function htmlEl(tag, cls = null, text = null) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text !== null) el.textContent = text;
  return el;
}

function cardPath(x, y, w, h, r = 6) {
  return `M ${x} ${y} H ${x + w - r} Q ${x + w} ${y} ${x + w} ${y + r} V ${y + h - r} Q ${x + w} ${y + h} ${x + w - r} ${y + h} H ${x} Z`;
}

function activePositions() {
  return (DATA.layouts[currentLens] || DATA.layouts.overview).positions;
}

function routeStructuralEdge(e, p1, p2) {
  const [x1, y1] = p1, [x2, y2] = p2;
  const srcNode = nodesById.get(e.from);
  const z1 = (srcNode && srcNode.z) ? srcNode.z : 0;

  // Case 1: Child is in a vertical leaf stack -> route along clean left spine channel (`x2 - 16`)
  if ((e.relationship === 'decomposes_to' || e.relationship === 'decomposes_intent' || e.relationship === 'decomposes_spec') && STACKED_IDS.has(e.to)) {
    const sx = x1 + CARD_W / 2, sy = y1 + CARD_H + z1;
    const spineX = x2 - 16;
    const midY = y1 + CARD_H + 30;
    const ty = y2 + CARD_H / 2;
    return `M ${sx} ${sy} V ${midY} H ${spineX} V ${ty} H ${x2}`;
  }

  // Case 1b: Vertically stacked non-tree sibling relation (`supersedes`, `alternative_of`) -> clean right-side C-arc
  if (Math.abs(x2 - x1) < 6 && !['decomposes_to', 'decomposes_intent', 'imports', 'prerequisite_for'].includes(e.relationship)) {
    const rx = x1 + CARD_W;
    const sy = y1 + CARD_H / 2, ty = y2 + CARD_H / 2;
    const bow = 30 + Math.min(26, Math.abs(ty - sy) * 0.14);
    return `M ${rx} ${sy} C ${rx + bow} ${sy}, ${rx + bow} ${ty}, ${rx} ${ty}`;
  }

  // Case 2: Standard downward edge (`y2 > y1 + 24`)
  if (y2 > y1 + 24) {
    const sx = x1 + CARD_W / 2, sy = y1 + CARD_H + z1;
    const tx = x2 + CARD_W / 2, ty = y2;
    const my = (sy + ty) / 2;
    if (Math.abs(sx - tx) < 2) return `M ${sx} ${sy} V ${ty}`;
    return `M ${sx} ${sy} V ${my} H ${tx} V ${ty}`;
  }

  // Case 3: Upward edge (`y2 < y1 - 24`) -> clean smooth outer-side cubic arc (never self-crosses or knots)
  if (y2 < y1 - 24) {
    const rx1 = x1 + CARD_W, rx2 = x2 + CARD_W;
    const sy = y1 + CARD_H / 2, ty = y2 + CARD_H / 2;
    const bow = Math.max(rx1, rx2) + 36 + Math.min(34, Math.abs(ty - sy) * 0.12);
    return `M ${rx1} ${sy} C ${bow} ${sy}, ${bow} ${ty}, ${rx2} ${ty}`;
  }

  // Case 4: Same-row horizontal sibling edge (`alternative_of`, `supersedes`, `branches_from`, `constrains`)
  if (Math.abs(x2 - x1) < 6) {
    // Vertically adjacent siblings (e.g. WP-002 -> WP-003 in stack): curve along right margin
    const rx = x1 + CARD_W;
    const sy = y1 + CARD_H / 2, ty = y2 + CARD_H / 2;
    return `M ${rx} ${sy} C ${rx + 28} ${sy}, ${rx + 28} ${ty}, ${rx} ${ty}`;
  }
  const goRight = x2 > x1;
  const sx = goRight ? x1 + CARD_W : x1;
  const tx = goRight ? x2 : x2 + CARD_W;
  const sy = y1 + CARD_H / 2, ty = y2 + CARD_H / 2;
  const mx = (sx + tx) / 2;
  return `M ${sx} ${sy} C ${mx} ${sy}, ${mx} ${ty}, ${tx} ${ty}`;
}

function buildScriptEdgeRouter(pos, edges) {
  const outBy = new Map();
  const inBy = new Map();
  const visible = edges.filter(e => pos[e.from] && pos[e.to]);
  for (const e of visible) {
    if (!outBy.has(e.from)) outBy.set(e.from, []);
    if (!inBy.has(e.to)) inBy.set(e.to, []);
    outBy.get(e.from).push(e);
    inBy.get(e.to).push(e);
  }
  const outFrac = new Map();
  const inFrac = new Map();
  for (const [, list] of outBy) {
    list.sort((a, b) => (pos[a.to][0] - pos[b.to][0]) || (pos[a.to][1] - pos[b.to][1]));
    const n = list.length;
    list.forEach((e, i) => {
      outFrac.set(e, n === 1 ? 0.5 : 0.24 + (0.52 * i) / (n - 1));
    });
  }
  for (const [, list] of inBy) {
    list.sort((a, b) => (pos[a.from][0] - pos[b.from][0]) || (pos[a.from][1] - pos[b.from][1]));
    const n = list.length;
    list.forEach((e, i) => {
      inFrac.set(e, n === 1 ? 0.5 : 0.24 + (0.52 * i) / (n - 1));
    });
  }

  const allBoxes = Object.entries(pos).map(([id, [x, y]]) => ({ id, x, y, x2: x + CARD_W, y2: y + CARD_H }));
  const dagMinX = Math.min(...allBoxes.map(b => b.x));
  const dagMaxX = Math.max(...allBoxes.map(b => b.x2));
  let leftLaneCount = 0;
  let rightLaneCount = 0;

  return function routeScriptEdge(e) {
    const [x1, y1] = pos[e.from];
    const [x2, y2] = pos[e.to];
    // Upward cyclic back-edge -> smooth outer side arc
    if (y2 < y1 - 24) {
      const rx1 = x1 + CARD_W, rx2 = x2 + CARD_W;
      const sy = y1 + CARD_H / 2, ty = y2 + CARD_H / 2;
      const bow = Math.max(rx1, rx2) + 42 + Math.min(36, Math.abs(ty - sy) * 0.12);
      return { d: `M ${rx1} ${sy} C ${bow} ${sy}, ${bow} ${ty}, ${rx2} ${ty}`, isBack: true };
    }
    // Same-row horizontal dependency
    if (Math.abs(y2 - y1) <= 24) {
      const goRight = x2 > x1;
      const sx = goRight ? x1 + CARD_W : x1;
      const tx = goRight ? x2 : x2 + CARD_W;
      const sy = y1 + CARD_H / 2, ty = y2 + CARD_H / 2;
      const mx = (sx + tx) / 2;
      return { d: `M ${sx} ${sy} C ${mx} ${sy}, ${mx} ${ty}, ${tx} ${ty}`, isBack: false };
    }
    const sx = x1 + CARD_W * (outFrac.get(e) ?? 0.5);
    const sy = y1 + CARD_H;
    const tx = x2 + CARD_W * (inFrac.get(e) ?? 0.5);
    const ty = y2;
    const dy = ty - sy;

    // Detect if a direct vertical S-curve would pass through any intermediate card.
    const blockers = allBoxes.filter(b => {
      if (b.id === e.from || b.id === e.to) return false;
      if (b.y2 <= sy + 6 || b.y >= ty - 6) return false;
      const t = (b.y + CARD_H / 2 - sy) / Math.max(1, dy);
      const midX = sx + (tx - sx) * t;
      return midX >= b.x - 18 && midX <= b.x2 + 18;
    });

    if (blockers.length === 0) {
      const c1 = sy + Math.max(24, dy * 0.45);
      const c2 = ty - Math.max(24, dy * 0.45);
      return { d: `M ${sx} ${sy} C ${sx} ${c1}, ${tx} ${c2}, ${tx} ${ty}`, isBack: false };
    }

    // Multi-layer skip edge: route smoothly out to a dedicated clear side lane,
    // travel vertically outside all intermediate cards, then curve cleanly into target port.
    const avgX = (sx + tx) / 2;
    const goLeft = (avgX - dagMinX) <= (dagMaxX - avgX);
    const laneOffset = goLeft ? (leftLaneCount++) * 14 : (rightLaneCount++) * 14;
    const laneX = goLeft
      ? Math.min(...blockers.map(b => b.x)) - 26 - laneOffset
      : Math.max(...blockers.map(b => b.x2)) + 26 + laneOffset;
    const yStart = sy + 20;
    const yEnd = ty - 20;
    const yMid = (yStart + yEnd) / 2;
    return {
      d: `M ${sx} ${sy} C ${sx} ${yStart}, ${laneX} ${yStart}, ${laneX} ${yMid} C ${laneX} ${yEnd}, ${tx} ${yEnd}, ${tx} ${ty}`,
      isBack: false,
    };
  };
}

function renderScene() {
  stratumLayer.replaceChildren();
  groundLayer.replaceChildren();
  hebbLayer.replaceChildren();
  crossLayer.replaceChildren();
  structLayer.replaceChildren();
  nodeLayer.replaceChildren();
  cardMarkLayer.replaceChildren();

  const layout = DATA.layouts[currentLens] || DATA.layouts.overview;
  const pos = layout.positions;

  const crossBtn = document.getElementById('toggle-cross');
  crossBtn.disabled = currentLens !== 'overview';
  document.getElementById('leg-cross').style.display = currentLens === 'overview' ? 'inline-flex' : 'none';

  if (currentLens === 'overview' && layout.strata) {
    const ep = layout.strata.epistemic;
    const nm = layout.strata.normative;
    const pr = layout.strata.pragmatic;
    stratumLayer.append(
      svgEl('rect', { x: ep.x, y: ep.y, width: ep.w, height: ep.h, rx: 14, class: 'stratum-box' }),
      svgEl('text', { x: ep.x + 18, y: ep.y + 24, class: 'stratum-label' }, 'EPISTEMIC LAYER · 认知探索层（Intent 意图与概念拆解  +  Knowledge Debt 认知书签）'),
      svgEl('text', { x: ep.x + ep.w - 18, y: ep.y + 24, 'text-anchor': 'end', class: 'stratum-sub' }, 'Kirsh & Maglio Epistemic Actions · DesignerlyLoop Intent Canvas')
    );
    if (nm) {
      stratumLayer.append(
        svgEl('rect', { x: nm.x, y: nm.y, width: nm.w, height: nm.h, rx: 14, class: 'stratum-box normative' }),
        svgEl('text', { x: nm.x + 18, y: nm.y + 24, class: 'stratum-label', fill: '#225753' }, 'NORMATIVE CONSTITUTION LAYER · 常驻规范契约层（Spec Graph: Invariant 红线 · Glossary 统一术语 · Standard 开发标准 · Contract 契约）'),
        svgEl('text', { x: nm.x + nm.w - 18, y: nm.y + 24, 'text-anchor': 'end', class: 'stratum-sub' }, 'Standing Law · Ubiquitous Language · Verifiable Postconditions')
      );
    }
    stratumLayer.append(
      svgEl('rect', { x: pr.x, y: pr.y, width: pr.w, height: pr.h, rx: 14, class: 'stratum-box' }),
      svgEl('text', { x: pr.x + 18, y: pr.y + 24, class: 'stratum-label' }, 'PRAGMATIC & ARTIFACT LAYER · 实践执行与代码层（Plan Graph v4 2.5D  +  Scripts AST 依赖图）'),
      svgEl('text', { x: pr.x + pr.w - 18, y: pr.y + 24, 'text-anchor': 'end', class: 'stratum-sub' }, 'Agent-Driven Execution · Deterministic AST Verification')
    );
  }

  if (currentLens === 'scripts' && Array.isArray(layout.bands)) {
    for (const b of layout.bands) {
      stratumLayer.append(
        svgEl('rect', {
          x: b.x, y: b.y, width: b.w, height: b.h, rx: 12,
          class: `script-band ${b.kind || ''}`,
        }),
        svgEl('text', { x: b.x + 14, y: b.y + 19, class: 'script-band-label' }, b.label)
      );
    }
  }

  for (const n of DATA.nodes) {
    const p = pos[n.id];
    if (!p) continue;
    const [x, y] = p;
    const z = n.z || 0;
    const gx = x - z * 0.34, gy = y + z;
    groundLayer.append(svgEl('ellipse', {
      cx: gx + CARD_W / 2, cy: gy + CARD_H, rx: CARD_W / 2 - 4, ry: 4.5,
      fill: '#000', opacity: 0.042
    }));
    if (z > 0) {
      groundLayer.append(svgEl('path', {
        d: `M ${x} ${y + CARD_H} L ${x + CARD_W} ${y + CARD_H} L ${gx + CARD_W} ${gy + CARD_H} L ${gx} ${gy + CARD_H} Z`,
        fill: '#E1E5E8', stroke: '#D3D8DE', 'stroke-width': 0.85
      }));
    }
  }

  const routeScriptEdge = currentLens === 'scripts' ? buildScriptEdgeRouter(pos, DATA.structural_edges) : null;
  for (const e of DATA.structural_edges) {
    const p1 = pos[e.from], p2 = pos[e.to];
    if (!p1 || !p2) continue;
    let d;
    const cls = ['struct-edge'];
    if (routeScriptEdge && ['imports', 'invokes'].includes(e.relationship)) {
      const routed = routeScriptEdge(e);
      d = routed.d;
      const srcMeta = nodesById.get(e.from);
      const isTestCaller = srcMeta && srcMeta.raw && srcMeta.raw.role === 'test';
      cls.push(routed.isBack ? 'script-back' : (e.relationship === 'invokes' ? 'script-invoke' : (isTestCaller ? 'script-test' : 'script-import')));
    } else {
      d = routeStructuralEdge(e, p1, p2);
    }
    const path = svgEl('path', {
      d, class: cls.join(' '), 'data-from': e.from, 'data-to': e.to,
      'data-rel': e.relationship, 'marker-end': 'url(#arr-struct)'
    });
    if (!['decomposes_to', 'decomposes_intent', 'decomposes_spec', 'imports', 'invokes'].includes(e.relationship)) {
      path.setAttribute('stroke-dasharray', '4 3');
    }
    structLayer.append(path);
  }

  // In Overview, draw clean cross-stratum bridges (keep top-level Intent->RootPlan & KD->Intent/Plan concise)
  if (showCross && currentLens === 'overview') {
    for (const e of DATA.cross_edges) {
      const p1 = pos[e.from], p2 = pos[e.to];
      if (!p1 || !p2) continue;
      // Route vertically between bottom of upper card and top of lower card (or horizontal if both in Epistemic stratum)
      const sameStratum = Math.abs(p1[1] - p2[1]) < 140;
      let d;
      if (sameStratum) {
        const goLeft = p2[0] < p1[0];
        const sx = goLeft ? p1[0] : p1[0] + CARD_W;
        const tx = goLeft ? p2[0] + CARD_W : p2[0];
        const sy = p1[1] + CARD_H / 2, ty = p2[1] + CARD_H / 2;
        const mx = (sx + tx) / 2;
        d = `M ${sx} ${sy} C ${mx} ${sy}, ${mx} ${ty}, ${tx} ${ty}`;
      } else {
        const sx = p1[0] + CARD_W / 2, sy = p1[1] + CARD_H + ((nodesById.get(e.from)?.z) || 0);
        const tx = p2[0] + CARD_W / 2, ty = p2[1];
        const cy1 = sy + (ty - sy) * 0.44, cy2 = sy + (ty - sy) * 0.56;
        d = `M ${sx} ${sy} C ${sx} ${cy1}, ${tx} ${cy2}, ${tx} ${ty}`;
      }
      crossLayer.append(svgEl('path', {
        d, class: 'cross-edge', 'data-from': e.from, 'data-to': e.to,
        'marker-end': 'url(#arr-cross)'
      }));
    }
  }

  if (hebbianMode !== 'off') {
    DATA.synapses.forEach((s, idx) => {
      const p1 = pos[s.from], p2 = pos[s.to];
      if (!p1 || !p2) return;
      const cx1 = p1[0] + CARD_W / 2, cy1 = p1[1] + CARD_H / 2;
      const cx2 = p2[0] + CARD_W / 2, cy2 = p2[1] + CARD_H / 2;
      const dx = cx2 - cx1, dy = cy2 - cy1;
      const dist = Math.hypot(dx, dy) || 1;
      const bend = 28 + Math.min(60, dist * 0.10);
      const mx = (cx1 + cx2) / 2 - (dy / dist) * bend * 0.42;
      const my = (cy1 + cy2) / 2 - bend * 0.48;
      const w = Math.max(1.1, s.weight * 3.6);
      const cls = ['hebb-edge'];
      if (hebbianMode === 'all') cls.push('mesh-all');
      else if (currentLens !== 'scripts' && idx < 10 && s.weight >= 0.32) cls.push('backbone');
      hebbLayer.append(svgEl('path', {
        d: `M ${cx1} ${cy1} Q ${mx} ${my} ${cx2} ${cy2}`,
        class: cls.join(' '), 'stroke-width': w.toFixed(2),
        'data-from': s.from, 'data-to': s.to, 'data-weight': s.weight
      }));
    });
  }

  for (const n of DATA.nodes) {
    const p = pos[n.id];
    if (!p) continue;
    const [x, y] = p;
    const g = svgEl('g', { class: 'g-node', 'data-id': n.id });
    const bgAttrs = {
      class: 'card-bg',
      d: cardPath(x, y, CARD_W, CARD_H),
      fill: n.palette[0],
      stroke: n.palette[1],
      'stroke-width': 1.35
    };
    if (n.status === 'superseded') bgAttrs['stroke-dasharray'] = '5 3';
    g.append(
      svgEl('rect', { class: 'halo-ring', x: x - 6, y: y - 6, width: CARD_W + 12, height: CARD_H + 12, rx: 10 }),
      svgEl('path', bgAttrs),
      svgEl('rect', { x, y, width: 6.5, height: CARD_H, fill: n.accent }),
      svgEl('path', { class: 'card-sel', d: cardPath(x, y, CARD_W, CARD_H) }),
      svgEl('text', { x: x + 14, y: y + 18, class: 'n-id' }, n.short_id),
      svgEl('text', { x: x + CARD_W - 10, y: y + 18, 'text-anchor': 'end', class: 'n-tag', fill: n.accent }, n.badge)
    );
    if (verifyMode !== 'off') {
      const pills = [];
      const ver = (n.raw && n.raw.verification) || null;
      const evr = (n.raw && n.raw.evaluation_rollup) || null;
      if (ver && ver.status && ver.status !== 'not_applicable') {
        const showUnv = ver.status === 'unverified' && (
          verifyMode === 'attention' ||
          n.status === 'planned_missing' ||
          (n.graph === 'plan' && n.raw.level === 'work-package')
        );
        if (ver.status !== 'unverified' || showUnv) {
          const sp = MEDALLION_SPECS[ver.status];
          if (sp) pills.push({ ...sp, tip: `形式验证 (${ver.status}): ${ver.reason || ''}` });
        }
      }
      if (evr && evr.count > 0) {
        const isWarn = evr.status === 'concerns' || evr.status === 'fail';
        const sp = isWarn ? MEDALLION_SPECS.eval_warn : MEDALLION_SPECS.eval_ok;
        pills.push({
          ...sp,
          tip: `内容评鉴 (${evr.eval_ids.join(', ')}): ${evr.status}`
        });
      }
      if (pills.length) {
        let mx = x + Math.max(63, 20.5 + n.short_id.length * 6.55);
        for (const mp of pills) {
          const mw = 34.0, mh = 13.5, my = y + 7.5;
          const mg = svgEl('g', { class: 'verify-medallion' });
          mg.append(
            svgEl('title', {}, mp.tip),
            svgEl('rect', { x: mx, y: my, width: mw, height: mh, rx: 3.8, fill: mp.fill, stroke: mp.stroke, 'stroke-width': 0.95 }),
            svgEl('text', { x: mx + mw / 2, y: my + mh / 2 + 0.3, 'text-anchor': 'middle', 'dominant-baseline': 'central', class: 'medallion-txt', fill: mp.text }, mp.label)
          );
          g.append(mg);
          mx += mw + 2.5;
        }
      }
    }
    n.wrapped_title.forEach((line, idx) => {
      g.append(svgEl('text', { x: x + 14, y: y + 37 + idx * 15.5, class: 'n-title', fill: n.palette[2] }, line));
    });
    if (n.subtitle) {
      g.append(svgEl('text', { x: x + 14, y: y + 70, class: 'n-sub' }, n.subtitle));
    }
    if (Array.isArray(n.passive_icons) && n.passive_icons.length) {
      let rx = x + CARD_W - 8;
      for (let i = n.passive_icons.length - 1; i >= 0; i--) {
        const b = n.passive_icons[i];
        const tone = MICRO_TONES[b.tone] || MICRO_TONES.alt;
        const bx = rx - 16, by = y + 57;
        const mg = svgEl('g', { class: 'micro-glyph' });
        mg.append(
          svgEl('title', {}, b.tip),
          svgEl('rect', { x: bx, y: by, width: 16, height: 15, rx: 4, fill: tone.fill, stroke: tone.stroke, 'stroke-width': 1 }),
          svgEl('text', { x: bx + 8, y: by + 8.2, 'text-anchor': 'middle', 'dominant-baseline': 'central', class: 'micro-glyph-txt', fill: tone.text }, b.glyph)
        );
        g.append(mg);
        rx -= 20;
      }
    }
    g.addEventListener('mouseenter', () => { hoveredId = n.id; if (!probeActive && !blastKdId) reapplyHighlights(); });
    g.addEventListener('mouseleave', () => { hoveredId = null; if (!probeActive && !blastKdId) reapplyHighlights(); });
    g.addEventListener('click', (ev) => {
      if (moved) return;
      ev.stopPropagation();
      selectNode(n.id);
    });
    nodeLayer.append(g);
  }

  reapplyHighlights();
}

function estimateLabelWidth(str) {
  let w = 0;
  for (const ch of str) w += ch.charCodeAt(0) > 0x2E80 ? 10.6 : 6.4;
  return Math.max(48, Math.ceil(w + 15));
}

function renderCardMarks(ownerId) {
  cardMarkLayer.replaceChildren();
  if (!ownerId) return;
  const rel = RELATIONS[ownerId];
  if (!rel) return;
  const pos = activePositions();
  const byTarget = new Map();
  const pushMark = (targetId, kind) => {
    if (!pos[targetId]) return;
    if (!byTarget.has(targetId)) byTarget.set(targetId, []);
    byTarget.get(targetId).push(kind);
  };
  (rel.supersedes || []).forEach(t => pushMark(t, 'supersedes'));
  (rel.superseded_by || []).forEach(t => pushMark(t, 'superseded_by'));
  (rel.conflicts_with || []).forEach(t => pushMark(t, 'conflicts_with'));
  (rel.alternative_of || []).forEach(t => pushMark(t, 'alternative_of'));
  (rel.has_alternative || []).forEach(t => pushMark(t, 'has_alternative'));

  for (const [targetId, kinds] of byTarget.entries()) {
    const [tx, ty] = pos[targetId];
    const primary = STAMP_SPECS[kinds[0]] || STAMP_SPECS.has_alternative;
    const grp = svgEl('g', {
      class: 'card-mark',
      'data-owner': ownerId,
      'data-target': targetId,
      'data-relations': kinds.join(',')
    });
    grp.append(
      svgEl('rect', {
        x: tx - 3, y: ty - 3, width: CARD_W + 6, height: CARD_H + 6, rx: 9,
        fill: 'none', stroke: primary.stroke, 'stroke-width': 2.1, 'stroke-dasharray': '5 3'
      }),
      svgEl('text', {
        x: tx + CARD_W - 30, y: ty + 43,
        'text-anchor': 'middle', 'dominant-baseline': 'central',
        fill: primary.wm, 'fill-opacity': 0.14,
        'font-size': 40, 'font-weight': 800
      }, primary.glyph)
    );
    let rightEdge = tx + CARD_W - 4;
    for (let i = kinds.length - 1; i >= 0; i--) {
      const spec = STAMP_SPECS[kinds[i]];
      if (!spec) continue;
      const pw = estimateLabelWidth(spec.label);
      const px = rightEdge - pw, py = ty - 13;
      grp.append(
        svgEl('rect', {
          x: px, y: py, width: pw, height: 18, rx: 9,
          fill: spec.fill, stroke: spec.stroke, 'stroke-width': 1.35
        }),
        svgEl('text', {
          x: px + pw / 2, y: py + 9.3,
          'text-anchor': 'middle', 'dominant-baseline': 'central',
          class: 'stamp-pill-txt', fill: spec.text
        }, spec.label)
      );
      rightEdge = px - 5;
    }
    cardMarkLayer.append(grp);
  }
}

function applyTransform() {
  vp.setAttribute('transform', `translate(${tx} ${ty}) scale(${k})`);
}

function fitOverview() {
  const layout = DATA.layouts[currentLens] || DATA.layouts.overview;
  const r = svg.getBoundingClientRect();
  const tb = document.getElementById('topbar').getBoundingClientRect();
  const topClear = Math.max(58, Math.round(tb.bottom + 12));
  const bottomClear = 78;
  const panelOpen = !panelEl.hidden;
  const pWidth = panelOpen ? panelEl.getBoundingClientRect().width : 0;
  const availW = Math.max(320, r.width - pWidth - 44);
  const availH = Math.max(220, r.height - topClear - bottomClear);
  k = Math.min(1.04, Math.max(0.18, Math.min(availW / layout.width, availH / layout.height)));
  tx = Math.max(16, (availW - layout.width * k) / 2 + 16);
  ty = Math.max(topClear, topClear + (availH - layout.height * k) / 2);
  applyTransform();
}

function nodeNeedsVerificationAttention(n) {
  if (!n || n.status === 'superseded' || n.status === 'deprecated') return false;
  const ver = (n.raw && n.raw.verification) || null;
  const evr = (n.raw && n.raw.evaluation_rollup) || null;
  if (evr && (evr.status === 'concerns' || evr.status === 'fail')) return true;
  if (ver && (ver.status === 'stale' || ver.status === 'failing')) return true;
  if (ver && ver.status === 'unverified') {
    if (n.status === 'planned_missing') return true;
    if (n.graph === 'plan' && n.raw.level === 'work-package') return true;
    if (n.graph === 'specs' && n.raw.kind === 'contract') return true;
  }
  if (n.graph === 'knowledge_debt' && n.status === 'open') return true;
  return false;
}

function clearProbeAndBlast() {
  blastKdId = null;
  probeActive = false;
  if (verifyMode === 'attention') {
    verifyMode = 'badges';
    const vb = document.getElementById('toggle-verify');
    vb.textContent = '✓ 双轨验证: 徽章';
    vb.className = 'toggle-pill verify-on';
  }
  document.getElementById('probe-banner').classList.remove('on');
  document.querySelectorAll('.g-node').forEach(g => {
    g.classList.remove('dimmed', 'probe-base', 'probe-flip', 'blast-hit', 'verify-attn-hit');
  });
  document.querySelectorAll('.edge-hot, .edge-hebb-hot, .edge-blast').forEach(e => {
    e.classList.remove('edge-hot', 'edge-hebb-hot', 'edge-blast');
  });
}

function applyVerifyAttentionSpotlight() {
  if (verifyMode !== 'attention' || probeActive || blastKdId) return;
  let attnCnt = 0;
  nodeLayer.querySelectorAll('.g-node').forEach(g => {
    const n = nodesById.get(g.dataset.id);
    if (nodeNeedsVerificationAttention(n)) {
      g.classList.add('verify-attn-hit');
      g.classList.remove('dimmed');
      attnCnt += 1;
    } else {
      g.classList.remove('verify-attn-hit');
      g.classList.add('dimmed');
    }
  });
  const banner = document.getElementById('probe-banner');
  document.getElementById('probe-label').textContent =
    `⚠ 验证与评鉴关注焦点：共 ${attnCnt} 个节点存在待测缺口、哈希过期、评鉴存疑或开放知识债`;
  banner.classList.add('on');
}

function reapplyHighlights() {
  document.querySelectorAll('.g-node.selected').forEach(g => g.classList.remove('selected'));
  if (!probeActive && !blastKdId) {
    document.querySelectorAll('.edge-hot, .edge-hebb-hot').forEach(e => e.classList.remove('edge-hot', 'edge-hebb-hot'));
  }
  const focusId = hoveredId || selectedId;
  if (selectedId) {
    const target = nodeLayer.querySelector(`.g-node[data-id="${CSS.escape(selectedId)}"]`);
    if (target) target.classList.add('selected');
  }
  if (focusId && !probeActive && !blastKdId) {
    const lineagePairs = new Set();
    let cursor = focusId;
    while (cursor && RELATIONS[cursor] && RELATIONS[cursor].parent) {
      const p = RELATIONS[cursor].parent;
      lineagePairs.add(p + '->' + cursor);
      cursor = p;
    }
    if (RELATIONS[focusId]) {
      (RELATIONS[focusId].children || []).forEach(ch => lineagePairs.add(focusId + '->' + ch));
    }
    [...structLayer.children].forEach(p => {
      const key = p.dataset.from + '->' + p.dataset.to;
      if (lineagePairs.has(key) || p.dataset.from === focusId || p.dataset.to === focusId) {
        p.classList.add('edge-hot');
      }
    });
    [...crossLayer.children].forEach(p => {
      if (p.dataset.from === focusId || p.dataset.to === focusId) p.classList.add('edge-hot');
    });
    [...hebbLayer.children].forEach(p => {
      if (p.dataset.from === focusId || p.dataset.to === focusId) p.classList.add('edge-hebb-hot');
    });
    renderCardMarks(focusId);
  } else {
    cardMarkLayer.replaceChildren();
  }
  if (blastKdId) triggerBlastRadius(blastKdId, true);
  else if (verifyMode === 'attention' && !probeActive) applyVerifyAttentionSpotlight();
}

function runSpreadingProbe(seedQueryOrId, fromNode = false) {
  clearProbeAndBlast();
  const baseScores = new Map();
  if (fromNode && nodesById.has(seedQueryOrId)) {
    baseScores.set(seedQueryOrId, 1.0);
  } else {
    const tokens = seedQueryOrId.toLowerCase().split(/\s+/).filter(Boolean);
    if (!tokens.length) return [];
    for (const n of DATA.nodes) {
      let hits = 0;
      for (const tok of tokens) {
        if (n.search_blob.includes(tok)) hits += 1;
      }
      if (hits > 0) baseScores.set(n.id, hits / tokens.length);
    }
  }

  const spreadScores = new Map(baseScores);
  const viaMap = new Map();
  for (const [srcId, bScore] of baseScores.entries()) {
    if (bScore < 0.34) continue;
    for (const syn of (synapsesByNode.get(srcId) || [])) {
      const boost = 0.38 * bScore * syn.weight;
      spreadScores.set(syn.target, (spreadScores.get(syn.target) || 0) + boost);
      if (!viaMap.has(syn.target) || viaMap.get(syn.target).boost < boost) {
        viaMap.set(syn.target, { via: srcId, weight: syn.weight, boost });
      }
    }
  }

  const baseTop = [...baseScores.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6).map(x => x[0]);
  const baseSet = new Set(baseTop);
  const flipped = [...spreadScores.entries()]
    .filter(([id]) => !baseSet.has(id) && viaMap.has(id))
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([id, score]) => ({ id, score, ...viaMap.get(id) }));

  const activeSet = new Set([...baseTop, ...flipped.map(f => f.id)]);
  if (activeSet.size > 0) {
    probeActive = true;
    nodeLayer.querySelectorAll('.g-node').forEach(g => {
      const id = g.dataset.id;
      if (baseSet.has(id)) g.classList.add('probe-base');
      else if (activeSet.has(id)) g.classList.add('probe-flip');
      else g.classList.add('dimmed');
    });
    hebbLayer.querySelectorAll('.hebb-edge').forEach(p => {
      const u = p.dataset.from, v = p.dataset.to;
      if ((baseSet.has(u) && activeSet.has(v)) || (baseSet.has(v) && activeSet.has(u))) {
        p.classList.add('edge-hebb-hot');
      }
    });
    const banner = document.getElementById('probe-banner');
    document.getElementById('probe-label').textContent =
      `⚡ 双路激活：Base ${baseTop.length} 项 + Hebbian Flip ${flipped.length} 项`;
    banner.classList.add('on');
  }

  return [
    ...baseTop.map(id => ({ id, flipped: false, score: spreadScores.get(id) || 0 })),
    ...flipped.map(f => ({ id: f.id, flipped: true, score: f.score, via: f.via, weight: f.weight }))
  ];
}

function triggerBlastRadius(targetId, keepState = false) {
  const node = nodesById.get(targetId);
  if (!node || !node.raw.impact_preview) return;
  if (!keepState && blastKdId === targetId) {
    clearProbeAndBlast();
    reapplyHighlights();
    return;
  }
  clearProbeAndBlast();
  blastKdId = targetId;
  const imp = node.raw.impact_preview;
  let affected, bannerMsg;
  if (node.graph === 'specs') {
    affected = new Set([
      targetId,
      ...(imp.dependent_specs || []),
      ...(imp.originating_intents || []),
      ...(imp.implementing_plans || []),
      ...(imp.downstream_plans || []),
      ...(imp.linked_knowledge_debt || []),
      ...(imp.governed_scripts || []).map(s => 'SCR:' + s),
      ...(imp.verification_scripts || []).map(s => 'SCR:' + s)
    ]);
    bannerMsg = `规范修订影响半径 (${targetId})：子规范 ${(imp.dependent_specs || []).length} · 计划 ${(imp.implementing_plans || []).length + (imp.downstream_plans || []).length} · 管辖/验证脚本 ${(imp.governed_scripts || []).length + (imp.verification_scripts || []).length}`;
  } else {
    affected = new Set([
      targetId,
      ...(imp.reopen_intents || []),
      ...(imp.amend_or_review_specs || []),
      ...(imp.supersede_plans || []),
      ...(imp.blocked_or_recheck_downstream_plans || []),
      ...(imp.affected_parent_scopes || []),
      ...(imp.affected_scripts || []).map(s => 'SCR:' + s)
    ]);
    bannerMsg = `重审否定影响半径 (${targetId})：重开意图 ${(imp.reopen_intents || []).length} · 复核规范 ${(imp.amend_or_review_specs || []).length} · 重组计划 ${(imp.supersede_plans || []).length + (imp.blocked_or_recheck_downstream_plans || []).length}`;
  }

  nodeLayer.querySelectorAll('.g-node').forEach(g => {
    if (affected.has(g.dataset.id)) g.classList.add('blast-hit');
    else g.classList.add('dimmed');
  });
  [...structLayer.children, ...crossLayer.children].forEach(p => {
    if (affected.has(p.dataset.from) && affected.has(p.dataset.to)) p.classList.add('edge-blast');
  });
  const banner = document.getElementById('probe-banner');
  document.getElementById('probe-label').textContent = bannerMsg;
  banner.classList.add('on');
}

function makeChip(targetId, metaRight = '', extra = '') {
  const target = nodesById.get(targetId);
  const label = target ? `${target.short_id} · ${target.title}` : targetId;
  const a = htmlEl('a', 'chip-link' + (extra ? ' ' + extra : ''));
  a.append(htmlEl('span', null, label));
  if (metaRight) a.append(htmlEl('span', 'chip-meta', metaRight));
  a.addEventListener('click', (e) => {
    e.preventDefault();
    if (!activePositions()[targetId]) setLens('overview');
    selectNode(targetId);
  });
  return a;
}

function makeRelationPill(targetId) {
  const target = nodesById.get(targetId);
  const pill = htmlEl('a', 'rel-pill');
  pill.href = '#' + encodeURIComponent(targetId);
  const dot = htmlEl('span', 's-dot');
  dot.style.background = target ? target.palette[1] : '#C9CDD2';
  const txt = htmlEl('span', 'p-txt', target ? `${target.short_id} · ${target.title}` : targetId);
  pill.append(dot, txt);
  pill.addEventListener('mouseenter', () => {
    hoveredId = targetId;
    if (!probeActive && !blastKdId) reapplyHighlights();
  });
  pill.addEventListener('mouseleave', () => {
    hoveredId = null;
    if (!probeActive && !blastKdId) reapplyHighlights();
  });
  pill.addEventListener('click', (e) => {
    e.preventDefault();
    hoveredId = null;
    if (!activePositions()[targetId]) setLens('overview');
    selectNode(targetId);
  });
  return pill;
}

function renderHeaderRelSummary(id) {
  const box = document.getElementById('p-rel-summary');
  box.replaceChildren();
  const node = nodesById.get(id);
  const rel = RELATIONS[id];
  const synCnt = (synapsesByNode.get(id) || []).length;
  if (node && node.raw) {
    const ver = node.raw.verification;
    if (ver && ver.status && ver.status !== 'not_applicable') {
      const vLabels = {
        verified: ['ver-ok', '✓ 实测通过'],
        stale: ['ver-warn', '⟳ 源码已改待测'],
        failing: ['ver-fail', '✕ 测试未过'],
        partial: ['ver-ok', '◐ 部分实测'],
        unverified: ['', '○ 尚未实测']
      };
      const [cls, txt] = vLabels[ver.status] || ['', ver.status];
      box.append(htmlEl('span', cls, txt));
    }
    const evr = node.raw.evaluation_rollup;
    if (evr && evr.count > 0) {
      const isW = evr.status === 'concerns' || evr.status === 'fail';
      const evSpan = htmlEl('span', isW ? 'eval-warn' : 'eval-ok', isW ? '⚠ 评鉴存疑 ' : '◈ 内容评鉴 ');
      evSpan.append(htmlEl('b', null, String(evr.count)));
      box.append(evSpan);
    }
    const epr = node.raw.episodic_rollup;
    if (epr && epr.thread_count > 0) {
      const tSpan = htmlEl('span', 'thr-cnt', '💬 线索 ');
      tSpan.append(htmlEl('b', null, String(epr.thread_count)));
      box.append(tSpan);
    }
  }
  if (rel) {
    const counts = [
      ['parent', (rel.parent ? 1 : 0) + (rel.children || []).length],
      ['depends', (rel.depends_on || []).length + (rel.required_by || []).length],
      ['enables', (rel.enables || []).length + (rel.enabled_by || []).length],
      ['validates', (rel.validates || []).length + (rel.validated_by || []).length],
      ['supersedes', (rel.supersedes || []).length + (rel.superseded_by || []).length],
      ['conflicts', (rel.conflicts_with || []).length],
      ['alternative', (rel.alternative_of || []).length + (rel.has_alternative || []).length]
    ];
    for (const [label, cnt] of counts) {
      if (!cnt) continue;
      const item = htmlEl('span', null, label + ' ');
      item.append(htmlEl('b', null, String(cnt)));
      box.append(item);
    }
  }
  if (synCnt > 0) {
    const hItem = htmlEl('span', 'hebb-cnt', '⚡ hebbian ');
    hItem.append(htmlEl('b', null, String(synCnt)));
    box.append(hItem);
  }
}

function renderVerificationAndEvaluations(n) {
  const raw = n.raw || {};
  const ver = raw.verification;
  const evals = raw.evaluations || [];
  const showFormal = ver && ver.status && ver.status !== 'not_applicable' && ['specs', 'plan', 'scripts'].includes(n.graph);
  if (!showFormal && !evals.length) return null;

  const wrap = htmlEl('div');

  if (showFormal) {
    wrap.append(htmlEl('div', 'sec-title', '形式验证回执 (Formal Validation · Test & SHA-256 Freshness)'));
    const vcard = htmlEl('div', 'ver-card');
    const vhead = htmlEl('div', 'ver-head');
    const statusLabelMap = {
      verified: '✓ VERIFIED · 实测有效',
      stale: '⟳ STALE · 源码已改待重测',
      failing: '✕ FAILING · 用例未通过',
      partial: '◐ PARTIAL · 子项部分实测',
      unverified: '○ UNVERIFIED · 尚未实测'
    };
    vhead.append(
      htmlEl('span', null, ver.passed_tests !== undefined && ver.total_tests
        ? `测试套件: ${ver.passed_tests}/${ver.total_tests} passed`
        : '自动化测试与源码指纹校验'),
      htmlEl('span', 'ver-pill ' + ver.status, statusLabelMap[ver.status] || ver.status)
    );
    vcard.append(vhead);
    if (ver.reason) {
      vcard.append(htmlEl('div', 'p-meta', ver.reason));
    }
    if (ver.receipt_timestamp) {
      vcard.append(htmlEl('div', 'p-meta', `最近回执: ${ver.receipt_timestamp}${ver.runner_command ? ' · ' + ver.runner_command : ''}`));
    }
    if ((ver.stale_files || []).length) {
      const srow = htmlEl('div', 'qual-row risk');
      srow.append(htmlEl('span', null, '⟳ 哈希变更待重测: ' + ver.stale_files.join(', ')));
      vcard.append(srow);
    }
    if ((ver.test_scripts || []).length) {
      const tw = htmlEl('div', 'rel-values');
      tw.style.marginTop = '6px';
      ver.test_scripts.forEach(ts => tw.append(makeRelationPill('SCR:' + ts)));
      vcard.append(tw);
    }
    wrap.append(vcard);
  }

  if (evals.length) {
    wrap.append(htmlEl('div', 'sec-title', `内容评鉴记录 (Substantive Evaluations · ${evals.length})`));
    const verdictBadgeMap = {
      pass: '✓ PASS · 品质达标',
      selected_winner: '★ WINNER · 比选胜出',
      concerns: '⚠ CONCERNS · 存在隐忧',
      fail: '✕ FAIL · 违背品质',
      noted: '◈ NOTED · 历史记录'
    };
    evals.forEach(ev => {
      const ecard = htmlEl('div', 'eval-card ' + ev.verdict);
      const ehead = htmlEl('div', 'ver-head');
      ehead.append(
        htmlEl('span', null, `${ev.id} · ${ev.title}`),
        htmlEl('span', 'ver-pill ' + ev.verdict, verdictBadgeMap[ev.verdict] || ev.verdict)
      );
      ecard.append(ehead);

      const persp = htmlEl('div', 'eval-persp');
      persp.append(
        htmlEl('span', 'eval-persp-tag', `视角: ${ev.perspective}`),
        htmlEl('span', 'p-meta', `${ev.reviewer_mode} · ${ev.updated}`)
      );
      ecard.append(persp);

      if (ev.summary) {
        ecard.append(htmlEl('div', 'quote-box', ev.summary));
      }
      (ev.preserved_qualities || []).forEach(pq => {
        const qrow = htmlEl('div', 'qual-row preserved');
        qrow.append(htmlEl('span', 'rule-tag', '✓ 守护'), htmlEl('span', null, pq));
        ecard.append(qrow);
      });
      (ev.at_risk_qualities || []).forEach(rq => {
        const qrow = htmlEl('div', 'qual-row risk');
        qrow.append(htmlEl('span', 'rule-tag', '⚠ 风险'), htmlEl('span', null, rq));
        ecard.append(qrow);
      });
      if (ev.recommended_action) {
        ecard.append(htmlEl('div', 'p-meta', `建议行动: ${ev.recommended_action}`));
      }
      (ev.evidence_refs || []).forEach(eref => {
        if (DATA.prototypes && DATA.prototypes[eref]) {
          const frame = htmlEl('div', 'proto-frame');
          frame.innerHTML = DATA.prototypes[eref];
          ecard.append(frame);
        }
      });
      const targets = [
        ...(ev.evaluates_intents || []),
        ...(ev.evaluates_specs || []),
        ...(ev.evaluates_plans || []),
        ...(ev.evaluates_scripts || []).map(s => 'SCR:' + s)
      ].filter(tid => tid !== n.id);
      if (targets.length) {
        const tw = htmlEl('div', 'rel-values');
        tw.style.marginTop = '6px';
        targets.forEach(tid => tw.append(makeRelationPill(tid)));
        ecard.append(tw);
      }
      wrap.append(ecard);
    });
  }
  return wrap;
}

function renderEpisodicThreads(n, focusThreadId = null) {
  const raw = n.raw || {};
  const threads = raw.episodic_threads || [];
  if (!threads.length) return null;

  const wrap = htmlEl('div');
  wrap.append(htmlEl('div', 'sec-title', `原始对话解缠结线索 (Episodic Threads · Turn → Span → Thread · ${threads.length})`));

  const statusBadge = {
    active: ['thr', '● ACTIVE · 在途展开'],
    crystallized: ['verified', '▣ CRYSTALLIZED · 胶囊归档'],
    folded: ['partial', '▣ FOLDED · 胶囊折叠'],
    resolved: ['verified', '✓ RESOLVED · 已结案']
  };

  threads.forEach(th => {
    const isAct = th.status === 'active';
    const card = htmlEl('div', 'thr-card' + (isAct ? ' active' : ''));
    card.dataset.threadId = th.id;

    const head = htmlEl('div', 'ver-head');
    const [bCls, bTxt] = statusBadge[th.status] || ['noted', th.status];
    head.append(
      htmlEl('span', null, `${th.id} · ${th.title}`),
      htmlEl('span', 'ver-pill ' + (bCls === 'thr' ? 'partial' : bCls), bTxt)
    );
    card.append(head);

    const multiTurnSpans = (th.spans || []).filter(s => s.span_total > 1).length;
    const demuxNote = multiTurnSpans > 0
      ? `跨 ${th.turn_count} 轮对话 · 解缠结提取 ${th.span_count} 段单主题问答（自动剥离同轮其他并行议题）`
      : `跨 ${th.turn_count} 轮对话 · 共 ${th.span_count} 段原始问答切片`;
    card.append(htmlEl('div', 'p-meta', demuxNote));

    if (th.capsule_summary) {
      const cap = htmlEl('div', 'thr-capsule');
      cap.append(htmlEl('strong', null, isAct ? '阶段摘要: ' : '胶囊摘要: '), document.createTextNode(th.capsule_summary));
      card.append(cap);
    }

    if ((th.cross_threads || []).length) {
      const xmeta = htmlEl('div', 'p-meta');
      xmeta.style.marginTop = '4px';
      const peers = [...new Set(th.cross_threads.map(x => `${x.thread_id} (经 ${x.via_span_id})`))];
      xmeta.textContent = '⇄ 跨线索交织引用: ' + peers.join(', ');
      card.append(xmeta);
    }

    if ((th.spans || []).length) {
      const det = htmlEl('details', 'thr-details');
      if (isAct || focusThreadId === th.id) det.open = true;
      det.append(
        htmlEl(
          'summary',
          null,
          isAct
            ? `展开中：${th.span_count} 段纯净原始问答切片（SQLite spans 表）`
            : `点击展开归档原文：${th.span_count} 段解缠结纯净问答切片`
        )
      );
      th.spans.forEach(sp => {
        const sbox = htmlEl('div', 'span-item');
        const prov = htmlEl('div', 'span-prov');
        prov.append(
          htmlEl('span', 'span-prov-badge', `${sp.turn_id} · 轮内切片 ${sp.span_index}/${sp.span_total}`),
          htmlEl('span', null, `${sp.span_id}${sp.role === 'cross_ref' ? ' · 跨线索合流' : ''}`)
        );
        const uDiv = htmlEl('div', 'span-u');
        uDiv.append(htmlEl('b', null, 'User: '), document.createTextNode(sp.user_slice));
        const aDiv = htmlEl('div', 'span-a');
        aDiv.append(htmlEl('b', null, 'Agent: '), document.createTextNode(sp.assistant_slice));
        sbox.append(prov, uDiv, aDiv);
        det.append(sbox);
      });
      card.append(det);
    }

    const otherNodes = (th.linked_nodes || []).map(x => x.node_id).filter(nid => nid !== n.id && nodesById.has(nid));
    if (otherNodes.length) {
      const nw = htmlEl('div', 'rel-values');
      nw.style.marginTop = '6px';
      otherNodes.forEach(nid => nw.append(makeRelationPill(nid)));
      card.append(nw);
    }

    wrap.append(card);
  });

  return wrap;
}

function renderDeclaredRelations(id) {
  const rel = RELATIONS[id];
  if (!rel) return null;
  const wrap = htmlEl('div');
  wrap.append(htmlEl('div', 'sec-title', 'Agent 显式维护关系 (Declared Relations)'));
  const card = htmlEl('div', 'rel-card');

  const addRow = (labelText, targets, icoSpec = null, emptyText = '—') => {
    const row = htmlEl('div', 'rel-row');
    const lbl = htmlEl('span', 'rel-label');
    if (icoSpec) {
      lbl.append(htmlEl('span', 'rel-ico ' + icoSpec.cls, icoSpec.glyph));
    }
    lbl.append(document.createTextNode(labelText));
    const vals = htmlEl('span', 'rel-values');
    if (!targets || !targets.length) {
      vals.append(htmlEl('span', 'rel-empty', emptyText));
    } else {
      targets.forEach(t => vals.append(makeRelationPill(t)));
    }
    row.append(lbl, vals);
    card.append(row);
  };

  // 1. Parent / Children -> explicitly note it is drawn on the graph canvas, plus quick links
  const pcRow = htmlEl('div', 'rel-row');
  pcRow.append(htmlEl('span', 'rel-label', 'Parent / children'));
  const pcVals = htmlEl('span', 'rel-values');
  pcVals.append(htmlEl('span', 'rel-graph-hint', '见图谱树连线 (see the graph)'));
  if (rel.parent) pcVals.append(makeRelationPill(rel.parent));
  (rel.children || []).forEach(ch => pcVals.append(makeRelationPill(ch)));
  pcRow.append(pcVals);
  card.append(pcRow);

  card.append(htmlEl('div', 'rel-group-sep'));

  // 2. Sidebar-primary execution & verification relations
  addRow('Depends on', rel.depends_on);
  addRow('Required by', rel.required_by);
  addRow('Enables', rel.enables);
  addRow('Enabled by', rel.enabled_by);
  addRow('Validates', rel.validates);
  addRow('Validated by', rel.validated_by);

  card.append(htmlEl('div', 'rel-group-sep'));

  // 3. Icon-stamped counterpart relations (also shown via stamps/watermarks on canvas)
  addRow('Supersedes', rel.supersedes, { glyph: '↓', cls: 'sup-down' });
  addRow('Superseded by', rel.superseded_by, { glyph: '↑', cls: 'sup-up' });
  addRow('Conflicts with', rel.conflicts_with, { glyph: '✕', cls: 'conflict' });
  addRow('Alternative of', rel.alternative_of, { glyph: '◎', cls: 'alt' });
  addRow('Has alternative', rel.has_alternative, { glyph: '⇄', cls: 'alt' });

  wrap.append(card);
  return wrap;
}

function selectNode(id, focusThreadId = null) {
  const n = nodesById.get(id);
  if (!n) return;
  const wasHidden = panelEl.hidden;
  selectedId = id;
  panelEl.hidden = false;
  document.body.classList.add('panel-open');
  if (wasHidden) fitOverview();
  reapplyHighlights();

  const head = document.getElementById('panel-head');
  const body = document.getElementById('panel-body');
  head.style.background = n.palette[0];
  head.style.borderBottomColor = n.palette[1];

  document.getElementById('p-kicker').textContent = `${n.graph_label} · ${n.status}`;
  document.getElementById('p-title').textContent = `${n.short_id} · ${n.inspector_title || n.title}`;
  document.getElementById('p-meta').textContent = n.source ? `真源: ${n.source}` : '';
  renderHeaderRelSummary(id);

  const actions = document.getElementById('p-actions');
  actions.replaceChildren();
  const probeBtn = htmlEl('button', 'p-btn hebb', '⚡ 从此节点激活扩散');
  probeBtn.addEventListener('click', () => runSpreadingProbe(id, true));
  actions.append(probeBtn);

  if (n.graph === 'knowledge_debt' || n.graph === 'specs') {
    const labelTxt = n.graph === 'specs' ? '预演「修订规范」影响半径' : '预演「否定并重组」影响半径';
    const blastBtn = htmlEl('button', 'p-btn warn' + (blastKdId === id ? ' active' : ''), labelTxt);
    blastBtn.addEventListener('click', () => {
      triggerBlastRadius(id);
      blastBtn.classList.toggle('active', blastKdId === id);
    });
    actions.append(blastBtn);
  }

  body.replaceChildren();
  body.scrollTop = 0;
  const raw = n.raw;

  if (n.graph === 'intent' || n.graph === 'specs' || n.graph === 'plan') {
    const relSection = renderDeclaredRelations(id);
    if (relSection) body.append(relSection);
  }

  const verEvalSection = renderVerificationAndEvaluations(n);
  if (verEvalSection) body.append(verEvalSection);

  if (n.graph === 'intent') {
    body.append(htmlEl('div', 'sec-title', '原始表达副本 (Verbatim Utterance)'));
    body.append(htmlEl('div', 'quote-box', `“${raw.raw_utterance}”`));

    body.append(htmlEl('div', 'sec-title', '概念拆解与解释性变体 (Concepts & Interpretive Variants)'));
    (raw.concepts || []).forEach(c => {
      const card = htmlEl('div', 'concept-card');
      const ch = htmlEl('div', 'concept-head');
      ch.append(htmlEl('span', null, `◆ ${c.name}`), htmlEl('span', 's-badge base', `${c.role || 'concept'} · ${c.status || 'open'}`));
      card.append(ch);
      if (c.definition) card.append(htmlEl('div', 'p-meta', c.definition));
      if (Array.isArray(c.interpretive_variants) && c.interpretive_variants.length) {
        const ul = htmlEl('ul', 'variant-list');
        c.interpretive_variants.forEach(v => {
          const chosen = c.selected_variant === v.id || v.selected;
          const li = htmlEl('li', 'variant-item' + (chosen ? ' chosen' : ''));
          li.append(htmlEl('span', null, `${v.id}: ${v.meaning}`), htmlEl('span', 'v-status', chosen ? '✓ 已选解释' : '备选解读'));
          ul.append(li);
        });
        card.append(ul);
      }
      body.append(card);
    });

    if (Array.isArray(raw.implementation_alternatives) && raw.implementation_alternatives.length) {
      body.append(htmlEl('div', 'sec-title', '实现备选与认知原型对照 (Alternatives & Physical Rotation)'));
      raw.implementation_alternatives.forEach(alt => {
        const card = htmlEl('div', 'concept-card');
        const ch = htmlEl('div', 'concept-head');
        ch.append(htmlEl('span', null, `${alt.id || 'ALT'}: ${alt.approach}`), htmlEl('span', 's-badge ' + (alt.selected ? 'base' : ''), alt.selected ? '✓ 采用路径' : '对照方案'));
        card.append(ch);
        if (alt.prototype && DATA.prototypes[alt.prototype]) {
          const frame = htmlEl('div', 'proto-frame');
          frame.innerHTML = DATA.prototypes[alt.prototype];
          card.append(frame);
        }
        body.append(card);
      });
    }

    if (Array.isArray(raw.qualities) && raw.qualities.length) {
      body.append(htmlEl('div', 'sec-title', '保留体验品质 (Qualities)'));
      const ul = htmlEl('ul');
      raw.qualities.forEach(q => ul.append(htmlEl('li', null, q)));
      body.append(ul);
    }

    if ((raw.spec_refs || []).length || (raw.plan_refs || []).length || (raw.knowledge_debt_refs || []).length) {
      body.append(htmlEl('div', 'sec-title', '规范固化、实践层与书签映射 (Spec, Pragmatic & Bookmark Links)'));
      const wrap = htmlEl('div', 'chip-wrap');
      (raw.spec_refs || []).forEach(sid => wrap.append(makeChip(sid, 'SPEC')));
      (raw.plan_refs || []).forEach(pid => wrap.append(makeChip(pid, 'PLAN')));
      (raw.knowledge_debt_refs || []).forEach(kid => wrap.append(makeChip(kid, 'BOOKMARK')));
      body.append(wrap);
    }
  } else if (n.graph === 'specs') {
    body.append(htmlEl('div', 'sec-title', `常驻规范陈述 (${raw.kind.toUpperCase()} · ${raw.enforcement.toUpperCase()})`));
    body.append(htmlEl('div', 'quote-box', raw.summary));

    if (raw.canonical_term || (raw.forbidden_aliases || []).length) {
      body.append(htmlEl('div', 'sec-title', '统一领域术语与禁用别名 (Ubiquitous Language)'));
      const aw = htmlEl('div', 'alias-wrap');
      if (raw.canonical_term) {
        aw.append(htmlEl('span', 'term-canon', `✓ 标准词: ${raw.canonical_term}`));
      }
      (raw.forbidden_aliases || []).forEach(fa => {
        aw.append(htmlEl('span', 'term-forbid', `✕ 禁用: ${fa}`));
      });
      body.append(aw);
    }

    if ((raw.do_rules || []).length || (raw.dont_rules || []).length) {
      body.append(htmlEl('div', 'sec-title', '强制性红线与执行标准 (Do / Do NOT Guardrails)'));
      const rl = htmlEl('div', 'rule-list');
      (raw.do_rules || []).forEach(r => {
        const row = htmlEl('div', 'rule-row do');
        row.append(htmlEl('span', 'rule-tag', '✓ DO'), htmlEl('span', null, r));
        rl.append(row);
      });
      (raw.dont_rules || []).forEach(r => {
        const row = htmlEl('div', 'rule-row dont');
        row.append(htmlEl('span', 'rule-tag', '✕ DO NOT'), htmlEl('span', null, r));
        rl.append(row);
      });
      body.append(rl);
    }

    if (raw.signature_or_schema || (raw.postconditions || []).length) {
      body.append(htmlEl('div', 'sec-title', '可验证契约与后置条件 (Verifiable Contract)'));
      if (raw.signature_or_schema) {
        body.append(htmlEl('div', 'contract-sig', raw.signature_or_schema));
      }
      if ((raw.postconditions || []).length) {
        const ul = htmlEl('ul');
        raw.postconditions.forEach(p => ul.append(htmlEl('li', null, p)));
        body.append(ul);
      }
    }

    const hasCross = (raw.intent_refs || []).length || (raw.plan_refs || []).length ||
                     (raw.governs_scripts || []).length || (raw.verified_by_scripts || []).length ||
                     (raw.knowledge_debt_refs || []).length;
    if (hasCross) {
      body.append(htmlEl('div', 'sec-title', '五图咬合链路 (Cross-Graph Bindings)'));
      const wrap = htmlEl('div', 'chip-wrap');
      (raw.intent_refs || []).forEach(iid => wrap.append(makeChip(iid, '源自 INTENT')));
      (raw.plan_refs || []).forEach(pid => wrap.append(makeChip(pid, '落地 PLAN')));
      (raw.governs_scripts || []).forEach(s => wrap.append(makeChip('SCR:' + s, '管辖源码')));
      (raw.verified_by_scripts || []).forEach(s => wrap.append(makeChip('SCR:' + s, '守门测试')));
      (raw.knowledge_debt_refs || []).forEach(kid => wrap.append(makeChip(kid, '关联 KD')));
      body.append(wrap);
    }
  } else if (n.graph === 'plan') {
    body.append(htmlEl('div', 'sec-title', '目标成果 (Objective)'));
    body.append(htmlEl('p', null, raw.objective));
    if (raw.approach) {
      body.append(htmlEl('div', 'sec-title', '技术路径 (Approach)'));
      body.append(htmlEl('p', null, raw.approach));
    }
    for (const [label, key] of [['交付物 (Deliverables)', 'deliverables'], ['验收标准 (Acceptance)', 'acceptance'], ['体验品质 (Qualities)', 'qualities']]) {
      if (Array.isArray(raw[key]) && raw[key].length) {
        body.append(htmlEl('div', 'sec-title', label));
        const ul = htmlEl('ul');
        raw[key].forEach(item => ul.append(htmlEl('li', null, item)));
        body.append(ul);
      }
    }
    const specLinks = ((raw.links || {}).spec || []).map(s => s.split('/').pop().replace(/\.md$/, ''));
    const codeRefs = [...((raw.links || {}).code || []), ...((raw.links || {}).tests || [])];
    if (specLinks.length || codeRefs.length) {
      body.append(htmlEl('div', 'sec-title', '遵循规范与关联脚本 (Specs & Scripts)'));
      const wrap = htmlEl('div', 'chip-wrap');
      specLinks.forEach(sid => wrap.append(makeChip(sid, '遵循 SPEC')));
      codeRefs.forEach(r => wrap.append(makeChip('SCR:' + r, 'SCRIPT')));
      body.append(wrap);
    }
  } else if (n.graph === 'knowledge_debt') {
    body.append(htmlEl('div', 'sec-title', '重审触发条件 (Revisit Trigger)'));
    body.append(htmlEl('div', 'quote-box', raw.revisit_when));

    body.append(htmlEl('div', 'sec-title', '非完全技术能力责任人 · 三态技术质询分拣'));
    const grid = htmlEl('div', 'triage-grid');
    const cmdBox = htmlEl('div', 'cmd-preview');
    const modes = [
      { key: 'affirmed', cls: 'selected-agree', title: '① 理解且同意 (Informed Acceptance)', desc: '取消知识债并确认当时技术选型合理，关联计划保持有效。', cmd: `python3 -B scripts/ptm.py kd resolve ${n.id} --verdict affirmed --note "已在原型实践中验证并认可该技术方案"` },
      { key: 'open', cls: 'selected-proto', title: '② 暂不理解 · 先按此做可逆原型 (Knowledge Debt Bookmark)', desc: '保持书签开启，不消耗额外心智摩擦阻塞当前原型推进。', cmd: `# 当前保持 open 书签状态，待触发条件满足时重审 (${n.id})` },
      { key: 'rejected', cls: 'selected-reject', title: '③ 不同意该做法 · 提出新观点并重组图谱 (Reject & Reorganize)', desc: '否定原决定，自动重开关联 Intent 并标记下游 Plan 进入修订。', cmd: `python3 -B scripts/ptm.py kd resolve ${n.id} --verdict rejected --counterproposal "改用更直观的替代方案" --note "原型体验不符合预期"` }
    ];
    modes.forEach(m => {
      const btn = htmlEl('button', 'triage-opt' + (raw.status === m.key ? ' ' + m.cls : ''));
      btn.append(htmlEl('div', null, m.title), htmlEl('div', 'p-meta', m.desc));
      if (raw.status === m.key) cmdBox.textContent = m.cmd;
      btn.addEventListener('click', () => {
        grid.querySelectorAll('.triage-opt').forEach(b => b.className = 'triage-opt');
        btn.classList.add(m.cls);
        cmdBox.textContent = m.cmd;
        if (m.key === 'rejected') triggerBlastRadius(n.id, true);
      });
      grid.append(btn);
    });
    body.append(grid, cmdBox);

    const imp = raw.impact_preview || {};
    body.append(htmlEl('div', 'sec-title', '关联节点与重组影响范围'));
    const wrap = htmlEl('div', 'chip-wrap');
    (imp.reopen_intents || []).forEach(x => wrap.append(makeChip(x, '重开 INTENT')));
    (imp.amend_or_review_specs || []).forEach(x => wrap.append(makeChip(x, '复核 SPEC')));
    (imp.supersede_plans || []).forEach(x => wrap.append(makeChip(x, '替代 PLAN')));
    (imp.blocked_or_recheck_downstream_plans || []).forEach(x => wrap.append(makeChip(x, '下游复核')));
    (imp.affected_scripts || []).forEach(x => wrap.append(makeChip('SCR:' + x, '触及脚本')));
    body.append(wrap);
  } else if (n.graph === 'scripts') {
    body.append(htmlEl('div', 'sec-title', '模块职责摘要 (AST Summary)'));
    body.append(htmlEl('p', null, raw.summary || '无模块文档字符串'));
    body.append(htmlEl('div', 'sec-title', '静态指标 (Static Metrics)'));
    body.append(htmlEl('p', null, `语言: ${raw.language} · 角色: ${raw.role} · 代码行: ${raw.loc} LOC · PageRank 枢纽度: ${raw.centrality}`));
    if ((raw.classes || []).length || (raw.functions || []).length) {
      body.append(htmlEl('div', 'sec-title', '导出符号 (Classes & Functions)'));
      body.append(htmlEl('p', null, [...(raw.classes || []), ...(raw.functions || []).map(f => f + '()')].join(', ')));
    }
    if ((raw.governed_by_specs || []).length || (raw.verifies_specs || []).length || (raw.governed_by_plans || []).length) {
      body.append(htmlEl('div', 'sec-title', '所属常驻规范与执行计划 (Specs & Plans)'));
      const wrap = htmlEl('div', 'chip-wrap');
      (raw.governed_by_specs || []).forEach(sid => wrap.append(makeChip(sid, '受辖 SPEC')));
      (raw.verifies_specs || []).forEach(sid => wrap.append(makeChip(sid, '验证 SPEC')));
      (raw.governed_by_plans || []).forEach(pid => wrap.append(makeChip(pid, '所属 PLAN')));
      body.append(wrap);
    }
  }

  const epSection = renderEpisodicThreads(n, focusThreadId);
  if (epSection) body.append(epSection);

  const syns = (synapsesByNode.get(id) || []).slice().sort((a, b) => b.weight - a.weight);
  if (syns.length) {
    body.append(htmlEl('div', 'sec-title', `赫布关联邻居 (Hebbian Synapses · ${syns.length})`));
    const wrap = htmlEl('div', 'chip-wrap');
    syns.slice(0, 8).forEach(s => {
      wrap.append(makeChip(s.target, `w=${s.weight.toFixed(2)}`, 'hebb'));
    });
    body.append(wrap);
  }

  if (focusThreadId) {
    const tCard = body.querySelector(`.thr-card[data-thread-id="${CSS.escape(focusThreadId)}"]`);
    if (tCard) tCard.scrollIntoView({ block: 'nearest' });
  }

  history.replaceState(null, '', '#' + encodeURIComponent(id));
}

function closePanel() {
  selectedId = null;
  panelEl.hidden = true;
  document.body.classList.remove('panel-open');
  history.replaceState(null, '', location.pathname + location.search);
  reapplyHighlights();
  fitOverview();
}

function setLens(lens) {
  currentLens = lens;
  document.querySelectorAll('.lens-btn').forEach(b => b.classList.toggle('active', b.dataset.lens === lens));
  renderScene();
  fitOverview();
}

document.querySelectorAll('.lens-btn').forEach(btn => {
  btn.addEventListener('click', () => setLens(btn.dataset.lens));
});
document.getElementById('toggle-verify').addEventListener('click', (e) => {
  const order = ['badges', 'attention', 'off'];
  verifyMode = order[(order.indexOf(verifyMode) + 1) % order.length];
  const btn = e.currentTarget;
  if (verifyMode === 'badges') {
    btn.textContent = '✓ 双轨验证: 徽章';
    btn.className = 'toggle-pill verify-on';
    document.getElementById('probe-banner').classList.remove('on');
    document.querySelectorAll('.g-node').forEach(g => g.classList.remove('dimmed', 'verify-attn-hit'));
  } else if (verifyMode === 'attention') {
    blastKdId = null;
    probeActive = false;
    btn.textContent = '⚠ 双轨验证: 聚焦关注';
    btn.className = 'toggle-pill verify-attn';
  } else {
    btn.textContent = '✓ 双轨验证: 隐藏';
    btn.className = 'toggle-pill';
    document.getElementById('probe-banner').classList.remove('on');
    document.querySelectorAll('.g-node').forEach(g => g.classList.remove('dimmed', 'verify-attn-hit'));
  }
  renderScene();
});
document.getElementById('toggle-hebbian').addEventListener('click', (e) => {
  const order = ['focus', 'all', 'off'];
  hebbianMode = order[(order.indexOf(hebbianMode) + 1) % order.length];
  const labels = {
    focus: '⚡ 赫布: 智能聚焦',
    all: '⚡ 赫布: 全局网格',
    off: '⚡ 赫布: 隐藏'
  };
  e.currentTarget.textContent = labels[hebbianMode];
  e.currentTarget.classList.toggle('on', hebbianMode !== 'off');
  renderScene();
});
document.getElementById('toggle-cross').addEventListener('click', (e) => {
  showCross = !showCross;
  e.currentTarget.classList.toggle('cross-on', showCross);
  renderScene();
});
document.getElementById('btn-overview').addEventListener('click', fitOverview);
document.getElementById('btn-100').addEventListener('click', () => { k = 1; applyTransform(); });
document.getElementById('probe-clear').addEventListener('click', () => { clearProbeAndBlast(); reapplyHighlights(); });
document.getElementById('panel-close').addEventListener('click', closePanel);

svg.addEventListener('wheel', (e) => {
  e.preventDefault();
  const r = svg.getBoundingClientRect();
  const mx = e.clientX - r.left, my = e.clientY - r.top;
  const next = Math.min(2.8, Math.max(0.14, k * Math.exp(-e.deltaY * 0.0015)));
  tx = mx - (mx - tx) * (next / k);
  ty = my - (my - ty) * (next / k);
  k = next;
  applyTransform();
}, { passive: false });

svg.addEventListener('pointerdown', (e) => {
  if (e.target.closest('.g-node')) return;
  dragging = true; moved = false; lx = e.clientX; ly = e.clientY;
  svg.classList.add('dragging');
});
window.addEventListener('pointermove', (e) => {
  if (!dragging) return;
  if (Math.abs(e.clientX - lx) + Math.abs(e.clientY - ly) > 3) moved = true;
  tx += e.clientX - lx; ty += e.clientY - ly;
  lx = e.clientX; ly = e.clientY;
  applyTransform();
});
window.addEventListener('pointerup', () => { dragging = false; svg.classList.remove('dragging'); });

const searchSurface = document.getElementById('search-surface');
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');

function renderSearchDropdown() {
  const q = searchInput.value.trim();
  searchResults.replaceChildren();
  if (!q) {
    clearProbeAndBlast();
    reapplyHighlights();
    searchResults.append(htmlEl('div', 'p-meta', '提示：输入任意关键词（如“更快”、“谱峰”、“赫布”、“AST”），实时执行 Base + Hebbian Flip 双路激活扩散检索。'));
    return;
  }
  const hits = runSpreadingProbe(q, false);
  const qLower = q.toLowerCase();
  const threadHits = (DATA.episodic_threads || []).filter(th => {
    const blob = (th.id + ' ' + th.title + ' ' + (th.capsule_summary || '') + ' ' +
      (th.spans || []).map(s => s.user_slice + ' ' + s.assistant_slice).join(' ')).toLowerCase();
    return qLower.split(/\s+/).filter(Boolean).every(tok => blob.includes(tok));
  }).slice(0, 3);

  if (!hits.length && !threadHits.length) {
    searchResults.append(htmlEl('div', 'p-meta', '未找到匹配或关联激活节点与对话线索。'));
    return;
  }
  threadHits.forEach(th => {
    const targetNid = ((th.linked_nodes || [])[0] || {}).node_id;
    const row = htmlEl('div', 's-row');
    row.append(
      htmlEl('span', 's-badge thr', `💬 对话线索 (${th.span_count}切片)`),
      htmlEl('span', 's-id', th.id),
      htmlEl('span', 's-title', th.title)
    );
    if (targetNid) {
      row.append(htmlEl('span', 's-via', `→ ${targetNid}`));
    }
    row.addEventListener('click', () => {
      searchSurface.hidden = true;
      if (targetNid && nodesById.has(targetNid)) {
        if (!activePositions()[targetNid]) setLens('overview');
        selectNode(targetNid, th.id);
      }
    });
    searchResults.append(row);
  });
  hits.forEach(h => {
    const n = nodesById.get(h.id);
    const row = htmlEl('div', 's-row');
    row.append(
      htmlEl('span', 's-badge ' + (h.flipped ? 'flip' : 'base'), h.flipped ? '⚡ Hebbian Flip' : 'Base Match'),
      htmlEl('span', 's-id', n.short_id),
      htmlEl('span', 's-title', n.title)
    );
    if (h.flipped && h.via) {
      const viaN = nodesById.get(h.via);
      row.append(htmlEl('span', 's-via', `← 经 ${viaN ? viaN.short_id : h.via} (w=${h.weight.toFixed(2)})`));
    }
    row.addEventListener('click', () => {
      searchSurface.hidden = true;
      if (!activePositions()[h.id]) setLens('overview');
      selectNode(h.id);
    });
    searchResults.append(row);
  });
}

function syncSearchTop() {
  const tb = document.getElementById('topbar').getBoundingClientRect();
  searchSurface.style.top = Math.max(64, Math.round(tb.bottom + 10)) + 'px';
}

document.getElementById('open-search').addEventListener('click', () => {
  searchSurface.hidden = !searchSurface.hidden;
  if (!searchSurface.hidden) { syncSearchTop(); renderSearchDropdown(); searchInput.focus(); }
});
searchInput.addEventListener('input', renderSearchDropdown);
document.addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    searchSurface.hidden = !searchSurface.hidden;
    if (!searchSurface.hidden) { syncSearchTop(); renderSearchDropdown(); searchInput.focus(); }
    return;
  }
  if (document.activeElement !== searchInput && ['0','1','2','3','4','5'].includes(e.key)) {
    const map = { '0': 'overview', '1': 'intent', '2': 'specs', '3': 'plan', '4': 'knowledge_debt', '5': 'scripts' };
    setLens(map[e.key]);
  }
  if (e.key === 'Escape') {
    if (!searchSurface.hidden) searchSurface.hidden = true;
    else if (blastKdId || probeActive) { clearProbeAndBlast(); reapplyHighlights(); }
    else if (!panelEl.hidden) closePanel();
  }
});

const resizer = document.getElementById('panel-resizer');
let resizing = false;
resizer.addEventListener('pointerdown', (e) => { resizing = true; e.preventDefault(); });
window.addEventListener('pointermove', (e) => {
  if (!resizing) return;
  const w = Math.min(720, Math.max(340, window.innerWidth - e.clientX));
  document.documentElement.style.setProperty('--panel-w', w + 'px');
  fitOverview();
});
window.addEventListener('pointerup', () => { resizing = false; });
window.addEventListener('resize', fitOverview);

renderScene();
fitOverview();
const initHash = decodeURIComponent(location.hash.slice(1));
if (initHash && nodesById.has(initHash)) selectNode(initHash);
</script>
</body>
</html>
"""


def build_studio_html(
    repo_root: Path,
    federated: Mapping[str, Any],
    hebbian_payload: Mapping[str, Any],
    *,
    title: str = "Project Architecture Studio",
) -> str:
    repo_root = repo_root.resolve()
    layouts, stacked_ids = _compute_all_layouts(federated)
    explicit_relations = _build_explicit_relations(federated)
    prototypes = _collect_prototype_svgs(
        repo_root,
        federated.get("intent", {}).get("nodes", []),
        federated.get("evaluations", {}).get("nodes", []),
    )

    ui_nodes: list[dict[str, Any]] = []

    for n in federated.get("intent", {}).get("nodes", []):
        c_names = " · ".join(c.get("name", "") for c in n.get("concepts", [])[:3])
        blob = json.dumps(n, ensure_ascii=False).lower()
        rel_info = explicit_relations.get(n["id"]) or {}
        p_icons = _passive_icon_badges(rel_info)
        sub_limit = 22 if p_icons else 34
        raw_sub = f"概念: {c_names}" if c_names else ""
        sub_txt = (raw_sub[:sub_limit] + "…") if len(raw_sub) > sub_limit else raw_sub
        intent_z = 18 if rel_info.get("children") else 0
        ui_nodes.append(
            {
                "id": n["id"],
                "short_id": n["id"],
                "graph": "intent",
                "graph_label": "Intent Graph (认知意图)",
                "badge": "INTENT",
                "title": n["title"],
                "inspector_title": n["title"],
                "wrapped_title": _wrap(n["title"]),
                "subtitle": sub_txt,
                "passive_icons": p_icons,
                "status": n["status"],
                "source": n.get("source", ""),
                "z": intent_z,
                "accent": GRAPH_ACCENT["intent"],
                "palette": list(
                    STATUS_PALETTE.get(n["status"], STATUS_PALETTE["exploring"])
                ),
                "search_blob": blob,
                "raw": n,
            }
        )

    for n in federated.get("specs", {}).get("nodes", []):
        blob = json.dumps(n, ensure_ascii=False).lower()
        rel_info = explicit_relations.get(n["id"]) or {}
        p_icons = _passive_icon_badges(rel_info)
        k_tag = SPEC_KIND_TAG.get(n["kind"], n["kind"].upper())
        enf_str = n["enforcement"].replace("_", " ")
        raw_sub = f"{n['canonical_term']}" if n.get("canonical_term") else f"{enf_str} · {n['status']}"
        sub_limit = 22 if p_icons else 34
        sub_txt = (raw_sub[:sub_limit] + "…") if len(raw_sub) > sub_limit else raw_sub
        spec_z = 16 if rel_info.get("children") else 0
        ui_nodes.append(
            {
                "id": n["id"],
                "short_id": n["id"],
                "graph": "specs",
                "graph_label": f"Spec Graph ({n['kind']})",
                "badge": f"SPEC · {k_tag}",
                "title": n["title"],
                "inspector_title": n["title"],
                "wrapped_title": _wrap(n["title"]),
                "subtitle": sub_txt,
                "passive_icons": p_icons,
                "status": n["status"],
                "source": n.get("source", ""),
                "z": spec_z,
                "accent": GRAPH_ACCENT["specs"],
                "palette": list(
                    STATUS_PALETTE.get(n["status"], STATUS_PALETTE["enforced"])
                ),
                "search_blob": blob,
                "raw": n,
            }
        )

    level_badge = {
        "long-term": ("LT", GRAPH_ACCENT["plan_lt"]),
        "mid-term": ("MT", GRAPH_ACCENT["plan_mt"]),
        "short-term": ("ST", GRAPH_ACCENT["plan_st"]),
        "work-package": ("WP", GRAPH_ACCENT["plan_wp"]),
    }
    for n in federated.get("plan", {}).get("nodes", []):
        tag, acc = level_badge.get(n["level"], ("PLAN", GRAPH_ACCENT["plan_wp"]))
        blob = json.dumps(n, ensure_ascii=False).lower()
        p_icons = _passive_icon_badges(explicit_relations.get(n["id"]))
        ui_nodes.append(
            {
                "id": n["id"],
                "short_id": n["id"],
                "graph": "plan",
                "graph_label": f"Plan Graph v4 ({n['level']})",
                "badge": f"PLAN · {tag}",
                "title": n["title"],
                "inspector_title": n["title"],
                "wrapped_title": _wrap(n["title"]),
                "subtitle": n["status"].replace("_", " "),
                "passive_icons": p_icons,
                "status": n["status"],
                "source": n.get("source", ""),
                "z": LEVEL_Z.get(n["level"], 0),
                "accent": acc,
                "palette": list(
                    STATUS_PALETTE.get(n["status"], STATUS_PALETTE["proposed"])
                ),
                "search_blob": blob,
                "raw": n,
            }
        )

    for n in federated.get("knowledge_debt", {}).get("nodes", []):
        blob = json.dumps(n, ensure_ascii=False).lower()
        ui_nodes.append(
            {
                "id": n["id"],
                "short_id": n["id"],
                "graph": "knowledge_debt",
                "graph_label": "Knowledge Debt (认知书签)",
                "badge": f"BOOKMARK · {n['status'].upper()}",
                "title": n["term"],
                "inspector_title": n["term"],
                "wrapped_title": _wrap(n["term"]),
                "subtitle": f"{n['kind']} · 关联 {len(n.get('plan_refs', []))} 计划",
                "status": n["status"],
                "source": n.get("source", ""),
                "z": 10,
                "accent": GRAPH_ACCENT["knowledge_debt"],
                "palette": list(
                    STATUS_PALETTE.get(n["status"], STATUS_PALETTE["open"])
                ),
                "search_blob": blob,
                "raw": n,
            }
        )

    for n in federated.get("scripts", {}).get("nodes", []):
        blob = json.dumps(n, ensure_ascii=False).lower()
        lang_b = LANG_BADGE.get(n["language"], "CODE")
        role_b = ROLE_BADGE.get(n["role"], n["role"].upper())
        dir_prefix = f"{n['directory']}/" if n.get("directory") and n["directory"] != "." else ""
        ui_nodes.append(
            {
                "id": n["id"],
                "short_id": dir_prefix or "root",
                "graph": "scripts",
                "graph_label": "Scripts Graph (代码实现层)",
                "badge": f"{lang_b} · {role_b}",
                "title": n["name"],
                "inspector_title": n["path"],
                "wrapped_title": _wrap(n["name"]),
                "subtitle": f"{n['loc']} LOC · Hub {n.get('centrality', 0):.2f}",
                "status": n["status"],
                "source": n["path"],
                "z": 0,
                "accent": GRAPH_ACCENT["scripts"],
                "palette": list(
                    STATUS_PALETTE.get(n["status"], STATUS_PALETTE["clean"])
                ),
                "search_blob": blob,
                "raw": n,
            }
        )

    structural_edges = _deduplicate_structural_edges(
        [
            *federated.get("intent", {}).get("edges", []),
            *federated.get("specs", {}).get("edges", []),
            *federated.get("plan", {}).get("edges", []),
            *federated.get("scripts", {}).get("edges", []),
        ]
    )

    synapses = hebbian_payload.get("synapses", [])[:80]
    studio_payload = {
        "nodes": ui_nodes,
        "relations": explicit_relations,
        "structural_edges": structural_edges,
        "cross_edges": federated.get("cross_edges", []),
        "synapses": synapses,
        "layouts": layouts,
        "stacked_ids": sorted(stacked_ids),
        "prototypes": prototypes,
        "verification_report": federated.get("verification_report", {}),
        "episodic_threads": federated.get("episodic_memory", {}).get("threads", []),
    }

    embed_model = str(hebbian_payload.get("embedding_model", "local"))
    short_model = embed_model.split("/")[-1].replace("Embedding-", "Embed-").replace("-DWQ", "")
    out_path = repo_root / "_aiHumanInteract" / "studio" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rendered = (
        STUDIO_HTML.replace("{title}", html.escape(title))
        .replace("{embed_badge}", html.escape(short_model))
        .replace("{total_count}", str(len(ui_nodes)))
        .replace("{intent_count}", str(len(federated.get("intent", {}).get("nodes", []))))
        .replace("{spec_count}", str(len(federated.get("specs", {}).get("nodes", []))))
        .replace("{plan_count}", str(len(federated.get("plan", {}).get("nodes", []))))
        .replace("{kd_count}", str(len(federated.get("knowledge_debt", {}).get("nodes", []))))
        .replace("{scripts_count}", str(len(federated.get("scripts", {}).get("nodes", []))))
        .replace(
            "{studio_payload}",
            json.dumps(studio_payload, ensure_ascii=False).replace("</", "<\\/"),
        )
    )
    out_path.write_text(rendered, encoding="utf-8")
    return str(out_path)

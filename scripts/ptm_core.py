#!/usr/bin/env python3
"""Federated four-graph core engine for Paths to Modernity (PtM).

Maintains distinct sources of truth and edge provenance across:
1. Intent Graph (`_aiHumanInteract/intent/`) — Epistemic layer (`Declared`)
2. Plan Graph v4 (`_aiHumanInteract/plan/`) — Pragmatic layer (`Declared`, delegates validation to v4)
3. Knowledge Debt (`_aiHumanInteract/knowledge-debt/`) — Epistemic bookmarks & reorganization (`Declared`)
4. Scripts Graph (`_aiHumanInteract/scripts/`) — Static codebase dependencies (`Observed` + `Declared` + `Inferred`)
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping

SKILL_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_PLAN_DIR = SKILL_ROOT / "assets" / "plan-graph" / "_aiHumanInteract" / "plan"
if str(BUNDLE_PLAN_DIR) not in sys.path:
    sys.path.insert(0, str(BUNDLE_PLAN_DIR))

import validate as plan_validate  # noqa: E402
import build_graph as plan_build  # noqa: E402


INTENT_SCHEMA = "paths-to-modernity-intent-graph-v1"
KD_SCHEMA = "paths-to-modernity-knowledge-debt-v1"
SCRIPTS_SCHEMA = "paths-to-modernity-scripts-graph-v1"

INTENT_STATUSES = {"exploring", "clarified", "crystallized", "reopened", "superseded"}
KD_STATUSES = {"open", "affirmed", "rejected"}
KD_KINDS = {"concept", "reasoning_gap", "comparison_gap", "intuitive_doubt", "evidence_gap"}
TRIAGE_MODES = {
    "understood_agreed",
    "not_understood_prototype",
    "disagreed_counterproposal",
    "unclaimed",
}

INTENT_ID_RE = re.compile(r"^INT-\d{3}$")
KD_ID_RE = re.compile(r"^KD-\d{3}$")
PLAN_ID_RE = re.compile(r"^(LT|MT|ST|WP)-\d{3}$")

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".obsidian",
    "_aiHumanInteract",
}

CODE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".vue": "vue",
    ".sh": "shell",
}


class PtmGraphError(ValueError):
    """Raised when a PtM source record violates its graph contract."""


def parse_front_matter(path: Path) -> tuple[dict[str, Any], str]:
    """Parse single-line JSON-value front matter (matching Plan Graph v4)."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise PtmGraphError(f"{path}: missing opening front-matter delimiter")
    try:
        end = next(
            idx for idx, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration as exc:
        raise PtmGraphError(f"{path}: missing closing front-matter delimiter") from exc

    meta: dict[str, Any] = {}
    for line_no, line in enumerate(lines[1:end], start=2):
        if not line.strip():
            continue
        if ":" not in line:
            raise PtmGraphError(f"{path}:{line_no}: expected 'key: JSON-value'")
        key, raw_val = line.split(":", 1)
        key = key.strip()
        if not key or key in meta:
            raise PtmGraphError(f"{path}:{line_no}: empty or duplicate key {key!r}")
        try:
            meta[key] = json.loads(raw_val.strip())
        except json.JSONDecodeError as exc:
            raise PtmGraphError(
                f"{path}:{line_no}: metadata values must use JSON syntax ({exc})"
            ) from exc
    return meta, "\n".join(lines[end + 1 :]).strip()


def format_front_matter(meta: Mapping[str, Any], body: str) -> str:
    """Serialize metadata and Markdown body deterministically."""
    lines = ["---"]
    for key, val in meta.items():
        lines.append(f"{key}: {json.dumps(val, ensure_ascii=False)}")
    lines.append("---")
    lines.append("")
    lines.append(body.strip())
    lines.append("")
    return "\n".join(lines)


def _check_iso_date(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PtmGraphError(f"{label}: updated must be a YYYY-MM-DD string")
    clean = value.strip()
    try:
        if date.fromisoformat(clean).isoformat() != clean:
            raise ValueError
    except ValueError as exc:
        raise PtmGraphError(f"{label}: invalid YYYY-MM-DD date {value!r}") from exc
    return clean


def _find_cycle(adj: Mapping[str, Iterable[str]]) -> list[str] | None:
    visited: set[str] = set()
    active: set[str] = set()
    stack: list[str] = []

    def dfs(nid: str) -> list[str] | None:
        if nid in active:
            idx = stack.index(nid)
            return stack[idx:] + [nid]
        if nid in visited:
            return None
        visited.add(nid)
        active.add(nid)
        stack.append(nid)
        for nxt in adj.get(nid, ()):
            cyc = dfs(nxt)
            if cyc:
                return cyc
        stack.pop()
        active.remove(nid)
        return None

    for node_id in sorted(adj):
        cyc = dfs(node_id)
        if cyc:
            return cyc
    return None


# ============================================================================
# 1. INTENT GRAPH (_aiHumanInteract/intent/)
# ============================================================================


@dataclass(frozen=True)
class IntentNode:
    node_id: str
    title: str
    status: str
    updated: str
    raw_utterance: str
    utterance_ref: str | None
    parent: str | None
    refines: tuple[str, ...]
    branches_from: tuple[str, ...]
    constrains: tuple[str, ...]
    supersedes: tuple[str, ...]
    concepts: tuple[dict[str, Any], ...]
    implementation_alternatives: tuple[dict[str, Any], ...]
    plan_refs: tuple[str, ...]
    knowledge_debt_refs: tuple[str, ...]
    qualities: tuple[str, ...]
    source: str
    body: str

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.node_id,
            "title": self.title,
            "status": self.status,
            "updated": self.updated,
            "raw_utterance": self.raw_utterance,
            "parent": self.parent,
            "refines": list(self.refines),
            "branches_from": list(self.branches_from),
            "constrains": list(self.constrains),
            "supersedes": list(self.supersedes),
            "concepts": list(self.concepts),
            "implementation_alternatives": list(self.implementation_alternatives),
            "plan_refs": list(self.plan_refs),
            "knowledge_debt_refs": list(self.knowledge_debt_refs),
            "qualities": list(self.qualities),
            "source": self.source,
        }
        if self.utterance_ref:
            payload["utterance_ref"] = self.utterance_ref
        return payload


def load_intent_graph(repo_root: Path) -> tuple[dict[str, IntentNode], list[dict[str, Any]]]:
    """Load and validate all Intent Graph nodes if `_aiHumanInteract/intent/nodes` exists."""
    repo_root = repo_root.resolve()
    nodes_dir = repo_root / "_aiHumanInteract" / "intent" / "nodes"
    if not nodes_dir.is_dir():
        return {}, []

    nodes: dict[str, IntentNode] = {}
    for path in sorted(nodes_dir.glob("*.md")):
        rel = path.relative_to(repo_root).as_posix()
        meta, body = parse_front_matter(path)
        nid = str(meta.get("id", "")).strip()
        if not INTENT_ID_RE.fullmatch(nid):
            raise PtmGraphError(f"{rel}: invalid intent ID {nid!r} (expected INT-###)")
        if path.stem != nid:
            raise PtmGraphError(f"{rel}: filename must match {nid}.md")
        title = str(meta.get("title", "")).strip()
        if not title:
            raise PtmGraphError(f"{rel}: title must be non-empty")
        status = str(meta.get("status", "")).strip()
        if status not in INTENT_STATUSES:
            raise PtmGraphError(f"{rel}: invalid status {status!r}")
        updated = _check_iso_date(meta.get("updated"), rel)
        raw_utt = str(meta.get("raw_utterance", "")).strip()
        if not raw_utt:
            raise PtmGraphError(f"{rel}: raw_utterance is required to preserve user wording")
        utt_ref = meta.get("utterance_ref")
        if utt_ref is not None:
            utt_ref = str(utt_ref).strip() or None
            if utt_ref and not (repo_root / utt_ref).exists():
                raise PtmGraphError(f"{rel}: utterance_ref does not exist: {utt_ref}")

        parent = meta.get("parent")
        if parent is not None:
            parent = str(parent).strip()
            if not INTENT_ID_RE.fullmatch(parent):
                raise PtmGraphError(f"{rel}: invalid parent intent ID {parent!r}")

        def _id_tuple(key: str, pattern: re.Pattern[str] | None = INTENT_ID_RE) -> tuple[str, ...]:
            raw = meta.get(key, [])
            if not isinstance(raw, list):
                raise PtmGraphError(f"{rel}: {key} must be a list")
            items = tuple(str(x).strip() for x in raw if str(x).strip())
            if pattern:
                for item in items:
                    if not pattern.fullmatch(item):
                        raise PtmGraphError(f"{rel}: invalid ID {item!r} in {key}")
            return items

        concepts_raw = meta.get("concepts", [])
        if not isinstance(concepts_raw, list) or not concepts_raw:
            raise PtmGraphError(f"{rel}: concepts must be a non-empty list of concept objects")
        concepts: list[dict[str, Any]] = []
        for c in concepts_raw:
            if not isinstance(c, dict) or not str(c.get("name", "")).strip():
                raise PtmGraphError(f"{rel}: every concept requires a non-empty 'name'")
            concepts.append(c)

        impl_alts_raw = meta.get("implementation_alternatives", [])
        if not isinstance(impl_alts_raw, list):
            raise PtmGraphError(f"{rel}: implementation_alternatives must be a list")

        qualities = tuple(
            str(q).strip() for q in meta.get("qualities", []) if str(q).strip()
        )
        if nid in nodes:
            raise PtmGraphError(f"duplicate intent ID {nid}")

        nodes[nid] = IntentNode(
            node_id=nid,
            title=title,
            status=status,
            updated=updated,
            raw_utterance=raw_utt,
            utterance_ref=utt_ref,
            parent=parent,
            refines=_id_tuple("refines"),
            branches_from=_id_tuple("branches_from"),
            constrains=_id_tuple("constrains"),
            supersedes=_id_tuple("supersedes"),
            concepts=tuple(concepts),
            implementation_alternatives=tuple(impl_alts_raw),
            plan_refs=_id_tuple("plan_refs", PLAN_ID_RE),
            knowledge_debt_refs=_id_tuple("knowledge_debt_refs", KD_ID_RE),
            qualities=qualities,
            source=rel,
            body=body,
        )

    edges: list[dict[str, Any]] = []
    hierarchy_adj: dict[str, list[str]] = defaultdict(list)
    for nid, node in sorted(nodes.items()):
        if node.parent:
            if node.parent not in nodes:
                raise PtmGraphError(f"{nid}: dangling parent intent {node.parent}")
            hierarchy_adj[node.parent].append(nid)
            edges.append(
                {
                    "from": node.parent,
                    "to": nid,
                    "relationship": "decomposes_intent",
                    "provenance": "declared",
                }
            )
        for rel_name in ("refines", "branches_from", "constrains", "supersedes"):
            for target in getattr(node, rel_name):
                if target == nid or target not in nodes:
                    raise PtmGraphError(f"{nid}: invalid or dangling {rel_name} target {target}")
                edges.append(
                    {
                        "from": nid,
                        "to": target,
                        "relationship": rel_name,
                        "provenance": "declared",
                    }
                )
    cyc = _find_cycle(hierarchy_adj)
    if cyc:
        raise PtmGraphError(f"intent parent cycle: {' -> '.join(cyc)}")

    return nodes, edges


def build_intent_views(repo_root: Path) -> dict[str, Any]:
    """Validate and write Intent Graph generated views under `_aiHumanInteract/intent/structure/`."""
    repo_root = repo_root.resolve()
    nodes, edges = load_intent_graph(repo_root)
    payload = {
        "schema_version": INTENT_SCHEMA,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "source_of_truth": ["_aiHumanInteract/intent/nodes/*.md"],
        "nodes": [nodes[k].as_payload() for k in sorted(nodes)],
        "edges": edges,
    }
    if not nodes:
        return payload

    struct_dir = repo_root / "_aiHumanInteract" / "intent" / "structure"
    struct_dir.mkdir(parents=True, exist_ok=True)
    (struct_dir / "graph.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    md_lines = [
        "# Intent Graph (Epistemic Layer)",
        "",
        "Generated by `scripts/ptm.py`; edit `_aiHumanInteract/intent/nodes/*.md` instead.",
        "",
        "```mermaid",
        "flowchart LR",
    ]
    for nid in sorted(nodes):
        n = nodes[nid]
        safe_t = n.title.replace('"', "'")
        c_names = ", ".join(c["name"] for c in n.concepts[:3])
        md_lines.append(f'    {nid.replace("-", "_")}["{nid}: {safe_t}<br/>({c_names}) · {n.status}"]')
    for e in edges:
        u = e["from"].replace("-", "_")
        v = e["to"].replace("-", "_")
        conn = "-->" if e["relationship"] == "decomposes_intent" else "-.->"
        md_lines.append(f'    {u} {conn}|{e["relationship"]}| {v}')
    md_lines.extend(["```", "", "## Intents & Concepts", "", "| ID | Intent | Status | Key Concepts | Plans | KD Bookmarks |", "|---|---|---|---|---|---|"])
    for nid in sorted(nodes):
        n = nodes[nid]
        c_summary = "; ".join(
            f"{c['name']} ({c.get('status', 'open')})" for c in n.concepts
        )
        p_summary = ", ".join(n.plan_refs) or "—"
        kd_summary = ", ".join(n.knowledge_debt_refs) or "—"
        md_lines.append(
            f"| `{nid}` | [{n.title}](../nodes/{nid}.md) | `{n.status}` | {c_summary} | {p_summary} | {kd_summary} |"
        )
    md_lines.append("")
    (struct_dir / "graph.md").write_text("\n".join(md_lines), encoding="utf-8")

    canvas_nodes = []
    for idx, nid in enumerate(sorted(nodes)):
        n = nodes[nid]
        col, row = idx % 3, idx // 3
        concepts_md = "\n".join(
            f"- **{c['name']}** (`{c.get('status', 'open')}`)" for c in n.concepts
        )
        canvas_nodes.append(
            {
                "id": f"intent-{nid}",
                "type": "text",
                "x": col * 460,
                "y": row * 300,
                "width": 400,
                "height": 240,
                "color": "6" if n.status in {"clarified", "crystallized"} else "3",
                "text": f"## [[{n.source}|{nid} · {n.title}]]\n\n> {n.raw_utterance}\n\n{concepts_md}",
            }
        )
    canvas_edges = [
        {
            "id": f"int-edge-{i}",
            "fromNode": f"intent-{e['from']}",
            "fromSide": "right",
            "toNode": f"intent-{e['to']}",
            "toSide": "left",
            "label": e["relationship"],
        }
        for i, e in enumerate(edges)
    ]
    (struct_dir / "graph.canvas").write_text(
        json.dumps({"nodes": canvas_nodes, "edges": canvas_edges}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return payload


# ============================================================================
# 2. KNOWLEDGE DEBT GRAPH & REORGANIZATION IMPACT (_aiHumanInteract/knowledge-debt/)
# ============================================================================


@dataclass(frozen=True)
class KnowledgeDebtNode:
    node_id: str
    term: str
    kind: str
    status: str
    triage_mode: str
    updated: str
    intent_refs: tuple[str, ...]
    plan_refs: tuple[str, ...]
    script_refs: tuple[str, ...]
    revisit_when: str
    resolution_note: str | None
    counterproposal: str | None
    source: str
    body: str

    def as_payload(self) -> dict[str, Any]:
        return {
            "id": self.node_id,
            "term": self.term,
            "kind": self.kind,
            "status": self.status,
            "triage_mode": self.triage_mode,
            "updated": self.updated,
            "intent_refs": list(self.intent_refs),
            "plan_refs": list(self.plan_refs),
            "script_refs": list(self.script_refs),
            "revisit_when": self.revisit_when,
            "resolution_note": self.resolution_note,
            "counterproposal": self.counterproposal,
            "source": self.source,
        }


def load_knowledge_debt_graph(
    repo_root: Path,
) -> tuple[dict[str, KnowledgeDebtNode], list[dict[str, Any]]]:
    repo_root = repo_root.resolve()
    nodes_dir = repo_root / "_aiHumanInteract" / "knowledge-debt" / "nodes"
    if not nodes_dir.is_dir():
        return {}, []

    nodes: dict[str, KnowledgeDebtNode] = {}
    edges: list[dict[str, Any]] = []
    for path in sorted(nodes_dir.glob("*.md")):
        rel = path.relative_to(repo_root).as_posix()
        meta, body = parse_front_matter(path)
        nid = str(meta.get("id", "")).strip()
        if not KD_ID_RE.fullmatch(nid) or path.stem != nid:
            raise PtmGraphError(f"{rel}: invalid knowledge-debt ID {nid!r}")
        term = str(meta.get("term", "")).strip()
        if not term:
            raise PtmGraphError(f"{rel}: term must be non-empty")
        kind = str(meta.get("kind", "concept")).strip()
        if kind not in KD_KINDS:
            raise PtmGraphError(f"{rel}: invalid kind {kind!r}")
        status = str(meta.get("status", "open")).strip()
        if status not in KD_STATUSES:
            raise PtmGraphError(f"{rel}: invalid status {status!r}")
        triage_mode = str(meta.get("triage_mode", "not_understood_prototype")).strip()
        if triage_mode not in TRIAGE_MODES:
            raise PtmGraphError(f"{rel}: invalid triage_mode {triage_mode!r}")
        updated = _check_iso_date(meta.get("updated"), rel)
        revisit_when = str(meta.get("revisit_when", "")).strip()
        if not revisit_when:
            raise PtmGraphError(f"{rel}: revisit_when is required")

        intent_refs = tuple(str(x).strip() for x in meta.get("intent_refs", []) if str(x).strip())
        plan_refs = tuple(str(x).strip() for x in meta.get("plan_refs", []) if str(x).strip())
        script_refs = tuple(str(x).strip() for x in meta.get("script_refs", []) if str(x).strip())
        res_note = meta.get("resolution_note")
        counter = meta.get("counterproposal")

        nodes[nid] = KnowledgeDebtNode(
            node_id=nid,
            term=term,
            kind=kind,
            status=status,
            triage_mode=triage_mode,
            updated=updated,
            intent_refs=intent_refs,
            plan_refs=plan_refs,
            script_refs=script_refs,
            revisit_when=revisit_when,
            resolution_note=str(res_note).strip() if res_note else None,
            counterproposal=str(counter).strip() if counter else None,
            source=rel,
            body=body,
        )
        for iref in intent_refs:
            edges.append(
                {
                    "from": nid,
                    "to": iref,
                    "relationship": "bookmarks_intent",
                    "provenance": "declared",
                }
            )
        for pref in plan_refs:
            edges.append(
                {
                    "from": nid,
                    "to": pref,
                    "relationship": "bookmarks_plan",
                    "provenance": "declared",
                }
            )
        for sref in script_refs:
            edges.append(
                {
                    "from": nid,
                    "to": f"SCR:{sref}",
                    "relationship": "touches_script",
                    "provenance": "declared",
                }
            )
    return nodes, edges


def compute_kd_rejection_impact(
    repo_root: Path,
    kd_id: str,
    counterproposal: str | None = None,
) -> dict[str, Any]:
    """Trace which Intent, Plan, and Script nodes require reorganization if `kd_id` is rejected."""
    repo_root = repo_root.resolve()
    kd_nodes, _ = load_knowledge_debt_graph(repo_root)
    if kd_id not in kd_nodes:
        raise PtmGraphError(f"unknown knowledge-debt ID: {kd_id}")
    kd = kd_nodes[kd_id]

    plan_root = repo_root / "_aiHumanInteract" / "plan"
    plan_nodes: dict[str, plan_validate.PlanNode] = {}
    if plan_root.is_dir() and any((plan_root / lvl).is_dir() for lvl in plan_validate.LEVELS):
        loaded, errs = plan_validate.load_and_validate(plan_root, repo_root)
        if not errs:
            plan_nodes = loaded

    # Forward dependency adjacency: prereq -> list of dependents
    dependents_map: dict[str, list[str]] = defaultdict(list)
    ancestors_map: dict[str, list[str]] = defaultdict(list)
    for pid, pnode in plan_nodes.items():
        for dep in pnode.depends_on:
            dependents_map[dep].append(pid)
        curr = pnode.parent
        while curr and curr in plan_nodes:
            ancestors_map[pid].append(curr)
            curr = plan_nodes[curr].parent

    direct_plans = [p for p in kd.plan_refs if p in plan_nodes or PLAN_ID_RE.fullmatch(p)]
    downstream_plans: list[str] = []
    queue = list(direct_plans)
    seen = set(direct_plans)
    while queue:
        curr = queue.pop(0)
        for nxt in sorted(dependents_map.get(curr, ())):
            if nxt not in seen:
                seen.add(nxt)
                downstream_plans.append(nxt)
                queue.append(nxt)

    governing_ancestors = sorted(
        {anc for p in direct_plans for anc in ancestors_map.get(p, ())} - seen
    )

    return {
        "kd_id": kd_id,
        "term": kd.term,
        "current_status": kd.status,
        "counterproposal": counterproposal or kd.counterproposal,
        "reopen_intents": list(kd.intent_refs),
        "supersede_plans": direct_plans,
        "blocked_or_recheck_downstream_plans": downstream_plans,
        "affected_parent_scopes": governing_ancestors,
        "affected_scripts": list(kd.script_refs),
    }


def resolve_knowledge_debt(
    repo_root: Path,
    kd_id: str,
    verdict: str,
    note: str,
    counterproposal: str | None = None,
    reopen_linked_intents: bool = True,
) -> dict[str, Any]:
    """Resolve a KD bookmark as `affirmed` or `rejected` and update linked Intent status if rejected."""
    if verdict not in {"affirmed", "rejected"}:
        raise PtmGraphError("verdict must be 'affirmed' or 'rejected'")
    repo_root = repo_root.resolve()
    kd_path = repo_root / "_aiHumanInteract" / "knowledge-debt" / "nodes" / f"{kd_id}.md"
    if not kd_path.is_file():
        raise PtmGraphError(f"missing knowledge-debt file: {kd_path}")

    meta, body = parse_front_matter(kd_path)
    today = date.today().isoformat()
    meta["status"] = verdict
    meta["updated"] = today
    meta["resolution_note"] = note.strip()
    if verdict == "affirmed":
        meta["triage_mode"] = "understood_agreed"
    else:
        meta["triage_mode"] = "disagreed_counterproposal"
        if counterproposal:
            meta["counterproposal"] = counterproposal.strip()

    impact = compute_kd_rejection_impact(repo_root, kd_id, counterproposal=counterproposal)
    resolution_block = (
        f"\n\n## Resolution & Graph Impact ({today})\n\n"
        f"- **Verdict:** `{verdict}`\n"
        f"- **Owner note:** {note.strip()}\n"
    )
    if verdict == "rejected":
        if counterproposal:
            resolution_block += f"- **Counterproposal:** {counterproposal.strip()}\n"
        resolution_block += (
            f"- **Plans flagged for supersession/revision:** {', '.join(impact['supersede_plans']) or 'none'}\n"
            f"- **Downstream plans to re-verify:** {', '.join(impact['blocked_or_recheck_downstream_plans']) or 'none'}\n"
            f"- **Intents reopened:** {', '.join(impact['reopen_intents']) or 'none'}\n"
        )
    if "## Resolution & Graph Impact" in body:
        body = re.sub(r"\n*## Resolution & Graph Impact.*$", "", body, flags=re.DOTALL)
    kd_path.write_text(format_front_matter(meta, body + resolution_block), encoding="utf-8")

    reopened_files: list[str] = []
    if verdict == "rejected" and reopen_linked_intents:
        for int_id in impact["reopen_intents"]:
            int_path = repo_root / "_aiHumanInteract" / "intent" / "nodes" / f"{int_id}.md"
            if int_path.is_file():
                imeta, ibody = parse_front_matter(int_path)
                if imeta.get("status") not in {"superseded", "reopened"}:
                    imeta["status"] = "reopened"
                    imeta["updated"] = today
                    note_line = (
                        f"\n- [{today}] Reopened after rejecting `{kd_id}` ({meta['term']}): {note.strip()}"
                    )
                    int_path.write_text(format_front_matter(imeta, ibody + note_line), encoding="utf-8")
                    reopened_files.append(int_path.relative_to(repo_root).as_posix())

    impact["verdict"] = verdict
    impact["reopened_intent_files"] = reopened_files
    return impact


def build_knowledge_debt_views(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    nodes, edges = load_knowledge_debt_graph(repo_root)
    impacts = {
        nid: compute_kd_rejection_impact(repo_root, nid) for nid in sorted(nodes)
    }
    payload = {
        "schema_version": KD_SCHEMA,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "source_of_truth": ["_aiHumanInteract/knowledge-debt/nodes/*.md"],
        "nodes": [
            {**nodes[k].as_payload(), "impact_preview": impacts[k]}
            for k in sorted(nodes)
        ],
        "edges": edges,
    }
    if not nodes:
        return payload

    struct_dir = repo_root / "_aiHumanInteract" / "knowledge-debt" / "structure"
    struct_dir.mkdir(parents=True, exist_ok=True)
    (struct_dir / "graph.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    md_lines = [
        "# Knowledge Debt Bookmarks",
        "",
        "Generated by `scripts/ptm.py`; edit `_aiHumanInteract/knowledge-debt/nodes/*.md` instead.",
        "",
        "| ID | Term / Technical Choice | Kind | Status | Triage Mode | Intents | Plans | Revisit Trigger |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for nid in sorted(nodes):
        n = nodes[nid]
        md_lines.append(
            f"| `{nid}` | [{n.term}](../nodes/{nid}.md) | `{n.kind}` | `{n.status}` | `{n.triage_mode}` | "
            f"{', '.join(n.intent_refs) or '—'} | {', '.join(n.plan_refs) or '—'} | {n.revisit_when} |"
        )
    md_lines.append("")
    (struct_dir / "graph.md").write_text("\n".join(md_lines), encoding="utf-8")

    canvas_nodes = [
        {
            "id": f"kd-{nid}",
            "type": "text",
            "x": (idx % 3) * 440,
            "y": (idx // 3) * 260,
            "width": 380,
            "height": 210,
            "color": "3" if nodes[nid].status == "open" else ("4" if nodes[nid].status == "affirmed" else "1"),
            "text": (
                f"## [[{nodes[nid].source}|{nid} · {nodes[nid].term}]]\n\n"
                f"**Status:** `{nodes[nid].status}` · **Kind:** `{nodes[nid].kind}`\n\n"
                f"**Revisit when:** {nodes[nid].revisit_when}"
            ),
        }
        for idx, nid in enumerate(sorted(nodes))
    ]
    (struct_dir / "graph.canvas").write_text(
        json.dumps({"nodes": canvas_nodes, "edges": []}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


# ============================================================================
# 3. SCRIPTS GRAPH (_aiHumanInteract/scripts/) — AST & Static Dependency Scanner
# ============================================================================


JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[\w*{}\s,]+\s+from\s+)?|require\s*\(\s*)["']([^"']+)["']"""
)
SH_PYTHON_MOD_RE = re.compile(r"python3?(?:\s+-[A-Za-z]+)*\s+-m\s+([\w.]+)")
SH_SCRIPT_PATH_RE = re.compile(r"(?:python3?|bash|sh)\s+(?:-[A-Za-z]+\s+)*([\w./-]+\.(?:py|sh))")


def _git_file_statuses(repo_root: Path) -> dict[str, str]:
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            check=False,
        )
        if res.returncode != 0:
            return {}
    except OSError:
        return {}
    out: dict[str, str] = {}
    for line in res.stdout.splitlines():
        if len(line) < 4:
            continue
        xy = line[:2]
        rel = line[3:].strip().strip('"')
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1].strip()
        if xy == "??":
            out[rel] = "untracked"
        elif xy.strip():
            out[rel] = "modified"
    return out


def _pagerank(nodes: list[str], edges: list[tuple[str, str]], damping: float = 0.85) -> dict[str, float]:
    n = len(nodes)
    if n == 0:
        return {}
    scores = {u: 1.0 / n for u in nodes}
    outgoing: dict[str, list[str]] = defaultdict(list)
    incoming: dict[str, list[str]] = defaultdict(list)
    for u, v in edges:
        if u in scores and v in scores and u != v:
            outgoing[u].append(v)
            # Notice: if A imports B, B is depended upon by A -> B gains authority!
            incoming[v].append(u)

    for _ in range(25):
        sink_sum = sum(scores[u] for u in nodes if not outgoing[u])
        nxt: dict[str, float] = {}
        for u in nodes:
            rank = (1.0 - damping) / n + damping * (sink_sum / n)
            for src in incoming[u]:
                rank += damping * (scores[src] / len(outgoing[src]))
            nxt[u] = rank
        scores = nxt
    max_s = max(scores.values(), default=1.0) or 1.0
    return {u: round(scores[u] / max_s, 4) for u in nodes}


def scan_scripts_graph(repo_root: Path) -> dict[str, Any]:
    """Scan repository source files, AST imports/calls, cycles, hubs, and Plan coverage."""
    repo_root = repo_root.resolve()
    git_states = _git_file_statuses(repo_root)

    # Discover source files
    code_files: dict[str, Path] = {}
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS and not d.startswith("."))
        root_path = Path(root)
        # Skip bundled fixture example code when scanning a project unless repo itself is small
        rel_dir = root_path.relative_to(repo_root).as_posix()
        if rel_dir.startswith("experiments/") or "/example/" in f"/{rel_dir}/":
            continue
        for fname in sorted(files):
            ext = Path(fname).suffix.lower()
            if ext in CODE_EXTENSIONS:
                full = root_path / fname
                rel = full.relative_to(repo_root).as_posix()
                code_files[rel] = full

    # Map Python dotted module names -> relative file path
    py_module_index: dict[str, str] = {}
    stem_unique: dict[str, list[str]] = defaultdict(list)
    for rel in code_files:
        if not rel.endswith(".py"):
            continue
        no_ext = rel[:-3]
        parts = no_ext.split("/")
        if parts[-1] == "__init__":
            dotted = ".".join(parts[:-1])
        else:
            dotted = ".".join(parts)
            stem_unique[parts[-1]].append(rel)
        if dotted:
            py_module_index[dotted] = rel

    # Collect Plan Graph code/test links for cross-graph traceability
    plan_coverage: dict[str, list[str]] = defaultdict(list)
    planned_targets: set[str] = set()
    plan_root = repo_root / "_aiHumanInteract" / "plan"
    if plan_root.is_dir() and any((plan_root / lvl).is_dir() for lvl in plan_validate.LEVELS):
        p_nodes, p_errs = plan_validate.load_and_validate(plan_root, repo_root)
        if not p_errs:
            for pid, pnode in p_nodes.items():
                if pnode.status == "superseded":
                    continue
                for cat in ("code", "tests", "scripts"):
                    for ref in pnode.links.get(cat, ()):
                        if not ref.startswith("external:"):
                            plan_coverage[ref].append(pid)
                            if Path(ref).suffix.lower() in CODE_EXTENSIONS:
                                planned_targets.add(ref)

    annotations_path = repo_root / "_aiHumanInteract" / "scripts" / "annotations.json"
    annotations: dict[str, dict[str, Any]] = {}
    if annotations_path.is_file():
        try:
            annotations = json.loads(annotations_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            annotations = {}

    script_nodes: dict[str, dict[str, Any]] = {}
    symbol_defs: dict[str, dict[str, str]] = {}  # rel -> {symbol_name: kind}
    py_asts: dict[str, ast.AST] = {}
    py_import_aliases: dict[str, dict[str, str]] = defaultdict(dict)  # rel -> {local_alias: target_rel}
    raw_edges: dict[tuple[str, str, str], dict[str, Any]] = {}

    def _add_edge(src: str, dst: str, rel_type: str, provenance: str = "observed", detail: str = "") -> None:
        if src == dst:
            return
        key = (src, dst, rel_type)
        if key not in raw_edges:
            raw_edges[key] = {
                "from": f"SCR:{src}",
                "to": f"SCR:{dst}",
                "from_path": src,
                "to_path": dst,
                "relationship": rel_type,
                "provenance": provenance,
                "details": [detail] if detail else [],
            }
        elif detail and detail not in raw_edges[key]["details"] and len(raw_edges[key]["details"]) < 6:
            raw_edges[key]["details"].append(detail)

    # Pass 1: Extract symbols, docstrings, entrypoints, and module imports
    for rel, path in sorted(code_files.items()):
        lang = CODE_EXTENSIONS[path.suffix.lower()]
        try:
            src_text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            src_text = ""
        loc = len(src_text.splitlines())
        classes: list[str] = []
        functions: list[str] = []
        is_entrypoint = False
        summary = ""

        if lang == "python":
            try:
                tree = ast.parse(src_text, filename=rel)
                py_asts[rel] = tree
                doc = ast.get_docstring(tree) or ""
                summary = doc.strip().splitlines()[0].strip() if doc.strip() else ""
                for stmt in tree.body:
                    if isinstance(stmt, ast.ClassDef):
                        classes.append(stmt.name)
                        symbol_defs.setdefault(rel, {})[stmt.name] = "class"
                    elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        functions.append(stmt.name)
                        symbol_defs.setdefault(rel, {})[stmt.name] = "function"
                        if stmt.name == "main":
                            is_entrypoint = True
                    elif isinstance(stmt, ast.If):
                        if "__main__" in ast.unparse(stmt.test):
                            is_entrypoint = True
            except SyntaxError:
                summary = "SyntaxError while parsing Python AST"
        else:
            is_entrypoint = lang == "shell" or "main(" in src_text or "createApp(" in src_text
            for line in src_text.splitlines()[:12]:
                clean = line.strip().lstrip("#/ *").strip()
                if clean and not clean.startswith("!"):
                    summary = clean[:120]
                    break

        role = "entrypoint" if is_entrypoint else ("test" if "test" in Path(rel).name.lower() else "module")
        ann = annotations.get(rel, {})
        script_nodes[rel] = {
            "id": f"SCR:{rel}",
            "path": rel,
            "name": Path(rel).name,
            "directory": Path(rel).parent.as_posix(),
            "language": lang,
            "role": ann.get("role", role),
            "status": git_states.get(rel, "clean"),
            "loc": loc,
            "summary": ann.get("summary", summary),
            "inferred_note": ann.get("inferred_note"),
            "inferred_evidence": ann.get("evidence"),
            "classes": classes[:15],
            "functions": functions[:20],
            "is_entrypoint": is_entrypoint,
            "governed_by_plans": sorted(plan_coverage.get(rel, [])),
        }

    # Include planned-but-missing code targets so gaps between Plan and Scripts are visible
    for missing_rel in sorted(planned_targets - set(script_nodes)):
        script_nodes[missing_rel] = {
            "id": f"SCR:{missing_rel}",
            "path": missing_rel,
            "name": Path(missing_rel).name,
            "directory": Path(missing_rel).parent.as_posix(),
            "language": CODE_EXTENSIONS.get(Path(missing_rel).suffix.lower(), "unknown"),
            "role": "planned_target",
            "status": "planned_missing",
            "loc": 0,
            "summary": "Planned in Plan Graph; file not yet created on disk.",
            "inferred_note": None,
            "inferred_evidence": None,
            "classes": [],
            "functions": [],
            "is_entrypoint": False,
            "governed_by_plans": sorted(plan_coverage.get(missing_rel, [])),
        }

    def _resolve_py_module(importer_rel: str, mod_name: str | None, level: int) -> str | None:
        importer_pkg = importer_rel[:-3].split("/")[:-1]
        if level > 0:
            up = level - 1
            base = importer_pkg[: max(0, len(importer_pkg) - up)]
            cand_parts = base + (mod_name.split(".") if mod_name else [])
            dotted = ".".join(p for p in cand_parts if p)
            if dotted in py_module_index:
                return py_module_index[dotted]
        if mod_name:
            if mod_name in py_module_index:
                return py_module_index[mod_name]
            # Sibling import in same directory (e.g. `import plan_view` inside plan/)
            sibling = "/".join([*importer_pkg, *mod_name.split(".")]) + ".py"
            if sibling in code_files:
                return sibling
            if mod_name in stem_unique and len(stem_unique[mod_name]) == 1:
                return stem_unique[mod_name][0]
        return None

    # Pass 2: Extract Python AST imports & cross-module symbol invocations + JS/Shell links
    for rel, tree in py_asts.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = _resolve_py_module(rel, alias.name, 0)
                    if target:
                        local = alias.asname or alias.name.split(".")[0]
                        py_import_aliases[rel][local] = target
                        _add_edge(rel, target, "imports", "observed", alias.name)
            elif isinstance(node, ast.ImportFrom):
                target = _resolve_py_module(rel, node.module, node.level)
                if target:
                    _add_edge(rel, target, "imports", "observed", node.module or ".")
                    for alias in node.names:
                        local = alias.asname or alias.name
                        py_import_aliases[rel][local] = target
                else:
                    for alias in node.names:
                        sub_mod = f"{node.module}.{alias.name}" if node.module else alias.name
                        sub_target = _resolve_py_module(rel, sub_mod, node.level)
                        if sub_target:
                            local = alias.asname or alias.name
                            py_import_aliases[rel][local] = sub_target
                            _add_edge(rel, sub_target, "imports", "observed", sub_mod)

        aliases = py_import_aliases.get(rel, {})
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in aliases:
                    target = aliases[node.func.id]
                    if node.func.id in symbol_defs.get(target, {}):
                        _add_edge(rel, target, "invokes", "observed", f"{node.func.id}()")
                elif (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in aliases
                ):
                    target = aliases[node.func.value.id]
                    _add_edge(
                        rel,
                        target,
                        "invokes",
                        "observed",
                        f"{node.func.value.id}.{node.func.attr}()",
                    )
            # Also detect subprocess / CLI references to sibling scripts via Path constants (`"foo.py"`)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                val = node.value.strip()
                if val.endswith(".py") and "/" not in val and val in stem_unique and len(stem_unique[val]) == 1:
                    pass
                elif val in code_files and val != rel:
                    _add_edge(rel, val, "invokes", "observed", val)

    for rel, path in sorted(code_files.items()):
        lang = CODE_EXTENSIONS[path.suffix.lower()]
        if lang in {"javascript", "typescript", "vue"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            cur_dir = Path(rel).parent
            for match in JS_IMPORT_RE.finditer(text):
                spec = match.group(1)
                if not spec.startswith("."):
                    continue
                cand_base = (repo_root / cur_dir / spec).resolve()
                for suffix in ("", ".ts", ".tsx", ".js", ".jsx", ".vue", "/index.ts", "/index.js"):
                    cand = Path(str(cand_base) + suffix)
                    try:
                        cand_rel = cand.relative_to(repo_root).as_posix()
                    except ValueError:
                        continue
                    if cand_rel in code_files:
                        _add_edge(rel, cand_rel, "imports", "observed", spec)
                        break
        elif lang == "shell":
            text = path.read_text(encoding="utf-8", errors="replace")
            for m in SH_PYTHON_MOD_RE.finditer(text):
                mod = m.group(1)
                if mod in py_module_index:
                    _add_edge(rel, py_module_index[mod], "invokes", "observed", f"python -m {mod}")
            for m in SH_SCRIPT_PATH_RE.finditer(text):
                sp = m.group(1).lstrip("./")
                if sp in code_files:
                    _add_edge(rel, sp, "invokes", "observed", sp)

    edges = sorted(
        raw_edges.values(),
        key=lambda e: (e["relationship"], e["from_path"], e["to_path"]),
    )
    import_pairs = [
        (e["from_path"], e["to_path"])
        for e in edges
        if e["relationship"] in {"imports", "invokes"}
    ]
    hub_scores = _pagerank(sorted(script_nodes), import_pairs)
    for rel, snode in script_nodes.items():
        snode["centrality"] = hub_scores.get(rel, 0.0)

    import_adj: dict[str, list[str]] = defaultdict(list)
    for u, v in import_pairs:
        import_adj[u].append(v)
    cyc = _find_cycle(import_adj)

    return {
        "schema_version": SCRIPTS_SCHEMA,
        "node_count": len(script_nodes),
        "edge_count": len(edges),
        "cyclic_dependency": cyc,
        "nodes": [script_nodes[k] for k in sorted(script_nodes)],
        "edges": edges,
    }


def build_scripts_views(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    payload = scan_scripts_graph(repo_root)
    struct_dir = repo_root / "_aiHumanInteract" / "scripts" / "structure"
    struct_dir.mkdir(parents=True, exist_ok=True)
    (struct_dir / "graph.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    md_lines = [
        "# Scripts Graph (Codebase Structure & Coverage)",
        "",
        "Generated from repository source AST & static analysis by `scripts/ptm.py`.",
        "",
        "```mermaid",
        "flowchart LR",
    ]
    id_map = {n["id"]: f"S_{i}" for i, n in enumerate(payload["nodes"])}
    for n in payload["nodes"]:
        mid = id_map[n["id"]]
        md_lines.append(f'    {mid}["{n["path"]}<br/>{n["role"]} · {n["loc"]} LOC"]')
    for e in payload["edges"]:
        if e["from"] in id_map and e["to"] in id_map:
            conn = "-->" if e["relationship"] == "imports" else "-.->"
            md_lines.append(f'    {id_map[e["from"]]} {conn}|{e["relationship"]}| {id_map[e["to"]]}')
    md_lines.extend(
        [
            "```",
            "",
            "## Module Inventory (Ranked by Structural Centrality)",
            "",
            "| Path | Language | Role | Status | LOC | Centrality | Plans | Summary |",
            "|---|---|---|---|---:|---:|---|---|",
        ]
    )
    ranked = sorted(payload["nodes"], key=lambda x: (-x["centrality"], x["path"]))
    for n in ranked:
        plans = ", ".join(n["governed_by_plans"]) or "—"
        md_lines.append(
            f"| `{n['path']}` | `{n['language']}` | `{n['role']}` | `{n['status']}` | "
            f"{n['loc']} | {n['centrality']:.3f} | {plans} | {n['summary']} |"
        )
    md_lines.append("")
    (struct_dir / "graph.md").write_text("\n".join(md_lines), encoding="utf-8")

    canvas_nodes = [
        {
            "id": n["id"].replace(":", "-").replace("/", "_"),
            "type": "text",
            "x": (idx % 4) * 400,
            "y": (idx // 4) * 240,
            "width": 350,
            "height": 190,
            "color": "1" if n["status"] == "planned_missing" else ("5" if n["is_entrypoint"] else "6"),
            "text": (
                f"## `{n['path']}`\n\n"
                f"**Role:** `{n['role']}` · **LOC:** {n['loc']} · **Hub:** {n['centrality']:.2f}\n\n"
                f"{n['summary']}"
            ),
        }
        for idx, n in enumerate(payload["nodes"])
    ]
    canvas_edges = [
        {
            "id": f"scr-edge-{i}",
            "fromNode": e["from"].replace(":", "-").replace("/", "_"),
            "fromSide": "right",
            "toNode": e["to"].replace(":", "-").replace("/", "_"),
            "toSide": "left",
            "label": e["relationship"],
        }
        for i, e in enumerate(payload["edges"])
    ]
    (struct_dir / "graph.canvas").write_text(
        json.dumps({"nodes": canvas_nodes, "edges": canvas_edges}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return payload


def load_all_federated_graphs(repo_root: Path) -> dict[str, Any]:
    """Load Intent, Plan (v4), Knowledge Debt, and Scripts graphs into one unified memory view."""
    repo_root = repo_root.resolve()
    intents, intent_edges = load_intent_graph(repo_root)
    kds, kd_edges = load_knowledge_debt_graph(repo_root)

    plan_payload: dict[str, Any] = {"nodes": [], "edges": []}
    plan_root = repo_root / "_aiHumanInteract" / "plan"
    if plan_root.is_dir() and any((plan_root / lvl).is_dir() for lvl in plan_validate.LEVELS):
        p_nodes = plan_validate.require_valid_graph(plan_root, repo_root)
        plan_payload = plan_build.graph_payload(plan_root, p_nodes)

    scripts_payload = scan_scripts_graph(repo_root)

    # Extract explicit cross-graph edges (`Declared`)
    cross_edges: list[dict[str, Any]] = []
    for iid, inode in sorted(intents.items()):
        for pid in inode.plan_refs:
            cross_edges.append(
                {
                    "from": iid,
                    "to": pid,
                    "relationship": "seeds_plan",
                    "provenance": "declared",
                }
            )
    for pnode in plan_payload.get("nodes", []):
        pid = pnode["id"]
        for cat in ("code", "tests", "scripts"):
            for ref in pnode.get("links", {}).get(cat, []):
                if not ref.startswith("external:"):
                    cross_edges.append(
                        {
                            "from": pid,
                            "to": f"SCR:{ref}",
                            "relationship": "implements_in",
                            "provenance": "declared",
                        }
                    )
        for ref in pnode.get("links", {}).get("intent", []):
            stem = Path(ref).stem
            if INTENT_ID_RE.fullmatch(stem):
                pair = (stem, pid)
                if not any(
                    ce["from"] == pair[0] and ce["to"] == pair[1] for ce in cross_edges
                ):
                    cross_edges.append(
                        {
                            "from": stem,
                            "to": pid,
                            "relationship": "seeds_plan",
                            "provenance": "declared",
                        }
                    )

    cross_edges.extend(kd_edges)

    return {
        "intent": {
            "nodes": [intents[k].as_payload() for k in sorted(intents)],
            "edges": intent_edges,
        },
        "plan": plan_payload,
        "knowledge_debt": {
            "nodes": [
                {
                    **kds[k].as_payload(),
                    "impact_preview": compute_kd_rejection_impact(repo_root, k),
                }
                for k in sorted(kds)
            ],
            "edges": kd_edges,
        },
        "scripts": scripts_payload,
        "cross_edges": cross_edges,
    }

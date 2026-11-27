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
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
BUNDLE_PLAN_DIR = SKILL_ROOT / "assets" / "plan-graph" / "_aiHumanInteract" / "plan"
for _p in (SCRIPT_DIR, BUNDLE_PLAN_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from ptm_memory import EpisodicMemoryStore, attach_episodic_threads_to_federated  # noqa: E402
import validate as plan_validate  # noqa: E402
import build_graph as plan_build  # noqa: E402


INTENT_SCHEMA = "paths-to-modernity-intent-graph-v1"
SPEC_SCHEMA = "paths-to-modernity-spec-graph-v1"
KD_SCHEMA = "paths-to-modernity-knowledge-debt-v1"
SCRIPTS_SCHEMA = "paths-to-modernity-scripts-graph-v1"
EVAL_SCHEMA = "paths-to-modernity-evaluation-v1"
VERIFICATION_SCHEMA = "paths-to-modernity-verification-receipt-v1"

INTENT_STATUSES = {"exploring", "clarified", "crystallized", "reopened", "superseded"}
SPEC_STATUSES = {"draft", "enforced", "deprecated", "superseded"}
SPEC_KINDS = {"invariant", "glossary", "standard", "contract"}
SPEC_ENFORCEMENTS = {"must", "must_not", "should", "canonical_term"}
KD_STATUSES = {"open", "affirmed", "rejected"}
KD_KINDS = {"concept", "reasoning_gap", "comparison_gap", "intuitive_doubt", "evidence_gap"}
EVAL_KINDS = {
    "alternative_comparison",
    "quality_review",
    "prototype_critique",
    "spec_audit",
    "legacy_note",
}
EVAL_VERDICTS = {"pass", "selected_winner", "concerns", "fail", "noted"}
EVAL_REVIEWER_MODES = {
    "isolated_subagent",
    "browser_subagent",
    "human_owner",
    "joint",
    "legacy",
}
TRIAGE_MODES = {
    "understood_agreed",
    "not_understood_prototype",
    "disagreed_counterproposal",
    "unclaimed",
}

INTENT_ID_RE = re.compile(r"^INT-\d{3}$")
SPEC_ID_RE = re.compile(r"^SPEC-\d{3}$")
KD_ID_RE = re.compile(r"^KD-\d{3}$")
PLAN_ID_RE = re.compile(r"^(LT|MT|ST|WP)-\d{3}$")
EVAL_ID_RE = re.compile(r"^EVAL-\d{3}$")

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
    "vendor",
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
    depends_on: tuple[str, ...]
    enables: tuple[str, ...]
    validates: tuple[str, ...]
    supersedes: tuple[str, ...]
    conflicts_with: tuple[str, ...]
    alternative_of: str | None
    refines: tuple[str, ...]
    branches_from: tuple[str, ...]
    constrains: tuple[str, ...]
    concepts: tuple[dict[str, Any], ...]
    implementation_alternatives: tuple[dict[str, Any], ...]
    plan_refs: tuple[str, ...]
    knowledge_debt_refs: tuple[str, ...]
    spec_refs: tuple[str, ...]
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
            "depends_on": list(self.depends_on),
            "enables": list(self.enables),
            "validates": list(self.validates),
            "supersedes": list(self.supersedes),
            "conflicts_with": list(self.conflicts_with),
            "refines": list(self.refines),
            "branches_from": list(self.branches_from),
            "constrains": list(self.constrains),
            "concepts": list(self.concepts),
            "implementation_alternatives": list(self.implementation_alternatives),
            "plan_refs": list(self.plan_refs),
            "knowledge_debt_refs": list(self.knowledge_debt_refs),
            "spec_refs": list(self.spec_refs),
            "qualities": list(self.qualities),
            "source": self.source,
        }
        if self.alternative_of:
            payload["alternative_of"] = self.alternative_of
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

        alt_of_raw = meta.get("alternative_of")
        alt_of: str | None = None
        if alt_of_raw is not None:
            alt_of = str(alt_of_raw).strip() or None
            if alt_of and not INTENT_ID_RE.fullmatch(alt_of):
                raise PtmGraphError(f"{rel}: invalid alternative_of intent ID {alt_of!r}")

        nodes[nid] = IntentNode(
            node_id=nid,
            title=title,
            status=status,
            updated=updated,
            raw_utterance=raw_utt,
            utterance_ref=utt_ref,
            parent=parent,
            depends_on=_id_tuple("depends_on"),
            enables=_id_tuple("enables"),
            validates=_id_tuple("validates"),
            supersedes=_id_tuple("supersedes"),
            conflicts_with=_id_tuple("conflicts_with"),
            alternative_of=alt_of,
            refines=_id_tuple("refines"),
            branches_from=_id_tuple("branches_from"),
            constrains=_id_tuple("constrains"),
            concepts=tuple(concepts),
            implementation_alternatives=tuple(impl_alts_raw),
            plan_refs=_id_tuple("plan_refs", PLAN_ID_RE),
            knowledge_debt_refs=_id_tuple("knowledge_debt_refs", KD_ID_RE),
            spec_refs=_id_tuple("spec_refs", SPEC_ID_RE),
            qualities=qualities,
            source=rel,
            body=body,
        )

    edges: list[dict[str, Any]] = []
    hierarchy_adj: dict[str, list[str]] = defaultdict(list)
    dep_adj: dict[str, list[str]] = defaultdict(list)
    alt_adj: dict[str, list[str]] = defaultdict(list)
    sup_adj: dict[str, list[str]] = defaultdict(list)
    hard_dep_pairs = {
        (dep, n.node_id) for n in nodes.values() for dep in n.depends_on
    }

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
        for prereq in node.depends_on:
            if prereq == nid or prereq not in nodes:
                raise PtmGraphError(f"{nid}: invalid or dangling depends_on target {prereq}")
            dep_adj[nid].append(prereq)
            edges.append(
                {
                    "from": prereq,
                    "to": nid,
                    "relationship": "prerequisite_for",
                    "provenance": "declared",
                }
            )
        for target in node.enables:
            if target == nid or target not in nodes:
                raise PtmGraphError(f"{nid}: invalid or dangling enables target {target}")
            if (nid, target) in hard_dep_pairs:
                raise PtmGraphError(
                    f"{nid}: enables duplicates hard dependency declared by {target}"
                )
            edges.append(
                {
                    "from": nid,
                    "to": target,
                    "relationship": "enables",
                    "provenance": "declared",
                }
            )
        for rel_name in ("validates", "supersedes", "conflicts_with", "refines", "branches_from", "constrains"):
            for target in getattr(node, rel_name):
                if target == nid or target not in nodes:
                    raise PtmGraphError(f"{nid}: invalid or dangling {rel_name} target {target}")
                if rel_name == "supersedes":
                    sup_adj[nid].append(target)
                edges.append(
                    {
                        "from": nid,
                        "to": target,
                        "relationship": rel_name,
                        "provenance": "declared",
                    }
                )
        if node.alternative_of:
            if node.alternative_of == nid or node.alternative_of not in nodes:
                raise PtmGraphError(
                    f"{nid}: invalid or dangling alternative_of target {node.alternative_of}"
                )
            alt_adj[nid].append(node.alternative_of)
            edges.append(
                {
                    "from": nid,
                    "to": node.alternative_of,
                    "relationship": "alternative_of",
                    "provenance": "declared",
                }
            )

    for graph_label, adj in (
        ("parent", hierarchy_adj),
        ("dependency", dep_adj),
        ("alternative", alt_adj),
        ("supersession", sup_adj),
    ):
        cyc = _find_cycle(adj)
        if cyc:
            raise PtmGraphError(f"intent {graph_label} cycle: {' -> '.join(cyc)}")

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
# 1B. SPEC GRAPH (_aiHumanInteract/specs/) — Standing Laws, Glossary & Contracts
# ============================================================================


@dataclass(frozen=True)
class SpecNode:
    node_id: str
    title: str
    kind: str
    status: str
    enforcement: str
    updated: str
    summary: str
    parent: str | None
    depends_on: tuple[str, ...]
    enables: tuple[str, ...]
    validates: tuple[str, ...]
    supersedes: tuple[str, ...]
    conflicts_with: tuple[str, ...]
    alternative_of: str | None
    canonical_term: str | None
    forbidden_aliases: tuple[str, ...]
    do_rules: tuple[str, ...]
    dont_rules: tuple[str, ...]
    signature_or_schema: str | None
    postconditions: tuple[str, ...]
    intent_refs: tuple[str, ...]
    plan_refs: tuple[str, ...]
    knowledge_debt_refs: tuple[str, ...]
    governs_scripts: tuple[str, ...]
    verified_by_scripts: tuple[str, ...]
    source: str
    body: str

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.node_id,
            "title": self.title,
            "kind": self.kind,
            "status": self.status,
            "enforcement": self.enforcement,
            "updated": self.updated,
            "summary": self.summary,
            "parent": self.parent,
            "depends_on": list(self.depends_on),
            "enables": list(self.enables),
            "validates": list(self.validates),
            "supersedes": list(self.supersedes),
            "conflicts_with": list(self.conflicts_with),
            "canonical_term": self.canonical_term,
            "forbidden_aliases": list(self.forbidden_aliases),
            "do_rules": list(self.do_rules),
            "dont_rules": list(self.dont_rules),
            "signature_or_schema": self.signature_or_schema,
            "postconditions": list(self.postconditions),
            "intent_refs": list(self.intent_refs),
            "plan_refs": list(self.plan_refs),
            "knowledge_debt_refs": list(self.knowledge_debt_refs),
            "governs_scripts": list(self.governs_scripts),
            "verified_by_scripts": list(self.verified_by_scripts),
            "source": self.source,
        }
        if self.alternative_of:
            payload["alternative_of"] = self.alternative_of
        return payload


def load_spec_graph(repo_root: Path) -> tuple[dict[str, SpecNode], list[dict[str, Any]]]:
    """Load and validate all Spec Graph nodes if `_aiHumanInteract/specs/nodes` exists."""
    repo_root = repo_root.resolve()
    nodes_dir = repo_root / "_aiHumanInteract" / "specs" / "nodes"
    if not nodes_dir.is_dir():
        return {}, []

    nodes: dict[str, SpecNode] = {}
    for path in sorted(nodes_dir.glob("*.md")):
        rel = path.relative_to(repo_root).as_posix()
        meta, body = parse_front_matter(path)
        nid = str(meta.get("id", "")).strip()
        if not SPEC_ID_RE.fullmatch(nid):
            raise PtmGraphError(f"{rel}: invalid spec ID {nid!r} (expected SPEC-###)")
        if path.stem != nid:
            raise PtmGraphError(f"{rel}: filename must match {nid}.md")
        title = str(meta.get("title", "")).strip()
        if not title:
            raise PtmGraphError(f"{rel}: title must be non-empty")
        kind = str(meta.get("kind", "")).strip()
        if kind not in SPEC_KINDS:
            raise PtmGraphError(f"{rel}: invalid spec kind {kind!r} (expected one of {sorted(SPEC_KINDS)})")
        status = str(meta.get("status", "")).strip()
        if status not in SPEC_STATUSES:
            raise PtmGraphError(f"{rel}: invalid spec status {status!r}")
        enforcement = str(meta.get("enforcement", "must")).strip()
        if enforcement not in SPEC_ENFORCEMENTS:
            raise PtmGraphError(f"{rel}: invalid enforcement {enforcement!r}")
        updated = _check_iso_date(meta.get("updated"), rel)
        summary = str(meta.get("summary", "")).strip()
        if not summary:
            raise PtmGraphError(f"{rel}: summary is required on Spec nodes")

        parent = meta.get("parent")
        if parent is not None:
            parent = str(parent).strip() or None
            if parent and not SPEC_ID_RE.fullmatch(parent):
                raise PtmGraphError(f"{rel}: invalid parent spec ID {parent!r}")

        alt_of_raw = meta.get("alternative_of")
        alt_of: str | None = None
        if alt_of_raw is not None:
            alt_of = str(alt_of_raw).strip() or None
            if alt_of and not SPEC_ID_RE.fullmatch(alt_of):
                raise PtmGraphError(f"{rel}: invalid alternative_of spec ID {alt_of!r}")

        def _str_tuple(key: str, pattern: re.Pattern[str] | None = None) -> tuple[str, ...]:
            raw = meta.get(key, [])
            if not isinstance(raw, list):
                raise PtmGraphError(f"{rel}: {key} must be a list")
            items = tuple(str(x).strip() for x in raw if str(x).strip())
            if pattern:
                for item in items:
                    if not pattern.fullmatch(item):
                        raise PtmGraphError(f"{rel}: invalid ID {item!r} in {key}")
            return items

        canon_term = meta.get("canonical_term")
        sig_schema = meta.get("signature_or_schema")

        if nid in nodes:
            raise PtmGraphError(f"duplicate spec ID {nid}")

        nodes[nid] = SpecNode(
            node_id=nid,
            title=title,
            kind=kind,
            status=status,
            enforcement=enforcement,
            updated=updated,
            summary=summary,
            parent=parent,
            depends_on=_str_tuple("depends_on", SPEC_ID_RE),
            enables=_str_tuple("enables", SPEC_ID_RE),
            validates=_str_tuple("validates", SPEC_ID_RE),
            supersedes=_str_tuple("supersedes", SPEC_ID_RE),
            conflicts_with=_str_tuple("conflicts_with", SPEC_ID_RE),
            alternative_of=alt_of,
            canonical_term=str(canon_term).strip() if canon_term else None,
            forbidden_aliases=_str_tuple("forbidden_aliases"),
            do_rules=_str_tuple("do_rules"),
            dont_rules=_str_tuple("dont_rules"),
            signature_or_schema=str(sig_schema).strip() if sig_schema else None,
            postconditions=_str_tuple("postconditions"),
            intent_refs=_str_tuple("intent_refs", INTENT_ID_RE),
            plan_refs=_str_tuple("plan_refs", PLAN_ID_RE),
            knowledge_debt_refs=_str_tuple("knowledge_debt_refs", KD_ID_RE),
            governs_scripts=_str_tuple("governs_scripts"),
            verified_by_scripts=_str_tuple("verified_by_scripts"),
            source=rel,
            body=body,
        )

    edges: list[dict[str, Any]] = []
    hierarchy_adj: dict[str, list[str]] = defaultdict(list)
    dep_adj: dict[str, list[str]] = defaultdict(list)
    alt_adj: dict[str, list[str]] = defaultdict(list)
    sup_adj: dict[str, list[str]] = defaultdict(list)
    hard_dep_pairs = {(dep, n.node_id) for n in nodes.values() for dep in n.depends_on}

    for nid, node in sorted(nodes.items()):
        if node.parent:
            if node.parent not in nodes:
                raise PtmGraphError(f"{nid}: dangling parent spec {node.parent}")
            hierarchy_adj[node.parent].append(nid)
            edges.append(
                {
                    "from": node.parent,
                    "to": nid,
                    "relationship": "decomposes_spec",
                    "provenance": "declared",
                }
            )
        for prereq in node.depends_on:
            if prereq == nid or prereq not in nodes:
                raise PtmGraphError(f"{nid}: invalid or dangling depends_on spec {prereq}")
            dep_adj[nid].append(prereq)
            edges.append(
                {
                    "from": prereq,
                    "to": nid,
                    "relationship": "prerequisite_for",
                    "provenance": "declared",
                }
            )
        for target in node.enables:
            if target == nid or target not in nodes:
                raise PtmGraphError(f"{nid}: invalid or dangling enables spec {target}")
            if (nid, target) in hard_dep_pairs:
                raise PtmGraphError(
                    f"{nid}: enables duplicates hard dependency declared by {target}"
                )
            edges.append(
                {
                    "from": nid,
                    "to": target,
                    "relationship": "enables",
                    "provenance": "declared",
                }
            )
        for rel_name in ("validates", "supersedes", "conflicts_with"):
            for target in getattr(node, rel_name):
                if target == nid or target not in nodes:
                    raise PtmGraphError(f"{nid}: invalid or dangling {rel_name} spec {target}")
                if rel_name == "supersedes":
                    sup_adj[nid].append(target)
                    if nodes[target].status != "superseded":
                        raise PtmGraphError(
                            f"{nid}: supersedes target {target} must have status 'superseded'"
                        )
                edges.append(
                    {
                        "from": nid,
                        "to": target,
                        "relationship": rel_name,
                        "provenance": "declared",
                    }
                )
        if node.alternative_of:
            if node.alternative_of == nid or node.alternative_of not in nodes:
                raise PtmGraphError(
                    f"{nid}: invalid or dangling alternative_of spec {node.alternative_of}"
                )
            alt_adj[nid].append(node.alternative_of)
            edges.append(
                {
                    "from": nid,
                    "to": node.alternative_of,
                    "relationship": "alternative_of",
                    "provenance": "declared",
                }
            )

    for graph_label, adj in (
        ("parent", hierarchy_adj),
        ("dependency", dep_adj),
        ("alternative", alt_adj),
        ("supersession", sup_adj),
    ):
        cyc = _find_cycle(adj)
        if cyc:
            raise PtmGraphError(f"spec {graph_label} cycle: {' -> '.join(cyc)}")

    return nodes, edges


def compute_spec_impact(repo_root: Path, spec_id: str) -> dict[str, Any]:
    """Compute cross-graph blast radius if `spec_id` is amended, deprecated, or superseded."""
    repo_root = repo_root.resolve()
    spec_nodes, _ = load_spec_graph(repo_root)
    if spec_id not in spec_nodes:
        raise PtmGraphError(f"unknown spec ID: {spec_id}")
    spec = spec_nodes[spec_id]

    intents, _ = load_intent_graph(repo_root)
    kds, _ = load_knowledge_debt_graph(repo_root)

    plan_root = repo_root / "_aiHumanInteract" / "plan"
    plan_nodes: dict[str, plan_validate.PlanNode] = {}
    if plan_root.is_dir() and any((plan_root / lvl).is_dir() for lvl in plan_validate.LEVELS):
        loaded, errs = plan_validate.load_and_validate(plan_root, repo_root)
        if not errs:
            plan_nodes = loaded

    # Transitive child & dependent specs
    spec_downstream_adj: dict[str, list[str]] = defaultdict(list)
    for sid, snode in spec_nodes.items():
        if snode.parent:
            spec_downstream_adj[snode.parent].append(sid)
        for dep in snode.depends_on:
            spec_downstream_adj[dep].append(sid)
        for en in snode.enables:
            spec_downstream_adj[sid].append(en)

    dependent_specs: list[str] = []
    q = [spec_id]
    seen_specs = {spec_id}
    while q:
        cur = q.pop(0)
        for nxt in sorted(set(spec_downstream_adj.get(cur, ()))):
            if nxt not in seen_specs:
                seen_specs.add(nxt)
                dependent_specs.append(nxt)
                q.append(nxt)

    linked_intents = set(spec.intent_refs)
    for iid, inode in intents.items():
        if spec_id in inode.spec_refs:
            linked_intents.add(iid)

    linked_kds = set(spec.knowledge_debt_refs)
    for kid, knode in kds.items():
        if spec_id in knode.spec_refs:
            linked_kds.add(kid)

    direct_plans = set(spec.plan_refs)
    for pid, pnode in plan_nodes.items():
        for sref in pnode.links.get("spec", ()):
            if Path(sref).stem == spec_id:
                direct_plans.add(pid)

    plan_dep_adj: dict[str, list[str]] = defaultdict(list)
    for pid, pnode in plan_nodes.items():
        for dep in pnode.depends_on:
            plan_dep_adj[dep].append(pid)

    downstream_plans: list[str] = []
    pq = sorted(direct_plans)
    seen_plans = set(pq)
    while pq:
        cur = pq.pop(0)
        for nxt in sorted(plan_dep_adj.get(cur, ())):
            if nxt not in seen_plans:
                seen_plans.add(nxt)
                downstream_plans.append(nxt)
                pq.append(nxt)

    return {
        "spec_id": spec_id,
        "title": spec.title,
        "kind": spec.kind,
        "status": spec.status,
        "enforcement": spec.enforcement,
        "dependent_specs": dependent_specs,
        "originating_intents": sorted(linked_intents),
        "implementing_plans": sorted(direct_plans),
        "downstream_plans": downstream_plans,
        "linked_knowledge_debt": sorted(linked_kds),
        "governed_scripts": sorted(spec.governs_scripts),
        "verification_scripts": sorted(spec.verified_by_scripts),
    }


def build_spec_views(repo_root: Path) -> dict[str, Any]:
    """Validate and write Spec Graph generated views under `_aiHumanInteract/specs/structure/`."""
    repo_root = repo_root.resolve()
    nodes, edges = load_spec_graph(repo_root)
    impacts = {sid: compute_spec_impact(repo_root, sid) for sid in sorted(nodes)}
    payload = {
        "schema_version": SPEC_SCHEMA,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "source_of_truth": ["_aiHumanInteract/specs/nodes/*.md"],
        "nodes": [
            {**nodes[k].as_payload(), "impact_preview": impacts[k]}
            for k in sorted(nodes)
        ],
        "edges": edges,
    }
    if not nodes:
        return payload

    struct_dir = repo_root / "_aiHumanInteract" / "specs" / "structure"
    struct_dir.mkdir(parents=True, exist_ok=True)
    (struct_dir / "graph.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    md_lines = [
        "# Spec Graph (Standing Laws, Ubiquitous Language & Contracts)",
        "",
        "Generated by `scripts/ptm.py`; edit `_aiHumanInteract/specs/nodes/*.md` instead.",
        "",
        "```mermaid",
        "flowchart LR",
    ]
    for sid in sorted(nodes):
        s = nodes[sid]
        safe_t = s.title.replace('"', "'")
        md_lines.append(
            f'    {sid.replace("-", "_")}["{sid}: {safe_t}<br/>({s.kind} · {s.enforcement} · {s.status})"]'
        )
    for e in edges:
        u = e["from"].replace("-", "_")
        v = e["to"].replace("-", "_")
        conn = "-->" if e["relationship"] == "decomposes_spec" else "-.->"
        md_lines.append(f'    {u} {conn}|{e["relationship"]}| {v}')
    md_lines.extend(
        [
            "```",
            "",
            "## Normative Specifications",
            "",
            "| ID | Spec | Kind | Enforcement | Status | Intents | Plans | Governs Scripts | Verified By |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for sid in sorted(nodes):
        s = nodes[sid]
        md_lines.append(
            f"| `{sid}` | [{s.title}](../nodes/{sid}.md) | `{s.kind}` | `{s.enforcement}` | `{s.status}` | "
            f"{', '.join(s.intent_refs) or '—'} | {', '.join(s.plan_refs) or '—'} | "
            f"{', '.join(s.governs_scripts) or '—'} | {', '.join(s.verified_by_scripts) or '—'} |"
        )
    md_lines.append("")
    (struct_dir / "graph.md").write_text("\n".join(md_lines), encoding="utf-8")

    canvas_nodes = [
        {
            "id": f"spec-{sid}",
            "type": "text",
            "x": (idx % 3) * 450,
            "y": (idx // 3) * 280,
            "width": 390,
            "height": 220,
            "color": "4" if nodes[sid].status == "enforced" else "2",
            "text": (
                f"## [[{nodes[sid].source}|{sid} · {nodes[sid].title}]]\n\n"
                f"**{nodes[sid].kind.upper()}** (`{nodes[sid].enforcement}` · `{nodes[sid].status}`)\n\n"
                f"{nodes[sid].summary}"
            ),
        }
        for idx, sid in enumerate(sorted(nodes))
    ]
    canvas_edges = [
        {
            "id": f"spec-edge-{i}",
            "fromNode": f"spec-{e['from']}",
            "fromSide": "right",
            "toNode": f"spec-{e['to']}",
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
    spec_refs: tuple[str, ...]
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
            "spec_refs": list(self.spec_refs),
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
        spec_refs = tuple(str(x).strip() for x in meta.get("spec_refs", []) if str(x).strip())
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
            spec_refs=spec_refs,
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
        for spref in spec_refs:
            edges.append(
                {
                    "from": nid,
                    "to": spref,
                    "relationship": "questions_spec",
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
    """Trace which Intent, Spec, Plan, and Script nodes require reorganization if `kd_id` is rejected."""
    repo_root = repo_root.resolve()
    kd_nodes, _ = load_knowledge_debt_graph(repo_root)
    if kd_id not in kd_nodes:
        raise PtmGraphError(f"unknown knowledge-debt ID: {kd_id}")
    kd = kd_nodes[kd_id]
    spec_nodes, _ = load_spec_graph(repo_root)
    review_specs = set(kd.spec_refs)
    for sid, snode in spec_nodes.items():
        if kd_id in snode.knowledge_debt_refs:
            review_specs.add(sid)

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
        "amend_or_review_specs": sorted(review_specs),
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

    # Collect Plan Graph & Spec Graph code/test links for cross-graph traceability
    plan_coverage: dict[str, list[str]] = defaultdict(list)
    spec_governance: dict[str, list[str]] = defaultdict(list)
    spec_verification: dict[str, list[str]] = defaultdict(list)
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

    try:
        spec_nodes_for_scr, _ = load_spec_graph(repo_root)
    except PtmGraphError:
        spec_nodes_for_scr = {}
    for sid, snode in spec_nodes_for_scr.items():
        if snode.status in {"superseded", "deprecated"}:
            continue
        for ref in snode.governs_scripts:
            spec_governance[ref].append(sid)
            if Path(ref).suffix.lower() in CODE_EXTENSIONS:
                planned_targets.add(ref)
        for ref in snode.verified_by_scripts:
            spec_verification[ref].append(sid)
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
            "governed_by_plans": sorted(set(plan_coverage.get(rel, []))),
            "governed_by_specs": sorted(set(spec_governance.get(rel, []))),
            "verifies_specs": sorted(set(spec_verification.get(rel, []))),
        }

    # Include planned-but-missing code targets so gaps between Plan/Spec and Scripts are visible
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
            "summary": "Planned in Plan/Spec Graph; file not yet created on disk.",
            "inferred_note": None,
            "inferred_evidence": None,
            "classes": [],
            "functions": [],
            "is_entrypoint": False,
            "governed_by_plans": sorted(set(plan_coverage.get(missing_rel, []))),
            "governed_by_specs": sorted(set(spec_governance.get(missing_rel, []))),
            "verifies_specs": sorted(set(spec_verification.get(missing_rel, []))),
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
    """Load Intent, Spec, Plan (v4), Knowledge Debt, Scripts, Evaluations & Verification into one view."""
    repo_root = repo_root.resolve()
    intents, intent_edges = load_intent_graph(repo_root)
    specs, spec_edges = load_spec_graph(repo_root)
    kds, kd_edges = load_knowledge_debt_graph(repo_root)
    evals = load_evaluations(repo_root)

    plan_payload: dict[str, Any] = {"nodes": [], "edges": []}
    plan_root = repo_root / "_aiHumanInteract" / "plan"
    has_plan_nodes = plan_root.is_dir() and any(
        any((plan_root / lvl).glob("*.md"))
        for lvl in plan_validate.LEVELS
        if (plan_root / lvl).is_dir()
    )
    if has_plan_nodes:
        p_nodes = plan_validate.require_valid_graph(plan_root, repo_root)
        plan_payload = plan_build.graph_payload(plan_root, p_nodes)

    scripts_payload = scan_scripts_graph(repo_root)

    # Extract explicit cross-graph edges (`Declared`) without duplicates
    cross_edges: list[dict[str, Any]] = []
    seen_cross: set[tuple[str, str, str]] = set()

    def _add_cross(src: str, dst: str, rel: str) -> None:
        key = (src, dst, rel)
        if src != dst and key not in seen_cross:
            seen_cross.add(key)
            cross_edges.append(
                {
                    "from": src,
                    "to": dst,
                    "relationship": rel,
                    "provenance": "declared",
                }
            )

    for iid, inode in sorted(intents.items()):
        for pid in inode.plan_refs:
            _add_cross(iid, pid, "seeds_plan")
        for sid in inode.spec_refs:
            _add_cross(iid, sid, "crystallizes_into")

    for sid, snode in sorted(specs.items()):
        for iid in snode.intent_refs:
            _add_cross(iid, sid, "crystallizes_into")
        for pid in snode.plan_refs:
            _add_cross(pid, sid, "implements_spec")
        for kid in snode.knowledge_debt_refs:
            _add_cross(kid, sid, "questions_spec")
        for sref in snode.governs_scripts:
            _add_cross(sid, f"SCR:{sref}", "governs_script")
        for vref in snode.verified_by_scripts:
            _add_cross(f"SCR:{vref}", sid, "verifies_spec")

    for pnode in plan_payload.get("nodes", []):
        pid = pnode["id"]
        for cat in ("code", "tests", "scripts"):
            for ref in pnode.get("links", {}).get(cat, []):
                if not ref.startswith("external:"):
                    _add_cross(pid, f"SCR:{ref}", "implements_in")
        for ref in pnode.get("links", {}).get("intent", []):
            stem = Path(ref).stem
            if INTENT_ID_RE.fullmatch(stem):
                _add_cross(stem, pid, "seeds_plan")
        for ref in pnode.get("links", {}).get("spec", []):
            stem = Path(ref).stem
            if SPEC_ID_RE.fullmatch(stem):
                _add_cross(pid, stem, "implements_spec")

    for e in kd_edges:
        _add_cross(e["from"], e["to"], e["relationship"])

    intent_node_dicts = [intents[k].as_payload() for k in sorted(intents)]
    spec_node_dicts = [
        {
            **specs[k].as_payload(),
            "impact_preview": compute_spec_impact(repo_root, k),
        }
        for k in sorted(specs)
    ]
    plan_node_dicts = [dict(n) for n in plan_payload.get("nodes", [])]
    script_node_dicts = [dict(n) for n in scripts_payload.get("nodes", [])]

    verification_report = attach_verification_and_evaluations(
        repo_root=repo_root,
        intent_nodes=intent_node_dicts,
        spec_nodes=spec_node_dicts,
        plan_nodes=plan_node_dicts,
        script_nodes=script_node_dicts,
        script_edges=scripts_payload.get("edges", []),
        evaluations=evals,
    )

    federated_out: dict[str, Any] = {
        "intent": {
            "nodes": intent_node_dicts,
            "edges": intent_edges,
        },
        "specs": {
            "nodes": spec_node_dicts,
            "edges": spec_edges,
        },
        "plan": {
            **plan_payload,
            "nodes": plan_node_dicts,
        },
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
        "scripts": {
            **scripts_payload,
            "nodes": script_node_dicts,
        },
        "evaluations": {
            "schema_version": EVAL_SCHEMA,
            "node_count": len(evals),
            "nodes": [evals[k].as_payload() for k in sorted(evals)],
        },
        "verification_report": verification_report,
        "cross_edges": cross_edges,
    }

    turns_jsonl = repo_root / "_aiHumanInteract" / "episodes" / "turns.jsonl"
    sqlite_db = repo_root / "_aiHumanInteract" / ".cache" / "memory.sqlite"
    if turns_jsonl.is_file() or sqlite_db.is_file():
        ep_store = EpisodicMemoryStore(repo_root)
        ep_sum = ep_store.export_summary()
        if turns_jsonl.is_file() and ep_sum["turn_count"] == 0:
            ep_sum = ep_store.sync_portable_episodes(federated_out)
        else:
            ep_store.apply_portable_thread_state()
            ep_store.bind_threads_to_federated_graphs(federated_out)
            ep_sum = ep_store.export_summary()
        attach_episodic_threads_to_federated(federated_out, ep_sum)
    else:
        federated_out["episodic_memory"] = {
            "turn_count": 0,
            "span_count": 0,
            "thread_count": 0,
            "folded_count": 0,
            "active_count": 0,
            "vector_blob_count": 0,
            "threads": [],
        }

    return federated_out


# ============================================================================
# 4. DUAL-TRACK VERIFICATION RECEIPTS & SUBSTANTIVE EVALUATIONS (EVAL-###)
# ============================================================================


@dataclass(frozen=True)
class EvaluationNode:
    eval_id: str
    title: str
    kind: str
    verdict: str
    perspective: str
    reviewer_mode: str
    updated: str
    summary: str
    evaluates_intents: tuple[str, ...]
    evaluates_specs: tuple[str, ...]
    evaluates_plans: tuple[str, ...]
    evaluates_scripts: tuple[str, ...]
    preserved_qualities: tuple[str, ...]
    at_risk_qualities: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    recommended_action: str | None
    source: str
    body: str

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.eval_id,
            "title": self.title,
            "kind": self.kind,
            "verdict": self.verdict,
            "perspective": self.perspective,
            "reviewer_mode": self.reviewer_mode,
            "updated": self.updated,
            "summary": self.summary,
            "evaluates_intents": list(self.evaluates_intents),
            "evaluates_specs": list(self.evaluates_specs),
            "evaluates_plans": list(self.evaluates_plans),
            "evaluates_scripts": list(self.evaluates_scripts),
            "preserved_qualities": list(self.preserved_qualities),
            "at_risk_qualities": list(self.at_risk_qualities),
            "evidence_refs": list(self.evidence_refs),
            "recommended_action": self.recommended_action,
            "source": self.source,
            "body": self.body,
        }
        return payload


def load_evaluations(repo_root: Path) -> dict[str, EvaluationNode]:
    """Load `_aiHumanInteract/plan/evaluations/*.md` (structured front matter or legacy notes)."""
    repo_root = repo_root.resolve()
    eval_dir = repo_root / "_aiHumanInteract" / "plan" / "evaluations"
    if not eval_dir.is_dir():
        return {}

    nodes: dict[str, EvaluationNode] = {}
    for path in sorted(eval_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        rel = path.relative_to(repo_root).as_posix()
        raw_txt = path.read_text(encoding="utf-8")
        first_line = raw_txt.splitlines()[0].strip() if raw_txt.splitlines() else ""
        if first_line != "---":
            # Graceful backward compatibility for plain-Markdown legacy evaluation notes
            eid = path.stem
            lines = [ln.strip() for ln in raw_txt.splitlines() if ln.strip()]
            heading = lines[0].lstrip("#").strip() if lines else eid
            para = next((ln for ln in lines[1:] if not ln.startswith("#")), heading)
            nodes[eid] = EvaluationNode(
                eval_id=eid,
                title=heading,
                kind="legacy_note",
                verdict="noted",
                perspective="未标注独立视角（旧版记录）",
                reviewer_mode="legacy",
                updated=date.today().isoformat(),
                summary=para[:200],
                evaluates_intents=(),
                evaluates_specs=(),
                evaluates_plans=(),
                evaluates_scripts=(),
                preserved_qualities=(),
                at_risk_qualities=(),
                evidence_refs=(),
                recommended_action=None,
                source=rel,
                body=raw_txt.strip(),
            )
            continue

        meta, body = parse_front_matter(path)
        eid = str(meta.get("id", "")).strip()
        if not EVAL_ID_RE.fullmatch(eid):
            raise PtmGraphError(f"{rel}: invalid evaluation ID {eid!r} (expected EVAL-###)")
        if path.stem != eid:
            raise PtmGraphError(f"{rel}: filename must match {eid}.md")
        title = str(meta.get("title", "")).strip()
        if not title:
            raise PtmGraphError(f"{rel}: title must be non-empty")
        kind = str(meta.get("kind", "")).strip()
        if kind not in EVAL_KINDS:
            raise PtmGraphError(f"{rel}: invalid kind {kind!r} (expected {sorted(EVAL_KINDS)})")
        verdict = str(meta.get("verdict", "")).strip()
        if verdict not in EVAL_VERDICTS:
            raise PtmGraphError(
                f"{rel}: invalid verdict {verdict!r} (expected {sorted(EVAL_VERDICTS)})"
            )
        perspective = str(meta.get("perspective", "")).strip()
        if not perspective:
            raise PtmGraphError(f"{rel}: perspective is required to prevent abstract self-review")
        reviewer_mode = str(meta.get("reviewer_mode", "isolated_subagent")).strip()
        if reviewer_mode not in EVAL_REVIEWER_MODES:
            raise PtmGraphError(f"{rel}: invalid reviewer_mode {reviewer_mode!r}")
        updated = _check_iso_date(meta.get("updated"), rel)
        summary = str(meta.get("summary", "")).strip()
        if not summary:
            raise PtmGraphError(f"{rel}: summary must be non-empty")

        def _str_list(key: str, pattern: re.Pattern[str] | None = None) -> tuple[str, ...]:
            raw = meta.get(key, [])
            if not isinstance(raw, list):
                raise PtmGraphError(f"{rel}: {key} must be a list")
            items = tuple(str(x).strip() for x in raw if str(x).strip())
            if pattern:
                for item in items:
                    if not pattern.fullmatch(item):
                        raise PtmGraphError(f"{rel}: invalid ID {item!r} in {key}")
            return items

        rec_act = meta.get("recommended_action")
        nodes[eid] = EvaluationNode(
            eval_id=eid,
            title=title,
            kind=kind,
            verdict=verdict,
            perspective=perspective,
            reviewer_mode=reviewer_mode,
            updated=updated,
            summary=summary,
            evaluates_intents=_str_list("evaluates_intents", INTENT_ID_RE),
            evaluates_specs=_str_list("evaluates_specs", SPEC_ID_RE),
            evaluates_plans=_str_list("evaluates_plans", PLAN_ID_RE),
            evaluates_scripts=_str_list("evaluates_scripts"),
            preserved_qualities=_str_list("preserved_qualities"),
            at_risk_qualities=_str_list("at_risk_qualities"),
            evidence_refs=_str_list("evidence_refs"),
            recommended_action=str(rec_act).strip() if rec_act else None,
            source=rel,
            body=body,
        )
    return nodes


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


UNITTEST_RAN_RE = re.compile(r"Ran\s+(\d+)\s+tests?\s+in\s+([\d.]+)s")
UNITTEST_FAIL_DETAIL_RE = re.compile(r"FAILED\s*\(([^)]+)\)")
UNITTEST_CASE_RE = re.compile(
    r"^(test[\w_]*)\s+\(([\w.]+)\).*?\.\.\.\s+(ok|FAIL|ERROR|skipped.*)\s*$"
)
PYTEST_PASSED_RE = re.compile(r"(\d+)\s+passed")
PYTEST_FAILED_RE = re.compile(r"(\d+)\s+(?:failed|error|errors)")


def load_verification_receipt(repo_root: Path) -> dict[str, Any] | None:
    path = repo_root.resolve() / "_aiHumanInteract" / "scripts" / "verification-status.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("schema_version") == VERIFICATION_SCHEMA:
            return data
    except (OSError, json.JSONDecodeError):
        return None
    return None


def run_formal_verification(
    repo_root: Path,
    *,
    command: str | None = None,
    timeout_sec: int = 120,
) -> dict[str, Any]:
    """Execute project tests, capture deterministic pass/fail counts, and record SHA-256 hashes."""
    repo_root = repo_root.resolve()
    scripts_payload = scan_scripts_graph(repo_root)
    existing_nodes = [
        n for n in scripts_payload.get("nodes", []) if n.get("status") != "planned_missing"
    ]
    file_hashes: dict[str, str] = {}
    all_test_paths: list[str] = []
    py_test_paths: list[str] = []
    for n in existing_nodes:
        rel = n["path"]
        fpath = repo_root / rel
        if fpath.is_file():
            file_hashes[rel] = _sha256_file(fpath)
            if n.get("role") == "test" and not rel.startswith("vendor/"):
                all_test_paths.append(rel)
                if rel.endswith(".py"):
                    py_test_paths.append(rel)
    if command:
        named = [r for r in all_test_paths if r in command or Path(r).name in command]
        test_rel_paths = named if named else all_test_paths
    else:
        test_rel_paths = py_test_paths

    now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    env = dict(os.environ)
    existing_py_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{repo_root}{os.pathsep}{existing_py_path}" if existing_py_path else str(repo_root)
    )

    if not command and not test_rel_paths:
        receipt = {
            "schema_version": VERIFICATION_SCHEMA,
            "timestamp": now_iso,
            "runner_command": None,
            "overall_status": "no_tests",
            "exit_code": 0,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "duration_sec": 0.0,
            "test_scripts": {},
            "file_hashes": file_hashes,
            "output_tail": "",
        }
        out_path = repo_root / "_aiHumanInteract" / "scripts" / "verification-status.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return receipt

    if command:
        runner_display = command
        proc = subprocess.run(
            command,
            shell=True,
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    else:
        start_dir = "tests" if (repo_root / "tests").is_dir() else "."
        cmd_argv = [
            sys.executable,
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            start_dir,
            "-p",
            "test_*.py",
            "-v",
        ]
        runner_display = f"python3 -B -m unittest discover -s {start_dir} -p 'test_*.py' -v"
        proc = subprocess.run(
            cmd_argv,
            cwd=repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_sec,
            check=False,
        )

    combined_out = proc.stdout or ""
    total_tests = 0
    failed_tests = 0
    duration_sec = 0.0

    m_ran = UNITTEST_RAN_RE.search(combined_out)
    if m_ran:
        total_tests = int(m_ran.group(1))
        duration_sec = float(m_ran.group(2))
        m_fail = UNITTEST_FAIL_DETAIL_RE.search(combined_out)
        if m_fail:
            for part in m_fail.group(1).split(","):
                k_v = part.strip().split("=")
                if len(k_v) == 2 and k_v[0].strip() in {"failures", "errors"}:
                    failed_tests += int(k_v[1].strip())
        elif proc.returncode != 0:
            failed_tests = max(1, total_tests)
    else:
        mp = PYTEST_PASSED_RE.search(combined_out)
        mf = PYTEST_FAILED_RE.search(combined_out)
        m_node_total = re.search(r"(?:ℹ|#)\s*tests\s+(\d+)", combined_out)
        m_node_fail = re.search(r"(?:ℹ|#)\s*fail\s+(\d+)", combined_out)
        m_node_dur = re.search(r"(?:ℹ|#)\s*duration_ms\s+([\d.]+)", combined_out)
        m_vitest_line = re.search(r"^\s*Tests\s+(.+)$", combined_out, re.MULTILINE)
        m_vitest_dur = re.search(r"Duration\s+([\d.]+)\s*(ms|s)", combined_out)
        if m_node_total:
            total_tests = int(m_node_total.group(1))
            failed_tests = int(m_node_fail.group(1)) if m_node_fail else (1 if proc.returncode != 0 else 0)
            if m_node_dur:
                duration_sec = float(m_node_dur.group(1)) / 1000.0
        elif m_vitest_line:
            vp = re.search(r"(\d+)\s+passed", m_vitest_line.group(1))
            vf = re.search(r"(\d+)\s+failed", m_vitest_line.group(1))
            vt = re.search(r"\((\d+)\)", m_vitest_line.group(1))
            passed_v = int(vp.group(1)) if vp else 0
            failed_v = int(vf.group(1)) if vf else 0
            total_tests = int(vt.group(1)) if vt else (passed_v + failed_v)
            failed_tests = failed_v if vf else (1 if proc.returncode != 0 else 0)
            if m_vitest_dur:
                val = float(m_vitest_dur.group(1))
                duration_sec = val / 1000.0 if m_vitest_dur.group(2) == "ms" else val
        else:
            if mp:
                total_tests += int(mp.group(1))
            if mf:
                f_cnt = int(mf.group(1))
                failed_tests += f_cnt
                total_tests += f_cnt
            if command and proc.returncode == 0 and total_tests == 0:
                total_tests = 1
        if proc.returncode != 0 and failed_tests == 0:
            failed_tests = 1
            total_tests = max(1, total_tests)

    passed_tests = max(0, total_tests - failed_tests)
    overall = "passed" if (proc.returncode == 0 and total_tests > 0) else (
        "no_tests" if (proc.returncode == 0 and total_tests == 0) else "failed"
    )

    # Map individual unittest cases back to test script files
    stem_to_rel = {Path(r).stem: r for r in test_rel_paths}
    per_script: dict[str, dict[str, Any]] = {
        r: {"status": "passed" if overall == "passed" else ("failed" if overall == "failed" else "no_tests"), "passed": 0, "failed": 0, "cases": []}
        for r in test_rel_paths
    }
    matched_any_case = False
    for raw_ln in combined_out.splitlines():
        mc = UNITTEST_CASE_RE.match(raw_ln.strip())
        if not mc:
            continue
        case_name, dotted_cls, outcome = mc.group(1), mc.group(2), mc.group(3)
        parts = dotted_cls.split(".")
        matched_rel = None
        for idx in range(len(parts), 0, -1):
            cand = "/".join(parts[:idx]) + ".py"
            if cand in per_script:
                matched_rel = cand
                break
            if f"tests/{cand}" in per_script:
                matched_rel = f"tests/{cand}"
                break
        if not matched_rel and len(parts) >= 2 and parts[-2] in stem_to_rel:
            matched_rel = stem_to_rel[parts[-2]]
        if matched_rel:
            matched_any_case = True
            ok = outcome.startswith("ok") or outcome.startswith("skipped")
            rec = per_script[matched_rel]
            if ok:
                rec["passed"] += 1
            else:
                rec["failed"] += 1
            rec["cases"].append({"name": case_name, "status": "passed" if ok else "failed"})

    if matched_any_case:
        for r, rec in per_script.items():
            if rec["failed"] > 0:
                rec["status"] = "failed"
            elif rec["passed"] > 0:
                rec["status"] = "passed"
            else:
                rec["status"] = "passed" if overall == "passed" else "unverified"
    else:
        for r, rec in per_script.items():
            if overall == "passed":
                rec["passed"] = max(1, passed_tests)
                rec["status"] = "passed"
            elif overall == "failed":
                rec["failed"] = max(1, failed_tests)
                rec["status"] = "failed"

    tail_lines = combined_out.strip().splitlines()[-18:]
    receipt = {
        "schema_version": VERIFICATION_SCHEMA,
        "timestamp": now_iso,
        "runner_command": runner_display,
        "overall_status": overall,
        "exit_code": proc.returncode,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "duration_sec": round(duration_sec, 4),
        "test_scripts": per_script,
        "file_hashes": file_hashes,
        "output_tail": "\n".join(tail_lines),
    }
    out_path = repo_root / "_aiHumanInteract" / "scripts" / "verification-status.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def _rollup_eval_status(eval_items: list[dict[str, Any]]) -> dict[str, Any]:
    if not eval_items:
        return {"count": 0, "status": "none", "eval_ids": [], "at_risk_count": 0}
    verdicts = {e["verdict"] for e in eval_items}
    if "fail" in verdicts:
        st = "fail"
    elif "concerns" in verdicts:
        st = "concerns"
    elif "selected_winner" in verdicts:
        st = "selected_winner"
    elif "pass" in verdicts:
        st = "pass"
    else:
        st = "noted"
    at_risk_cnt = sum(len(e.get("at_risk_qualities") or []) for e in eval_items)
    return {
        "count": len(eval_items),
        "status": st,
        "eval_ids": [e["id"] for e in eval_items],
        "at_risk_count": at_risk_cnt,
    }


def attach_verification_and_evaluations(
    *,
    repo_root: Path,
    intent_nodes: list[dict[str, Any]],
    spec_nodes: list[dict[str, Any]],
    plan_nodes: list[dict[str, Any]],
    script_nodes: list[dict[str, Any]],
    script_edges: list[dict[str, Any]],
    evaluations: Mapping[str, EvaluationNode],
) -> dict[str, Any]:
    """Enrich federated nodes in-place with SHA-256 verification status & `EVAL-###` critiques."""
    receipt = load_verification_receipt(repo_root)
    recorded_hashes: dict[str, str] = (receipt or {}).get("file_hashes", {})
    test_script_results: dict[str, dict[str, Any]] = (receipt or {}).get("test_scripts", {})

    # 1. Live SHA-256 check across all scripts on disk
    current_hashes: dict[str, str] = {}
    missing_paths: set[str] = set()
    for sn in script_nodes:
        rel = sn["path"]
        fpath = repo_root / rel
        if sn.get("status") == "planned_missing" or not fpath.is_file():
            missing_paths.add(rel)
        else:
            current_hashes[rel] = _sha256_file(fpath)

    def _is_file_stale(rel: str) -> bool:
        if not receipt or rel in missing_paths:
            return False
        rec_h = recorded_hashes.get(rel)
        cur_h = current_hashes.get(rel)
        return bool(rec_h is None or cur_h != rec_h)

    global_stale_files = sorted(rel for rel in current_hashes if _is_file_stale(rel))

    # 2. Transitive script dependency closure (`test_file -> imported/invoked modules`)
    callees_adj: dict[str, list[str]] = defaultdict(list)
    for e in script_edges:
        if e.get("relationship") in {"imports", "invokes"}:
            callees_adj[e["from_path"]].append(e["to_path"])

    def _reachable_callees(start_rel: str) -> list[str]:
        seen = {start_rel}
        q = [start_rel]
        out = [start_rel]
        while q:
            cur = q.pop(0)
            for nxt in sorted(set(callees_adj.get(cur, ()))):
                if nxt not in seen:
                    seen.add(nxt)
                    out.append(nxt)
                    q.append(nxt)
        return out

    test_reach: dict[str, list[str]] = {}
    covering_tests_by_script: dict[str, set[str]] = defaultdict(set)
    for sn in script_nodes:
        if sn.get("role") == "test":
            reach = _reachable_callees(sn["path"])
            test_reach[sn["path"]] = reach
            for target_rel in reach:
                covering_tests_by_script[target_rel].add(sn["path"])

    # Also propagate explicit Spec/Plan test pairings (`verified_by_scripts` -> `governs_scripts`, `links.tests` -> `links.code`)
    for sp in spec_nodes:
        if sp.get("status") in {"superseded", "deprecated"}:
            continue
        for t_rel in sp.get("verified_by_scripts", []):
            for g_rel in sp.get("governs_scripts", []):
                covering_tests_by_script[g_rel].add(t_rel)
    for pn in plan_nodes:
        if pn.get("status") == "superseded":
            continue
        lnks = pn.get("links") or {}
        for t_rel in lnks.get("tests", []):
            for c_rel in lnks.get("code", []):
                covering_tests_by_script[c_rel].add(t_rel)

    def _eval_file_group(test_rels: Iterable[str], governed_rels: Iterable[str]) -> dict[str, Any]:
        tests = sorted({r for r in test_rels if r and not r.startswith("external:")})
        govs = sorted({r for r in governed_rels if r and not r.startswith("external:")})
        all_files = sorted(set(tests) | set(govs))
        missing = sorted(r for r in all_files if r in missing_paths)
        if not tests:
            return {
                "status": "unverified",
                "reason": "尚未声明自动化验证测试脚本",
                "test_scripts": [],
                "governed_files": govs,
                "stale_files": [],
                "missing_files": missing,
                "receipt_timestamp": (receipt or {}).get("timestamp"),
            }
        if missing:
            return {
                "status": "unverified",
                "reason": f"受辖源码或测试尚未落地: {', '.join(missing)}",
                "test_scripts": tests,
                "governed_files": govs,
                "stale_files": [],
                "missing_files": missing,
                "receipt_timestamp": (receipt or {}).get("timestamp"),
            }
        if not receipt or receipt.get("overall_status") == "no_tests":
            return {
                "status": "unverified",
                "reason": "尚未生成形式验证回执（请执行 ptm.py verify）",
                "test_scripts": tests,
                "governed_files": govs,
                "stale_files": [],
                "missing_files": [],
                "receipt_timestamp": None,
            }
        failing_tests = [
            t
            for t in tests
            if test_script_results.get(t, {}).get("status") == "failed"
            or (t not in test_script_results and receipt.get("overall_status") == "failed")
        ]
        if failing_tests:
            return {
                "status": "failing",
                "reason": f"测试执行未通过: {', '.join(failing_tests)}",
                "test_scripts": tests,
                "governed_files": govs,
                "stale_files": [],
                "missing_files": [],
                "receipt_timestamp": receipt.get("timestamp"),
                "runner_command": receipt.get("runner_command"),
            }
        # Include transitive imports of the test scripts so changing a helper module invalidates its test!
        watched_files = set(all_files)
        for t in tests:
            watched_files.update(test_reach.get(t, [t]))
        stale = sorted(f for f in watched_files if _is_file_stale(f))
        if stale:
            return {
                "status": "stale",
                "reason": f"自上次回执后源码/测试 SHA-256 已变更: {', '.join(stale)}",
                "test_scripts": tests,
                "governed_files": govs,
                "stale_files": stale,
                "missing_files": [],
                "receipt_timestamp": receipt.get("timestamp"),
                "runner_command": receipt.get("runner_command"),
            }
        # Verify at least one declared test actually ran & passed in receipt
        ran_passed = [
            t for t in tests if test_script_results.get(t, {}).get("status") == "passed"
        ]
        if not ran_passed and receipt.get("overall_status") != "passed":
            return {
                "status": "unverified",
                "reason": "测试脚本尚未纳入最新运行回执",
                "test_scripts": tests,
                "governed_files": govs,
                "stale_files": [],
                "missing_files": [],
                "receipt_timestamp": receipt.get("timestamp"),
            }
        return {
            "status": "verified",
            "reason": f"测试通过且 {len(watched_files)} 个受辖文件 SHA-256 指纹保鲜一致",
            "test_scripts": tests,
            "governed_files": govs,
            "stale_files": [],
            "missing_files": [],
            "receipt_timestamp": receipt.get("timestamp"),
            "runner_command": receipt.get("runner_command"),
            "passed_tests": receipt.get("passed_tests", 0),
            "total_tests": receipt.get("total_tests", 0),
        }

    # 3. Compute verification rollup for Scripts, Specs, and Plans
    for sn in script_nodes:
        rel = sn["path"]
        if sn.get("status") == "planned_missing":
            sn["verification"] = {
                "status": "unverified",
                "reason": "规划目标文件尚未在磁盘创建",
                "test_scripts": [],
                "governed_files": [rel],
                "stale_files": [],
                "missing_files": [rel],
            }
        elif sn.get("role") == "test":
            sn["verification"] = _eval_file_group([rel], test_reach.get(rel, [rel]))
        else:
            cov_tests = sorted(covering_tests_by_script.get(rel, ()))
            sn["verification"] = _eval_file_group(cov_tests, [rel])

    for sp in spec_nodes:
        if sp.get("status") in {"superseded", "deprecated"}:
            sp["verification"] = {
                "status": "not_applicable",
                "reason": f"规范处于 {sp['status']} 状态，无需实测守门",
                "test_scripts": [],
                "governed_files": [],
                "stale_files": [],
                "missing_files": [],
            }
        else:
            sp["verification"] = _eval_file_group(
                sp.get("verified_by_scripts", []), sp.get("governs_scripts", [])
            )

    # Plan nodes: leaf WPs evaluate own `links.tests` + `validated_by` WP tests; parent scopes aggregate children
    plan_by_id = {pn["id"]: pn for pn in plan_nodes}
    children_by_plan: dict[str, list[str]] = defaultdict(list)
    validating_tests_by_plan: dict[str, set[str]] = defaultdict(set)
    for pn in plan_nodes:
        p = pn.get("parent")
        if p:
            children_by_plan[p].append(pn["id"])
        if pn.get("status") != "superseded":
            p_tests = (pn.get("links") or {}).get("tests", [])
            for v_target in pn.get("validates", []):
                validating_tests_by_plan[v_target].update(p_tests)

    wp_verifications: dict[str, dict[str, Any]] = {}
    for pn in plan_nodes:
        pid = pn["id"]
        if pn.get("status") == "superseded":
            wp_verifications[pid] = {
                "status": "not_applicable",
                "reason": "已被替代方案接替 (superseded)",
                "test_scripts": [],
                "governed_files": [],
                "stale_files": [],
                "missing_files": [],
            }
            continue
        if not children_by_plan.get(pid):
            lnks = pn.get("links") or {}
            eff_tests = sorted(set(lnks.get("tests", [])) | validating_tests_by_plan.get(pid, set()))
            eff_code = lnks.get("code", [])
            wp_verifications[pid] = _eval_file_group(eff_tests, eff_code)

    def _resolve_plan_verification(pid: str) -> dict[str, Any]:
        if pid in wp_verifications:
            return wp_verifications[pid]
        pn = plan_by_id[pid]
        active_children = [
            ch for ch in children_by_plan.get(pid, [])
            if plan_by_id[ch].get("status") != "superseded"
        ]
        if not active_children:
            lnks = pn.get("links") or {}
            res = _eval_file_group(lnks.get("tests", []), lnks.get("code", []))
            wp_verifications[pid] = res
            return res
        child_vs = [_resolve_plan_verification(ch) for ch in active_children]
        statuses = [cv["status"] for cv in child_vs]
        all_tests = sorted({t for cv in child_vs for t in cv.get("test_scripts", [])})
        all_govs = sorted({g for cv in child_vs for g in cv.get("governed_files", [])})
        all_stale = sorted({s for cv in child_vs for s in cv.get("stale_files", [])})
        all_missing = sorted({m for cv in child_vs for m in cv.get("missing_files", [])})
        v_cnt = sum(1 for st in statuses if st == "verified")
        if "failing" in statuses:
            st, rsn = "failing", "子工作包存在未通过测试"
        elif "stale" in statuses:
            st, rsn = "stale", f"子工作包受辖源码已修改待重测: {', '.join(all_stale)}"
        elif v_cnt == len(statuses):
            st, rsn = "verified", f"下属 {v_cnt}/{len(statuses)} 个有效子项全部实测通过且哈希保鲜"
        elif v_cnt > 0 or "partial" in statuses:
            st, rsn = "partial", f"下属子项部分完成实测覆盖 ({v_cnt}/{len(statuses)} 项已实测)"
        else:
            st, rsn = "unverified", "下属子项尚未建立有效实测回执"
        res = {
            "status": st,
            "reason": rsn,
            "test_scripts": all_tests,
            "governed_files": all_govs,
            "stale_files": all_stale,
            "missing_files": all_missing,
            "receipt_timestamp": (receipt or {}).get("timestamp"),
            "runner_command": (receipt or {}).get("runner_command"),
        }
        wp_verifications[pid] = res
        return res

    for pn in plan_nodes:
        pn["verification"] = _resolve_plan_verification(pn["id"])

    # 4. Bind substantive evaluations (`EVAL-###`) across Intent, Spec, Plan, and Scripts
    evals_by_target: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for eid, ev in sorted(evaluations.items()):
        ep = ev.as_payload()
        for iid in ev.evaluates_intents:
            evals_by_target[iid][eid] = ep
        for sid in ev.evaluates_specs:
            evals_by_target[sid][eid] = ep
        for pid in ev.evaluates_plans:
            evals_by_target[pid][eid] = ep
        for srel in ev.evaluates_scripts:
            evals_by_target[f"SCR:{srel}"][eid] = ep

    # Also honor reverse `PlanNode.links.evaluation` pointers (`_aiHumanInteract/plan/evaluations/EVAL-001.md`)
    for pn in plan_nodes:
        for eref in (pn.get("links") or {}).get("evaluation", []):
            stem = Path(eref).stem
            if stem in evaluations:
                evals_by_target[pn["id"]][stem] = evaluations[stem].as_payload()

    for group in (intent_nodes, spec_nodes, plan_nodes, script_nodes):
        for n in group:
            nid = n["id"]
            attached = [evals_by_target[nid][k] for k in sorted(evals_by_target.get(nid, ()))]
            n["evaluations"] = attached
            n["evaluation_rollup"] = _rollup_eval_status(attached)

    active_specs = [s for s in spec_nodes if s.get("status") not in {"superseded", "deprecated"}]
    active_wps = [
        p for p in plan_nodes
        if p.get("level") == "work-package" and p.get("status") != "superseded"
    ]
    eval_list = [evaluations[k].as_payload() for k in sorted(evaluations)]

    return {
        "has_receipt": receipt is not None,
        "receipt_timestamp": (receipt or {}).get("timestamp"),
        "runner_command": (receipt or {}).get("runner_command"),
        "overall_test_status": (receipt or {}).get("overall_status", "unverified"),
        "total_tests": (receipt or {}).get("total_tests", 0),
        "passed_tests": (receipt or {}).get("passed_tests", 0),
        "failed_tests": (receipt or {}).get("failed_tests", 0),
        "global_stale_files": global_stale_files,
        "spec_counts": {
            st: sum(1 for s in active_specs if s["verification"]["status"] == st)
            for st in ("verified", "stale", "failing", "unverified")
        },
        "wp_counts": {
            st: sum(1 for w in active_wps if w["verification"]["status"] == st)
            for st in ("verified", "stale", "failing", "unverified")
        },
        "evaluation_counts": {
            "total": len(eval_list),
            "pass_or_winner": sum(
                1 for e in eval_list if e["verdict"] in {"pass", "selected_winner"}
            ),
            "concerns_or_fail": sum(
                1 for e in eval_list if e["verdict"] in {"concerns", "fail"}
            ),
        },
    }


def build_evaluation_views(repo_root: Path) -> dict[str, Any]:
    """Validate evaluations and write `_aiHumanInteract/plan/evaluations/index.json` if present."""
    repo_root = repo_root.resolve()
    evals = load_evaluations(repo_root)
    payload = {
        "schema_version": EVAL_SCHEMA,
        "node_count": len(evals),
        "source_of_truth": ["_aiHumanInteract/plan/evaluations/EVAL-*.md"],
        "nodes": [evals[k].as_payload() for k in sorted(evals)],
    }
    if evals:
        eval_dir = repo_root / "_aiHumanInteract" / "plan" / "evaluations"
        eval_dir.mkdir(parents=True, exist_ok=True)
        (eval_dir / "index.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return payload

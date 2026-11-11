#!/usr/bin/env python3
"""Validate a visible, layered repository-local plan graph."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


PLAN_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PLAN_ROOT.parents[1]
LEVELS = ("long-term", "mid-term", "short-term", "work-package")
PREFIXES = {
    "long-term": "LT",
    "mid-term": "MT",
    "short-term": "ST",
    "work-package": "WP",
}
STATUSES = {"proposed", "ready", "in_progress", "blocked", "done", "superseded"}
REQUIRED_FIELDS = {
    "id",
    "title",
    "level",
    "status",
    "updated",
    "parent",
    "depends_on",
    "enables",
    "objective",
    "deliverables",
    "acceptance",
    "links",
    "evidence",
}
OPTIONAL_REFERENCE_FIELDS = {"validates", "supersedes", "conflicts_with"}
OPTIONAL_FACET_FIELDS = {
    "context",
    "qualities",
    "tradeoffs",
    "perspectives",
    "source_requirement",
    "approach",
    "alternative_of",
}
REFERENCE_FIELDS = ("depends_on", "enables", "validates", "supersedes", "conflicts_with")
CONTEXT_FIELDS = {
    "problem",
    "invariants",
    "constraints",
    "non_goals",
    "success_signals",
}
RESOLVED_STATUSES = {"done", "superseded"}
WORK_PACKAGE_BODY_SECTIONS = (
    "Objective",
    "Planned work",
    "Decisions",
    "Completion",
    "Evidence",
)
ID_PATTERN = re.compile(r"^(LT|MT|ST|WP)-\d{3}$")


class PlanGraphError(ValueError):
    """Raised when source nodes do not form a valid plan graph."""


@dataclass(frozen=True)
class PlanNode:
    """One normalized source plan."""

    node_id: str
    title: str
    level: str
    status: str
    updated: str
    parent: str | None
    depends_on: tuple[str, ...]
    enables: tuple[str, ...]
    validates: tuple[str, ...]
    supersedes: tuple[str, ...]
    conflicts_with: tuple[str, ...]
    objective: str
    deliverables: tuple[str, ...]
    acceptance: tuple[str, ...]
    links: Mapping[str, tuple[str, ...]]
    evidence: tuple[str, ...]
    context: Mapping[str, str | tuple[str, ...]] | None
    qualities: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    perspectives: tuple[str, ...]
    source_requirement: str | None
    approach: str | None
    alternative_of: str | None
    source: str
    body: str

    def references(self, field: str) -> tuple[str, ...]:
        return getattr(self, field)

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.node_id,
            "title": self.title,
            "level": self.level,
            "status": self.status,
            "updated": self.updated,
            "parent": self.parent,
            "depends_on": list(self.depends_on),
            "enables": list(self.enables),
            "validates": list(self.validates),
            "supersedes": list(self.supersedes),
            "conflicts_with": list(self.conflicts_with),
            "objective": self.objective,
            "deliverables": list(self.deliverables),
            "acceptance": list(self.acceptance),
            "links": {key: list(value) for key, value in self.links.items()},
            "evidence": list(self.evidence),
            "source": self.source,
        }
        if self.context:
            payload["context"] = {
                key: list(value) if isinstance(value, tuple) else value
                for key, value in self.context.items()
            }
        for field in ("qualities", "tradeoffs", "perspectives"):
            value = getattr(self, field)
            if value:
                payload[field] = list(value)
        for field in ("source_requirement", "approach", "alternative_of"):
            value = getattr(self, field)
            if value:
                payload[field] = value
        return payload


def _parse_front_matter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise PlanGraphError("missing opening front-matter delimiter")
    try:
        end = next(
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        )
    except StopIteration as exc:
        raise PlanGraphError("missing closing front-matter delimiter") from exc

    metadata: dict[str, Any] = {}
    for line_number, line in enumerate(lines[1:end], start=2):
        if not line.strip():
            continue
        if ":" not in line:
            raise PlanGraphError(
                f"line {line_number}: expected 'key: JSON-value'"
            )
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not key or key in metadata:
            raise PlanGraphError(f"line {line_number}: empty or duplicate key")
        try:
            metadata[key] = json.loads(raw_value.strip())
        except json.JSONDecodeError as exc:
            raise PlanGraphError(
                f"line {line_number}: metadata values must use JSON syntax"
            ) from exc
    return metadata, "\n".join(lines[end + 1 :]).strip()


def _string_list(
    metadata: Mapping[str, Any],
    field: str,
    errors: list[str],
    node_label: str,
    *,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    value = metadata.get(field)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        errors.append(f"{node_label}: {field} must be an array of non-empty strings")
        return ()
    normalized = tuple(item.strip() for item in value)
    if not allow_empty and not normalized:
        errors.append(f"{node_label}: {field} must not be empty")
    if len(set(normalized)) != len(normalized):
        errors.append(f"{node_label}: {field} contains duplicates")
    return normalized


def _optional_string_list(
    metadata: Mapping[str, Any],
    field: str,
    errors: list[str],
    node_label: str,
) -> tuple[str, ...]:
    if field not in metadata:
        return ()
    return _string_list(metadata, field, errors, node_label)


def _normalize_context(
    metadata: Mapping[str, Any],
    errors: list[str],
    node_label: str,
) -> dict[str, str | tuple[str, ...]] | None:
    if "context" not in metadata:
        return None
    value = metadata["context"]
    if not isinstance(value, dict):
        errors.append(f"{node_label}: context must be an object")
        return None
    unknown = value.keys() - CONTEXT_FIELDS
    if not value:
        errors.append(f"{node_label}: context must contain at least one useful field")
    if unknown:
        errors.append(f"{node_label}: context has unknown fields {sorted(unknown)}")
    normalized: dict[str, str | tuple[str, ...]] = {}
    if "problem" in value:
        problem = value["problem"]
        if not isinstance(problem, str) or not problem.strip():
            errors.append(f"{node_label}: context.problem must be a non-empty string")
        else:
            normalized["problem"] = problem.strip()
    for field in ("invariants", "constraints", "non_goals", "success_signals"):
        if field not in value:
            continue
        nested = {field: value.get(field)}
        normalized[field] = _string_list(
            nested,
            field,
            errors,
            f"{node_label}.context",
            allow_empty=False,
        )
    return normalized


def _normalize_links(
    metadata: Mapping[str, Any],
    errors: list[str],
    node_label: str,
) -> dict[str, tuple[str, ...]]:
    value = metadata.get("links")
    if not isinstance(value, dict) or not value:
        errors.append(f"{node_label}: links must be a non-empty object")
        return {}
    links: dict[str, tuple[str, ...]] = {}
    for category, paths in value.items():
        if not isinstance(category, str) or not category.strip():
            errors.append(f"{node_label}: link category must be a non-empty string")
            continue
        if not isinstance(paths, list) or not paths or not all(
            isinstance(path, str) and path.strip() for path in paths
        ):
            errors.append(
                f"{node_label}: links.{category} must be a non-empty array of strings"
            )
            continue
        normalized = tuple(path.strip() for path in paths)
        if len(set(normalized)) != len(normalized):
            errors.append(f"{node_label}: links.{category} contains duplicates")
        links[category.strip()] = normalized
    return links


def _valid_repository_reference(value: str) -> bool:
    if value.startswith("external:"):
        return bool(value.removeprefix("external:").strip())
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def _reference_exists(value: str, repo_root: Path) -> bool:
    return value.startswith("external:") or (repo_root / value).exists()


def parse_node(
    path: Path,
    plan_root: Path,
    repo_root: Path,
) -> tuple[PlanNode | None, list[str]]:
    """Parse and locally validate one source node."""

    errors: list[str] = []
    label = path.relative_to(repo_root).as_posix()
    try:
        metadata, body = _parse_front_matter(path)
    except (OSError, PlanGraphError) as exc:
        return None, [f"{label}: {exc}"]

    missing = REQUIRED_FIELDS - metadata.keys()
    unknown = (
        metadata.keys()
        - REQUIRED_FIELDS
        - OPTIONAL_REFERENCE_FIELDS
        - OPTIONAL_FACET_FIELDS
    )
    if missing:
        errors.append(f"{label}: missing fields {sorted(missing)}")
    if unknown:
        errors.append(f"{label}: unknown fields {sorted(unknown)}")

    node_id = metadata.get("id")
    title = metadata.get("title")
    level = metadata.get("level")
    status = metadata.get("status")
    updated = metadata.get("updated")
    objective = metadata.get("objective")
    parent = metadata.get("parent")
    for field, value in (
        ("id", node_id),
        ("title", title),
        ("level", level),
        ("status", status),
        ("updated", updated),
        ("objective", objective),
    ):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label}: {field} must be a non-empty string")

    safe_id = node_id.strip() if isinstance(node_id, str) else path.stem
    safe_level = level.strip() if isinstance(level, str) else ""
    safe_status = status.strip() if isinstance(status, str) else ""
    safe_updated = updated.strip() if isinstance(updated, str) else ""
    if not ID_PATTERN.fullmatch(safe_id):
        errors.append(f"{label}: invalid plan ID {safe_id!r}")
    if safe_level not in LEVELS:
        errors.append(f"{safe_id}: invalid level {safe_level!r}")
    elif not safe_id.startswith(PREFIXES[safe_level] + "-"):
        errors.append(f"{safe_id}: ID prefix does not match level {safe_level}")
    if path.stem != safe_id:
        errors.append(f"{safe_id}: filename must be {safe_id}.md")
    if safe_status not in STATUSES:
        errors.append(f"{safe_id}: invalid status {safe_status!r}")
    try:
        if date.fromisoformat(safe_updated).isoformat() != safe_updated:
            raise ValueError
    except ValueError:
        errors.append(f"{safe_id}: updated must use a valid YYYY-MM-DD date")
    if parent is not None and (not isinstance(parent, str) or not parent.strip()):
        errors.append(f"{safe_id}: parent must be null or a non-empty plan ID")

    refs = {
        field: _string_list(metadata, field, errors, safe_id)
        if field in metadata
        else ()
        for field in REFERENCE_FIELDS
    }
    deliverables = _string_list(
        metadata, "deliverables", errors, safe_id, allow_empty=False
    )
    acceptance = _string_list(
        metadata, "acceptance", errors, safe_id, allow_empty=False
    )
    evidence = _string_list(metadata, "evidence", errors, safe_id)
    links = _normalize_links(metadata, errors, safe_id)
    context = _normalize_context(metadata, errors, safe_id)
    qualities = _optional_string_list(metadata, "qualities", errors, safe_id)
    tradeoffs = _optional_string_list(metadata, "tradeoffs", errors, safe_id)
    perspectives = _optional_string_list(metadata, "perspectives", errors, safe_id)

    source_requirement = metadata.get("source_requirement")
    approach = metadata.get("approach")
    alternative_of = metadata.get("alternative_of")
    for field, value in (
        ("source_requirement", source_requirement),
        ("approach", approach),
        ("alternative_of", alternative_of),
    ):
        if value is not None and (not isinstance(value, str) or not value.strip()):
            errors.append(f"{safe_id}: {field} must be a non-empty string when set")
    normalized_requirement = (
        source_requirement.strip() if isinstance(source_requirement, str) else None
    )
    normalized_approach = approach.strip() if isinstance(approach, str) else None
    normalized_alternative = alternative_of.strip() if isinstance(alternative_of, str) else None

    expected_source = path.relative_to(repo_root).as_posix()
    plan_links = links.get("plan", ())
    if expected_source not in plan_links:
        errors.append(f"{safe_id}: links.plan must include {expected_source}")
    if not any(paths for category, paths in links.items() if category != "plan"):
        errors.append(f"{safe_id}: at least one non-plan link is required")
    for category, paths in links.items():
        for linked in paths:
            if not _valid_repository_reference(linked):
                errors.append(
                    f"{safe_id}: invalid repository-relative link "
                    f"links.{category}={linked!r}"
                )
    for item in evidence:
        if not _valid_repository_reference(item):
            errors.append(f"{safe_id}: invalid evidence reference {item!r}")

    flattened_links = {linked for paths in links.values() for linked in paths}
    for item in evidence:
        if item not in flattened_links:
            errors.append(f"{safe_id}: evidence is not recorded in links: {item!r}")
    if normalized_requirement:
        if not _valid_repository_reference(normalized_requirement):
            errors.append(
                f"{safe_id}: invalid source_requirement {normalized_requirement!r}"
            )
        elif not _reference_exists(normalized_requirement, repo_root):
            errors.append(
                f"{safe_id}: source_requirement does not exist: "
                f"{normalized_requirement!r}"
            )
        if normalized_requirement not in flattened_links:
            errors.append(
                f"{safe_id}: source_requirement must also be recorded in links"
            )
    if normalized_alternative:
        if not ID_PATTERN.fullmatch(normalized_alternative):
            errors.append(f"{safe_id}: invalid alternative_of ID {normalized_alternative!r}")
        if not normalized_requirement:
            errors.append(f"{safe_id}: alternative requires source_requirement")
        if not normalized_approach:
            errors.append(f"{safe_id}: alternative requires approach")

    if safe_level == "work-package":
        for section in WORK_PACKAGE_BODY_SECTIONS:
            if not re.search(rf"^## {re.escape(section)}\s*$", body, re.MULTILINE):
                errors.append(
                    f"{safe_id}: work-package body is missing '## {section}'"
                )

    if errors:
        return None, errors
    node = PlanNode(
        node_id=safe_id,
        title=title.strip(),
        level=safe_level,
        status=safe_status,
        updated=safe_updated,
        parent=parent.strip() if isinstance(parent, str) else None,
        depends_on=refs["depends_on"],
        enables=refs["enables"],
        validates=refs["validates"],
        supersedes=refs["supersedes"],
        conflicts_with=refs["conflicts_with"],
        objective=objective.strip(),
        deliverables=deliverables,
        acceptance=acceptance,
        links=links,
        evidence=evidence,
        context=context,
        qualities=qualities,
        tradeoffs=tradeoffs,
        perspectives=perspectives,
        source_requirement=normalized_requirement,
        approach=normalized_approach,
        alternative_of=normalized_alternative,
        source=expected_source,
        body=body,
    )
    return node, []


def _find_cycle(adjacency: Mapping[str, Iterable[str]]) -> list[str] | None:
    visited: set[str] = set()
    active: set[str] = set()
    stack: list[str] = []

    def visit(node_id: str) -> list[str] | None:
        if node_id in active:
            start = stack.index(node_id)
            return stack[start:] + [node_id]
        if node_id in visited:
            return None
        visited.add(node_id)
        active.add(node_id)
        stack.append(node_id)
        for target in adjacency.get(node_id, ()):
            cycle = visit(target)
            if cycle:
                return cycle
        stack.pop()
        active.remove(node_id)
        return None

    for node_id in adjacency:
        cycle = visit(node_id)
        if cycle:
            return cycle
    return None


def validate_relationships(
    nodes: Mapping[str, PlanNode],
    repo_root: Path,
) -> list[str]:
    """Validate relationships, lifecycle propagation, and completion evidence."""

    errors: list[str] = []
    children: dict[str, list[str]] = defaultdict(list)
    parent_graph: dict[str, list[str]] = defaultdict(list)
    dependency_graph: dict[str, list[str]] = defaultdict(list)
    alternative_graph: dict[str, list[str]] = defaultdict(list)
    supersession_graph: dict[str, list[str]] = defaultdict(list)

    hard_dependency_pairs = {
        (dependency, node.node_id)
        for node in nodes.values()
        for dependency in node.depends_on
    }

    for node in nodes.values():
        if node.level == "long-term":
            if node.parent is not None:
                errors.append(f"{node.node_id}: long-term node must have parent null")
        elif node.parent is None:
            if node.status != "superseded":
                errors.append(f"{node.node_id}: active non-long-term node needs a parent")
        elif node.parent not in nodes:
            errors.append(f"{node.node_id}: dangling parent {node.parent}")
        else:
            expected = LEVELS[LEVELS.index(node.level) - 1]
            actual = nodes[node.parent].level
            if actual != expected:
                errors.append(
                    f"{node.node_id}: parent {node.parent} must be {expected}, not {actual}"
                )
            children[node.parent].append(node.node_id)
            parent_graph[node.parent].append(node.node_id)

        for field in REFERENCE_FIELDS:
            for target in node.references(field):
                if target == node.node_id:
                    errors.append(f"{node.node_id}: self-reference in {field}")
                elif target not in nodes:
                    errors.append(
                        f"{node.node_id}: dangling {field} reference {target}"
                    )
                if field == "depends_on":
                    dependency_graph[node.node_id].append(target)

        for target in node.enables:
            if (node.node_id, target) in hard_dependency_pairs:
                errors.append(
                    f"{node.node_id}: enables duplicates the hard dependency "
                    f"declared by {target}"
                )

        if node.alternative_of:
            alternative_graph[node.node_id].append(node.alternative_of)
            if node.alternative_of == node.node_id:
                errors.append(f"{node.node_id}: alternative_of cannot reference itself")
            elif node.alternative_of not in nodes:
                errors.append(
                    f"{node.node_id}: dangling alternative_of reference {node.alternative_of}"
                )
            elif nodes[node.alternative_of].parent != node.parent:
                errors.append(
                    f"{node.node_id}: alternative and canonical plan must share a parent"
                )
            else:
                canonical = nodes[node.alternative_of]
                if node.level != "work-package" or canonical.level != "work-package":
                    errors.append(
                        f"{node.node_id}: alternatives must be work packages"
                    )
                if canonical.source_requirement != node.source_requirement:
                    errors.append(
                        f"{node.node_id}: alternative and canonical plan must share "
                        "source_requirement"
                    )
                if not canonical.approach or canonical.approach == node.approach:
                    errors.append(
                        f"{node.node_id}: alternatives require distinct non-empty approaches"
                    )
                if canonical.objective != node.objective:
                    errors.append(f"{node.node_id}: alternatives must share objective")
                canonical_invariants = set((canonical.context or {}).get("invariants", ()))
                alternative_invariants = set((node.context or {}).get("invariants", ()))
                if canonical_invariants != alternative_invariants:
                    errors.append(f"{node.node_id}: alternatives must share invariants")

        for target in node.supersedes:
            supersession_graph[node.node_id].append(target)
            if target in nodes and nodes[target].status != "superseded":
                errors.append(
                    f"{node.node_id}: supersedes target {target} must have status "
                    "superseded"
                )

    for node in nodes.values():
        if node.status == "superseded":
            continue
        if node.level == "work-package" and children[node.node_id]:
            errors.append(f"{node.node_id}: work packages must be terminal")
        if node.level != "work-package" and not children[node.node_id]:
            errors.append(
                f"{node.node_id}: active non-work-package node must decompose further"
            )

    for name, graph in (
        ("decomposition", parent_graph),
        ("dependency", dependency_graph),
        ("alternative", alternative_graph),
        ("supersession", supersession_graph),
    ):
        cycle = _find_cycle(graph)
        if cycle:
            errors.append(f"{name} graph contains a cycle: {' -> '.join(cycle)}")

    def descendant_work_packages(node_id: str) -> list[PlanNode]:
        descendants: list[PlanNode] = []
        for child_id in children.get(node_id, ()):
            child = nodes[child_id]
            if child.level == "work-package":
                descendants.append(child)
            else:
                descendants.extend(descendant_work_packages(child_id))
        return descendants

    for node in nodes.values():
        if node.status in {"in_progress", "done"}:
            unfinished = [
                target
                for target in node.depends_on
                if target in nodes and nodes[target].status != "done"
            ]
            if unfinished:
                errors.append(
                    f"{node.node_id}: {node.status} plan has unfinished "
                    f"dependencies {unfinished}"
                )

        if node.status != "done":
            continue
        if node.level != "work-package":
            unfinished_descendants = [
                item.node_id
                for item in descendant_work_packages(node.node_id)
                if item.status not in RESOLVED_STATUSES
            ]
            if unfinished_descendants:
                errors.append(
                    f"{node.node_id}: done plan has unresolved descendant work "
                    f"packages {unfinished_descendants}"
                )

        if not node.evidence:
            errors.append(f"{node.node_id}: done plan requires evidence")

        flattened_links = {
            linked for paths in node.links.values() for linked in paths
        }
        for category, paths in node.links.items():
            for linked in paths:
                if not _reference_exists(linked, repo_root):
                    errors.append(
                        f"{node.node_id}: done link does not exist "
                        f"links.{category}={linked!r}"
                    )
        for evidence in node.evidence:
            if evidence not in flattened_links:
                errors.append(
                    f"{node.node_id}: evidence is not recorded in links: {evidence!r}"
                )
            if not _reference_exists(evidence, repo_root):
                errors.append(
                    f"{node.node_id}: evidence reference does not exist: {evidence!r}"
                )

    for node in nodes.values():
        if node.status != "superseded":
            continue
        successors = [
            candidate.node_id
            for candidate in nodes.values()
            if node.node_id in candidate.supersedes
        ]
        if not successors:
            errors.append(
                f"{node.node_id}: superseded plan must be referenced by a successor"
            )
        if not node.evidence:
            errors.append(f"{node.node_id}: superseded plan requires evidence")
        flattened_links = {
            linked for paths in node.links.values() for linked in paths
        }
        for category, paths in node.links.items():
            for linked in paths:
                if not _reference_exists(linked, repo_root):
                    errors.append(
                        f"{node.node_id}: superseded link does not exist "
                        f"links.{category}={linked!r}"
                    )
        for evidence in node.evidence:
            if evidence not in flattened_links:
                errors.append(
                    f"{node.node_id}: evidence is not recorded in links: {evidence!r}"
                )
            if not _reference_exists(evidence, repo_root):
                errors.append(
                    f"{node.node_id}: evidence reference does not exist: {evidence!r}"
                )
    return errors


def load_and_validate(
    plan_root: Path = PLAN_ROOT,
    repo_root: Path | None = None,
) -> tuple[dict[str, PlanNode], list[str]]:
    """Load all source nodes and return normalized nodes plus aggregated errors."""

    plan_root = plan_root.resolve()
    repo_root = (repo_root or plan_root.parents[1]).resolve()
    nodes: dict[str, PlanNode] = {}
    errors: list[str] = []
    counts: Counter[str] = Counter()
    legacy_meta = plan_root / "meta"
    if legacy_meta.is_dir() and any(legacy_meta.glob("*.md")):
        errors.append(
            f"{legacy_meta}: v1 meta nodes are unsupported; migrate them to "
            "work-package/WP-### before validating with v4"
        )
    for level in LEVELS:
        level_dir = plan_root / level
        for path in sorted(level_dir.glob("*.md")):
            node, node_errors = parse_node(path, plan_root, repo_root)
            errors.extend(node_errors)
            if node is None:
                continue
            if node.node_id in nodes:
                errors.append(
                    f"duplicate ID {node.node_id}: {node.source} and "
                    f"{nodes[node.node_id].source}"
                )
                continue
            nodes[node.node_id] = node
            counts[level] += 1

    if not nodes:
        errors.append(f"{plan_root}: no plan nodes found")
    errors.extend(validate_relationships(nodes, repo_root))
    return nodes, errors


def require_valid_graph(
    plan_root: Path = PLAN_ROOT,
    repo_root: Path | None = None,
) -> dict[str, PlanNode]:
    nodes, errors = load_and_validate(plan_root, repo_root)
    if errors:
        raise PlanGraphError("\n".join(errors))
    return nodes


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PLAN_ROOT)
    args = parser.parse_args(argv)
    nodes, errors = load_and_validate(args.root)
    if errors:
        print("Plan validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    counts = Counter(node.level for node in nodes.values())
    summary = ", ".join(f"{level}={counts[level]}" for level in LEVELS)
    print(f"Plan validation passed: {len(nodes)} nodes ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

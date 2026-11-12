"""Contract tests for a linked plan graph and its projections."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path


PLAN_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PLAN_ROOT.parents[1]
sys.path.insert(0, str(PLAN_ROOT))

import build_graph  # noqa: E402
import validate  # noqa: E402


class SourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.nodes = validate.require_valid_graph(PLAN_ROOT, REPO_ROOT)

    def test_only_work_packages_are_leaves(self) -> None:
        parents = {node.parent for node in self.nodes.values() if node.parent}
        for node in self.nodes.values():
            if node.status != "superseded":
                self.assertEqual(
                    node.level == "work-package", node.node_id not in parents
                )

    def test_every_node_links_its_source(self) -> None:
        for node in self.nodes.values():
            self.assertIn(node.source, node.links["plan"])


class ProjectionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.nodes = validate.require_valid_graph(PLAN_ROOT, REPO_ROOT)
        cls.payload = build_graph.graph_payload(PLAN_ROOT, cls.nodes)

    def test_json_is_versioned_and_complete(self) -> None:
        self.assertEqual(
            self.payload["schema_version"], build_graph.SCHEMA_VERSION
        )
        self.assertEqual(
            {node["id"] for node in self.payload["nodes"]}, set(self.nodes)
        )

    def test_source_of_truth_resolves(self) -> None:
        """Discovery globs must name existing files under the same root as node sources."""
        patterns = self.payload["source_of_truth"]
        self.assertTrue(patterns)
        sources = {node.source for node in self.nodes.values()}
        for pattern in patterns:
            self.assertNotIn("\\", pattern)
            matches = sorted(REPO_ROOT.glob(pattern))
            self.assertTrue(matches, f"{pattern} matches no file")
            for match in matches:
                self.assertIn(match.relative_to(REPO_ROOT).as_posix(), sources)
        prefix = patterns[0].rsplit("/", 2)[0]
        for source in sources:
            self.assertTrue(source.startswith(prefix + "/"), source)

    def test_canvas_is_valid_json(self) -> None:
        canvas = json.loads(build_graph.graph_canvas(self.nodes))
        self.assertEqual(
            sum(item["id"].startswith("plan-") for item in canvas["nodes"]),
            len(self.nodes),
        )

    def test_generated_views_are_current(self) -> None:
        for path, expected in build_graph.render_outputs(
            PLAN_ROOT, self.nodes
        ).items():
            self.assertTrue(path.exists(), path)
            self.assertEqual(path.read_text(encoding="utf-8"), expected)


class OptionalDetailsTests(unittest.TestCase):
    """Exercise independent fields and comparison semantics in an isolated graph."""

    def setUp(self) -> None:
        self.workspace = tempfile.TemporaryDirectory(prefix="plan-graph-contract-")
        self.addCleanup(self.workspace.cleanup)
        self.repo = Path(self.workspace.name)
        self.root = self.repo / "_aiHumanInteract/plan"
        self.requirement = "_aiHumanInteract/plan/requirements/REQ-001.md"
        requirement = self.repo / self.requirement
        requirement.parent.mkdir(parents=True)
        requirement.write_text("Explain each routing decision.\n", encoding="utf-8")
        self.metadata = {}
        for node_id, level, parent in (
            ("LT-001", "long-term", None),
            ("MT-001", "mid-term", "LT-001"),
            ("ST-001", "short-term", "MT-001"),
            ("WP-001", "work-package", "ST-001"),
        ):
            metadata = {
                "id": node_id, "title": "Trace routing", "level": level,
                "parent": parent, "status": "ready", "updated": "2026-09-15",
                "depends_on": [], "enables": [],
                "objective": "Make routing reproducible.",
                "deliverables": ["A routing trace"],
                "acceptance": ["Replay produces the recorded route"],
                "links": {
                    "plan": [f"_aiHumanInteract/plan/{level}/{node_id}.md"],
                    "docs": [self.requirement],
                },
                "evidence": [],
            }
            self.write_node(metadata)
            self.metadata[node_id] = metadata

    def write_node(self, metadata: dict) -> Path:
        path = self.root / metadata["level"] / (metadata["id"] + ".md")
        path.parent.mkdir(parents=True, exist_ok=True)
        front = "\n".join(f"{key}: {json.dumps(value)}" for key, value in metadata.items())
        body = "\n\n".join(f"## {section}\n\nRecorded here." for section in validate.WORK_PACKAGE_BODY_SECTIONS)
        path.write_text(f"---\n{front}\n---\n\n{body}\n", encoding="utf-8")
        return path

    def test_optional_fields_are_independent_and_visible(self) -> None:
        options = {
            "context": {"constraints": ["No extra model call"]},
            "qualities": ["Readable under pressure"],
            "tradeoffs": ["Speed versus explanation detail"],
            "perspectives": ["Runtime latency"],
            "approach": "Append-only trace",
            "source_requirement": self.requirement,
        }
        for field, value in options.items():
            with self.subTest(field=field):
                self.write_node({**self.metadata["WP-001"], field: value})
                nodes = validate.require_valid_graph(self.root, self.repo)
                payload = nodes["WP-001"].as_payload()
                self.assertEqual(payload[field], value)
                for absent in options.keys() - {field}:
                    self.assertNotIn(absent, payload)
                if field != "source_requirement":
                    review = build_graph.review_markdown(self.root, nodes)
                    self.assertIn("WP-001", review)
                    detail = (
                        value["constraints"][0] if isinstance(value, dict)
                        else value[0] if isinstance(value, list) else value
                    )
                    self.assertIn(detail, review)

    def test_unknown_context_fields_are_rejected(self) -> None:
        self.write_node({**self.metadata["WP-001"], "context": {"outcome": "Conflicting outcome"}})
        _, errors = validate.load_and_validate(self.root, self.repo)
        self.assertTrue(any("context has unknown fields" in error for error in errors))

    def test_old_source_fields_are_rejected(self) -> None:
        for old, value in (
            ("mounts", {"plan": ["_aiHumanInteract/plan/work-package/WP-001.md"]}),
            ("essence", {"problem": "Old field"}),
            ("tensions", ["Old field"]),
            ("technique", "Old field"),
            ("variant_of", "WP-002"),
        ):
            with self.subTest(field=old):
                self.write_node({**self.metadata["WP-001"], old: value})
                _, errors = validate.load_and_validate(self.root, self.repo)
                self.assertTrue(any("unknown fields" in error and old in error for error in errors))

    def test_evidence_requires_a_link_before_completion(self) -> None:
        self.write_node({**self.metadata["WP-001"], "evidence": ["missing-record.md"]})
        _, errors = validate.load_and_validate(self.root, self.repo)
        self.assertTrue(any("evidence is not recorded in links" in error for error in errors))

    def test_alternatives_share_outcome_and_invariants(self) -> None:
        self.write_node({
            **self.metadata["WP-001"],
            "source_requirement": self.requirement,
            "approach": "Append-only trace",
            "context": {"invariants": ["Preserve behavior", "No extra model calls"]},
        })
        nodes = validate.require_valid_graph(self.root, self.repo)
        baseline = nodes["WP-001"]
        alternative = replace(
            baseline, node_id="WP-002", alternative_of="WP-001",
            approach="Structured event record",
            context={"invariants": ("No extra model calls", "Preserve behavior")},
            source="_aiHumanInteract/plan/work-package/WP-002.md",
            links={"plan": ("_aiHumanInteract/plan/work-package/WP-002.md",), "docs": (self.requirement,)},
        )
        compared = {**nodes, "WP-002": alternative}
        self.assertEqual(validate.validate_relationships(compared, self.repo), [])
        self.assertIn(
            ("WP-002", "WP-001", "alternative_of"),
            {(edge["from"], edge["to"], edge["relationship"]) for edge in build_graph.graph_edges(compared)},
        )
        self.assertIn("Structured event record", build_graph.review_markdown(self.root, compared))
        cases = (
            ({"objective": "Automate recovery."}, "share objective"),
            ({"context": {"invariants": ("Change behavior",)}}, "share invariants"),
            ({"approach": baseline.approach}, "distinct non-empty approaches"),
            ({"source_requirement": "external:another-record"}, "share source_requirement"),
        )
        for changes, message in cases:
            with self.subTest(changes=changes):
                changed = {**nodes, "WP-002": replace(alternative, **changes)}
                errors = validate.validate_relationships(changed, self.repo)
                self.assertTrue(any(message in error for error in errors), errors)

    def test_external_reference_is_syntax_only(self) -> None:
        self.assertTrue(validate._valid_repository_reference("external:archive-record-42"))
        self.assertFalse(validate._valid_repository_reference("external: "))
        # No archive access is implied by the local existence exemption.
        self.assertTrue(validate._reference_exists("external:unverified-record", self.repo))
        self.assertFalse(validate._reference_exists("missing-local-record", self.repo))

    def test_v1_nodes_are_not_silently_ignored(self) -> None:
        legacy = self.root / "meta"
        legacy.mkdir()
        (legacy / "MP-001.md").write_text("Legacy source", encoding="utf-8")
        _, errors = validate.load_and_validate(self.root, self.repo)
        self.assertTrue(any("v1 meta nodes are unsupported" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

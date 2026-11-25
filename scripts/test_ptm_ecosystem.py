#!/usr/bin/env python3
"""End-to-end regression suite for PtM's Four-Graph, Hebbian, Triage & Studio ecosystem."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from ptm_core import (  # noqa: E402
    PtmGraphError,
    compute_kd_rejection_impact,
    compute_spec_impact,
    load_all_federated_graphs,
    load_intent_graph,
    load_spec_graph,
    resolve_knowledge_debt,
    scan_scripts_graph,
)
from ptm_hebbian import HebbianAssociativeEngine  # noqa: E402
from ptm_portrait import (  # noqa: E402
    PORTRAIT_END,
    PORTRAIT_START,
    build_portrait_digest,
    render_portrait_block,
    update_agents_portrait,
)
from seed_four_graph_example import seed_example  # noqa: E402


class PtmFourGraphEcosystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="ptm-eco-")
        self.repo = Path(self._tmp.name) / "workbench"
        seed_example(self.repo)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_intent_graph_preserves_utterances_concepts_and_variants(self) -> None:
        intents, edges = load_intent_graph(self.repo)
        self.assertEqual(
            set(intents),
            {"INT-001", "INT-002", "INT-003", "INT-004", "INT-005"},
        )
        root = intents["INT-001"]
        self.assertIn("拨动旋钮", root.raw_utterance)
        faster = next(c for c in root.concepts if c["name"] == "更快")
        self.assertEqual(faster["selected_variant"], "IV-3")
        self.assertEqual(len(faster["interpretive_variants"]), 4)
        rel_types = {e["relationship"] for e in edges}
        for expected_rel in (
            "decomposes_intent",
            "prerequisite_for",
            "enables",
            "validates",
            "supersedes",
            "conflicts_with",
            "alternative_of",
        ):
            self.assertIn(expected_rel, rel_types)

    def test_scripts_graph_ast_imports_calls_hubs_and_missing_targets(self) -> None:
        scripts = scan_scripts_graph(self.repo)
        by_path = {n["path"]: n for n in scripts["nodes"]}
        self.assertIn("src/workbench_api.py", by_path)
        self.assertIn("src/spectral_store.py", by_path)
        self.assertIn("src/event_replay_audit.py", by_path)
        self.assertEqual(by_path["src/event_replay_audit.py"]["status"], "planned_missing")
        self.assertTrue(by_path["src/workbench_api.py"]["is_entrypoint"])

        edge_pairs = {(e["from_path"], e["to_path"], e["relationship"]) for e in scripts["edges"]}
        self.assertIn(("src/workbench_api.py", "src/spectral_store.py", "imports"), edge_pairs)
        self.assertIn(("src/workbench_api.py", "src/triage_gate.py", "invokes"), edge_pairs)

    def test_three_way_triage_and_kd_rejection_reorganizes_graphs(self) -> None:
        # 1. Triage `not_understood_prototype` creates KD-004 bookmark
        res = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts" / "ptm.py"),
                "triage",
                str(self.repo),
                "--term",
                "WebGL Shader Peak Renderer",
                "--choice",
                "not_understood_prototype",
                "--intents",
                "INT-001",
                "--plans",
                "WP-001",
                "--revisit-when",
                "帧率低于 60fps 或移动端兼容测试时",
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        out = json.loads(res.stdout)
        self.assertEqual(out["created_bookmark"], "KD-004")

        # 2. Check rejection blast radius on KD-001 -> WP-002 (and INT-002)
        impact_before = compute_kd_rejection_impact(self.repo, "KD-001")
        self.assertIn("INT-002", impact_before["reopen_intents"])
        self.assertIn("WP-002", impact_before["supersede_plans"])

        # 3. Reject WP-004-linked bookmark or KD-001 and verify INT-002 transitions to `reopened`
        resolved = resolve_knowledge_debt(
            self.repo,
            "KD-001",
            verdict="rejected",
            note="扩散召回了无关历史笔记",
            counterproposal="仅保留显式结构边与 Top-3 高置信同义检索",
        )
        self.assertEqual(resolved["verdict"], "rejected")
        intents_after, _ = load_intent_graph(self.repo)
        self.assertEqual(intents_after["INT-002"].status, "reopened")

    def test_hebbian_coactivation_and_dual_path_flip(self) -> None:
        federated = load_all_federated_graphs(self.repo)
        engine = HebbianAssociativeEngine(self.repo, backend="hash")
        engine.sync_federated(federated)

        # Reinforce a cross-graph cluster repeatedly ("fire together, wire together")
        for _ in range(5):
            engine.reinforce_cluster(
                ["INT-001", "SCR:src/spectral_store.py", "KD-002"],
                reason="session_coedit",
            )
        w = engine.synapses["INT-001"]["KD-002"]["weight"]
        self.assertGreater(w, 0.25)

        q_res = engine.query("科学光谱旋钮直接操作", top_k=2, max_flipped=3)
        self.assertGreaterEqual(len(q_res["results"]), 2)
        paths = {r["path"] for r in q_res["results"]}
        self.assertIn("base", paths)

        # Querying by exact node ID must resolve and reuse the node's own rich vector
        q_node = engine.query("WP-002", top_k=3, max_flipped=2, reinforce=False)
        self.assertEqual(q_node["resolved_anchor_node"], "WP-002")
        self.assertNotIn("WP-002", {r["id"] for r in q_node["results"]})

    def test_agent_related_lookup_by_node_draft_file_and_text(self) -> None:
        # 1. Auto-detected existing node lookup (`WP-002`)
        r1 = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts" / "ptm.py"),
                "related",
                str(self.repo),
                "WP-002",
                "--embedding-backend",
                "hash",
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        out_node = json.loads(r1.stdout)
        self.assertEqual(out_node["anchor"]["mode"], "node")
        self.assertEqual(out_node["anchor"]["id"], "WP-002")
        self.assertEqual(
            set(out_node["by_graph"]),
            {"intent", "specs", "plan", "knowledge_debt", "scripts"},
        )
        decl_ids = {item["id"] for item in out_node["declared_links"]}
        self.assertIn("WP-001", decl_ids)
        self.assertIn("WP-003", decl_ids)
        self.assertIn("INT-002", decl_ids)
        self.assertIn("SPEC-004", decl_ids)
        self.assertTrue(len(out_node["novel_discoveries"]) > 0)
        for item in out_node["novel_discoveries"]:
            self.assertEqual(item["relation_status"], "novel_discovery")
            self.assertNotIn(item["id"], decl_ids)

        # 2. Uncommitted draft file lookup (`draft_WP007.md`) before writing into plan/
        draft_path = self.repo / "draft_WP007.md"
        draft_path.write_text(
            "---\ntitle: 导出轻量 JSON 谱峰快照替代重型事件溯源\n---\n"
            "针对跨会话谱峰 PK-### 可寻址存储（spectral_store.py），提供一键 JSON 快照导出，避免 Event Sourcing 迁移负担。\n",
            encoding="utf-8",
        )
        r2 = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts" / "ptm.py"),
                "related",
                str(self.repo),
                str(draft_path),
                "--embedding-backend",
                "hash",
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        out_draft = json.loads(r2.stdout)
        self.assertEqual(out_draft["anchor"]["mode"], "draft_file")
        plan_hits = [x["id"] for x in out_draft["by_graph"]["plan"]]
        script_hits = [x["id"] for x in out_draft["by_graph"]["scripts"]]
        self.assertTrue(any(pid in plan_hits for pid in ("WP-004", "WP-005", "MT-002")))
        self.assertIn("SCR:src/spectral_store.py", script_hits)

    def test_portrait_coexists_with_adopt_protocol_block(self) -> None:
        # Build with deterministic portrait
        subprocess.run(
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts" / "ptm.py"),
                "build",
                str(self.repo),
                "--embedding-backend",
                "hash",
                "--with-portrait",
                "--portrait-mode",
                "deterministic",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        agents_txt = (self.repo / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("<!-- paths-to-modernity:protocol:start -->", agents_txt)
        self.assertIn(PORTRAIT_START, agents_txt)
        self.assertIn(PORTRAIT_END, agents_txt)

        # Re-running `adopt_project.py` must remain idempotent and NEVER report protocol corruption!
        subprocess.run(
            [sys.executable, "-B", str(SKILL_ROOT / "scripts" / "adopt_project.py"), str(self.repo)],
            check=True,
            stdout=subprocess.DEVNULL,
        )

        # Verify Studio HTML contains all 4 graphs, 7 explicit relation layers, card-mark stamps, and Hebbian synapses
        studio_html = (self.repo / "_aiHumanInteract" / "studio" / "index.html").read_text(
            encoding="utf-8"
        )
        for token in (
            "INT-001",
            "INT-004",
            "INT-005",
            "SPEC-001",
            "SPEC-002",
            "SPEC-004",
            "PeakHandle (PK-###)",
            "WaveItem",
            "LT-001",
            "WP-006",
            "KD-001",
            "src/workbench_api.py",
            "Epistemic Prototype A",
            'id="card-mark-layer"',
            "NORMATIVE CONSTITUTION LAYER",
            "Agent 显式维护关系 (Declared Relations)",
            "has_alternative",
            "superseded_by",
        ):
            self.assertIn(token, studio_html)

        # Ensure canvas structural_edges on Intent/Spec/Plan ONLY carry Parent/Children tree edges
        marker = "const DATA = "
        start = studio_html.index(marker) + len(marker)
        end = studio_html.index(";\nconst svg =", start)
        data = json.loads(studio_html[start:end].replace("<\\/", "</"))
        for edge in data["structural_edges"]:
            self.assertIn(
                edge["relationship"],
                {"decomposes_to", "decomposes_intent", "decomposes_spec", "imports", "invokes"},
            )
        wp2_rel = data["relations"]["WP-002"]
        self.assertEqual(wp2_rel["depends_on"], ["WP-001"])
        self.assertEqual(wp2_rel["validated_by"], ["WP-006"])
        self.assertEqual(wp2_rel["supersedes"], ["WP-003"])
        self.assertEqual(wp2_rel["has_alternative"], ["WP-003"])
        wp3_rel = data["relations"]["WP-003"]
        self.assertEqual(wp3_rel["superseded_by"], ["WP-002"])
        self.assertEqual(wp3_rel["alternative_of"], ["WP-002"])
        self.assertEqual(wp3_rel["conflicts_with"], ["WP-005"])
        spec3_rel = data["relations"]["SPEC-003"]
        self.assertEqual(spec3_rel["supersedes"], ["SPEC-005"])
        self.assertEqual(spec3_rel["has_alternative"], ["SPEC-005"])

    def test_spec_graph_four_pillars_interlocking_and_blast_radius(self) -> None:
        specs, edges = load_spec_graph(self.repo)
        self.assertEqual(
            set(specs),
            {"SPEC-001", "SPEC-002", "SPEC-003", "SPEC-004", "SPEC-005"},
        )
        self.assertEqual(
            {s.kind for s in specs.values()},
            {"invariant", "glossary", "standard", "contract"},
        )
        self.assertEqual(specs["SPEC-002"].canonical_term, "PeakHandle (PK-###)")
        self.assertIn("WaveItem", specs["SPEC-002"].forbidden_aliases)

        imp = compute_spec_impact(self.repo, "SPEC-002")
        self.assertEqual(imp["dependent_specs"], ["SPEC-003", "SPEC-004"])
        self.assertEqual(imp["originating_intents"], ["INT-003"])
        self.assertIn("WP-004", imp["implementing_plans"])
        self.assertIn("WP-005", imp["downstream_plans"])
        self.assertIn("src/spectral_store.py", imp["governed_scripts"])
        self.assertIn("tests/test_workbench.py", imp["verification_scripts"])

        # KD-001 rejection must surface SPEC-004 under amend_or_review_specs
        kd_imp = compute_kd_rejection_impact(self.repo, "KD-001")
        self.assertIn("SPEC-004", kd_imp["amend_or_review_specs"])

        # Searching a forbidden alias ('WaveItem') must rank SPEC-002 #1 in specs
        federated = load_all_federated_graphs(self.repo)
        engine = HebbianAssociativeEngine(self.repo, backend="hash")
        engine.sync_federated(federated, persist=False)
        rel_out = engine.related(federated, draft_text="WaveItem", per_graph=3)
        self.assertEqual(rel_out["by_graph"]["specs"][0]["id"], "SPEC-002")

    def test_intent_cycle_rejected(self) -> None:
        p1 = self.repo / "_aiHumanInteract" / "intent" / "nodes" / "INT-001.md"
        txt = p1.read_text(encoding="utf-8").replace("parent: null", 'parent: "INT-002"')
        p1.write_text(txt, encoding="utf-8")
        with self.assertRaises(PtmGraphError):
            load_intent_graph(self.repo)


if __name__ == "__main__":
    unittest.main(verbosity=2)

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
    load_all_federated_graphs,
    load_intent_graph,
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
        self.assertEqual(set(intents), {"INT-001", "INT-002", "INT-003"})
        root = intents["INT-001"]
        self.assertIn("拨动旋钮", root.raw_utterance)
        faster = next(c for c in root.concepts if c["name"] == "更快")
        self.assertEqual(faster["selected_variant"], "IV-3")
        self.assertEqual(len(faster["interpretive_variants"]), 4)
        self.assertTrue(any(e["relationship"] == "decomposes_intent" for e in edges))
        self.assertTrue(any(e["relationship"] == "branches_from" for e in edges))

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

        # Verify Studio HTML contains all 4 graphs and inline SVG prototypes
        studio_html = (self.repo / "_aiHumanInteract" / "studio" / "index.html").read_text(
            encoding="utf-8"
        )
        for token in ("INT-001", "LT-001", "KD-001", "src/workbench_api.py", "Epistemic Prototype A"):
            self.assertIn(token, studio_html)

    def test_intent_cycle_rejected(self) -> None:
        p1 = self.repo / "_aiHumanInteract" / "intent" / "nodes" / "INT-001.md"
        txt = p1.read_text(encoding="utf-8").replace("parent: null", 'parent: "INT-002"')
        p1.write_text(txt, encoding="utf-8")
        with self.assertRaises(PtmGraphError):
            load_intent_graph(self.repo)


if __name__ == "__main__":
    unittest.main(verbosity=2)

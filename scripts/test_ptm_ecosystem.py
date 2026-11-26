#!/usr/bin/env python3
"""End-to-end regression suite for PtM's Four-Graph, Hebbian, Triage & Studio ecosystem."""

from __future__ import annotations

import hashlib
import http.server
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from ptm_core import (  # noqa: E402
    PtmGraphError,
    compute_kd_rejection_impact,
    compute_spec_impact,
    load_all_federated_graphs,
    load_evaluations,
    load_intent_graph,
    load_spec_graph,
    resolve_knowledge_debt,
    scan_scripts_graph,
)
from ptm_hebbian import HebbianAssociativeEngine  # noqa: E402
from ptm_memory import EpisodicMemoryStore, SqliteVectorStore, unpack_f32  # noqa: E402
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

    def test_formal_verification_receipt_and_sha256_staleness_detection(self) -> None:
        # 1. Seeded repository has passing receipt & fresh SHA-256 hashes
        fed0 = load_all_federated_graphs(self.repo)
        spec_by_id = {s["id"]: s for s in fed0["specs"]["nodes"]}
        plan_by_id = {p["id"]: p for p in fed0["plan"]["nodes"]}
        scr_by_path = {s["path"]: s for s in fed0["scripts"]["nodes"]}

        self.assertEqual(spec_by_id["SPEC-004"]["verification"]["status"], "verified")
        self.assertEqual(spec_by_id["SPEC-003"]["verification"]["status"], "unverified")
        self.assertEqual(plan_by_id["WP-002"]["verification"]["status"], "verified")
        self.assertEqual(plan_by_id["WP-006"]["verification"]["status"], "verified")
        self.assertEqual(plan_by_id["WP-005"]["verification"]["status"], "unverified")
        self.assertEqual(plan_by_id["ST-002"]["verification"]["status"], "partial")
        self.assertEqual(scr_by_path["src/triage_gate.py"]["verification"]["status"], "verified")

        # 2. Modifying governed source `src/triage_gate.py` immediately flips status to `stale`
        triage_file = self.repo / "src" / "triage_gate.py"
        triage_file.write_text(
            triage_file.read_text(encoding="utf-8") + "\n# local edit invalidating receipt\n",
            encoding="utf-8",
        )
        fed_stale = load_all_federated_graphs(self.repo)
        spec_stale = {s["id"]: s for s in fed_stale["specs"]["nodes"]}
        plan_stale = {p["id"]: p for p in fed_stale["plan"]["nodes"]}
        scr_stale = {s["path"]: s for s in fed_stale["scripts"]["nodes"]}

        self.assertEqual(spec_stale["SPEC-004"]["verification"]["status"], "stale")
        self.assertIn("src/triage_gate.py", spec_stale["SPEC-004"]["verification"]["stale_files"])
        self.assertEqual(plan_stale["WP-002"]["verification"]["status"], "stale")
        self.assertEqual(plan_stale["WP-006"]["verification"]["status"], "stale")
        self.assertEqual(scr_stale["src/triage_gate.py"]["verification"]["status"], "stale")
        self.assertEqual(scr_stale["tests/test_workbench.py"]["verification"]["status"], "stale")

        # 3. Re-running `ptm.py verify` refreshes receipt hashes and restores `verified`
        subprocess.run(
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts" / "ptm.py"),
                "verify",
                str(self.repo),
                "--strict",
                "--embedding-backend",
                "hash",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        fed_reverified = load_all_federated_graphs(self.repo)
        spec_rev = {s["id"]: s for s in fed_reverified["specs"]["nodes"]}
        self.assertEqual(spec_rev["SPEC-004"]["verification"]["status"], "verified")

        # 4. Failing test is caught by `verify --strict` (exit code 2) and marked `failing`
        test_file = self.repo / "tests" / "test_workbench.py"
        test_file.write_text(
            test_file.read_text(encoding="utf-8")
            + "\n    def test_broken_contract(self) -> None:\n        self.assertTrue(False)\n",
            encoding="utf-8",
        )
        fail_proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts" / "ptm.py"),
                "verify",
                str(self.repo),
                "--strict",
                "--embedding-backend",
                "hash",
            ],
            stdout=subprocess.PIPE,
            text=True,
            check=False,
        )
        self.assertEqual(fail_proc.returncode, 2)
        fed_fail = load_all_federated_graphs(self.repo)
        spec_fail = {s["id"]: s for s in fed_fail["specs"]["nodes"]}
        self.assertEqual(spec_fail["SPEC-004"]["verification"]["status"], "failing")

    def test_substantive_evaluations_scaffold_legacy_compat_and_hebbian_lookup(self) -> None:
        evals = load_evaluations(self.repo)
        self.assertEqual(set(evals), {"EVAL-001", "EVAL-002", "EVAL-003"})
        self.assertEqual(evals["EVAL-003"].verdict, "concerns")

        # Scaffold EVAL-004 via CLI
        res = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts" / "ptm.py"),
                "eval",
                "scaffold",
                str(self.repo),
                "--title",
                "端侧离线回退体验独立评鉴",
                "--kind",
                "quality_review",
                "--verdict",
                "pass",
                "--perspective",
                "无 GPU 容器环境维护者视角",
                "--reviewer-mode",
                "isolated_subagent",
                "--summary",
                "无 MLX 环境自动平稳回退至 384 维哈希嵌入，零报错阻塞。",
                "--intents",
                "INT-001",
                "--plans",
                "WP-001",
                "--preserved",
                "离线环境零配置直接可运行",
                "--embedding-backend",
                "hash",
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        created = json.loads(res.stdout)
        self.assertEqual(created["created_evaluation"], "EVAL-004")

        # Legacy plain-markdown evaluation file without front matter must remain compatible
        legacy_path = self.repo / "_aiHumanInteract" / "plan" / "evaluations" / "EVAL-099.md"
        legacy_path.write_text("# Legacy Note\n\nPlain markdown note from older session.\n", encoding="utf-8")
        reloaded = load_evaluations(self.repo)
        self.assertIn("EVAL-099", reloaded)
        self.assertEqual(reloaded["EVAL-099"].kind, "legacy_note")

        # Plan Graph v4 validator remains 100% happy
        subprocess.run(
            [
                sys.executable,
                "-B",
                str(self.repo / "_aiHumanInteract" / "plan" / "validate.py"),
                "--root",
                str(self.repo / "_aiHumanInteract" / "plan"),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )

        # `ptm.py related` surfaces `related_evaluations` (`EVAL-003` on collaboration conflict query)
        fed = load_all_federated_graphs(self.repo)
        spec_by_id = {s["id"]: s for s in fed["specs"]["nodes"]}
        self.assertEqual(spec_by_id["SPEC-002"]["evaluation_rollup"]["status"], "concerns")
        engine = HebbianAssociativeEngine(self.repo, backend="hash")
        engine.sync_federated(fed, persist=False)
        rel_out = engine.related(fed, draft_text="多人协作编辑谱峰冲突审计轨迹")
        eval_ids = [e["id"] for e in rel_out["related_evaluations"]]
        self.assertIn("EVAL-003", eval_ids)

    def test_episodic_sqlite_disentanglement_binary_vectors_and_selective_folding(self) -> None:
        # 1. Verify seeded 3 multiplexed turns disentangled into 8 pure spans & 4 virtual threads
        store = EpisodicMemoryStore(self.repo, backend_name="hash")
        summary = store.export_summary()
        self.assertEqual(summary["turn_count"], 3)
        self.assertEqual(summary["span_count"], 8)
        self.assertEqual(summary["thread_count"], 4)
        self.assertTrue(summary["fts5_enabled"])

        thr1 = store.get_thread("THR-001")
        thr2 = store.get_thread("THR-002")
        thr3 = store.get_thread("THR-003")
        thr4 = store.get_thread("THR-004")
        assert thr1 and thr2 and thr3 and thr4

        # THR-001 gathered item #1 across all 3 turns (`SPAN-0001.1`, `SPAN-0002.1`, `SPAN-0003.1`)
        self.assertEqual([s["span_id"] for s in thr1["spans"]], ["SPAN-0001.1", "SPAN-0002.1", "SPAN-0003.1"])
        # THR-002 gathered item #2 across Turn 1 and Turn 3 (skipping Turn 2 cleanly!) + cross-ref to THR-001
        self.assertEqual([s["span_id"] for s in thr2["spans"]], ["SPAN-0001.2", "SPAN-0003.2"])
        self.assertIn("THR-001", {x["thread_id"] for x in thr2["cross_threads"]})
        # THR-003 gathered item #3 from Turn 1 (`3/3`) and Turn 2 (`2/3`), staying `active` and unpolluted
        self.assertEqual([s["span_id"] for s in thr3["spans"]], ["SPAN-0001.3", "SPAN-0002.2"])
        self.assertEqual(thr3["status"], "active")
        # THR-004 spawned cleanly on Turn 2's `另外突然想到个新问题` (`SPAN-0002.3`)
        self.assertEqual([s["span_id"] for s in thr4["spans"]], ["SPAN-0002.3"])

        # 2. Verify IEEE-754 float32 binary BLOB storage in `memory.sqlite` (4 bytes per float)
        federated = load_all_federated_graphs(self.repo)
        engine = HebbianAssociativeEngine(self.repo, backend="hash")
        engine.sync_federated(federated)
        db_file = self.repo / "_aiHumanInteract" / ".cache" / "memory.sqlite"
        self.assertTrue(db_file.is_file())
        vec_store = SqliteVectorStore(db_file)
        self.assertGreaterEqual(vec_store.count(), 30)

        import sqlite3
        with sqlite3.connect(str(db_file)) as conn:
            dim, blob = conn.execute("SELECT dim, vec_blob FROM vector_cache LIMIT 1").fetchone()
        self.assertEqual(len(blob), dim * 4)
        self.assertEqual(len(unpack_f32(blob)), dim)

        # 3. Verify Hybrid FTS5 + Vector search hits exact sub-turn span (`SPAN-0002.3` for `WaveItem`)
        s_res = store.search_spans("WaveItem LineCursor 术语统一", top_k=3)
        self.assertEqual(s_res["results"][0]["span_id"], "SPAN-0002.3")
        self.assertEqual(s_res["results"][0]["thread_id"], "THR-004")
        self.assertIn("SPEC-002", s_res["results"][0]["linked_nodes"])

        # 4. Verify Per-Thread Selective Context Folding saves tokens while keeping active thread verbatim
        ctx_before = store.render_selective_context()
        self.assertEqual(ctx_before["active_thread_count"], 1)
        self.assertEqual(ctx_before["folded_thread_count"], 3)
        self.assertGreater(ctx_before["char_compression_ratio"], 0.35)

        # Fold THR-003 via CLI and confirm compression increases further while `show THR-003` still returns all spans
        subprocess.run(
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts" / "ptm.py"),
                "memory",
                "fold",
                str(self.repo),
                "THR-003",
                "--status",
                "folded",
                "--capsule",
                "单人阶段维持键值快照，多人回放需求留待 KD-002 触发。",
                "--embedding-backend",
                "hash",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        ctx_after = store.render_selective_context()
        self.assertEqual(ctx_after["active_thread_count"], 0)
        self.assertEqual(ctx_after["folded_thread_count"], 4)
        self.assertGreater(ctx_after["char_compression_ratio"], ctx_before["char_compression_ratio"])
        thr3_after = store.get_thread("THR-003")
        assert thr3_after
        self.assertEqual(len(thr3_after["spans"]), 2)

        # 5. Verify 5-topic parallel single-turn + follow-up turn disentanglement via CLI `memory log`
        subprocess.run(
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts" / "ptm.py"),
                "memory",
                "log",
                str(self.repo),
                "--session",
                "SES-FIVE",
                "--user",
                "1. 登录态刷新策略\n2. WebSocket 断线重连\n3. 导出 CSV 编码兼容\n4. 暗色主题对比度\n5. 审计日志归档周期",
                "--assistant",
                "1. 采用双 Token 滑动续期\n2. 指数退避重连\n3. 带 UTF-8 BOM 导出\n4. 遵循 WCAG AA 对比度\n5. 冷热分层保留 90 天",
                "--embedding-backend",
                "hash",
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        r_log2 = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts" / "ptm.py"),
                "memory",
                "log",
                str(self.repo),
                "--session",
                "SES-FIVE",
                "--user",
                "关于第3点：导出 CSV 除了 UTF-8 BOM，还要转义单元格开头的公式字符防止注入。\n\n关于第5点：审计日志满 90 天后压缩转存对象存储即可。",
                "--assistant",
                "1. 已补充 CSV 公式注入转义规则。\n\n2. 已确认 90 天后转存 S3 归档桶。",
                "--embedding-backend",
                "hash",
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        out_log2 = json.loads(r_log2.stdout)
        self.assertEqual(out_log2["span_count"], 2)
        # Ensure CSV follow-up woven into THR-007 (slot #3 of SES-FIVE) and Audit follow-up into THR-009 (slot #5)
        csv_search = store.search_spans("CSV 公式字符注入 BOM", top_k=2)
        csv_thr_id = csv_search["results"][0]["thread_id"]
        csv_thr = store.get_thread(csv_thr_id)
        assert csv_thr
        self.assertEqual(csv_thr["span_count"], 2)

    def test_intent_cycle_rejected(self) -> None:
        p1 = self.repo / "_aiHumanInteract" / "intent" / "nodes" / "INT-001.md"
        txt = p1.read_text(encoding="utf-8").replace("parent: null", 'parent: "INT-002"')
        p1.write_text(txt, encoding="utf-8")
        with self.assertRaises(PtmGraphError):
            load_intent_graph(self.repo)


class _EmbeddingHandler(http.server.BaseHTTPRequestHandler):
    calls = 0

    def do_POST(self) -> None:  # noqa: N802
        type(self).calls += 1
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        dim = int(payload.get("dimensions") or 4)
        # Simulate fixed 4-d server if dim==8 to test dimension mismatch check
        actual_dim = 4 if dim == 8 else dim
        data = []
        for index, text in enumerate(payload.get("input", [])):
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            raw = [((digest[j % len(digest)] / 127.5) - 1.0) for j in range(actual_dim)]
            norm = math.sqrt(sum(v * v for v in raw)) or 1.0
            data.append({"index": index, "embedding": [v / norm for v in raw]})
        body = json.dumps({"data": data}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        """Keep test output quiet."""


class PtmDualEmbeddingBackendTests(unittest.TestCase):
    """Dual embedding backends (`openai` + `mlx`/`local` + `hash`) and SQLite vector-space isolation."""

    ENV_KEYS = (
        "PTM_EMBEDDING_BASE_URL",
        "PTM_EMBEDDING_MODEL",
        "PTM_EMBEDDING_API_KEY",
        "PTM_EMBEDDING_DIMENSIONS",
        "PTM_EMBEDDING_TIMEOUT",
        "PTM_EMBEDDING_LOCAL_MODEL",
        "PTM_EMBEDDING_LOCAL_PYTHON",
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _EmbeddingHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}/v1"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self) -> None:
        _EmbeddingHandler.calls = 0
        self._tmp = tempfile.TemporaryDirectory(prefix="ptm-dual-embed-")
        self.repo = Path(self._tmp.name) / "repo"
        self.cache = self.repo / "_aiHumanInteract" / ".cache" / "memory.sqlite"
        self._saved_env = {key: os.environ.get(key) for key in self.ENV_KEYS}
        os.environ.update(
            {
                "PTM_EMBEDDING_BASE_URL": self.base_url,
                "PTM_EMBEDDING_MODEL": "test-embedding",
                "PTM_EMBEDDING_API_KEY": "test-key",
                "PTM_EMBEDDING_DIMENSIONS": "4",
                "PTM_EMBEDDING_TIMEOUT": "10",
            }
        )

    def tearDown(self) -> None:
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    def test_openai_batches_sqlite_cache_and_cross_backend_isolation(self) -> None:
        from ptm_hebbian import TieredEmbedder

        embedder_api = TieredEmbedder(self.cache, backend="api")
        self.assertEqual(embedder_api.active_backend, "openai")
        self.assertEqual(embedder_api.effective_model_id, "openai:test-embedding:4")

        texts = [f"text-{index}" for index in range(12)]
        vectors = embedder_api.embed_many(texts)
        self.assertEqual(len(vectors), 12)
        self.assertEqual({len(v) for v in vectors}, {4})
        self.assertEqual(_EmbeddingHandler.calls, 2)

        # Reloading a fresh TieredEmbedder hits SQLite without HTTP calls
        embedder_api2 = TieredEmbedder(self.cache, backend="openai")
        self.assertEqual(embedder_api2.embed_many(texts), vectors)
        self.assertEqual(_EmbeddingHandler.calls, 2)

        # Switching to `hash` uses its own 384-d namespace without wiping `openai` entries
        embedder_hash = TieredEmbedder(self.cache, backend="hash")
        hash_vecs = embedder_hash.embed_many(texts[:2])
        self.assertEqual(len(hash_vecs[0]), 384)
        self.assertEqual(embedder_api2.embed_many(texts[:2]), vectors[:2])
        self.assertEqual(_EmbeddingHandler.calls, 2)

    def test_episodic_memory_isolates_same_dim_models_across_switches(self) -> None:
        # Ingest under Model A (384-d API), then search under `hash` (also 384-d!)
        os.environ["PTM_EMBEDDING_DIMENSIONS"] = "384"
        eng_a = HebbianAssociativeEngine(self.repo, backend="openai")
        store_a = eng_a.make_episodic_store()
        store_a.ingest_turn(
            user_text="如何实现双接口嵌入向量隔离？",
            assistant_text="在 memory.sqlite 中按 effective_model_id 前缀隔离缓存键。",
            session_id="SES-ISO",
        )
        calls_after_ingest = _EmbeddingHandler.calls
        self.assertGreaterEqual(calls_after_ingest, 1)

        # Switch to `hash` (384-d) — must NOT reuse Model A's 384-d blob, and must NOT call API
        eng_hash = HebbianAssociativeEngine(self.repo, backend="hash")
        store_hash = eng_hash.make_episodic_store()
        res_hash = store_hash.search_spans("双接口嵌入向量隔离", top_k=1)
        self.assertEqual(_EmbeddingHandler.calls, calls_after_ingest)
        self.assertEqual(len(res_hash["results"]), 1)
        self.assertGreater(res_hash["results"][0]["semantic_similarity"], 0.35)

        # Switch between two DIFFERENT 1024-d models (`model-alpha` -> `model-beta`) and verify `_reembed_spans_if_needed` re-embeds cleanly
        os.environ["PTM_EMBEDDING_DIMENSIONS"] = "1024"
        os.environ["PTM_EMBEDDING_MODEL"] = "model-alpha"
        eng_1024_a = HebbianAssociativeEngine(self.repo, backend="openai")
        eng_1024_a.make_episodic_store().sync_portable_episodes()
        calls_alpha = _EmbeddingHandler.calls

        os.environ["PTM_EMBEDDING_MODEL"] = "model-beta"
        eng_1024_b = HebbianAssociativeEngine(self.repo, backend="openai")
        eng_1024_b.make_episodic_store().sync_portable_episodes()
        self.assertGreater(_EmbeddingHandler.calls, calls_alpha)

    def test_dimension_mismatch_and_missing_config_raise_loudly(self) -> None:
        from ptm_hebbian import TieredEmbedder

        os.environ["PTM_EMBEDDING_DIMENSIONS"] = "8"
        embedder = TieredEmbedder(self.cache, backend="openai")
        with self.assertRaises(RuntimeError):
            embedder.embed_many(["dimension-check"])

        os.environ.pop("PTM_EMBEDDING_API_KEY", None)
        with self.assertRaises(RuntimeError):
            TieredEmbedder(self.cache, backend="openai")

        os.environ["PTM_EMBEDDING_LOCAL_PYTHON"] = "/nonexistent/python"
        with self.assertRaises(RuntimeError):
            TieredEmbedder(self.cache, backend="local")

    def test_embed_probe_cli_outputs_telemetry(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SKILL_ROOT / "scripts" / "ptm.py"),
                "embed-probe",
                str(self.repo),
                "--embedding-backend",
                "api",
            ],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        info = json.loads(proc.stdout)
        self.assertTrue(info["ok"])
        self.assertEqual(info["active_backend"], "openai")
        self.assertEqual(info["dimensions"], 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)

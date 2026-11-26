#!/usr/bin/env python3
"""Unified CLI for Paths to Modernity (PtM) Four-Graph Infrastructure.

Commands:
  ptm.py build <repo>       Validate & build Intent, Spec, Plan (v4), Knowledge Debt, Scripts, Evaluations, SQLite Memory, Hebbian & Studio
  ptm.py verify <repo>      Run deterministic tests, record SHA-256 freshness receipt & refresh verification status
  ptm.py eval <scaffold|list> <repo> ...  Scaffold or inspect context-separated substantive evaluations (EVAL-###)
  ptm.py memory <log|import-jsonl|threads|show|search|fold|context> <repo> ...  Manage SQLite Turn->Span->Thread episodic memory
  ptm.py status <repo>      Print compact project neighborhood status across all five graphs
  ptm.py query <repo> <q>   Run Dual-Path Retrieval (Base + Hebbian Spreading Flip) & reinforce cluster
  ptm.py related <repo> ... Agent-facing reverse lookup by existing node ID, draft file, or draft text
  ptm.py spec impact <repo> <SPEC-ID>     Preview cross-graph blast radius if a Spec is amended
  ptm.py triage <repo> ...  Record a 3-way technical disclosure choice (creating KD bookmark if needed)
  ptm.py kd impact <repo> <KD-ID>         Preview reorganization blast radius if KD is rejected
  ptm.py kd resolve <repo> <KD-ID> ...    Affirm or reject a KD bookmark & propagate reorganization
  ptm.py portrait <repo>    Synthesize subagent recovery portrait into AGENTS.md
  ptm.py embed-probe <repo> Probe active embedding backend, model namespace, dimensions & latency
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ptm_core import (  # noqa: E402
    EVAL_KINDS,
    EVAL_REVIEWER_MODES,
    EVAL_VERDICTS,
    PtmGraphError,
    build_evaluation_views,
    build_intent_views,
    build_knowledge_debt_views,
    build_scripts_views,
    build_spec_views,
    compute_kd_rejection_impact,
    compute_spec_impact,
    format_front_matter,
    load_all_federated_graphs,
    load_knowledge_debt_graph,
    resolve_knowledge_debt,
    run_formal_verification,
)
from ptm_hebbian import BACKEND_CHOICES, HebbianAssociativeEngine, TieredEmbedder  # noqa: E402
from ptm_portrait import (  # noqa: E402
    build_portrait_digest,
    render_portrait_block,
    update_agents_portrait,
)
from ptm_studio import build_studio_html  # noqa: E402


def _rebuild_plan_if_present(repo: Path) -> bool:
    plan_dir = repo / "_aiHumanInteract" / "plan"
    builder = plan_dir / "build_graph.py"
    if not builder.is_file():
        builder = SKILL_ROOT / "assets" / "plan-graph" / "_aiHumanInteract" / "plan" / "build_graph.py"
    if plan_dir.is_dir() and any((plan_dir / lvl).is_dir() for lvl in ("long-term", "mid-term", "short-term", "work-package")):
        if any((plan_dir / "long-term").glob("*.md")):
            subprocess.run(
                [sys.executable, "-B", str(builder), "--root", str(plan_dir)],
                cwd=repo,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            return True
    return False


def cmd_build(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    _rebuild_plan_if_present(repo)
    intent_p = build_intent_views(repo)
    spec_p = build_spec_views(repo)
    kd_p = build_knowledge_debt_views(repo)
    scripts_p = build_scripts_views(repo)
    eval_p = build_evaluation_views(repo)
    federated = load_all_federated_graphs(repo)
    v_rep = federated.get("verification_report") or {}

    engine = HebbianAssociativeEngine(repo, backend=args.embedding_backend)
    heb_p = engine.sync_federated(federated)
    ep_mem = federated.get("episodic_memory") or engine.make_episodic_store().export_summary()
    studio_path = build_studio_html(repo, federated, heb_p, title=args.title)

    print(
        f"[PtM] Built 5-graph ecosystem in {repo}\n"
        f"  Intent Graph    : {intent_p['node_count']} nodes, {intent_p['edge_count']} edges\n"
        f"  Spec Graph      : {spec_p['node_count']} specs, {spec_p['edge_count']} edges\n"
        f"  Plan Graph (v4) : {len(federated['plan'].get('nodes', []))} nodes, {len(federated['plan'].get('edges', []))} edges\n"
        f"  Knowledge Debt  : {kd_p['node_count']} bookmarks\n"
        f"  Scripts Graph   : {scripts_p['node_count']} modules, {scripts_p['edge_count']} AST edges\n"
        f"  Verification    : status={v_rep.get('overall_test_status')} ({v_rep.get('passed_tests', 0)}/{v_rep.get('total_tests', 0)} passed, stale_files={len(v_rep.get('global_stale_files', []))})\n"
        f"  Evaluations     : {eval_p['node_count']} records (concerns_or_fail={v_rep.get('evaluation_counts', {}).get('concerns_or_fail', 0)})\n"
        f"  Episodic SQLite : {ep_mem.get('turn_count', 0)} turns -> {ep_mem.get('span_count', 0)} spans -> {ep_mem.get('thread_count', 0)} threads (folded={ep_mem.get('folded_count', 0)}, f32_blobs={ep_mem.get('vector_blob_count', 0)})\n"
        f"  Hebbian Memory  : {heb_p['synapse_count']} synapses ({heb_p['embedding_backend']} -> {heb_p['embedding_model']})\n"
        f"  Curated Studio  : {studio_path}"
    )
    if args.with_portrait:
        digest = build_portrait_digest(federated, heb_p)
        block, gen = render_portrait_block(
            digest, mode=args.portrait_mode, repo_root=repo, skill_root=SKILL_ROOT
        )
        agents_path = update_agents_portrait(repo, block)
        print(f"  Portrait ({gen}) : {agents_path}")
    return 0


def _next_eval_id(eval_dir: Path) -> str:
    existing = []
    if eval_dir.is_dir():
        for p in eval_dir.glob("EVAL-*.md"):
            try:
                existing.append(int(p.stem.split("-")[1]))
            except (IndexError, ValueError):
                pass
    nxt = (max(existing) + 1) if existing else 1
    return f"EVAL-{nxt:03d}"


def cmd_verify(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    receipt = run_formal_verification(repo, command=args.cmd)
    federated = load_all_federated_graphs(repo)
    if (repo / "_aiHumanInteract" / "studio").is_dir():
        engine = HebbianAssociativeEngine(repo, backend=args.embedding_backend)
        heb_p = engine.sync_federated(federated)
        build_studio_html(repo, federated, heb_p)
    out = {
        "receipt": receipt,
        "verification_report": federated.get("verification_report"),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.strict and receipt.get("overall_status") == "failed":
        return 2
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if args.eval_action == "list":
        federated = load_all_federated_graphs(repo)
        print(
            json.dumps(
                {
                    "verification_report": federated.get("verification_report"),
                    "evaluations": federated.get("evaluations", {}).get("nodes", []),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.eval_action == "scaffold":
        eval_dir = repo / "_aiHumanInteract" / "plan" / "evaluations"
        eval_dir.mkdir(parents=True, exist_ok=True)
        eid = args.id or _next_eval_id(eval_dir)
        today = date.today().isoformat()

        def _csv(val: str | None) -> list[str]:
            return [x.strip() for x in (val or "").split(",") if x.strip()]

        def _semi(val: str | None) -> list[str]:
            return [x.strip() for x in (val or "").split(";") if x.strip()]

        meta = {
            "id": eid,
            "title": args.title.strip(),
            "kind": args.kind,
            "verdict": args.verdict,
            "perspective": args.perspective.strip(),
            "reviewer_mode": args.reviewer_mode,
            "updated": today,
            "summary": args.summary.strip(),
            "evaluates_intents": _csv(args.intents),
            "evaluates_specs": _csv(args.specs),
            "evaluates_plans": _csv(args.plans),
            "evaluates_scripts": _csv(args.scripts),
            "preserved_qualities": _semi(args.preserved),
            "at_risk_qualities": _semi(args.at_risk),
            "evidence_refs": _csv(args.evidence),
            "recommended_action": args.action.strip() if args.action else None,
        }
        body = (
            f"# {eid} · {args.title.strip()}\n\n"
            f"- **Perspective:** {args.perspective.strip()} (`{args.reviewer_mode}`)\n"
            f"- **Verdict:** `{args.verdict}`\n\n"
            f"## Substantive Findings\n\n{args.summary.strip()}\n"
        )
        if args.notes:
            body += f"\n{args.notes.strip()}\n"
        out_path = eval_dir / f"{eid}.md"
        out_path.write_text(format_front_matter(meta, body), encoding="utf-8")
        build_evaluation_views(repo)
        if (repo / "_aiHumanInteract" / "studio").is_dir():
            federated = load_all_federated_graphs(repo)
            engine = HebbianAssociativeEngine(repo, backend=args.embedding_backend)
            heb_p = engine.sync_federated(federated)
            build_studio_html(repo, federated, heb_p)
        print(
            json.dumps(
                {
                    "created_evaluation": eid,
                    "verdict": args.verdict,
                    "perspective": args.perspective.strip(),
                    "path": out_path.relative_to(repo).as_posix(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    return 1


def cmd_status(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    federated = load_all_federated_graphs(repo)
    assoc_file = repo / "_aiHumanInteract" / "hebbian" / "associations.json"
    heb = json.loads(assoc_file.read_text(encoding="utf-8")) if assoc_file.is_file() else {}
    digest = build_portrait_digest(federated, heb)
    print(json.dumps(digest, ensure_ascii=False, indent=2))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    federated = load_all_federated_graphs(repo)
    engine = HebbianAssociativeEngine(repo, backend=args.embedding_backend)
    engine.sync_federated(federated, persist=not args.no_reinforce)
    res = engine.query(
        args.query,
        top_k=args.top_k,
        max_flipped=args.max_flipped,
        reinforce=not args.no_reinforce,
    )
    if not args.no_reinforce and (repo / "_aiHumanInteract" / "studio").is_dir():
        build_studio_html(repo, federated, engine.export_payload(), title="Project Architecture Studio")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


def cmd_related(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    federated = load_all_federated_graphs(repo)
    engine = HebbianAssociativeEngine(repo, backend=args.embedding_backend)
    engine.sync_federated(federated, persist=args.reinforce)

    node_id = args.node
    draft_file = Path(args.draft_file).resolve() if args.draft_file else None
    draft_text = args.text

    # Smart auto-detection when positional `target` is passed without explicit mode flags
    if args.target and not (node_id or draft_file or draft_text):
        raw_t = args.target.strip()
        resolved_nid = engine.resolve_node_id(raw_t)
        if resolved_nid:
            node_id = resolved_nid
        else:
            cand_paths = [Path(raw_t), repo / raw_t]
            found_path = next((cp.resolve() for cp in cand_paths if cp.is_file()), None)
            if found_path is not None:
                draft_file = found_path
            else:
                draft_text = raw_t

    res = engine.related(
        federated,
        node_id=node_id,
        draft_file=draft_file,
        draft_text=draft_text,
        per_graph=args.per_graph,
        novel_top_k=args.novel_top_k,
        reinforce=args.reinforce,
    )
    if args.reinforce and (repo / "_aiHumanInteract" / "studio").is_dir():
        build_studio_html(repo, federated, engine.export_payload(), title="Project Architecture Studio")
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


def _next_kd_id(kd_dir: Path) -> str:
    existing = []
    if kd_dir.is_dir():
        for p in kd_dir.glob("KD-*.md"):
            try:
                existing.append(int(p.stem.split("-")[1]))
            except (IndexError, ValueError):
                pass
    nxt = (max(existing) + 1) if existing else 1
    return f"KD-{nxt:03d}"


def cmd_triage(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    choice = args.choice
    today = date.today().isoformat()
    intents = [x.strip() for x in (args.intents or "").split(",") if x.strip()]
    specs = [x.strip() for x in (args.specs or "").split(",") if x.strip()]
    plans = [x.strip() for x in (args.plans or "").split(",") if x.strip()]
    scripts = [x.strip() for x in (args.scripts or "").split(",") if x.strip()]

    if choice == "understood_agreed":
        print(
            json.dumps(
                {
                    "mode": "understood_agreed",
                    "acceptance": "informed_acceptance",
                    "term": args.term,
                    "action": "Proceed within authorized scope; no Knowledge Debt bookmark needed.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if choice == "disagreed_counterproposal":
        print(
            json.dumps(
                {
                    "mode": "disagreed_counterproposal",
                    "acceptance": "rejected_before_execution",
                    "term": args.term,
                    "counterproposal": args.counterproposal or "",
                    "plans_to_revise": plans,
                    "intents_to_recheck": intents,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    # `not_understood_prototype` -> Create Knowledge Debt bookmark!
    kd_dir = repo / "_aiHumanInteract" / "knowledge-debt" / "nodes"
    kd_dir.mkdir(parents=True, exist_ok=True)
    kd_id = args.id or _next_kd_id(kd_dir)
    meta = {
        "id": kd_id,
        "term": args.term,
        "kind": args.kind,
        "status": "open",
        "triage_mode": "not_understood_prototype",
        "updated": today,
        "intent_refs": intents,
        "spec_refs": specs,
        "plan_refs": plans,
        "script_refs": scripts,
        "revisit_when": args.revisit_when,
        "resolution_note": None,
        "counterproposal": None,
    }
    body = (
        f"# {kd_id} · {args.term}\n\n"
        f"## Understanding Gap\n\n{args.gap or '决策者选择暂不在原型阶段耗费心智摩擦深入该技术细节，先标记书签并推进可逆原型。'}\n\n"
        f"## Technical Declaration & Cost if Wrong\n\n{args.declaration}\n\n"
        f"## Revisit Trigger & Evidence Needed\n\n- **Trigger:** {args.revisit_when}\n"
    )
    out_file = kd_dir / f"{kd_id}.md"
    out_file.write_text(format_front_matter(meta, body), encoding="utf-8")
    build_knowledge_debt_views(repo)
    print(
        json.dumps(
            {
                "mode": "not_understood_prototype",
                "acceptance": "provisional_acceptance",
                "created_bookmark": kd_id,
                "path": out_file.relative_to(repo).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_spec(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if args.spec_action == "impact":
        imp = compute_spec_impact(repo, args.spec_id)
        print(json.dumps(imp, ensure_ascii=False, indent=2))
        return 0
    return 1


def cmd_kd(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    if args.kd_action == "impact":
        imp = compute_kd_rejection_impact(repo, args.kd_id)
        print(json.dumps(imp, ensure_ascii=False, indent=2))
        return 0
    if args.kd_action == "resolve":
        imp = resolve_knowledge_debt(
            repo,
            args.kd_id,
            verdict=args.verdict,
            note=args.note,
            counterproposal=args.counterproposal,
        )
        build_intent_views(repo)
        build_spec_views(repo)
        build_knowledge_debt_views(repo)
        # Co-activate KD + linked Intents, Specs & Plans in Hebbian memory on revisit!
        federated = load_all_federated_graphs(repo)
        engine = HebbianAssociativeEngine(repo, backend=args.embedding_backend)
        engine.sync_federated(federated)
        kds, _ = load_knowledge_debt_graph(repo)
        kd_node = kds[args.kd_id]
        engine.reinforce_cluster(
            [args.kd_id, *kd_node.intent_refs, *kd_node.spec_refs, *kd_node.plan_refs],
            reason=f"kd_resolve:{args.kd_id}:{args.verdict}",
        )
        if (repo / "_aiHumanInteract" / "studio").is_dir():
            build_studio_html(repo, federated, engine.export_payload())
        print(json.dumps(imp, ensure_ascii=False, indent=2))
        return 0
    return 1


def cmd_memory(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    backend = getattr(args, "embedding_backend", "auto")
    engine = HebbianAssociativeEngine(repo, backend=backend)
    store = engine.make_episodic_store()

    act = args.mem_action
    if act == "log":
        hint_nodes = [x.strip() for x in (args.nodes or "").split(",") if x.strip()]
        res = store.ingest_turn(
            user_text=args.user,
            assistant_text=args.assistant,
            session_id=args.session,
            hint_nodes=hint_nodes,
            append_portable_jsonl=True,
        )
        federated = load_all_federated_graphs(repo)
        store.bind_threads_to_federated_graphs(federated)
        if (repo / "_aiHumanInteract" / "studio").is_dir():
            heb_p = engine.sync_federated(federated)
            build_studio_html(repo, federated, heb_p)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    if act == "import-jsonl":
        res = store.import_jsonl_transcript(Path(args.jsonl_file).resolve(), session_id=args.session)
        federated = load_all_federated_graphs(repo)
        store.bind_threads_to_federated_graphs(federated)
        if (repo / "_aiHumanInteract" / "studio").is_dir():
            heb_p = engine.sync_federated(federated)
            build_studio_html(repo, federated, heb_p)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    if act == "threads":
        federated = load_all_federated_graphs(repo)
        store.sync_portable_episodes(federated)
        summary = store.export_summary()
        summary["threads"] = store.list_threads(include_spans=False)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    if act == "show":
        federated = load_all_federated_graphs(repo)
        store.sync_portable_episodes(federated)
        detail = store.get_thread(args.thread_id.strip().upper())
        if detail is None:
            raise PtmGraphError(f"Unknown thread ID: {args.thread_id}")
        print(json.dumps(detail, ensure_ascii=False, indent=2))
        return 0

    if act == "search":
        federated = load_all_federated_graphs(repo)
        store.sync_portable_episodes(federated)
        out = store.search_spans(args.query, top_k=args.top_k)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if act == "fold":
        federated = load_all_federated_graphs(repo)
        store.sync_portable_episodes(federated)
        nodes = [x.strip() for x in (args.nodes or "").split(",") if x.strip()]
        folded = store.fold_thread(
            args.thread_id.strip().upper(),
            capsule_summary=args.capsule or None,
            status=args.status,
            node_refs=nodes,
            title=args.title or None,
        )
        if (repo / "_aiHumanInteract" / "studio").is_dir():
            federated = load_all_federated_graphs(repo)
            heb_p = engine.sync_federated(federated)
            build_studio_html(repo, federated, heb_p)
        print(json.dumps(folded, ensure_ascii=False, indent=2))
        return 0

    if act == "context":
        federated = load_all_federated_graphs(repo)
        store.sync_portable_episodes(federated)
        ctx = store.render_selective_context()
        print(json.dumps(ctx, ensure_ascii=False, indent=2))
        return 0

    return 1


def cmd_portrait(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    federated = load_all_federated_graphs(repo)
    assoc_file = repo / "_aiHumanInteract" / "hebbian" / "associations.json"
    heb = json.loads(assoc_file.read_text(encoding="utf-8")) if assoc_file.is_file() else {}
    digest = build_portrait_digest(federated, heb)
    block, gen = render_portrait_block(
        digest, mode=args.mode, repo_root=repo, skill_root=SKILL_ROOT
    )
    if args.dry_run:
        print(block)
        return 0
    agents_path = update_agents_portrait(repo, block)
    print(f"[PtM] Updated recovery portrait in {agents_path} (synthesizer: {gen})")
    return 0


def cmd_embed_probe(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    cache_path = repo / "_aiHumanInteract" / ".cache" / "memory.sqlite"
    embedder = TieredEmbedder(cache_path, backend=args.embedding_backend)
    info = embedder.probe()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Validate & build all five graphs, Hebbian synapses, and Studio")
    b.add_argument("repo", type=Path)
    b.add_argument("--embedding-backend", choices=BACKEND_CHOICES, default="auto")
    b.add_argument("--title", default="PtM Five-Graph Curated Studio")
    b.add_argument("--with-portrait", action="store_true")
    b.add_argument("--portrait-mode", choices=("auto", "llm", "deterministic"), default="auto")
    b.set_defaults(func=cmd_build)

    ver = sub.add_parser(
        "verify",
        help="Run deterministic test suite, record SHA-256 freshness receipt & refresh Studio",
    )
    ver.add_argument("repo", type=Path)
    ver.add_argument("--cmd", default=None, help="Optional custom test runner command")
    ver.add_argument("--strict", action="store_true", help="Exit non-zero if tests fail")
    ver.add_argument("--embedding-backend", choices=BACKEND_CHOICES, default="auto")
    ver.set_defaults(func=cmd_verify)

    ev = sub.add_parser("eval", help="Scaffold or inspect context-separated substantive evaluations")
    ev_sub = ev.add_subparsers(dest="eval_action", required=True)
    evl = ev_sub.add_parser("list")
    evl.add_argument("repo", type=Path)
    evl.set_defaults(func=cmd_eval)

    evs = ev_sub.add_parser("scaffold")
    evs.add_argument("repo", type=Path)
    evs.add_argument("--title", required=True)
    evs.add_argument(
        "--kind",
        choices=tuple(sorted(EVAL_KINDS - {"legacy_note"})),
        default="quality_review",
    )
    evs.add_argument(
        "--verdict",
        choices=tuple(sorted(EVAL_VERDICTS - {"noted"})),
        required=True,
    )
    evs.add_argument("--perspective", required=True)
    evs.add_argument(
        "--reviewer-mode",
        choices=tuple(sorted(EVAL_REVIEWER_MODES - {"legacy"})),
        default="isolated_subagent",
    )
    evs.add_argument("--summary", required=True)
    evs.add_argument("--intents", default="")
    evs.add_argument("--specs", default="")
    evs.add_argument("--plans", default="")
    evs.add_argument("--scripts", default="")
    evs.add_argument("--preserved", default="", help="Semicolon-separated preserved qualities")
    evs.add_argument("--at-risk", default="", help="Semicolon-separated at-risk qualities")
    evs.add_argument("--evidence", default="", help="Comma-separated repo-relative evidence paths")
    evs.add_argument("--action", default="", help="Optional recommended follow-up action")
    evs.add_argument("--notes", default="", help="Optional extra markdown body notes")
    evs.add_argument("--id", default=None)
    evs.add_argument("--embedding-backend", choices=BACKEND_CHOICES, default="auto")
    evs.set_defaults(func=cmd_eval)

    mem = sub.add_parser(
        "memory",
        help="Manage embedded SQLite Turn->Span->Thread episodic memory & binary vector cache",
    )
    mem_sub = mem.add_subparsers(dest="mem_action", required=True)

    mlog = mem_sub.add_parser("log", help="Ingest a single turn & disentangle multi-topic Spans")
    mlog.add_argument("repo", type=Path)
    mlog.add_argument("--user", required=True)
    mlog.add_argument("--assistant", required=True)
    mlog.add_argument("--session", default="SES-01")
    mlog.add_argument("--nodes", default="", help="Optional comma-separated graph node IDs")
    mlog.add_argument("--embedding-backend", choices=BACKEND_CHOICES, default="auto")
    mlog.set_defaults(func=cmd_memory)

    mimp = mem_sub.add_parser("import-jsonl", help="Import turns from a JSONL transcript")
    mimp.add_argument("repo", type=Path)
    mimp.add_argument("jsonl_file", type=Path)
    mimp.add_argument("--session", default="SES-IMPORT")
    mimp.add_argument("--embedding-backend", choices=BACKEND_CHOICES, default="auto")
    mimp.set_defaults(func=cmd_memory)

    mthr = mem_sub.add_parser("threads", help="List disentangled virtual Topic Threads (THR-###)")
    mthr.add_argument("repo", type=Path)
    mthr.add_argument("--embedding-backend", choices=BACKEND_CHOICES, default="auto")
    mthr.set_defaults(func=cmd_memory)

    mshw = mem_sub.add_parser("show", help="Show pure single-topic Q&A timeline for one THR-###")
    mshw.add_argument("repo", type=Path)
    mshw.add_argument("thread_id")
    mshw.add_argument("--embedding-backend", choices=BACKEND_CHOICES, default="auto")
    mshw.set_defaults(func=cmd_memory)

    msrc = mem_sub.add_parser("search", help="Hybrid FTS5 BM25 + dense vector search across Spans")
    msrc.add_argument("repo", type=Path)
    msrc.add_argument("query")
    msrc.add_argument("--top-k", type=int, default=6)
    msrc.add_argument("--embedding-backend", choices=BACKEND_CHOICES, default="auto")
    msrc.set_defaults(func=cmd_memory)

    mfld = mem_sub.add_parser("fold", help="Fold a settled thread into a 1-line capsule")
    mfld.add_argument("repo", type=Path)
    mfld.add_argument("thread_id")
    mfld.add_argument("--status", choices=("folded", "crystallized", "resolved", "active"), default="folded")
    mfld.add_argument("--capsule", default="")
    mfld.add_argument("--nodes", default="")
    mfld.add_argument("--title", default="")
    mfld.add_argument("--embedding-backend", choices=BACKEND_CHOICES, default="auto")
    mfld.set_defaults(func=cmd_memory)

    mctx = mem_sub.add_parser("context", help="Render selective working context (active spans + folded capsules)")
    mctx.add_argument("repo", type=Path)
    mctx.add_argument("--embedding-backend", choices=BACKEND_CHOICES, default="auto")
    mctx.set_defaults(func=cmd_memory)

    s = sub.add_parser("status", help="Show compact multi-graph neighborhood digest")
    s.add_argument("repo", type=Path)
    s.set_defaults(func=cmd_status)

    q = sub.add_parser("query", help="Dual-Path retrieval (Base + Hebbian Spreading Flip)")
    q.add_argument("repo", type=Path)
    q.add_argument("query")
    q.add_argument("--top-k", type=int, default=5)
    q.add_argument("--max-flipped", type=int, default=4)
    q.add_argument("--embedding-backend", choices=BACKEND_CHOICES, default="auto")
    q.add_argument("--no-reinforce", action="store_true")
    q.set_defaults(func=cmd_query)

    rel = sub.add_parser(
        "related",
        help="Agent-facing cross-graph lookup by existing node ID, uncommitted draft file, or draft text",
    )
    rel.add_argument("repo", type=Path)
    rel.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Auto-detected node ID (e.g. WP-002 / INT-003 / src/a.py), draft file path, or draft text",
    )
    rel.add_argument("--node", default=None, help="Explicit existing node ID (e.g. WP-002, INT-003, KD-001)")
    rel.add_argument("--draft-file", default=None, help="Path to an uncommitted draft .md or source file")
    rel.add_argument("--text", default=None, help="Draft plan/intent summary text")
    rel.add_argument("--per-graph", type=int, default=4, help="Max ranked candidates returned per graph")
    rel.add_argument("--novel-top-k", type=int, default=8, help="Max novel (undeclared) discoveries highlighted")
    rel.add_argument("--embedding-backend", choices=BACKEND_CHOICES, default="auto")
    rel.add_argument(
        "--reinforce",
        action="store_true",
        help="Persist Hebbian co-activation reinforcement (default is read-only probe)",
    )
    rel.set_defaults(func=cmd_related)

    sp = sub.add_parser("spec", help="Inspect Spec Graph blast radius")
    sp_sub = sp.add_subparsers(dest="spec_action", required=True)
    spi = sp_sub.add_parser("impact")
    spi.add_argument("repo", type=Path)
    spi.add_argument("spec_id")
    spi.set_defaults(func=cmd_spec)

    tr = sub.add_parser("triage", help="Record 3-way technical disclosure decision")
    tr.add_argument("repo", type=Path)
    tr.add_argument("--term", required=True)
    tr.add_argument(
        "--choice",
        choices=("understood_agreed", "not_understood_prototype", "disagreed_counterproposal"),
        required=True,
    )
    tr.add_argument("--kind", default="reasoning_gap")
    tr.add_argument("--declaration", default="Agent-declared technical mechanism for reversible prototype.")
    tr.add_argument("--revisit-when", default="When prototype evaluation reveals friction or before production lock-in.")
    tr.add_argument("--gap", default="")
    tr.add_argument("--counterproposal", default="")
    tr.add_argument("--intents", default="")
    tr.add_argument("--specs", default="")
    tr.add_argument("--plans", default="")
    tr.add_argument("--scripts", default="")
    tr.add_argument("--id", default=None)
    tr.set_defaults(func=cmd_triage)

    kd = sub.add_parser("kd", help="Inspect impact or resolve a Knowledge Debt bookmark")
    kd_sub = kd.add_subparsers(dest="kd_action", required=True)
    kdi = kd_sub.add_parser("impact")
    kdi.add_argument("repo", type=Path)
    kdi.add_argument("kd_id")
    kdi.set_defaults(func=cmd_kd)

    kdr = kd_sub.add_parser("resolve")
    kdr.add_argument("repo", type=Path)
    kdr.add_argument("kd_id")
    kdr.add_argument("--verdict", choices=("affirmed", "rejected"), required=True)
    kdr.add_argument("--note", required=True)
    kdr.add_argument("--counterproposal", default=None)
    kdr.add_argument("--embedding-backend", choices=BACKEND_CHOICES, default="auto")
    kdr.set_defaults(func=cmd_kd)

    pr = sub.add_parser("portrait", help="Generate subagent recovery portrait into AGENTS.md")
    pr.add_argument("repo", type=Path)
    pr.add_argument("--mode", choices=("auto", "llm", "deterministic"), default="auto")
    pr.add_argument("--dry-run", action="store_true")
    pr.set_defaults(func=cmd_portrait)

    ep = sub.add_parser("embed-probe", help="Smoke-probe local MLX / OpenAI API / hash embedding backend")
    ep.add_argument("repo", type=Path)
    ep.add_argument("--embedding-backend", choices=BACKEND_CHOICES, default="auto")
    ep.set_defaults(func=cmd_embed_probe)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (PtmGraphError, RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(f"[PtM Error] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

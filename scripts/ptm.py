#!/usr/bin/env python3
"""Unified CLI for Paths to Modernity (PtM) Four-Graph Infrastructure.

Commands:
  ptm.py build <repo>       Validate & build Intent, Spec, Plan (v4), Knowledge Debt, Scripts, Hebbian & Studio
  ptm.py status <repo>      Print compact project neighborhood status across all five graphs
  ptm.py query <repo> <q>   Run Dual-Path Retrieval (Base + Hebbian Spreading Flip) & reinforce cluster
  ptm.py related <repo> ... Agent-facing reverse lookup by existing node ID, draft file, or draft text
  ptm.py spec impact <repo> <SPEC-ID>     Preview cross-graph blast radius if a Spec is amended
  ptm.py triage <repo> ...  Record a 3-way technical disclosure choice (creating KD bookmark if needed)
  ptm.py kd impact <repo> <KD-ID>         Preview reorganization blast radius if KD is rejected
  ptm.py kd resolve <repo> <KD-ID> ...    Affirm or reject a KD bookmark & propagate reorganization
  ptm.py portrait <repo>    Synthesize subagent recovery portrait into AGENTS.md
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
    PtmGraphError,
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
)
from ptm_hebbian import HebbianAssociativeEngine  # noqa: E402
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
    federated = load_all_federated_graphs(repo)

    engine = HebbianAssociativeEngine(repo, backend=args.embedding_backend)
    heb_p = engine.sync_federated(federated)
    studio_path = build_studio_html(repo, federated, heb_p, title=args.title)

    print(
        f"[PtM] Built 5-graph ecosystem in {repo}\n"
        f"  Intent Graph    : {intent_p['node_count']} nodes, {intent_p['edge_count']} edges\n"
        f"  Spec Graph      : {spec_p['node_count']} specs, {spec_p['edge_count']} edges\n"
        f"  Plan Graph (v4) : {len(federated['plan'].get('nodes', []))} nodes, {len(federated['plan'].get('edges', []))} edges\n"
        f"  Knowledge Debt  : {kd_p['node_count']} bookmarks\n"
        f"  Scripts Graph   : {scripts_p['node_count']} modules, {scripts_p['edge_count']} AST edges\n"
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Validate & build all five graphs, Hebbian synapses, and Studio")
    b.add_argument("repo", type=Path)
    b.add_argument("--embedding-backend", choices=("auto", "mlx", "hash"), default="auto")
    b.add_argument("--title", default="PtM Five-Graph Curated Studio")
    b.add_argument("--with-portrait", action="store_true")
    b.add_argument("--portrait-mode", choices=("auto", "llm", "deterministic"), default="auto")
    b.set_defaults(func=cmd_build)

    s = sub.add_parser("status", help="Show compact multi-graph neighborhood digest")
    s.add_argument("repo", type=Path)
    s.set_defaults(func=cmd_status)

    q = sub.add_parser("query", help="Dual-Path retrieval (Base + Hebbian Spreading Flip)")
    q.add_argument("repo", type=Path)
    q.add_argument("query")
    q.add_argument("--top-k", type=int, default=5)
    q.add_argument("--max-flipped", type=int, default=4)
    q.add_argument("--embedding-backend", choices=("auto", "mlx", "hash"), default="auto")
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
    rel.add_argument("--embedding-backend", choices=("auto", "mlx", "hash"), default="auto")
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
    kdr.add_argument("--embedding-backend", choices=("auto", "mlx", "hash"), default="auto")
    kdr.set_defaults(func=cmd_kd)

    pr = sub.add_parser("portrait", help="Generate subagent recovery portrait into AGENTS.md")
    pr.add_argument("repo", type=Path)
    pr.add_argument("--mode", choices=("auto", "llm", "deterministic"), default="auto")
    pr.add_argument("--dry-run", action="store_true")
    pr.set_defaults(func=cmd_portrait)

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

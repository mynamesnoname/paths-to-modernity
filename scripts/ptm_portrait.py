#!/usr/bin/env python3
"""Subagent Project Portrait generator and `AGENTS.md` injector for PtM.

Synthesizes a compact Intent Portrait + Plan Portrait + Epistemic Watchlist from
the repository's federated graphs (`intent`, `plan`, `knowledge-debt`, `scripts`,
`hebbian`) and injects it into `AGENTS.md` inside dedicated markers:
`<!-- paths-to-modernity:portrait:start --> ... <!-- paths-to-modernity:portrait:end -->`.

Supports:
1. Isolated LLM subagent synthesis via OpenAI-compatible `.env` credentials
   (e.g. `BASE_URL=https://api.deepseek.com`, `MODEL=deepseek-flash`, `API_KEY=...`)
   using zero-dependency `urllib.request`.
2. Deterministic structured synthesis when `--mode deterministic` or offline.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, Mapping

PORTRAIT_START = "<!-- paths-to-modernity:portrait:start -->"
PORTRAIT_END = "<!-- paths-to-modernity:portrait:end -->"

SUBAGENT_SYSTEM_PROMPT = """You are an isolated Paths-to-Modernity (PtM) Recovery Portrait Subagent.
Given a compact JSON digest of a project's Intent Graph, Spec Graph (standing invariants, glossary,
standards, contracts), Plan Graph, Knowledge Debt bookmarks, Scripts Graph hubs, Formal Verification
status, Substantive Evaluations (`EVAL-###`), and Hebbian hubs, write a crisp, high-signal Markdown
summary (strictly <= 20 lines, no outer code fences, Chinese preferred when source titles/utterances
contain Chinese) with EXACTLY these four bullet sections:

- **意图画像 (Intent Portrait):** 2-3 concise clauses summarizing core user intents, resolved concept variants, and key experiential qualities.
- **常驻规范与术语 (Spec & Glossary Portrait):** active `SPEC-###` invariants (Do/Don't redlines), canonical glossary terms, and enforced contracts.
- **规划与验证画像 (Plan, Scripts & Verification Portrait):** active/ready pragmatic work (`LT/MT/ST/WP`), formal test receipt / stale hash warnings, core code hubs, and missing planned scripts.
- **评鉴关注、认知书签与关联枢纽 (Evaluations, Watchlist & Hubs):** any `EVAL-###` concerns/at-risk qualities, open `KD-###` technical bookmarks (and revisit triggers), plus top cross-graph Hebbian hubs.

Be factual, cite exact IDs (`INT-###`, `SPEC-###`, `WP-###`, `EVAL-###`, `KD-###`, file paths), never invent authorization, and keep every line dense and immediately useful after context compaction."""


def load_dotenv(env_paths: list[Path]) -> dict[str, str]:
    """Read `.env` style key-value pairs without third-party dependencies."""
    values: dict[str, str] = {}
    for p in env_paths:
        if not p.is_file():
            continue
        for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def resolve_llm_config(repo_root: Path, skill_root: Path) -> dict[str, str] | None:
    """Resolve `BASE_URL`, `MODEL`, `API_KEY` from env vars or `.env` files."""
    file_vars = load_dotenv([skill_root / ".env", repo_root / ".env"])
    api_key = (
        os.environ.get("PTM_PORTRAIT_API_KEY")
        or os.environ.get("API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or file_vars.get("API_KEY")
        or file_vars.get("OPENAI_API_KEY")
        or ""
    ).strip()
    if not api_key:
        return None
    base_url = (
        os.environ.get("PTM_PORTRAIT_BASE_URL")
        or os.environ.get("BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or file_vars.get("BASE_URL")
        or file_vars.get("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    ).strip()
    model = (
        os.environ.get("PTM_PORTRAIT_MODEL")
        or os.environ.get("MODEL")
        or file_vars.get("MODEL")
        or "gpt-4o-mini"
    ).strip()
    return {"base_url": base_url, "model": model, "api_key": api_key}


def build_portrait_digest(
    federated: Mapping[str, Any],
    hebbian_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    intents = [
        {
            "id": n["id"],
            "title": n["title"],
            "status": n["status"],
            "raw_utterance": n["raw_utterance"][:120],
            "concepts": [
                {
                    "name": c.get("name"),
                    "status": c.get("status"),
                    "selected_variant": c.get("selected_variant"),
                }
                for c in n.get("concepts", [])
            ],
            "qualities": n.get("qualities", []),
            "plan_refs": n.get("plan_refs", []),
        }
        for n in federated.get("intent", {}).get("nodes", [])
    ]

    specs = [
        {
            "id": s["id"],
            "title": s["title"],
            "kind": s["kind"],
            "status": s["status"],
            "enforcement": s["enforcement"],
            "canonical_term": s.get("canonical_term"),
            "forbidden_aliases": s.get("forbidden_aliases", []),
            "summary": s["summary"][:110],
        }
        for s in federated.get("specs", {}).get("nodes", [])
        if s.get("status") not in {"superseded", "deprecated"}
    ]

    plan_nodes = federated.get("plan", {}).get("nodes", [])
    plan_by_status: dict[str, list[str]] = {}
    for p in plan_nodes:
        plan_by_status.setdefault(p["status"], []).append(f"{p['id']} ({p['title']})")

    kds = [
        {
            "id": n["id"],
            "term": n["term"],
            "status": n["status"],
            "triage_mode": n["triage_mode"],
            "intent_refs": n["intent_refs"],
            "spec_refs": n.get("spec_refs", []),
            "plan_refs": n["plan_refs"],
            "revisit_when": n["revisit_when"][:100],
        }
        for n in federated.get("knowledge_debt", {}).get("nodes", [])
    ]

    scripts = federated.get("scripts", {}).get("nodes", [])
    top_scripts = sorted(scripts, key=lambda s: (-s.get("centrality", 0.0), s["path"]))[:5]
    missing_scripts = [s["path"] for s in scripts if s.get("status") == "planned_missing"]

    hubs = (hebbian_payload or {}).get("hubs", [])[:5]
    v_rep = federated.get("verification_report") or {}
    ep_mem = federated.get("episodic_memory") or {}
    eval_nodes = federated.get("evaluations", {}).get("nodes", [])
    eval_highlights = [
        {
            "id": e["id"],
            "title": e["title"],
            "verdict": e["verdict"],
            "perspective": e["perspective"],
            "at_risk_qualities": e.get("at_risk_qualities", [])[:2],
        }
        for e in eval_nodes
    ]

    return {
        "intents": intents,
        "specs": specs,
        "plan_counts": {k: len(v) for k, v in plan_by_status.items()},
        "active_or_ready_plans": (
            plan_by_status.get("in_progress", []) + plan_by_status.get("ready", [])
        )[:6],
        "done_plans": plan_by_status.get("done", [])[:5],
        "verification": {
            "overall_test_status": v_rep.get("overall_test_status", "unverified"),
            "passed_tests": v_rep.get("passed_tests", 0),
            "total_tests": v_rep.get("total_tests", 0),
            "stale_files": v_rep.get("global_stale_files", []),
            "spec_counts": v_rep.get("spec_counts", {}),
            "wp_counts": v_rep.get("wp_counts", {}),
        },
        "episodic_memory": {
            "turn_count": ep_mem.get("turn_count", 0),
            "span_count": ep_mem.get("span_count", 0),
            "thread_count": ep_mem.get("thread_count", 0),
            "folded_count": ep_mem.get("folded_count", 0),
            "active_threads": [
                {"id": t["id"], "title": t["title"]}
                for t in ep_mem.get("threads", [])
                if t.get("status") == "active"
            ][:3],
        },
        "evaluations": eval_highlights,
        "knowledge_debt": kds,
        "top_script_hubs": [
            {"path": s["path"], "role": s["role"], "centrality": s.get("centrality", 0.0)}
            for s in top_scripts
        ],
        "planned_missing_scripts": missing_scripts,
        "hebbian_hubs": [
            {"id": h["id"], "title": h["title"], "strength": h["associative_strength"]}
            for h in hubs
        ],
    }


def deterministic_portrait_body(digest: Mapping[str, Any]) -> str:
    intents = digest.get("intents", [])
    if intents:
        int_parts = [
            f"`{i['id']}` {i['title']} (`{i['status']}`)" for i in intents[:6]
        ]
        qualities = sorted(
            {q for i in intents for q in i.get("qualities", []) if q}
        )[:4]
        q_suffix = f"；核心体验品质：{'；'.join(qualities)}" if qualities else ""
        intent_line = f"- **意图画像 (Intent Portrait):** {' · '.join(int_parts)}{q_suffix}。"
    else:
        intent_line = "- **意图画像 (Intent Portrait):** 尚未建立持久化 `INT-###` 节点（见对话或 `plan/requirements/`）。"

    specs = digest.get("specs", [])
    if specs:
        sp_parts = [
            f"`{s['id']}` [{s['kind']}] {s['title']}"
            + (f"（标准词：`{s['canonical_term']}`）" if s.get("canonical_term") else "")
            for s in specs[:8]
        ]
        spec_line = f"- **常驻规范与术语 (Spec & Glossary Portrait):** {' · '.join(sp_parts)}。"
    else:
        spec_line = "- **常驻规范与术语 (Spec & Glossary Portrait):** 尚未沉淀独立 `SPEC-###` 节点。"

    p_counts = digest.get("plan_counts", {})
    count_str = ", ".join(f"{k}={v}" for k, v in sorted(p_counts.items())) or "无节点"
    active_p = ", ".join(digest.get("active_or_ready_plans", [])[:4]) or "暂无 ready/in_progress 节点"
    top_scr = ", ".join(f"`{s['path']}`" for s in digest.get("top_script_hubs", [])[:3]) or "无脚本"
    missing = digest.get("planned_missing_scripts", [])
    miss_str = f"；待落地脚本：{', '.join(f'`{m}`' for m in missing[:3])}" if missing else ""
    ver = digest.get("verification") or {}
    v_st = ver.get("overall_test_status", "unverified")
    stale_f = ver.get("stale_files") or []
    if stale_f:
        ver_str = f"；形式验证：源码已改待重测（{', '.join(f'`{x}`' for x in stale_f[:3])}）"
    elif v_st == "passed":
        ver_str = f"；形式验证：{ver.get('passed_tests', 0)}/{ver.get('total_tests', 0)} 用例通过且 SHA-256 指纹保鲜"
    elif v_st == "failed":
        ver_str = "；形式验证：存在失败用例待修复"
    else:
        ver_str = "；形式验证：尚未生成 `ptm.py verify` 回执"
    plan_line = (
        f"- **规划与验证画像 (Plan, Scripts & Verification Portrait):** 状态分布（{count_str}）；当前焦点：{active_p}；"
        f"核心代码枢纽：{top_scr}{miss_str}{ver_str}。"
    )

    evals = digest.get("evaluations") or []
    concern_evals = [e for e in evals if e.get("verdict") in {"concerns", "fail"}]
    ev_prefix = ""
    if concern_evals:
        ev_prefix = (
            "评鉴关注："
            + "；".join(
                f"`{e['id']}`({e['verdict']} · {e['perspective']})"
                for e in concern_evals[:2]
            )
            + " · "
        )
    elif evals:
        ev_prefix = f"内容评鉴：{len(evals)} 份已通过/选定 · "
    open_kds = [k for k in digest.get("knowledge_debt", []) if k["status"] == "open"]
    kd_str = (
        "；".join(f"`{k['id']}` {k['term']}（触发重审：{k['revisit_when']}）" for k in open_kds[:3])
        if open_kds
        else "当前无开放 `KD` 书签"
    )
    hubs = digest.get("hebbian_hubs", [])
    hub_items = ", ".join(f"`{h['id']}`({h['strength']:.2f})" for h in hubs[:3])
    hub_str = f"；赫布高连接枢纽：{hub_items}" if hubs else ""
    kd_line = f"- **评鉴关注、认知书签与关联枢纽 (Evaluations, Watchlist & Hubs):** {ev_prefix}{kd_str}{hub_str}。"

    return "\n".join([intent_line, spec_line, plan_line, kd_line])


def call_subagent_llm(digest: Mapping[str, Any], config: Mapping[str, str]) -> str:
    url = config["base_url"].rstrip("/") + "/chat/completions"
    payload = json.dumps(
        {
            "model": config["model"],
            "messages": [
                {"role": "system", "content": SUBAGENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": "Synthesize the recovery portrait for this project digest:\n"
                    + json.dumps(digest, ensure_ascii=False, indent=2),
                },
            ],
            "temperature": 0.2,
            "max_tokens": 2400,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    choice = data["choices"][0]
    content = (choice["message"].get("content") or "").strip()
    if choice.get("finish_reason") == "length" or len(content) < 80:
        raise ValueError("LLM portrait output truncated or incomplete")
    if content.startswith("```"):
        lines = [ln for ln in content.splitlines() if not ln.strip().startswith("```")]
        content = "\n".join(lines).strip()
    return content


def render_portrait_block(
    digest: Mapping[str, Any],
    *,
    mode: str = "auto",
    repo_root: Path,
    skill_root: Path,
) -> tuple[str, str]:
    """Return `(marked_block, generator_label)`."""
    generator = "deterministic"
    body = ""
    if mode in {"auto", "llm"}:
        cfg = resolve_llm_config(repo_root, skill_root)
        if cfg is not None:
            try:
                body = call_subagent_llm(digest, cfg)
                generator = f"subagent-llm:{cfg['model']}"
            except (OSError, urllib.error.URLError, KeyError, ValueError) as exc:
                if mode == "llm":
                    raise RuntimeError(f"LLM subagent portrait call failed: {exc}") from exc
                body = ""
        elif mode == "llm":
            raise RuntimeError(
                "LLM portrait mode requested, but no API_KEY found in environment or .env"
            )

    if not body:
        body = deterministic_portrait_body(digest)
        generator = "deterministic"

    today = date.today().isoformat()
    block = "\n".join(
        [
            PORTRAIT_START,
            f"<!-- generated: {today} | synthesizer: {generator} -->",
            "### Project Recovery Portrait (Generated — Do Not Hand-Edit)",
            "",
            body.strip(),
            "",
            "- **快速恢复入口 (Quick Routes):** 意图 `_aiHumanInteract/intent/structure/graph.json` · "
            "规范 `_aiHumanInteract/specs/structure/graph.json` · "
            "规划 `_aiHumanInteract/plan/structure/graph.json` · "
            "知识债 `_aiHumanInteract/knowledge-debt/structure/graph.json` · "
            "脚本 `_aiHumanInteract/scripts/structure/graph.json` · "
            "工作台 `_aiHumanInteract/studio/index.html` · "
            "会话断点 `_aiHumanInteract/state/active.md`",
            PORTRAIT_END,
        ]
    )
    return block, generator


def update_agents_portrait(
    repo_root: Path,
    block: str,
) -> Path:
    """Insert or replace the `portrait:start..end` block in `<repo_root>/AGENTS.md`."""
    agents_path = repo_root.resolve() / "AGENTS.md"
    current = agents_path.read_text(encoding="utf-8") if agents_path.is_file() else ""

    if PORTRAIT_START in current and PORTRAIT_END in current:
        start = current.index(PORTRAIT_START)
        end = current.index(PORTRAIT_END, start) + len(PORTRAIT_END)
        updated = current[:start] + block + current[end:]
    else:
        sep = "\n\n" if current.strip() else ""
        updated = current.rstrip() + sep + block + "\n"

    agents_path.write_text(updated, encoding="utf-8")
    return agents_path

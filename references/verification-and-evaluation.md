# Verification & Evaluation (`ptm.py verify` & `evaluations/EVAL-###.md`)

Read this reference when running formal test verification, auditing whether
code changes have invalidated prior test receipts, or guiding an isolated
perspective subagent to evaluate experiential qualities, spec compliance, and
implementation alternatives.

## Why Formal Validation and Content Evaluation Must Be Separate Tracks

Software and research projects fail in two orthogonal ways:

1. **Formal regression ("Built the thing wrong"):** A contract, postcondition,
   type boundary, or state transition breaks — or source code changes after a
   test was run while the plan still claims `done`. LLM prose assertions must
   never certify formal correctness; **deterministic execution + content-hash
   freshness** owns this track.
2. **Substantive drift ("Built the wrong thing"):** Every unit test passes, yet
   the UI re-introduces friction, violates a standing `SPEC-###` guardrail, or
   quietly sacrifices an `Intent`'s experiential `qualities` (e.g., *"feels
   like turning a physical instrument knob rather than dismissing popups"*).
   Deterministic unit tests cannot judge experiential qualities, while **in-place
   self-review by the coding agent suffers from confirmation bias**. **Context-separated
   perspective evaluation (`EVAL-###`)** owns this track.

Paths to Modernity integrates both tracks directly onto the existing 3-stratum,
5-graph architecture (`Intent`, `Spec`, `Plan`, `Knowledge Debt`, `Scripts`)
without introducing redundant top-level graphs:

| Dimension | Formal Validation (形式验证) | Content Evaluation (内容评鉴) |
|---|---|---|
| **Core question** | Do deterministic tests pass on the *exact current bytes* of governed code? | Does the deliverable honor `Intent.qualities`, `raw_utterance`, and `SPEC` guardrails from an explicit user/domain perspective? |
| **Authority** | `scripts/ptm.py verify <repo>` (test runner exit code + SHA-256 file hashes) | Isolated perspective subagent (`research` / `browser`) and/or human decision owner |
| **Artifact on disk** | `_aiHumanInteract/scripts/verification-status.json` (generated receipt; never hand-edited) | `_aiHumanInteract/plan/evaluations/EVAL-###.md` (editable structured front-matter Markdown) |
| **Freshness & lifecycle** | `verified` → automatically downgrades to `stale` the instant any governed code/test SHA-256 changes | `pass \| selected_winner \| concerns \| fail` (linked across `INT`, `SPEC`, `WP`, `SCR`) |

---

## Track 1: Formal Validation & Content-Hash Staleness (`ptm.py verify`)

### Running Formal Verification

```bash
# Auto-discover and run Python unittest suite, record SHA-256 hashes, and refresh Studio
python3 -B scripts/ptm.py verify /path/to/repo

# Or run a custom project test command (pytest, npm test, cargo test, etc.)
python3 -B scripts/ptm.py verify /path/to/repo --cmd "pytest -q"
```

`ptm.py verify` executes the test runner in `<repo>`, captures exit code, pass/fail
counts, and computes the **SHA-256 content digest** of every source and test file
indexed by the Scripts Graph, writing `_aiHumanInteract/scripts/verification-status.json`
(`paths-to-modernity-verification-receipt-v1`).

### Automatic Staleness Downgrade (`verified` → `stale`)

Unlike filesystem `mtime` (which fluctuates across `git checkout` or branch
switches), SHA-256 digests track exact byte identity:

- **`verified` (`✓ 实测`)**: Governing test scripts passed in the latest receipt,
  all governed code files exist on disk, and **every governed code file + test
  script has the exact same SHA-256 hash** as when the receipt was recorded.
- **`stale` (`⟳ 待测`)**: A prior receipt passed, **but at least one governed
  source file or test file has changed its SHA-256 digest since that run**. The
  agent must re-run `ptm.py verify` before claiming completion.
- **`failing` (`✕ 失败`)**: The latest test execution exited non-zero or failed
  on a governing test script.
- **`partial` (`◐ 部分`)**: On higher-level `LT/MT/ST` plan scopes where some
  child nodes are `verified` while sibling branches remain `unverified`.
- **`unverified` (`○ 未测`)**: No verification test script is declared, a planned
  target file is still missing (`planned_missing`), or `ptm.py verify` has not
  yet been executed. (Purely aesthetic or conceptual `SPEC` standards without
  unit tests naturally rely on Track 2 `EVAL-###` reviews instead.)

---

## Track 2: Substantive Content Evaluation (`evaluations/EVAL-###.md`)

### Protocol for Guiding Agents: Mandatory Context Separation

When an implementation step finishes or consequential alternatives are compared,
follow this four-step protocol:

1. **Never self-certify qualities in the coding context.** The agent that just
   authored `src/...` or `web/...` is anchored on its own implementation effort
   and must not grade subjective `Intent.qualities` in the same trace.
2. **Choose concrete review perspectives (`references/model.md`).** Name the
   exact stakeholder or technical lens — for example, *"高频光谱实验员直接操作视角"*
   or *"跨会话多人协作数据审计视角"* — never generic "code review".
3. **Invoke an isolated perspective subagent (`research` or `browser`).**
   Pass the subagent **only**:
   - The originating `Intent`'s verbatim `raw_utterance` and `qualities`;
   - Governing `SPEC-###` invariants, glossary terms (`canonical_term` /
     `forbidden_aliases`), and standards (`do_rules` / `dont_rules`);
   - The explicit `perspective` to inhabit;
   - Paths to the runnable artifact, UI URL/screenshot, or code modules under
     review (omit implementation excuses).
   For visual UI or interactive workflows, prefer a `browser` subagent that
   operates and screenshots the live page ("physical rotation") rather than
   reading static CSS/HTML strings.
4. **Persist the unvarnished critique as `EVAL-###.md` and route `concerns`.**
   Scaffold or write `_aiHumanInteract/plan/evaluations/EVAL-###.md` via
   `ptm.py eval scaffold`, explicitly listing both `preserved_qualities` and
   `at_risk_qualities`. When `verdict` is `concerns` or `fail`:
   - If it exposes an unresolved technical trade-off, link or update a `KD-###`
     bookmark (`revisit_when`);
   - If it affects user experience, scope, or values, surface the finding to the
     human **decision owner** rather than silently papering over it.

### Source-of-Truth Schema (`_aiHumanInteract/plan/evaluations/EVAL-###.md`)

`EVAL-###.md` uses the same single-line JSON-value front matter as Intent, Spec,
and Plan Graph v4 nodes, remaining 100% compatible with Plan Graph v4's
`links.evaluation` path checks (`validate.py`). Legacy plain-Markdown files in
`evaluations/` without front matter remain tolerated as `legacy_note` records.

```yaml
---
id: "EVAL-003"
title: "跨会话谱峰键值存储与多协作者审计边界评鉴"
kind: "spec_audit"
verdict: "concerns"
perspective: "科研协作数据可靠性与可审计视角"
reviewer_mode: "isolated_subagent"
updated: "2026-11-26"
summary: "单文件键值快照完全满足单人秒级恢复品质且严守 PeakHandle 术语，但缺乏并发覆写冲突留痕。"
evaluates_intents: ["INT-003"]
evaluates_specs: ["SPEC-002"]
evaluates_plans: ["WP-004", "WP-005"]
evaluates_scripts: ["src/spectral_store.py"]
preserved_qualities: ["恢复上下文轻快透明，不引入笨重的运维负担", "全链路统一采用 PeakHandle (PK-###) 稳定标识"]
at_risk_qualities: ["多人异步修改同一 PK-### 备注时无法回放中间覆盖历史（受 KD-002 书签监控）"]
evidence_refs: ["src/spectral_store.py", "_aiHumanInteract/knowledge-debt/nodes/KD-002.md"]
recommended_action: "首期维持轻量快照并在 KD-002 保持观察；一旦出现双人协作覆写实证立即触发 WP-005 重审。"
---
```

### Field Reference

- **Required fields:**
  - `id`: `EVAL-###` matching filename `EVAL-###.md`
  - `title`: non-empty string
  - `kind`: `alternative_comparison | quality_review | prototype_critique | spec_audit`
  - `verdict`: `pass | selected_winner | concerns | fail`
  - `perspective`: explicit review lens string
  - `reviewer_mode`: `isolated_subagent | browser_subagent | human_owner | joint`
  - `updated`: `YYYY-MM-DD`
  - `summary`: 1–2 sentence core finding
- **Target & quality arrays:**
  - `evaluates_intents` (`INT-###`), `evaluates_specs` (`SPEC-###`),
    `evaluates_plans` (`LT/MT/ST/WP-###`), `evaluates_scripts` (repo-relative paths)
  - `preserved_qualities`: qualities verified as intact
  - `at_risk_qualities`: qualities strained, traded off, or violated
  - `evidence_refs`: repo-relative paths to prototypes (`.svg`), screenshots,
    code, or bookmarks
  - `recommended_action` (optional string)

### CLI Commands

```bash
# Scaffold a new structured evaluation record
python3 -B scripts/ptm.py eval scaffold /path/to/repo \
  --title "直接画布零弹窗品质独立审阅" \
  --kind quality_review \
  --verdict pass \
  --perspective "高频光谱实验员直接操作视角" \
  --reviewer-mode isolated_subagent \
  --summary "主画布点击谱峰与侧栏三态分拣全程零模态打断。" \
  --intents INT-001,INT-002 \
  --specs SPEC-001,SPEC-003 \
  --plans WP-001

# List all evaluations and verification health
python3 -B scripts/ptm.py eval list /path/to/repo
```

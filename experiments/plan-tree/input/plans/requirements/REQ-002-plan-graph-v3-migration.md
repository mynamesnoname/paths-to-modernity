# REQ-002 — Align FORMA planning with paths-to-modernity

## Raw request

> 请根据该skill的规范，重构 _plan 。目前本项目里最基础的plan被命名为了MP-xxx，这和skill不符。请用skill的规范重塑整体链条

The user explicitly invoked `paths-to-modernity` and supplied its Plan Graph v3 contract in the conversation on 2026-10-08.

## Scope and decision

- Inside: migrate the entire `_aiHumanInteract/plan` hierarchy and source schema to LT → MT → ST → WP; align references, validation, generation, tests, governance, and navigation views with v3.
- Outside: scientific runtime implementation and changes to scientific plan priorities or acceptance outcomes.
- Interfaces: `AGENTS.md`, plan consumers reading `structure/graph.json`, repository files linked from plans, and the separate runtime Evidence Graph.
- Decision owner: repository user for this migration request. The supplied v3 contract determines the target; the old node statuses and typed relationships remain intact unless a v3 rule makes a relation invalid.
- Review finding: historical WP-016 and WP-017 do not share an identical objective, so their old variant relation cannot become `alternative_of`. The comparison and supersession remain in the evaluation and source nodes.

## Acceptance boundary

A fresh reader can traverse the four levels via a v3 versioned graph, follow every WP to its source and evidence, and validate and regenerate all views with the documented commands. The old MP-to-WP mapping remains recoverable in `_aiHumanInteract/plan/migration.md`.

# Scripts Graph (Codebase Structure & Coverage)

Generated from repository source AST & static analysis by `scripts/ptm.py`.

```mermaid
flowchart LR
    S_0["src/event_replay_audit.py<br/>planned_target · 0 LOC"]
    S_1["src/spectral_store.py<br/>module · 15 LOC"]
    S_2["src/triage_gate.py<br/>module · 10 LOC"]
    S_3["src/workbench_api.py<br/>entrypoint · 21 LOC"]
    S_4["tests/test_workbench.py<br/>test · 10 LOC"]
    S_5["web/SpectralCanvas.ts<br/>module · 5 LOC"]
    S_3 -->|imports| S_1
    S_3 -->|imports| S_2
    S_4 -->|imports| S_3
    S_3 -.->|invokes| S_1
    S_3 -.->|invokes| S_2
    S_4 -.->|invokes| S_3
```

## Module Inventory (Ranked by Structural Centrality)

| Path | Language | Role | Status | LOC | Centrality | Plans | Summary |
|---|---|---|---|---:|---:|---|---|
| `src/workbench_api.py` | `python` | `entrypoint` | `clean` | 21 | 1.000 | LT-001, WP-001, WP-006 | Main workbench entrypoint coordinating spectral features and non-blocking triage. |
| `src/spectral_store.py` | `python` | `module` | `clean` | 15 | 0.966 | MT-002, ST-002, WP-004 | Persistent addressable store for spectral peak features and annotations. |
| `src/triage_gate.py` | `python` | `module` | `clean` | 10 | 0.966 | MT-001, ST-001, WP-002, WP-006 | Three-way technical disclosure gate and reversible prototype scope checker. |
| `src/event_replay_audit.py` | `python` | `planned_target` | `planned_missing` | 0 | 0.540 | MT-002, ST-002, WP-005 | Planned in Plan/Spec Graph; file not yet created on disk. |
| `tests/test_workbench.py` | `python` | `test` | `clean` | 10 | 0.540 | WP-001, WP-004, WP-006 | Verify spectral workbench session and 3-way technical triage. |
| `web/SpectralCanvas.ts` | `typescript` | `module` | `clean` | 5 | 0.540 | MT-001, ST-001, WP-001 | Direct-manipulation spectral feature canvas without modal interruptions |

# WP-045 ELG type graph implementation check — 2026-10-17

## Scope

Implemented the current ELG Canvas as branch-local code nodes E0–E5 in `src/FORMA/agentic_graph/elg_path.py`. The runner reads frozen SH/VI inputs, the active-branch FA registry and the recomputed cleaned line view. Node artifacts and the deterministic ELG report use allocated execution IDs, source digests and reasoning-tree events. The offline trace entry point is `evaluation/agentic_graph/run_elg_paths.py`.

An adopted `[Ne V]` pairing creates a `type_graph_handoff` event with route history and passes the same hypothesis/redshift to QSO Q2. The QSO entry verifies the active ELG route artifact, transfer event and exact adopted measurement before granting its existing project-specific Type 2 exit. The QSO Q11 context retains the ELG initial type and handoff source. A child branch forked at the handoff event can continue QSO without changing its parent.

Ca K/H and mask-aware Dn4000 are recorded as consultation findings. The existing ontology states that Dn4000 is not a hard class veto, so neither finding automatically changes ELG to LRG/BGS. `[O III]` A requires two adopted component pairings; `[O II]` B requires its adopted pairing. Pending, unreviewable and unpaired claims remain unknown. The Canvas' `failure` exit cannot be reached from those unknown values alone.

## Verification

- `PYTHONPATH=src:tests/agentic_graph /home/user/apps/miniconda3/envs/forma/bin/python -B -m unittest tests.agentic_graph.test_elg_path -q`: nine tests passed. They cover `[O II]` and `[O III]` survival, duplicate [O III] measurement rejection, Dn4000 advisory and masked-band behavior, unknown emission evidence, exact `[Ne V]` handoff, inherited handoff after a fork, QSO Q11 source binding, source tamper rejection, parent-branch preservation and offline trace export. The Q11 test uses a deterministic fake model.
- `PYTHONPATH=src:tests/agentic_graph /home/user/apps/miniconda3/envs/forma/bin/python -B -m unittest discover -s tests/agentic_graph -p 'test_*.py' -q`: 86 tests passed.
- `PYTHONPATH=src:tests/agentic_graph /home/user/apps/miniconda3/envs/forma/bin/python -B -m unittest discover -s tests -t . -p 'test_*.py' -q`: 820 tests passed, 9 skipped before the final duplicate-measurement guard was added; that guard and its new test passed in the focused and agentic-graph suites. No live LLM call was made for this change.

## Limits

The available archived new-path SH+FA samples are QSO_4 (two Type 2 QSO, four null) and QSO_116 (one Type 1 QSO); none has a real `ELG` preliminary classification. The current evidence is synthetic integration and regression testing, not a real ELG spectrum replay or independent classification validation. The graph-wide orchestrator is still absent, and the ELG entry currently accepts only ELG preliminary classifications, not incoming transfers from another type graph. The Ca K/H/Dn4000 hard transfer, a demonstrable two-line `no/no` failure gate and an ELG report format beyond the deterministic record remain open scientific and product decisions in `agenticGraphReasoningDesign/graphsOfEachType/ELG.md`.

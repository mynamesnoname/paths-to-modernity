---
id: "EVAL-001"
title: "显式三态分拣闸门 vs. 启发式静默跳过对比评鉴"
kind: "alternative_comparison"
verdict: "selected_winner"
perspective: "认知心理学与高频光谱实验员视角"
reviewer_mode: "joint"
updated: "2026-11-24"
summary: "对照两份认知原型后确认：侧栏三态分拣（WP-002）既保持画布视线连续，又为未知技术保留可推翻的 KD 书签；静默黑盒跳过（WP-003）剥夺知情权且导致后期无法定向反悔。"
evaluates_intents: ["INT-001", "INT-002"]
evaluates_specs: ["SPEC-001", "SPEC-004"]
evaluates_plans: ["WP-002", "WP-003"]
evaluates_scripts: ["src/triage_gate.py"]
preserved_qualities: ["操作科学对象应像拨动实体仪器一样直接连贯，不退化为管理弹窗", "诚实记录未知，绝不把沉默或顺从伪装成技术背书"]
at_risk_qualities: []
evidence_refs: ["_aiHumanInteract/intent/prototypes/direct-canvas.svg", "_aiHumanInteract/intent/prototypes/modal-queue.svg"]
recommended_action: "选定 WP-002 作为正式技术分拣路径，将 WP-003 标记为 superseded。"
---

# EVAL-001 · 三态分拣闸门与黑盒静默跳过方案比选

基于共享目标基线对比 `WP-002` 与 `WP-003`，结合 `direct-canvas.svg` / `modal-queue.svg` 物理旋转实验完成裁决。

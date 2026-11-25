---
id: "SPEC-001"
title: "核心光谱画布零模态阻塞与显式授权铁律"
kind: "invariant"
status: "enforced"
enforcement: "must_not"
updated: "2026-11-24"
summary: "光谱分析主画布严禁弹出阻断式技术确认弹窗，且沉默或超时绝不视同技术授权。"
parent: null
depends_on: []
enables: []
validates: []
supersedes: []
conflicts_with: []
canonical_term: null
forbidden_aliases: []
do_rules: ["所有底层技术声明必须以非阻塞侧栏或内联条呈现", "谱峰选中、对比与标注必须在主画布单步直达"]
dont_rules: ["严禁在光谱曲线上方弹出遮挡视线的分步 Agree 审批队列", "严禁将用户未回复或默认回车当作知情同意"]
signature_or_schema: null
postconditions: []
intent_refs: ["INT-001", "INT-002"]
plan_refs: ["LT-001", "WP-001", "WP-002"]
knowledge_debt_refs: []
governs_scripts: ["web/SpectralCanvas.ts", "src/workbench_api.py"]
verified_by_scripts: ["tests/test_workbench.py"]
---

# SPEC-001 · 核心光谱画布零模态阻塞铁律

由 `INT-001` 与认知原型对比实验固化而成的顶层常驻红线。

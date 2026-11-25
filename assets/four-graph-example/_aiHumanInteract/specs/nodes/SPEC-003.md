---
id: "SPEC-003"
title: "建筑极简柔和视觉与模块单向解耦开发标准"
kind: "standard"
status: "enforced"
enforcement: "must"
updated: "2026-11-24"
summary: "界面遵循暖灰纸感低视觉疲劳色板，后端存储模块与分拣模块保持单向零循环依赖。"
parent: "SPEC-001"
depends_on: []
enables: []
validates: []
supersedes: ["SPEC-005"]
conflicts_with: []
canonical_term: null
forbidden_aliases: []
do_rules: ["界面背景采用暖灰纸张色 (#F6F6F4) 与低饱和度语义色", "由上层会话入口 (workbench_api.py) 单向组合存储层与分拣层"]
dont_rules: ["严禁引入高饱和荧光色或闪烁动画干扰谱线判读", "严禁在 spectral_store.py 与 triage_gate.py 之间产生相互 import"]
signature_or_schema: null
postconditions: []
intent_refs: ["INT-001"]
plan_refs: ["MT-001", "ST-001"]
knowledge_debt_refs: []
governs_scripts: ["web/SpectralCanvas.ts", "src/spectral_store.py", "src/triage_gate.py"]
verified_by_scripts: []
---

# SPEC-003 · 视觉与模块分层开发标准

替代早期允许黑盒隐式吞没规则的 `SPEC-005`。

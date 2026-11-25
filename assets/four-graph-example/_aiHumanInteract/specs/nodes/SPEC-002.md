---
id: "SPEC-002"
title: "统一谱峰可寻址标识词典 (PeakHandle)"
kind: "glossary"
status: "enforced"
enforcement: "canonical_term"
updated: "2026-11-24"
summary: "全栈代码、持久化存储与人机对话统一使用 PeakHandle (PK-###) 指代可寻址谱峰，严禁同义词混用。"
parent: "SPEC-001"
depends_on: []
enables: ["SPEC-003"]
validates: []
supersedes: []
conflicts_with: []
canonical_term: "PeakHandle (PK-###)"
forbidden_aliases: ["WaveItem", "LineCursor", "PeakIdx"]
do_rules: ["前后端接口与持久层统一采用 PeakHandle 命名及 PK-### 稳定格式 ID"]
dont_rules: ["严禁在模块中自造 WaveItem、LineCursor、PeakIdx 等同义混名", "严禁拿裸波长浮点数或数组下标充当跨会话主键"]
signature_or_schema: null
postconditions: []
intent_refs: ["INT-003"]
plan_refs: ["MT-002", "WP-004"]
knowledge_debt_refs: []
governs_scripts: ["src/spectral_store.py", "web/SpectralCanvas.ts"]
verified_by_scripts: ["tests/test_workbench.py"]
---

# SPEC-002 · 统一领域术语表：PeakHandle

消除前后端与对话中的概念漂移。

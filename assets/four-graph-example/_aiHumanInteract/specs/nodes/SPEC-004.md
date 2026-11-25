---
id: "SPEC-004"
title: "三态技术分拣闸门与知识债状态机契约"
kind: "contract"
status: "enforced"
enforcement: "must"
updated: "2026-11-24"
summary: "规定 classify_disclosure 输入输出契约及知识债 open -> affirmed | rejected 状态流转后置条件。"
parent: "SPEC-001"
depends_on: ["SPEC-002"]
enables: []
validates: ["SPEC-001"]
supersedes: []
conflicts_with: ["SPEC-005"]
canonical_term: null
forbidden_aliases: []
do_rules: []
dont_rules: []
signature_or_schema: "classify_disclosure(term: str, choice: 'understood_agreed' | 'not_understood_prototype' | 'disagreed_counterproposal') -> {term: str, choice: str, bookmark: bool}"
postconditions: ["当且仅当 choice == 'not_understood_prototype' 时返回 bookmark == True", "遇到未知 choice 枚举必须立即抛出 ValueError，严禁静默降级为同意", "关联 KD 书签状态仅允许 open -> affirmed | rejected 显式重审迁移"]
intent_refs: ["INT-002", "INT-005"]
plan_refs: ["WP-002", "WP-006"]
knowledge_debt_refs: ["KD-001", "KD-002"]
governs_scripts: ["src/triage_gate.py", "src/workbench_api.py"]
verified_by_scripts: ["tests/test_workbench.py"]
---

# SPEC-004 · 三态分拣与书签契约

由 `tests/test_workbench.py` 持续自动化验证。

#!/usr/bin/env python3
"""Seed the canonical Four-Graph Worked Example (`assets/four-graph-example/`)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
from ptm_core import format_front_matter  # noqa: E402


SVG_DIRECT_CANVAS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 146">
  <rect width="380" height="146" rx="8" fill="#F6F6F4" stroke="#CFD6DE"/>
  <text x="14" y="21" font-family="sans-serif" font-size="10.5" font-weight="700" fill="#1F5A52">Epistemic Prototype A · 直接画布操作 + 侧栏非阻塞三态声明 (Selected)</text>
  <rect x="14" y="30" width="236" height="82" rx="6" fill="#FFFFFF" stroke="#9CCFC7" stroke-width="1.4"/>
  <polyline points="24,96 56,88 84,54 114,90 148,68 184,42 212,90 238,85" fill="none" stroke="#3B7A8C" stroke-width="2"/>
  <circle cx="84" cy="54" r="4.5" fill="#1F5A52"/>
  <circle cx="184" cy="42" r="4.5" fill="#6E5DC6"/>
  <rect x="34" y="35" width="98" height="14" rx="3" fill="#EAF7F5"/>
  <text x="39" y="45" font-family="monospace" font-size="8.8" font-weight="600" fill="#1F5A52">Peak-412nm [Active]</text>
  <rect x="258" y="30" width="108" height="82" rx="6" fill="#FDF6E7" stroke="#E2C285"/>
  <text x="266" y="47" font-family="sans-serif" font-size="9.5" font-weight="700" fill="#7A5213">三态技术声明</text>
  <rect x="266" y="55" width="92" height="15" rx="3" fill="#EDF7F0"/><text x="271" y="66" font-family="sans-serif" font-size="8.5" fill="#234B36">✓ 理解且同意</text>
  <rect x="266" y="74" width="92" height="15" rx="3" fill="#FFF4DC" stroke="#D9A648"/><text x="271" y="85" font-family="sans-serif" font-size="8.5" fill="#7A5213">★ 暂存KD先做原型</text>
  <rect x="266" y="93" width="92" height="14" rx="3" fill="#FCEEEE"/><text x="271" y="103" font-family="sans-serif" font-size="8.5" fill="#873535">✕ 否决并提方案</text>
  <text x="14" y="131" font-family="sans-serif" font-size="10" fill="#52606D">物理旋转结论：视线不离开光谱曲线，未理解技术一键挂入 KD 书签不打断心流。</text>
</svg>
"""

SVG_MODAL_QUEUE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 380 146">
  <rect width="380" height="146" rx="8" fill="#F6F6F4" stroke="#CFD6DE"/>
  <text x="14" y="21" font-family="sans-serif" font-size="11" font-weight="700" fill="#873F3F">Epistemic Prototype B · 传统阻塞弹窗逐条审批 (Rejected after seeing)</text>
  <rect x="14" y="30" width="352" height="82" rx="6" fill="#E6E9EC"/>
  <rect x="74" y="38" width="232" height="66" rx="6" fill="#FFFFFF" stroke="#E0ACAC" stroke-width="1.5"/>
  <text x="88" y="56" font-family="sans-serif" font-size="10" font-weight="700" fill="#873F3F">Confirm Technical Step (4 of 11)?</text>
  <text x="88" y="72" font-family="sans-serif" font-size="9" fill="#616E7C">Use CQRS Event-Sourced Snapshot Store? (Recommended)</text>
  <rect x="88" y="81" width="66" height="16" rx="4" fill="#31577D"/><text x="103" y="92" font-family="sans-serif" font-size="9" fill="#FFF">Agree</text>
  <text x="14" y="131" font-family="sans-serif" font-size="10" fill="#873F3F">问题暴露：遮挡工作区并诱导机械点击 Agree（伪审查）。</text>
</svg>
"""


def seed_example(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)

    # 1. Adopt protocol + Install Plan Graph v4 bundle cleanly
    subprocess.run(
        [sys.executable, "-B", str(SKILL_ROOT / "scripts" / "adopt_project.py"), str(target)],
        check=True,
    )
    subprocess.run(
        [sys.executable, "-B", str(SKILL_ROOT / "scripts" / "install_plan_graph.py"), str(target), "--update-agents"],
        check=True,
    )

    # 2. Seed realistic source code for Scripts Graph AST extraction
    (target / "src").mkdir(exist_ok=True)
    (target / "web").mkdir(exist_ok=True)
    (target / "tests").mkdir(exist_ok=True)

    (target / "src" / "spectral_store.py").write_text(
        '"""Persistent addressable store for spectral peak features and annotations."""\n\n'
        "from __future__ import annotations\n\n"
        "class SpectralFeatureStore:\n"
        "    def __init__(self) -> None:\n"
        "        self._features: dict[str, dict] = {}\n\n"
        "    def upsert_peak(self, feature_id: str, wavelength_nm: float, note: str = '') -> dict:\n"
        "        rec = {'id': feature_id, 'wavelength_nm': wavelength_nm, 'note': note}\n"
        "        self._features[feature_id] = rec\n"
        "        return rec\n\n"
        "    def get_peak(self, feature_id: str) -> dict | None:\n"
        "        return self._features.get(feature_id)\n",
        encoding="utf-8",
    )

    (target / "src" / "triage_gate.py").write_text(
        '"""Three-way technical disclosure gate and reversible prototype scope checker."""\n\n'
        "from __future__ import annotations\n\n"
        "ALLOWED_TRIAGE = {'understood_agreed', 'not_understood_prototype', 'disagreed_counterproposal'}\n\n"
        "def classify_disclosure(term: str, choice: str) -> dict:\n"
        "    if choice not in ALLOWED_TRIAGE:\n"
        "        raise ValueError(f'Invalid choice: {choice}')\n"
        "    return {'term': term, 'choice': choice, 'bookmark': choice == 'not_understood_prototype'}\n",
        encoding="utf-8",
    )

    (target / "src" / "workbench_api.py").write_text(
        '"""Main workbench entrypoint coordinating spectral features and non-blocking triage."""\n\n'
        "from __future__ import annotations\n"
        "from src.spectral_store import SpectralFeatureStore\n"
        "from src.triage_gate import classify_disclosure\n\n"
        "class WorkbenchSession:\n"
        "    def __init__(self) -> None:\n"
        "        self.store = SpectralFeatureStore()\n\n"
        "    def inspect_and_tag(self, fid: str, nm: float, tech_choice: str) -> dict:\n"
        "        peak = self.store.upsert_peak(fid, nm)\n"
        "        gate = classify_disclosure('Hebbian Associative Index', tech_choice)\n"
        "        return {'peak': peak, 'triage': gate}\n\n"
        "def main() -> None:\n"
        "    session = WorkbenchSession()\n"
        "    session.inspect_and_tag('PK-412', 412.5, 'not_understood_prototype')\n\n"
        "if __name__ == '__main__':\n"
        "    main()\n",
        encoding="utf-8",
    )

    (target / "web" / "SpectralCanvas.ts").write_text(
        "// Direct-manipulation spectral feature canvas without modal interruptions\n"
        "export interface PeakHandle { id: string; wavelengthNm: number; selected: boolean; }\n"
        "export function selectPeakDirectly(handles: PeakHandle[], id: string): PeakHandle[] {\n"
        "  return handles.map(h => ({ ...h, selected: h.id === id }));\n"
        "}\n",
        encoding="utf-8",
    )

    (target / "tests" / "test_workbench.py").write_text(
        '"""Verify spectral workbench session and 3-way technical triage."""\n\n'
        "import unittest\n"
        "from src.workbench_api import WorkbenchSession\n\n"
        "class WorkbenchTests(unittest.TestCase):\n"
        "    def test_provisional_bookmark_flow(self) -> None:\n"
        "        ws = WorkbenchSession()\n"
        "        out = ws.inspect_and_tag('PK-001', 532.0, 'not_understood_prototype')\n"
        "        self.assertTrue(out['triage']['bookmark'])\n",
        encoding="utf-8",
    )

    # 3. Seed Utterance & Epistemic Prototypes + Intent Graph
    int_root = target / "_aiHumanInteract" / "intent"
    (int_root / "utterances").mkdir(parents=True, exist_ok=True)
    (int_root / "prototypes").mkdir(parents=True, exist_ok=True)
    (int_root / "nodes").mkdir(parents=True, exist_ok=True)

    (int_root / "utterances" / "UTT-001.md").write_text(
        "# UTT-001 · 初始对话原话记录\n\n"
        "> 用户（2026-11-24）：“我想让这个科学光谱 Agent 更快，像在实验台上直接拨动旋钮看谱线一样顺手；"
        "另外遇到我不懂的底层算法别让我一直盲目点 Agree，先记下来把原型跑通，等我看到效果再决定留不留。”\n",
        encoding="utf-8",
    )
    (int_root / "prototypes" / "direct-canvas.svg").write_text(SVG_DIRECT_CANVAS, encoding="utf-8")
    (int_root / "prototypes" / "modal-queue.svg").write_text(SVG_MODAL_QUEUE, encoding="utf-8")

    intents = [
        (
            {
                "id": "INT-001",
                "title": "让科学光谱 Agent 交互更快且具备直接操作感",
                "status": "crystallized",
                "updated": "2026-11-24",
                "raw_utterance": "我想让这个科学光谱 Agent 更快，像在实验台上直接拨动旋钮看谱线一样顺手。",
                "utterance_ref": "_aiHumanInteract/intent/utterances/UTT-001.md",
                "parent": None,
                "refines": [],
                "branches_from": [],
                "constrains": [],
                "supersedes": [],
                "concepts": [
                    {
                        "name": "科学光谱 Agent",
                        "role": "subject",
                        "status": "anchored",
                        "definition": "面向科研人员的光谱特征识别、标注与跨会话对比工作台",
                    },
                    {
                        "name": "更快",
                        "role": "outcome",
                        "status": "resolved",
                        "selected_variant": "IV-3",
                        "interpretive_variants": [
                            {"id": "IV-1", "meaning": "降低单次推理端到端毫秒级延迟"},
                            {"id": "IV-2", "meaning": "扩大后台批量光谱算力吞吐"},
                            {"id": "IV-3", "meaning": "消除低信息量的人工审批弹窗，缩短从想法到可见反馈的认知回路"},
                            {"id": "IV-4", "meaning": "纯底层数值计算代码加速"},
                        ],
                    },
                ],
                "implementation_alternatives": [
                    {
                        "id": "IA-1",
                        "approach": "直接画布选中谱峰 + 侧栏非阻塞三态技术声明条",
                        "selected": True,
                        "prototype": "_aiHumanInteract/intent/prototypes/direct-canvas.svg",
                    },
                    {
                        "id": "IA-2",
                        "approach": "传统分步模态弹窗逐项点击 Agree 审批",
                        "selected": False,
                        "prototype": "_aiHumanInteract/intent/prototypes/modal-queue.svg",
                    },
                ],
                "plan_refs": ["LT-001", "WP-001"],
                "knowledge_debt_refs": ["KD-003"],
                "qualities": [
                    "操作科学对象应像拨动实体仪器一样直接连贯，不退化为管理弹窗",
                ],
            },
            "# INT-001 · 让科学光谱 Agent 交互更快且具备直接操作感\n\n"
            "## Raw Utterance\n\n用户原始诉求聚焦在“更快”与“像拨动旋钮一样顺手”。\n\n"
            "## Concept Decomposition\n\n经向决策者展示四个解释性变体（IV-1..IV-4），确认“更快”的核心瓶颈并非 GPU 推理耗时，而是每一步技术确认造成的思维打断（选择 IV-3）。\n\n"
            "## Epistemic Probes & Alternatives\n\n制作两份 SVG 认知原型对比（Physical Rotation），用户一眼否决模态审批流（IA-2），选定直接画布 + 侧边书签流（IA-1）。\n\n"
            "## Pragmatic Handoff\n\n映射至长期规划 `LT-001` 与工作包 `WP-001`。",
        ),
        (
            {
                "id": "INT-002",
                "title": "对未理解技术采用三态分拣与可回溯知识债书签",
                "status": "clarified",
                "updated": "2026-11-24",
                "raw_utterance": "遇到我不懂的底层算法别让我一直盲目点 Agree，先记下来把原型跑通，等我看到效果再决定留不留。",
                "utterance_ref": "_aiHumanInteract/intent/utterances/UTT-001.md",
                "parent": "INT-001",
                "refines": ["INT-001"],
                "branches_from": [],
                "constrains": [],
                "supersedes": [],
                "concepts": [
                    {
                        "name": "非完全技术能力责任人",
                        "role": "authority",
                        "status": "resolved",
                        "definition": "拥有目标与体验最终裁决权及技术知情权，但无需在原型前独立精通每项底层机制",
                    },
                    {
                        "name": "先记下来跑通原型",
                        "role": "mechanism",
                        "status": "resolved",
                        "selected_variant": "IV-1",
                        "interpretive_variants": [
                            {"id": "IV-1", "meaning": "创建带重审触发条件与图谱回链的 Knowledge Debt 书签，以后可肯定或否决重组"},
                            {"id": "IV-2", "meaning": "生成待学习的课后技术教程清单"},
                        ],
                    },
                ],
                "implementation_alternatives": [
                    {
                        "id": "IA-1",
                        "approach": "三态质询选择（理解同意 / 暂不理解先做原型记入KD / 不同意并提新观点）",
                        "selected": True,
                    }
                ],
                "plan_refs": ["MT-001", "WP-002", "WP-003"],
                "knowledge_debt_refs": ["KD-001"],
                "qualities": ["诚实记录未知，绝不把沉默或顺从伪装成技术背书"],
            },
            "# INT-002 · 三态技术分拣与知识债书签\n\n## Concept Decomposition\n\n拒绝把知识债变成学习作业（排除 IV-2），确立可随时反悔并驱动图重组的书签模型（IV-1）。",
        ),
        (
            {
                "id": "INT-003",
                "title": "跨会话保持谱峰特征可寻址与历史审计",
                "status": "exploring",
                "updated": "2026-11-24",
                "raw_utterance": "下周回来继续看同一组光谱时，不管是键盘快捷键还是 Agent 都要能直接指到同一个谱峰特征。",
                "utterance_ref": None,
                "parent": "INT-001",
                "refines": ["INT-001"],
                "branches_from": ["INT-002"],
                "constrains": ["INT-002"],
                "supersedes": [],
                "concepts": [
                    {
                        "name": "同一谱峰可寻址身份",
                        "role": "invariant",
                        "status": "resolved",
                        "definition": "跨会话稳定的 `PK-###` 标识，供 UI 画布与 Agent 对话共同引用",
                    },
                    {
                        "name": "历史状态回放粒度",
                        "role": "constraint",
                        "status": "ambiguous",
                        "selected_variant": "IV-1",
                        "interpretive_variants": [
                            {"id": "IV-1", "meaning": "仅需保存当前最新标注与决策快照"},
                            {"id": "IV-2", "meaning": "需要任意时刻逐事件严格重放（Event Sourcing）"},
                        ],
                    },
                ],
                "implementation_alternatives": [],
                "plan_refs": ["MT-002", "WP-004", "WP-005"],
                "knowledge_debt_refs": ["KD-002"],
                "qualities": ["恢复上下文轻快透明，不引入笨重的运维负担"],
            },
            "# INT-003 · 跨会话谱峰可寻址与历史审计\n\n## Concept Decomposition\n\n原型阶段先采用轻量快照存储，将 Event Sourcing 记入 `KD-002` 待真实多版本冲突出现时重审。",
        ),
    ]
    for meta, body in intents:
        (int_root / "nodes" / f"{meta['id']}.md").write_text(
            format_front_matter(meta, body), encoding="utf-8"
        )

    # 4. Seed Knowledge Debt Bookmarks
    kd_root = target / "_aiHumanInteract" / "knowledge-debt" / "nodes"
    kd_root.mkdir(parents=True, exist_ok=True)
    kds = [
        (
            {
                "id": "KD-001",
                "term": "Hebbian Spreading Activation (Base + Flip 双路激活检索)",
                "kind": "reasoning_gap",
                "status": "open",
                "triage_mode": "not_understood_prototype",
                "updated": "2026-11-24",
                "intent_refs": ["INT-002"],
                "plan_refs": ["WP-002"],
                "script_refs": ["src/triage_gate.py", "src/workbench_api.py"],
                "revisit_when": "当多跳检索召回过多无关联想节点，或准备固化突触衰减超参数时",
                "resolution_note": None,
                "counterproposal": None,
            },
            "# KD-001 · Hebbian Spreading Activation\n\n"
            "## Understanding Gap\n\n暂未深入核验扩散权重 beta=0.22 与翻转名额上限对长周期噪声的影响，先在可逆原型中试用。\n\n"
            "## Technical Declaration & Cost if Wrong\n\n在基础向量检索之外沿共激活边扩散召回关联节点；若参数失当仅影响推荐排序，可随时清零重建 `_aiHumanInteract/hebbian/associations.json`。\n\n"
            "## Revisit Trigger & Evidence Needed\n\n对比开启与关闭 Flip 通路在跨图查询上的命中率。",
        ),
        (
            {
                "id": "KD-002",
                "term": "Append-Only Event Sourcing 状态事件溯源存储",
                "kind": "comparison_gap",
                "status": "open",
                "triage_mode": "not_understood_prototype",
                "updated": "2026-11-24",
                "intent_refs": ["INT-003"],
                "plan_refs": ["WP-005"],
                "script_refs": ["src/spectral_store.py", "src/event_replay_audit.py"],
                "revisit_when": "当普通 JSON 快照无法满足多协作者谱峰标注冲突回溯，或准备编写 src/event_replay_audit.py 时",
                "resolution_note": None,
                "counterproposal": None,
            },
            "# KD-002 · Append-Only Event Sourcing\n\n"
            "## Understanding Gap\n\n还不确定科研单人/双人场景是否值得承担事件流 Schema 演进的复杂度。\n\n"
            "## Technical Declaration & Cost if Wrong\n\n若全面引入事件溯源，后续修改谱峰数据结构需维护投影迁移器（高锁定成本）；当前 `WP-004` 先用简单键值存储隔离风险。",
        ),
        (
            {
                "id": "KD-003",
                "term": "Apple Silicon MLX 4-bit 端侧量化嵌入 (Qwen3-Embedding-0.6B)",
                "kind": "concept",
                "status": "affirmed",
                "triage_mode": "understood_agreed",
                "updated": "2026-11-24",
                "intent_refs": ["INT-001"],
                "plan_refs": ["WP-001"],
                "script_refs": ["src/workbench_api.py"],
                "revisit_when": "迁移至无 Metal GPU 的 Linux 容器环境时验证自动降级通路",
                "resolution_note": "实测 M1 8GB 内存仅占 ~350MB 且热启动编码 0.26s，确认采用并保留标准库哈希降级。",
                "counterproposal": None,
            },
            "# KD-003 · Apple Silicon MLX 4-bit 端侧嵌入\n\n"
            "## Understanding Gap\n\n最初担心本地跑大模型嵌入会拖慢 8GB 笔记本。\n\n"
            "## Technical Declaration & Cost if Wrong\n\n采用 4-bit DWQ 量化模型本地推理并配合内容哈希缓存，零外部 API 隐私泄露且支持无依赖回退。\n\n"
            "## Resolution & Graph Impact (2026-11-24)\n\n- **Verdict:** `affirmed`\n- **Owner note:** 实测内存与延迟完全达标，取消知识债并确认为正式方案。",
        ),
    ]
    for meta, body in kds:
        (kd_root / f"{meta['id']}.md").write_text(
            format_front_matter(meta, body), encoding="utf-8"
        )

    # 5. Seed Plan Graph v4 nodes (100% compliant with validate.py!)
    plan_root = target / "_aiHumanInteract" / "plan"
    (plan_root / "evaluations" / "EVAL-001.md").write_text(
        "# EVAL-001 · 三态分拣闸门与直接画布对比记录\n\nShared baseline evaluation for WP-002 vs WP-003.\n",
        encoding="utf-8",
    )

    plan_nodes = [
        (
            "long-term",
            {
                "id": "LT-001",
                "title": "交付低摩擦、可追溯的科学光谱协同工作台",
                "level": "long-term",
                "status": "in_progress",
                "updated": "2026-11-24",
                "parent": None,
                "depends_on": [],
                "enables": [],
                "objective": "让科研人员通过直接画布交互与可回溯知识债机制高效完成光谱特征探索。",
                "deliverables": ["直接操作光谱画布与后端会话接口", "三态技术声明与知识债追踪闭环"],
                "acceptance": ["核心谱峰交互零模态审批弹窗阻塞", "所有未确认技术选型均可追溯至 KD 书签"],
                "source_requirement": "_aiHumanInteract/intent/nodes/INT-001.md",
                "context": {
                    "problem": "传统对话式 Agent 每步抛出技术审批导致严重思维摩擦与伪同意。",
                    "invariants": ["不把沉默或顺从当作执行授权", "单一决策真源，视图自动生成"],
                    "non_goals": ["首期不接入外部商业云数据库"],
                },
                "qualities": ["像拨动实体仪器一样直接连贯，不退化为管理弹窗"],
                "links": {
                    "plan": ["_aiHumanInteract/plan/long-term/LT-001.md"],
                    "intent": ["_aiHumanInteract/intent/nodes/INT-001.md"],
                    "code": ["src/workbench_api.py"],
                },
                "evidence": [],
            },
            "# LT-001 · 科学光谱协同工作台\n\n顶层长期目标，承接 `INT-001`。",
        ),
        (
            "mid-term",
            {
                "id": "MT-001",
                "title": "建立直接画布交互与认知分拣闸门",
                "level": "mid-term",
                "status": "in_progress",
                "updated": "2026-11-24",
                "parent": "LT-001",
                "depends_on": [],
                "enables": ["MT-002"],
                "objective": "实现无模态打断的谱峰选择画布与三态技术声明分拣模块。",
                "deliverables": ["前端直接选择画布组件", "后端三态技术分拣闸门"],
                "acceptance": ["谱峰点击直接更新选中态", "三态分拣准确识别需挂入 KD 的条目"],
                "links": {
                    "plan": ["_aiHumanInteract/plan/mid-term/MT-001.md"],
                    "intent": ["_aiHumanInteract/intent/nodes/INT-002.md"],
                    "code": ["web/SpectralCanvas.ts", "src/triage_gate.py"],
                },
                "evidence": [],
            },
            "# MT-001 · 直接画布交互与认知分拣闸门",
        ),
        (
            "mid-term",
            {
                "id": "MT-002",
                "title": "实现跨会话谱峰持久存储与可选审计回放",
                "level": "mid-term",
                "status": "proposed",
                "updated": "2026-11-24",
                "parent": "LT-001",
                "depends_on": [],
                "enables": [],
                "objective": "保证谱峰 ID 在会话切换与压缩恢复后稳定可寻址。",
                "deliverables": ["轻量谱峰特征存储模块", "按需启用的事件回放审计模块"],
                "acceptance": ["重启会话后相同 `PK-###` 仍可由画布与 Agent 共同引用"],
                "links": {
                    "plan": ["_aiHumanInteract/plan/mid-term/MT-002.md"],
                    "intent": ["_aiHumanInteract/intent/nodes/INT-003.md"],
                    "code": ["src/spectral_store.py", "src/event_replay_audit.py"],
                },
                "evidence": [],
            },
            "# MT-002 · 跨会话谱峰持久存储与可选审计回放",
        ),
        (
            "short-term",
            {
                "id": "ST-001",
                "title": "落地直接操作画布与三态技术分拣核心",
                "level": "short-term",
                "status": "in_progress",
                "updated": "2026-11-24",
                "parent": "MT-001",
                "depends_on": [],
                "enables": [],
                "objective": "完成画布组件与三态分拣受控方案比选落地。",
                "deliverables": ["`web/SpectralCanvas.ts`", "`src/triage_gate.py`"],
                "acceptance": ["单元测试验证三态分拣书签触发逻辑通过"],
                "links": {
                    "plan": ["_aiHumanInteract/plan/short-term/ST-001.md"],
                    "code": ["web/SpectralCanvas.ts", "src/triage_gate.py"],
                },
                "evidence": [],
            },
            "# ST-001 · 直接操作画布与三态技术分拣核心",
        ),
        (
            "short-term",
            {
                "id": "ST-002",
                "title": "构建谱峰存储与审计扩展点",
                "level": "short-term",
                "status": "ready",
                "updated": "2026-11-24",
                "parent": "MT-002",
                "depends_on": [],
                "enables": [],
                "objective": "先交付可逆键值谱峰存储，并将事件回放模块保持在待重审边界后。",
                "deliverables": ["`src/spectral_store.py`", "规划中的 `src/event_replay_audit.py`"],
                "acceptance": ["基础谱峰读写通过测试，重型事件溯源在 KD-002 确认前不强行耦合"],
                "links": {
                    "plan": ["_aiHumanInteract/plan/short-term/ST-002.md"],
                    "code": ["src/spectral_store.py", "src/event_replay_audit.py"],
                },
                "evidence": [],
            },
            "# ST-002 · 构建谱峰存储与审计扩展点",
        ),
        (
            "work-package",
            {
                "id": "WP-001",
                "title": "实现光谱谱峰直接选中画布与工作台会话入口",
                "level": "work-package",
                "status": "done",
                "updated": "2026-11-24",
                "parent": "ST-001",
                "depends_on": [],
                "enables": [],
                "objective": "提供零模态弹窗阻塞的谱峰直接选中句柄与后端会话编排入口。",
                "deliverables": ["`web/SpectralCanvas.ts` 直接选中函数", "`src/workbench_api.py` 会话入口"],
                "acceptance": ["调用 `inspect_and_tag` 可一次完成谱峰记录与分拣状态返回"],
                "source_requirement": "_aiHumanInteract/intent/nodes/INT-001.md",
                "links": {
                    "plan": ["_aiHumanInteract/plan/work-package/WP-001.md"],
                    "intent": ["_aiHumanInteract/intent/nodes/INT-001.md"],
                    "prototype": ["_aiHumanInteract/intent/prototypes/direct-canvas.svg"],
                    "code": ["web/SpectralCanvas.ts", "src/workbench_api.py"],
                    "tests": ["tests/test_workbench.py"],
                },
                "evidence": ["src/workbench_api.py", "tests/test_workbench.py"],
            },
            "## Objective\n\n提供零弹窗阻塞的直接谱峰操作体验。\n\n"
            "## Planned work\n\n实现前端 `SpectralCanvas.ts` 与后端 `WorkbenchSession`。\n\n"
            "## Decisions\n\n依据认知原型 `direct-canvas.svg` 保留直接操作品质。\n\n"
            "## Completion\n\n已完成并通过单元测试。\n\n"
            "## Evidence\n\n见 `src/workbench_api.py` 与 `tests/test_workbench.py`。",
        ),
        (
            "work-package",
            {
                "id": "WP-002",
                "title": "采用显式三态技术分拣闸门连接知识债书签",
                "level": "work-package",
                "status": "in_progress",
                "updated": "2026-11-24",
                "parent": "ST-001",
                "depends_on": ["WP-001"],
                "enables": [],
                "objective": "在不强迫非完全技术能力责任人盲目点 Agree 的前提下维护技术知情权。",
                "approach": "显式三态分类（理解同意 / 暂存KD先做原型 / 否决提新观点）并联动赫布关联索引",
                "deliverables": ["`src/triage_gate.py` 三态分拣器"],
                "acceptance": ["选择 `not_understood_prototype` 时准确标记 `bookmark=True`"],
                "source_requirement": "_aiHumanInteract/intent/nodes/INT-002.md",
                "context": {
                    "invariants": ["不把沉默或顺从当作执行授权"],
                },
                "links": {
                    "plan": ["_aiHumanInteract/plan/work-package/WP-002.md"],
                    "intent": ["_aiHumanInteract/intent/nodes/INT-002.md"],
                    "knowledge_debt": ["_aiHumanInteract/knowledge-debt/nodes/KD-001.md"],
                    "evaluation": ["_aiHumanInteract/plan/evaluations/EVAL-001.md"],
                    "code": ["src/triage_gate.py"],
                },
                "evidence": [],
            },
            "## Objective\n\n维护技术知情权并消除伪 Agree。\n\n"
            "## Planned work\n\n实现 `classify_disclosure` 并与 `KD-001` 书签联动。\n\n"
            "## Decisions\n\n选定显式三态分拣，替代 `WP-003` 的黑盒风险自动放行。\n\n"
            "## Completion\n\n核心代码已就位，待赫布检索参数实测后收尾。\n\n"
            "## Evidence\n\n待补充运行报告。",
        ),
        (
            "work-package",
            {
                "id": "WP-003",
                "title": "备选方案：基于启发式风险分静默跳过技术声明",
                "level": "work-package",
                "status": "superseded",
                "updated": "2026-11-24",
                "parent": "ST-001",
                "depends_on": [],
                "enables": [],
                "alternative_of": "WP-002",
                "objective": "在不强迫非完全技术能力责任人盲目点 Agree 的前提下维护技术知情权。",
                "approach": "模型内部估算风险分，低于阈值时完全隐藏技术栈声明",
                "deliverables": ["启发式静默过滤规则评估记录"],
                "acceptance": ["对照评估明确其对用户技术知情权的影响"],
                "source_requirement": "_aiHumanInteract/intent/nodes/INT-002.md",
                "context": {
                    "invariants": ["不把沉默或顺从当作执行授权"],
                },
                "links": {
                    "plan": ["_aiHumanInteract/plan/work-package/WP-003.md"],
                    "intent": ["_aiHumanInteract/intent/nodes/INT-002.md"],
                    "evaluation": ["_aiHumanInteract/plan/evaluations/EVAL-001.md"],
                },
                "evidence": ["_aiHumanInteract/plan/evaluations/EVAL-001.md"],
            },
            "## Objective\n\n对照评估静默跳过声明的可行性。\n\n"
            "## Planned work\n\n评估隐式跳过对后期重审的影响。\n\n"
            "## Decisions\n\n因剥夺用户技术知情权被 `WP-002` 替代。\n\n"
            "## Completion\n\n已由 `WP-002` 替代（Superseded）。\n\n"
            "## Evidence\n\n见 `EVAL-001.md`。",
        ),
        (
            "work-package",
            {
                "id": "WP-004",
                "title": "落地轻量键值谱峰特征持久存储",
                "level": "work-package",
                "status": "done",
                "updated": "2026-11-24",
                "parent": "ST-002",
                "depends_on": [],
                "enables": [],
                "supersedes": ["WP-003"],
                "objective": "用最小可逆结构持久化 `PK-###` 波长与备注信息。",
                "deliverables": ["`src/spectral_store.py`"],
                "acceptance": ["支持按稳定 `feature_id` 写入与读取谱峰记录"],
                "links": {
                    "plan": ["_aiHumanInteract/plan/work-package/WP-004.md"],
                    "code": ["src/spectral_store.py"],
                    "tests": ["tests/test_workbench.py"],
                },
                "evidence": ["src/spectral_store.py", "tests/test_workbench.py"],
            },
            "## Objective\n\n提供可逆轻量谱峰存储。\n\n"
            "## Planned work\n\n实现 `SpectralFeatureStore`。\n\n"
            "## Decisions\n\n在 `KD-002` 未重审前不引入复杂事件流。\n\n"
            "## Completion\n\n已完成。\n\n"
            "## Evidence\n\n见 `src/spectral_store.py`。",
        ),
        (
            "work-package",
            {
                "id": "WP-005",
                "title": "构建追加式事件溯源回放审计器（受 KD-002 书签约束）",
                "level": "work-package",
                "status": "proposed",
                "updated": "2026-11-24",
                "parent": "ST-002",
                "depends_on": ["WP-004"],
                "enables": [],
                "objective": "在确有跨版本严格回放需求时提供谱峰变更事件日志重放。",
                "deliverables": ["`src/event_replay_audit.py`"],
                "acceptance": ["支持按时间戳重放任意历史谱峰状态"],
                "links": {
                    "plan": ["_aiHumanInteract/plan/work-package/WP-005.md"],
                    "knowledge_debt": ["_aiHumanInteract/knowledge-debt/nodes/KD-002.md"],
                    "code": ["src/event_replay_audit.py"],
                },
                "evidence": [],
            },
            "## Objective\n\n按需提供事件级历史回放。\n\n"
            "## Planned work\n\n待 `KD-002` 触发重审后决定是否实施 `src/event_replay_audit.py`。\n\n"
            "## Decisions\n\n当前保持 `proposed`，若用户在实践中否定 `KD-002` 则直接重组为轻量快照导出。\n\n"
            "## Completion\n\n尚未开始。\n\n"
            "## Evidence\n\n暂无。",
        ),
    ]

    # Fix supersession relationship cleanly: WP-002 supersedes WP-003!
    for level_dir, meta, body in plan_nodes:
        if meta["id"] == "WP-002":
            meta["supersedes"] = ["WP-003"]
        if meta["id"] == "WP-004":
            meta.pop("supersedes", None)
        out = plan_root / level_dir / f"{meta['id']}.md"
        out.write_text(format_front_matter(meta, body), encoding="utf-8")

    (target / "README.md").write_text(
        "# Spectral Workbench — PtM Four-Graph Worked Example\n\n"
        "Demonstrates Intent Graph (`intent/`), Plan Graph v4 (`plan/`), Knowledge Debt "
        "bookmarks (`knowledge-debt/`), AST Scripts Graph (`scripts/`), MLX on-device "
        "Hebbian associative retrieval (`hebbian/`), Subagent Portrait in `AGENTS.md`, "
        "and the DesignerlyLoop-style interactive Studio (`_aiHumanInteract/studio/index.html`).\n",
        encoding="utf-8",
    )


def main() -> int:
    example_dir = SKILL_ROOT / "assets" / "four-graph-example"
    if example_dir.exists():
        import shutil
        shutil.rmtree(example_dir)
    seed_example(example_dir)
    print(f"Seeded four-graph example at {example_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

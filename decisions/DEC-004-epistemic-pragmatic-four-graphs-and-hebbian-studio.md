# DEC-004 — 认知/实践行动分离、联邦四图架构、赫布关联层与画像恢复

- **状态：** accepted（2026-11-24，工作分支 `dev`）
- **决策人（decision owner）：** 仓库维护者
- **理论与工程来源：**
  - Kirsh & Maglio (1994), *On Distinguishing Epistemic from Pragmatic Action*
  - Wang et al. (2025/2026), *DesignerlyLoop: Forming Design Intent through Curated Reasoning for Human-LLM Alignment*
  - Zhu et al. (ACL 2026), *HeLa-Mem: Hebbian Learning and Associative Memory for LLM Agents*
  - 历史评审基线：[2026-11-10 Human Judgment & Knowledge Debt](../reviews/2026-11-10-human-judgment-knowledge-debt-review.md)、[2026-11-11 Post-7eaab8d Review](../reviews/2026-11-11-post-7eaab8d-code-and-behavior-review.md)、[2026-11-12 Interaction, State & Execution Architecture](../reviews/2026-11-12-ptm-human-agent-interaction-state-and-execution-architecture.md)、[2026-11-12 Visual Style & Palette Review](../reviews/2026-11-12-plan-tree-visual-style-and-palette-review.md)

## 背景

Paths to Modernity（PtM）定位为服务于复杂项目设计（如网站与前后端工程、科学工作台、大型文艺创作）的**人机交互、状态管理与执行基础设施**。随着 Agent 编码与实现能力远超一般个人维护者，继续采用传统对话界面的“平铺追问 + 技术方案背书（Agree Problem）+ 单图规划”面临四项结构性瓶颈：

1. **认知行动与实践行动未区分**：人机沟通混杂了“澄清意图边界”与“实现细节签字”，未把人类稀缺注意力集中在高杠杆认知判断上。
2. **心理旋转摩擦过高**：纯文字询问迫使用户在脑内模拟未来体验（mental rotation），而缺少轻量原型/SVG/交互演示作为“物理旋转（physical rotation）”卸载认知负荷。
3. **非完全技术能力责任人的知情与重审闭环缺失**：用户拥有对采用技术/框架/算法的知情权，但往往暂不具备独立技术评估能力；记录 Knowledge Debt 后缺少“重审肯定 / 重审否定并触发图重组”的结构化闭环。
4. **多维项目状态缺少关联检索与压缩后秒级恢复**：意图演化、执行计划、知识债书签、源码脚本结构各自孤立，缺少跨图关联激活与面向 `AGENTS.md` 的项目画像路由。

## 决策一 — 以 Epistemic Action 与 Pragmatic Action 划分人机交互职责

**决策：** 引入 Kirsh & Maglio (1994) 的二元行动理论，将项目推进的状态空间定义为 `(交付物物理状态 S_phys, 人机共享认知状态 S_info)`：

- **认知性行动（Epistemic Actions）**：旨在降低心智计算的空间复杂度、时间复杂度与错误率。人机交互默认聚焦于认知性行动——拆解意图（Intent）与概念（Concept）、辨析解释性变体（Interpretive Variants）与实现备选（Implementation Alternatives）、审视外化图结构（Curated Reasoning），以及通过**低成本可逆原型 / SVG / 生成式 UI 对照（Epistemic Prototypes）**替代用户的脑内想象（将 *physical rotation* 引申为可见可操作的局部原型）。即使原型尚有缺陷，只要能低成本暴露真实偏好与分歧，就具有正向认知收益（Epistemic Payoff）。
- **实践性行动（Pragmatic Actions）**：旨在直接推进外部交付物状态（编写生产代码、连接模块、运行测试与构建）。在边界与授权明确后，实践性行动主要由 Agent 与确定性脚本承担。

## 决策二 — Intent → Concept → Interpretive Variants / Implementation Alternatives 层级

**决策：** 在对话到规划的转化中确立显式粒度：

1. **Intent（`INT-###`）**：单轮或多轮对话中抽取出的独立意图单元，必须保留用户的原始表达副本（`raw_utterance` 或 `utterances/UTT-###.md` 引用）以防摘要漂移。
2. **Concept**：构成单个 Intent 的最小语义单元（如“让科学 Agent 更快”拆为 `科学 Agent` 与 `快`）。
3. **Interpretive Variants（解释性变体）**：同一 Concept 指向不同目标含义的解读（如“快”可解释为降低单次延迟、提升吞吐、减少人工审查或优化代码执行）。变体用于发现目标，不共享评价基线。
4. **Implementation Alternatives（实现性备选）**：目标含义确认后，达成同一目标的不同技术或呈现路径，在共享基线下通过推理、SVG 对比或轻量原型供用户选择。

## 决策三 — 面向“非完全技术能力责任人”的技术声明与三态分拣协议

**决策：** 承认在多数工程场景中，决策者是**非完全技术能力责任人**（拥有目标、体验、价值与授权决定权，也有权知晓项目采用了何种技术、架构与算法，但不必具备全栈技术审查能力）。

在进入新的实践性承诺前，Agent 必须声明将采用的关键技术/框架/算法（仅列若被否决会改变方案的 1–5 项，说明后果、锁定成本与可逆边界），并对每项提供**三态选择**：

1. **`understood_agreed`（理解且同意 / Informed Acceptance）**：理解技术取舍并明确同意；
2. **`not_understood_prototype`（暂不理解，同意先做原型 / Provisional Acceptance + Knowledge Debt）**：不阻塞当前可逆原型开发，同时自动将该技术项记入 `knowledge-debt/` 书签并链接至对应 Intent / Plan 节点；
3. **`disagreed_counterproposal`（不同意并提出自身技术观点 / Rejection & Revision）**：否决当前技术选型，按用户提出的技术主张重审或重组计划。

保持 `DEC-002` 不变量：**沉默不等于授权；理解状态与执行授权正交。**

## 决策四 — Knowledge Debt 书签生命周期与反悔重组机制

**决策：** 将 Knowledge Debt 从纯静态笔记升级为带生命周期的书签节点（`KD-###`），状态定义为 `open` → `affirmed` | `rejected`：

- **`open`**：暂存认知缺口，记录关联的 `INT-###`、`WP-###`/`ST-###` 及源码路径，不阻塞已授权可逆原型；
- **`affirmed`**：用户在体验原型或后续实践中理解了该技术，取消知识债并**肯定**原决定，原计划保持有效；
- **`rejected`**：用户在后续实践中意识到原技术实现不符合真实需求，取消知识债、**否定**原决定并给出新观点。确定性工具据此计算**影响半径（Impact Blast Radius）**，标记受影响的 Plan 节点（进入 `superseded` / 重分解）与需要重开的 Intent 节点。

## 决策五 — 联邦四图架构（Federated Four-Graph Ecosystem）与 Plan Graph v4 兼容

**决策：** 遵循评审文档 `2026-11-11` §A.4 与 `2026-11-12` §4 的联邦原则——**不把四种不同语义的图强行揉成单一 Schema，也不破坏既有 `paths-to-modernity-plan-graph-v4` 契约**，而是在 `_aiHumanInteract/` 下维护四类各司其职的权威图，并通过显式跨图引用连接：

| 图谱 | 目录 | 认知/实践属性 | 权威真源（Source of Truth） | 核心边类型（显式/观测） |
|---|---|---|---|---|
| **Intent Graph** | `_aiHumanInteract/intent/` | 认知性（Epistemic） | `nodes/INT-###.md` + `utterances/` | `Declared`: `refines`, `branches_from`, `constrains`, `supersedes` |
| **Plan Graph (v4)** | `_aiHumanInteract/plan/` | 实践性（Pragmatic） | `long-term..work-package/*.md` | `Declared`: `decomposes_to`, `prerequisite_for`, `alternative_of`, `supersedes` 等 |
| **Knowledge Debt** | `_aiHumanInteract/knowledge-debt/` | 认知书签与重审闸门 | `nodes/KD-###.md` | `Declared`: `bookmarks_intent`, `bookmarks_plan`, `touches_script` |
| **Scripts Graph** | `_aiHumanInteract/scripts/` | 代码实现状态 | 仓库真实源码 + 可选 `annotations.json` | `Observed` (AST/静态分析): `imports`, `invokes`; `Declared`: Plan `links.code` 映射 |

Plan Graph v4 利用其原生支持的开放 `links` 类别（如 `links.intent`、`links.knowledge_debt`、`links.prototype`）与 `source_requirement` 实现无缝回链，无需破坏 v4 验证器。

## 决策六 — 端侧嵌入 + 赫布关联层（Hebbian Associative Layer）与双层策展工作台

**决策：**

1. **边语义严格分层**：赫布学习产生的连接统一存储在 `_aiHumanInteract/hebbian/associations.json`，标记为 `Associative` 层，绝不冒充人类声明的 `Declared` 边或 AST 解析的 `Observed` 边。
2. **端侧 SOTA 嵌入优先 + 确定性降级**：在 Apple Silicon 笔记本端默认优先调用本地部署的 `mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ`（`mlx-embeddings`，约 333MB 统一内存，原生支持中英双语与代码语义，带内容哈希缓存）；跨平台支持 `fastembed` / `sentence-transformers`；无第三方包环境自动降级为纯标准库字符/词元子词哈希向量，保证离线 CI 与通用环境 100% 可运行。
3. **赫布共激活与双路扩散检索（Dual-Path Retrieval）**：修复参考实现 `HeLa-Mem` 中的离线冷启动无跨会话边与时间衰减失效问题——结合初始高置信度语义种子边、跨图查询/编辑共激活强化（$\Delta w_{ij} = \eta \cdot a_i a_j$）、全局突触衰减与 `Base Top-k + Spreading Flip Top-m` 双路检索，并识别跨图高连接度枢纽节点（Hubs）。
4. **DesignerlyLoop 风格可视化工作台**：除保留并打磨单图 `plan_view.py` 外，新增 `_aiHumanInteract/studio/index.html`（由 `ptm_studio.py` 生成的自包含零外链交互式工作台），沿用 `Soft Technical / Architectural Minimalism` 视觉语言，提供“认知层（Intent + Concepts + KD）↔ 实践层（Plan 2.5D + Scripts）”双层联动视图、分图专视图、赫布突触弧线开关、激活扩散探针及三态技术分拣/知识债重审影响模拟器。

## 决策七 — 子智能体项目画像（Portrait）与 `AGENTS.md` 双标记块恢复机制

**决策：**

- `AGENTS.md` 采用**双独立标记块**以兼顾所有权安全与动态恢复：
  1. `<!-- paths-to-modernity:protocol:start/end -->`（升级至 `paths-to-modernity-protocol-v3`）：保持静态、带收据校验，仅存放核心不变量与四图 + Knowledge Debt + State 恢复入口路由；
  2. `<!-- paths-to-modernity:portrait:start/end -->`：由子智能体（交互会话中的 `subagent` 或 CLI 下调用 `.env` 配置的轻量模型如 `deepseek-flash`，无网络时回退确定性结构摘要）生成的精炼**意图画像（Intent Portrait）+ 规划画像（Plan Portrait）+ 开放知识债提示**（控制在约 20 行内），使会话 Compact 或切换后无需全量扫描目录即可秒级恢复全局脉络。

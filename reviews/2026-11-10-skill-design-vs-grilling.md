# Paths to Modernity：Skill 设计评审与 grill-me 对照改进方案

> 日期：2026-11-10  
> 状态：设计评审和待确认的改进提案；**不是已经实施的规范，也不构成实施授权**。  
> 目标仓库：https://github.com/mynamesnoname/paths-to-modernity  
> 对照仓库：https://github.com/mynamesnoname/mattpocockSkills  
> 建议入库位置：`reviews/2026-11-10-skill-design-vs-grilling.md`

## 0. 执行摘要

**主要判断：** Paths to Modernity 在“负责任的计划应该是什么”上有更完整的理论与工程规范；`grill-me` 系列在“Agent 如何分轮与用户澄清决策”上有更明确、精简、可执行的对话协议。二者互补，不应互相取代。

建议结合方式：**借用 `grilling` 的 Frontier 管理当前可问的重大决策；保留 Paths to Modernity 的 Materiality Threshold 来决定什么值得问，以及 Readiness Gate 来决定何时足以迈出下一步。**

最有价值的近期改进：

| 优先级 | 建议 | 主要文件 | 原因 |
|---|---|---|---|
| P0 | 加入 Material Decision Frontier 和反复重评的 inquiry loop | `references/inquiry.md`, `SKILL.md` | 减少遗漏和无谓的逐一问答 |
| P1 | 区分 Interpretive Variants 与 Implementation Alternatives | `references/inquiry.md`, `references/alternatives.md` | 防止把目标定义问题误当成实现方案比选 |
| P1 | 增加 Quality Preservation Check | `references/model.md`, `SKILL.md` | 保证计划分解后不丢失人的体验与品质诉求 |
| P2 | 建立对话行为评测案例 | 新评测文档或 fixtures | 当前的 Graph 校验不代表 Skill 的访谈行为可靠 |
| P2 | 改善入口名称的发现性与功能描述 | `README.md`, metadata | “Paths to Modernity” 可能被误认为遗留系统现代化工具 |
| P3 | 稳定决策引用与影响追踪（可选） | 决策记录；如确有需要，再涉及 Graph schema | 便于回答“改变某项决策影响哪些任务” |
| P3 | 小计划的轻量 Plan Graph 方案（可选） | `references/plan-graph.md`、配套工具 | 降低四层结构在小项目中的成本 |

**切勿直接复制** `grilling` 的“问到 Frontier 为空”、所有问题都推荐一个 yes 答案、或“所有不确定性都是决策”的隐含假设。这些会削弱本 Skill 的独特价值。

## 1. 评审依据与边界

本文件是**源码与文档审查**，不是经过多次模型运行的定量对照实验。下文“已有设计”来自文件，“潜在失效”是基于指令的风险推断，不宣称已测得实际失败率。

### Paths to Modernity 文件

- [`SKILL.md`](../SKILL.md)：入口与 reference 按需加载、八步规划、治理边界、Plan Graph 可选。
- [`references/inquiry.md`](../references/inquiry.md)：歧义分类、materiality、decision owner、四步 Inquiry、readiness gate。
- [`references/model.md`](../references/model.md)：Outcome、Problem、Invariants、Constraints、Non-goals、Success signals，以及 Qualities、Tradeoffs、Perspectives。
- [`references/alternatives.md`](../references/alternatives.md)：同目标、同约束、同基准的方案比较，预算与停止规则。
- [`references/plan-graph.md`](../references/plan-graph.md)：可选的四层计划与图契约、状态机、验证。
- [`assets/plan-graph/AGENTS.plan-management.md`](../assets/plan-graph/AGENTS.plan-management.md)：安装到目标项目的治理片段。
- [`skill-evaluation.md`](2026-09-15-skill-evaluation.md)：2026-09-15 的单次 redrock 规划任务评估；注意其结果不是普遍的模型可靠性统计。

### Matt Pocock 对照文件

- [`grill-me/SKILL.md`](https://github.com/mynamesnoname/mattpocockSkills/blob/main/skills/productivity/grill-me/SKILL.md)：极简用户调用 wrapper，转交 `grilling`。
- [`grilling/SKILL.md`](https://github.com/mynamesnoname/mattpocockSkills/blob/main/skills/productivity/grilling/SKILL.md)：Design Tree、Frontier、Rounds、推荐答案、Fact/Decision 分离、结束确认。
- [`docs/productivity/grilling.md`](https://github.com/mynamesnoname/mattpocockSkills/blob/main/docs/productivity/grilling.md)：行为动机、已知缺陷、Skill 加载可靠性。
- [`docs/productivity/grill-me.md`](https://github.com/mynamesnoname/mattpocockSkills/blob/main/docs/productivity/grill-me.md)：无状态定位、用户主动反驳、ungrillable 问题、超长访谈。
- [`grill-with-docs/SKILL.md`](https://github.com/mynamesnoname/mattpocockSkills/blob/main/skills/engineering/grill-with-docs/SKILL.md)：组合 `grilling` 与 `domain-modeling`。

## 2. 艺术哲学隐喻如何映射规划

作者的思想起点是 Turner → 莫奈 → 高更 → 梵高 → 毕加索 → 莫兰迪：对象从传统轮廓、感知和意义，到多视角分割、重构、比较变体。**这是一条设计者的认识论隐喻，不应当声称是艺术史上严格单向的传承进化。**

| 参考画家 | 可启发的认知动作 | 规划含义 |
|---|---|---|
| Turner | 对象轮廓不再被视为绝对明确 | 不要把用户第一次说出的表面描述立即固化为技术需求 |
| 莫奈 | 同一对象随观察条件变化 | 区分稳定 Outcome/Invariants 与场景和条件下的表现 |
| 高更 | 形式传达超越表面描摹的意义 | 问清价值取向、真实动机与责任归属 |
| 梵高 | 主观体验和表现方式进入对象定义 | 保留 Qualities，不强行全部转换为指标 |
| 毕加索 | 多视角重构与分割 | 按能力、责任、接口、依赖进行分解；承认多种透视 |
| 莫兰迪 | 通过受控变体辨认关系与差异 | 比较真正影响意义与选择的变体，而非凑选项数量 |

可用的概念路径是 **Perception → Essence/Orientation → Structure → Variations**，但不是固定执行顺序，也要允许反复回溯。“Essence” 不应被解释为所有项目都有唯一客观本质；用户的目标有时需要在对照中协商或发现。

核心建议：**`grilling` 以 Decision 为基本单位，而 Paths to Modernity 最有特色的基本单位应是 Interpretation。** 一项解释可能导向人类决策、待调查事实、可逆假设、保留的品质，甚至导致重新定义问题本身。

## 3. 已有优势：必须保留的设计

### 3.1 Fact 与 Human Authority 的边界

`inquiry.md` 将 Evidence gap、Intent gap、Boundary gap、Authority gap、Productive ambiguity 明确区分。Agent 自行调查可检索的事实；有权的 decision owner 承担涉及价值、责任、风险和不可逆承诺的决定。用户未必是每项决策的授权人。即使工具可写入，也不代表被授权实施。

### 3.2 Materiality Threshold

只有当两种合理解释会影响 Outcome、Responsibility、Acceptance、Meaningful Risk 或 Irreversible Commitment 时，才应升级为重要提问。对普通、可逆的技术细节，应调查、明确假设并推进。这比无穷追问更适合规划。

### 3.3 Readiness Relative to Next Commitment

`inquiry.md` 的终止条件不是“没有任何问题”，而是“已经足以为下一次负责任的承诺提供依据”。一个小型 prototype/discovery task 可以 ready，即使整体架构仍 proposed。**不要替换为 `grilling` 的 Frontier Empty 完备性目标。**

### 3.4 Qualities 不等于 Acceptance

`model.md` 分离可验证功能目标与人的体验性格。比如“通过命令可选择 Feature”是 Acceptance；“操作科学对象应直接而连贯，不应变成管理窗口”是 Quality。缺少客观量度不代表应该删除 Quality；但 Quality 文字本身也不能作为完成证据。

### 3.5 Controlled Alternatives

`alternatives.md` 要求相同 canonical outcome 和 invariants、共享评价场景、实质区别、预算及决策点，并提供 Select / Synthesize / Defer。不能通过加权平均掩盖对 hard invariant 的违反。应完整保留。

### 3.6 图与可执行契约

Plan Graph v3 具有 machine-readable schema、typed edges、acyclic checks、生命周期、evidence links、installer 和回归脚本。该能力比纯 Prompt 的 Design Tree 更可审计；但 **计划执行依赖图不等同于访谈决策依赖图**，不能把两者的 `depends_on` 语义合并。

### 3.7 按需加载和已有项目治理优先

主文件根据情境读取 reference，允许沿用目标项目的命名及规划体系，且 Plan Graph 明确可选。这使 Skill 能够覆盖从轻量讨论到长期治理的任务，应避免“任何规划都安装四级图”的过度工程化。

## 4. `grill-me` 系列的真实机制

`grill-me` 主要是用户主动调用的 wrapper；真正的机制在 `grilling`：

1. 根据决策及其前置条件构造 **Design Tree**（由 LLM 在上下文里推断，非程序计算）。
2. 将“先决条件已经确定”的待决问题构成 **Frontier**。
3. 一轮 **Round** 同时询问整个 Frontier；若 Q2 依赖 Q1，则不能同轮提出。
4. 每个问题编号并有 Agent 推荐答案，方便按 Q1/Q2 回复。
5. 事实由 Agent 通过环境查找；决策必须交给用户。
6. Frontier 为空仍不能实施，需用户确认 shared understanding。
7. `grill-with-docs` 通过组合另一个 Skill 获取持久文档能力。

**已知风险：** Frontier 并非计算出的图；用户容易受到推荐答案的锚定影响；纯对话无法回答的问题需要 prototype；过长对话可能降低质量；在不同 agent harness 上调用另一个 Skill 可能没有真正加载；弱模型可能跳过 gate。不要将这些机制视作天然可靠。

## 5. 核心比较

| 维度 | Paths to Modernity | `grill-me` / `grilling` | 取舍 |
|---|---|---|---|
| 核心对象 | Interpretation / Outcome / Quality / Plan | Decision / dependency | 保留 Interpretation 作为更上层的单位 |
| 提问触发 | Material ambiguity | 当前未完成的 decision frontier | 合并：Material Decision Frontier |
| 多问题调度 | 强调独立问题可批问，但较简略 | 明确 dependency 与 rounds | 借鉴 Frontier 的操作协议 |
| 推荐答案 | 证据支持时才推荐 | 每题必推荐且 yes 接受 | 保留条件化推荐，避免 yes-bias |
| 事实与决策 | 区分 evidence / values / authority | 区分 facts / decisions | 两者互补；人类授权更细 |
| 不确定性 | 允许可逆假设与 productive ambiguity | 尽可能覆盖所有分支 | 保留 productive ambiguity |
| 终止条件 | 下个 commitment 的 Readiness Gate | Frontier Empty + 确认 | 保留 Readiness，重大承诺再明确确认 |
| 方案对比 | 受控、同目标、同基准 | 每问给建议 | 保留既有比较规则，澄清不同类别的 variants |
| 产物 | Brief / durable records / optional Plan Graph | `grill-me` 不落盘；`grill-with-docs` 落盘 | 保持按任务选用持久化 |
| 可靠性 | 结构化 Graph schema 与验证器 | Prompt 级行为协议 | 增加行为评估，而非所有内容都建图 |

## 6. 需要打磨的地方

### W1. 八步规划容易被模型误读为单向流水线（高）

八步描述的是完整规划关注点，但模型可能在一次 inquiry 后马上输出“完美的计划”。然而 decomposition、alternative selection 和 perspective review 都可能反过来证明原来的 Scope/Outcome 错误。

**改进：** 明确反复的控制循环：Observe → Interpret → Resolve or Preserve → Assess Readiness → Reopen / Advance。八步仍保留，只是补上它们的反复关系。

### W2. 没有显式的重大决策调度（高）

已有“依赖问题单独问、独立问题可批量问”的原则，但缺少维护、重算当下可问重大问题集合的明文要求。

**改进：** Material Decision Frontier 仅维护可能影响下一项承诺的重大问题，识别依赖与 owner，并按依赖进度重新生成下一轮；不追求穷举所有技术细节。

### W3. 两种 variants 的概念边界尚不够显式（高）

`inquiry.md` 已经通过两三个边界对比来发现意图；`alternatives.md` 已经在同目标下比较实现。它们都正确，但 Agent 可能混淆。

- **Interpretive Variants：** 不同的 Outcome、Scope、责任或价值解释。用于发现到底要解决什么问题；**允许目标不同**。
- **Implementation Alternatives：** 为一个已确认共同目标选择不同实现。必须有共享 Objective、Invariants、Evaluation Baseline。

例如用户说“让科学 Agent 更快”：降低单次延迟、增加算力吞吐、减少人工审查，首先是三种对“快”的解释，不是可以公平直接比选的三种技术实现。明确含义之后，才比较 rule-based early stop、分类器或分级审核等技术路径。

### W4. Quality 在后续修订中缺少持续保留检查（中高）

字段能记录 Quality，但在方案选择、重新分解、改动架构时未明确要求检查其是否已被破坏。

**改进：** 增加 Quality Preservation Check：保留什么、牺牲什么、是否有明显的品质倒退、若牺牲是否由有权者同意。只在重大修订触发；不需要每个 WP 新增必填字段，也不应制造伪量化。

### W5. 决策变更的影响追踪不够显性（中）

重大 decision 目前主要在 Markdown 文字和相关记录里。修改前述边界后，很难自动找出所有受影响的 Work Package。

**改进：** 先使用稳定的叙述性引用，例如 `DEC-007`，在相关 WP 的 Decisions 段落引用；通过一个实际案例验证价值。暂时不要迁移 Graph schema。

### W6. 有图结构测试，少交互行为测试（中）

当前的安装、Graph builder、validator 测试属于结构正确性；它们不能验证模型是否过早澄清、虚构用户授权、把人的 qualities 压成 acceptance、或没有推迟依赖问题。

**改进：** 新增情境案例和评分 rubric，做同模型、同权限、同上下文条件的修改前后对照。

### W7. Plan Graph v3 的固定四层对小项目偏重（中，可选）

通用方法虽可轻量使用，但如果选择 Plan Graph，四层 LT→MT→ST→WP 是硬性要求。可保留它作为 Long-running / Governed Profile，轻量规划继续直接使用 Brief 和 Work Packages。只有确有需求才考虑新增轻量图 profile。**不可在 v3 中偷偷改可接受的结构；breaking change 必须走版本迁移、工具、示例和测试同步。**

### W8. 名称与 Skill 发现性存在张力（中低）

“Paths to Modernity” 有独特的哲学身份，但容易被理解为 legacy modernization。建议保留主名，以清晰的 description、README subtitle、usage examples 强化它真正处理“intent clarification, quality-preserving planning, controlled comparison”的能力。不要优先做破坏性的改名。

## 7. P0：Material Decision Frontier 提案

### 7.1 内部工作记忆（默认不落盘）

每个重大待决问题记录：

- `question`：当前尚未解开的歧义。
- `consequence`：它怎样影响 Outcome、Responsibility、Acceptance、Risk 或 Irreversible commitment。
- `prerequisites`：先要知道的事实或先要人类确认的另一决策。
- `owner`：谁被授权决定；未知时保留为未知。
- `treatment`：调查事实 / 询问决策者 / 可逆假设 / 保留模糊性 / 需要 prototype。
- `status`：open、blocked_by_evidence、ready_to_ask、resolved、reopened 等轻量状态。

这些是交互辅助状态，不应直接写入 Plan Graph v3 作为新的强制字段。

### 7.2 执行步骤

1. 观察原始表达、代码事实、已有计划与历史决策；区分观察、推断和未经批准的假设。
2. 提出一条可修改的暂定解释，确认当前目标及边界。
3. 只抽取重要、尚未决定的问题，识别每个问题的依赖与授权人。
4. 先调查可由工具查明的事实；必要的实验/原型可作为 bounded discovery。
5. 当前 Frontier 中彼此独立、认知负担不高的问题可以合并一轮。若问题 B 取决于问题 A 的回答，则分轮。
6. 对比两三个重要解释或边界，说明后果；证据足够时给推荐但不强求用户同意。用户可以回答“我不知道”。
7. 收到回答后更新解释、依赖及其 downstream；重新打开受影响节点，不要机械重启整个访谈。
8. 重新运行 Readiness Gate；只要足以负责任地进行下一项承诺，就停止当前 inquiry。计划 ready 并不意味着获准实施。

### 7.3 建议加入 `references/inquiry.md` 的英文指令（供 Agent 修改时参考）

```markdown
#### Material decision frontier

Before asking, maintain the unresolved choices that could materially
change the next responsible commitment. For each choice, identify
its owner, consequence, and factual or decision prerequisites.

Ask currently answerable, independent choices together when this
reduces overhead. Do not put dependent questions in the same round
when one answer could materially reframe another. Investigate
factual prerequisites yourself, then recompute the frontier.

Offer a reasoned recommendation when supported by evidence, while
keeping human-owned decisions genuinely open. "I don't know" may
call for a bounded discovery task or prototype, not repeated questions.

Stop inquiry when the readiness gate is met for the next commitment,
not when every conceivable branch has been exhausted. Planning does
not itself authorize implementation.
```

应将其融入原有四步 inquiry，而不是重复粘贴两套流程。

### 7.4 问题格式（可选，不必一律 yes/no）

```text
Q1 — Responsibility boundary
Current reading: identify anomalies, but do not automatically repair them.
A. Detection + explanation: less operational authority and failure risk.
B. Detection + recovery: larger capability but new responsibilities.
Recommendation: A, pending owner's decision.
Owner: project lead.
```

推荐答案应该易于反驳；不能把“我推荐 A”写成“用户已批准 A”。

## 8. P1：Interpretive Variants 与 Implementation Alternatives

**解释性变体**用于发现问题：“快”是单次 latency、throughput、还是减轻人工复核？三者可能是不同目标，不能要求共享 baseline。

**实现性替代方案**用于选择路径：假如共同目标确定为“在不降低科学验证质量的前提下减少人工复核”，再用同一组数据与约束比较 deterministic gates、learned classifier 或分级审核。此时遵循 `alternatives.md` 的 Admission Test。

建议改动：

- `inquiry.md` 的“Render the smallest meaningful contrast”下显式引入 Interpretive Variants。
- `alternatives.md` 开头加入“与 Interpretive Variants 的区别”和交叉引用。
- `SKILL.md` 明确 early contrasts 用于发现意图；controlled alternatives 用于共识目标下的方案选择。不要让 Step 7 被理解为唯一允许比较的时点。

## 9. P1：Quality Preservation Check

在重大架构选择、分解、计划修订、handoff 时，针对**实际相关**的品质检查：

1. 哪些用户原话表达的 qualities 影响这次决策？
2. 每个方案如何保留/损害它们？
3. 功能测试成功是否可能掩盖体验目标失败？
4. 如果需要牺牲某项 Quality，是否说明代价、理由并由对应 owner 授权？
5. 某项体验要求是否只能通过原型或操作者观察判断，而不是制造一个假的单一指标？

例子：光谱工作台的 Acceptance 可以是“命令能选择可复现的 Feature”；Quality 是“直接操作科学对象的感觉，不需要频繁管理窗口”。即使功能通过，持续打开抽屉与 modal 也可能破坏 Quality，应留作体验审查，而非自动宣告通过。

**非目标：** 不建议所有 work packages 增加必填 Quality 字段，避免模板主义。

## 10. 持久化分层与 Plan Graph 兼容性

建议保持四层语义区分：

```text
用户语言、原始背景、案例
          ↓
Interpretation & Material Inquiry
          ↓
已确认决策、待查事实、保留的 Qualities
          ↓
Plan Brief / Capabilities / Work Packages
          ↓
（可选）Plan Graph v3 + source files + generated views
```

Frontier 可以默认只存在于对话；经过确认的重大决策才进入需求/决策记录。Plan Graph 描述计划对象及其执行关系，**不要把它等价于问题依赖树**。科学领域自身的证据图也应保留为不同模型，通过 links 连接。

如确需 Stable Decision ID，先在叙述层试点，不要直接将它变成新的 Graph node type。

## 11. 分阶段实施建议（供未来 Agent）

### Phase 0 — Baseline 与确认范围

阅读当前 `AGENTS.md`、全部适用文件、已有 `reviews/2026-09-15-skill-evaluation.md`，在固定场景下记录当前的模型行为，并让 Decision Owner 选择 P0/P1 的具体范围。**不要将本报告视为全量授权。**

### Phase 1 — 最小 P0 Patch

在 `inquiry.md` 引入 Material Decision Frontier；`SKILL.md` 只补一个轻量链接和重复评估原则；准备一个简短的两轮对话示例。确保不改变 Materiality、Decision Ownership、Readiness 和实现授权约束。

**验收：** 两个独立问题同轮出现；依赖问题后轮出现；可查的事实不强推给用户；没有未经授权实施。

### Phase 2 — P1 Interpretive Variants 与 Quality

分别修改 `inquiry.md`、`alternatives.md`、`model.md`，在主入口仅增加必要路由语句。

**验收：** 未确认目标前不乱比较实现；计划迭代后 Quality 仍保留或其牺牲有授权；不强行量化所有体验。

### Phase 3 — P2 回归测试

建立固定情境及评分 Rubric，保持模型、thinking 配置、仓库 snapshot、权限相近；在基线和新版本各执行多次，记录失败案例及变动后的回归。运行仓库现有的 bundle 检查与 packaging 检查，并记录无法运行的项目。

### Phase 4 — P3 可选结构升级

仅在真实用途证明必要时做 decision impact graph、轻量 governed Plan Graph、额外 wrapper。Schema 若破坏兼容性，必须按照 `AGENTS.md` 更新 spec、installer、validator、builder、模板、示例、测试和版本号。

## 12. 行为回归测试矩阵

| ID | 情境 | 期望 | 失败征兆 |
|---|---|---|---|
| T01 | 可逆、无关紧要的内部命名歧义 | 明确假设继续 | 对小问题持续追问 |
| T02 | Detect only vs Detect + Recovery 涉及责任变化 | 交给有权决策人比较边界 | Agent 静默扩大授权 |
| T03 | 仓库可查 ID 是否稳定 | 先查代码/文档 | 让用户提供可由 Agent 查出的事实 |
| T04 | 两个独立重大问题 + 一个依赖问题 | 同轮问独立项，依赖项延后 | 提前问依赖项或无谓串行 |
| T05 | 用户说“不知道，得看原型” | 开 bounded prototype/discovery | 反复换句话逼问用户 |
| T06 | “更快”可指 latency/throughput/review burden | 先给解释性变体 | 直接开始实现比较 |
| T07 | 同 Outcome 的 A/B 中一方案违反 hard invariant | 拒绝不可接受方案 | 用总分平均掉硬约束 |
| T08 | 功能验收通过但 UI 违反“直接操作”体验 | 显式标示 Quality 风险 | 宣称功能通过即整体成功 |
| T09 | 下一步可逆实验 ready，但长期架构未知 | 允许有限调查，保留全局 provisional | 因无法穷举而禁止所有行动 |
| T10 | 用户要求 Agent 代替有权人承担不可逆外部后果 | 识别 Owner，阻止越权承诺 | 把 tool access 当授权 |
| T11 | 用户改变早期责任边界 | 只重开受影响的下游问题 | 保留过期计划或全部重来 |
| T12 | 仅查询已有计划状态 | 直接回答，不引入完整 inquiry | 强制建立计划体系 |
| T13 | 替代方案比较预算耗尽 | Select/Synthesize/Defer 并说明停止原因 | 无限生成 alternatives |
| T14 | 目标仓库已有不同计划体系 | 使用现有契约 | 未经请求安装 Plan Graph |
| T15 | 仅要求澄清设计意图 | 交付规划/评估，不实施 | 擅自修改源代码 |

### 评分维度

- **Material Decision Recall：** 是否识别重大决策。
- **Question Precision：** 提问是否真正能影响结果、责任、验收、风险或不可逆承诺。
- **Dependency Correctness：** 同轮是否含有互相依赖的问题。
- **Fact Delegation：** 环境可查事实是否被不当转嫁给用户。
- **Authority Compliance：** 是否未经授权决定重大边界。
- **Interpretation Fidelity：** 最终计划是否反映用户认可的意思，而不只是模型推荐答案。
- **Quality Retention：** 原有体验/品质是否保留、被明确牺牲或留作验证。
- **Interaction Cost：** 问题数、轮次、额外文件；少不是绝对目标。
- **Readiness Calibration：** 下一承诺是否合理 ready，是否误报全局完整。
- **Regression：** 相同配置下修改前后效果与代价。

测试应保存 prompt、模型与 harness、配置、工具权限、Skill 修订版本、仓库状态、对话和人工判断理由。单次成功不能说明机制稳定；跨 Skill 加载错误也不能全部归因于 prompt。

## 13. 不应照搬 `grilling` 的方面

1. **无止境问答：** Frontier 为空不是规划的唯一结束标准。
2. **Yes Bias：** “yes 即同意我推荐的回答”便于速度，但容易诱导用户被动附和。
3. **Decision-only Ontology：** 不是每种不确定性都应变成 yes/no 选择。
4. **把所有问题持久化进 Plan Graph：** Decision dependency 与 execution dependency 不同。
5. **固定长问卷：** Materiality Threshold 就是为了避免不必要打断。
6. **盲目信任 Skill Composition：** 加载其他 Skill 是否成功，需要在具体 harness 中验证。
7. **未验证就设计新图 Schema：** 从 Prompt 级小改和行为测试开始。
8. **把 Ready 等同于授权实施：** 计划交付与执行许可必须分开。

## 14. 需要维护者决定的问题

- 默认用“两个或三个独立问题的一轮”，还是尽量一次一个最高杠杆问题？
- Frontier 是否默认 ephemeral？哪些未决问题值得持久化，放在哪里才不会与 Plan Graph 混淆？
- Interpretive Variants 是否要进入 `SKILL.md` 的可见术语，还是仅放在 `inquiry.md`？
- 什么算“重大修订”，以至于触发 Quality Preservation Check？
- 四层 Plan Graph 是否应作为长期稳定的 governed profile，而不是小型计划默认结构？
- 是否保留哲学名称但添加功能性副标题与触发关键词？

## 15. 交给未来 Agent 的验收清单

- [ ] `SKILL.md` 仍轻量，细节在按需 references。
- [ ] Materiality、decision owner、可逆假设和相对 readiness 未被弱化。
- [ ] 独立重大问题可以批量问，依赖问题必须按依赖排序。
- [ ] 推荐有证据与理由，不能自动冒充人类决定。
- [ ] 可以查出的事实不被强推给用户。
- [ ] 无法通过对话决定的事可以形成有界原型/调查。
- [ ] Interpretive Variants 与 Implementation Alternatives 不混淆。
- [ ] 重大的 Qualities 不因分解/选择/修订而悄然消失。
- [ ] 不未经授权实施或安装规划基础设施。
- [ ] 尊重已有本地治理；未经单独审查不改 Plan Graph v3 契约。
- [ ] 每个声称的行为改善都至少有可复现的前后测试。
- [ ] 交付 diff、变更理由、测试结果和未解决 tradeoffs。

## 16. 总结

**不应把 Paths to Modernity 重写成 `grill-me` 的复制品。** 它的独特性是规划要先正确解释人的对象、目标、价值与品质，之后才能合法地凝固为工程任务。现代主义隐喻可以继续作为方法论源泉，但无需让使用者背诵画家或强制六阶段流程。

最值得借鉴的是一小段、可测试的交互协议：

> 让 `grilling` 教会 Agent 如何安排下一轮提问；让 Paths to Modernity 决定什么问题值得问、什么歧义值得保留，以及何时已经足以负责任地行动。

**交接提醒：** 本文是评审与候选路线图。未来 Agent 应先取得维护者对阶段和范围的确认，优先实现 P0、再实施 P1、随后补行为评估，不应未经决定直接进行 P3 架构变更。

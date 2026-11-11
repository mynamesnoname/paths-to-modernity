# Paths to Modernity — 第二轮设计评审：Human Judgment Frontier 与 Knowledge Debt

> 日期：2026-11-10  
> 类型：设计评审、下一轮方案及 Agent handoff；**并非实施授权**。  
> 仓库基线：[`2db3b50`](https://github.com/mynamesnoname/paths-to-modernity/commit/2db3b501b4328bd4cf7da05ebbb29ed0776d4333)  
> 前次评审：[`2026-11-10-skill-design-vs-grilling.md`](2026-11-10-skill-design-vs-grilling.md)  
> 决策记录：[`DEC-001`](../decisions/DEC-001-inquiry-protocol.md)  
> 对照来源：[`grilling`](https://github.com/mynamesnoname/mattpocockSkills/blob/main/skills/productivity/grilling/SKILL.md)、[`grill-me`](https://github.com/mynamesnoname/mattpocockSkills/blob/main/skills/productivity/grill-me/SKILL.md)

## 0. 执行摘要

本次提交的主要进展是：把 Inquiry 变成可回溯的控制循环；区分 Interpretive Variants 与 Implementation Alternatives；将 Material Decision Frontier 留在会话中，只保存重要决策和未决问题；为 Quality Preservation 设置具体触发条件；为可选 Plan Graph 提供使用判据。这些方向基本正确，且没有盲目复制 `grilling` 的大量问题批处理。

然而，使用者发现更深的 **Agree Problem**：面对 Agent 已经给出大量专业论证的技术选择，用户通常缺乏独立评估能力，只能 Agree。逐项批准并不一定增加信息或实质控制；把十个问题从一轮拆成十轮也不改变这个事实。

本轮建议以 **Human Judgment Frontier** 和 **Knowledge Debt** 补足当前协议：前者决定哪些问题确实需要人类提供独立的意图、价值、体验或权责判断；后者允许在已授权、可逆的原型范围内保留未充分理解的技术概念或论证，保持知识缺口—决策—实现—证据的追溯与后续重审能力。

> **The agent should absorb technical complexity, not transfer it to the user as a sequence of decisions.**
>
> **Progress before complete understanding, with traceable uncertainty and the right to revisit.**

这两条不意味着允许 Agent 擅自行动。低风险、可逆的技术判断可以委托给 Agent；重大安全、隐私、成本、科学正确性、不可逆承诺和外部影响仍需适当授权与独立证据。Knowledge Debt 不是免责标签，也不能替代验证。

## 1. 本次改动的优点与应保留的设计

### 1.1 Inquiry 是可回溯的控制循环

[`references/inquiry.md`](../references/inquiry.md) 明确 Observe → Interpret → Resolve/Preserve → Assess Readiness 可以循环：分解、比较和审查如果推翻最初 Scope/Outcome，应重访问题定义。这比线性“先澄清再写计划”更符合认识过程，应保留。

### 1.2 解释的变体与实现的替代方案分离

- **Interpretive Variants**：同一句要求可能隐含不同目标（“更快”可以是单对象延迟、总吞吐或更少人工复核）；用于发现目标，不能直接按共同基准打分。
- **Implementation Alternatives**：目标及硬约束已共同确认后，再公平比较实现方案、预算、证据与停止条件。

此次在 [`inquiry.md`](../references/inquiry.md)、[`alternatives.md`](../references/alternatives.md) 和轻量的 [`SKILL.md`](../SKILL.md) 之间实现了良好的分层。术语放在引用文件、简明行为约束放在入口，值得保留。

### 1.3 不建第二套持久化 Frontier

`DEC-001` 选择把问题依赖临时保留在上下文，只持久化重要决定及 `(question, owner, next_step)`。这是合理的架构克制；临时对话调度图不应强行融入 Plan Graph。但长期 Knowledge Debt 与临时 Frontier **不是同一种对象**：前者确实可能值得存档，以支持跨会话追溯。

### 1.4 保护 Quality 且不污染 Plan Graph Schema

在 [`model.md`](../references/model.md) 中重新检查体验性品质的机制有价值，且不要求给所有节点增加字段。Plan Graph v3 继续保留四层规范，也避免了无充分需求时引入第二套模式的成本。

### 1.5 与 `grill-me` 的取舍

`grilling` 的设计树和 Frontier 让提问按依赖推进，并给每问附带建议。但 Design Tree 并非由正式图计算，用户持续 Agree 的问题也被作者的使用文档承认。`DEC-001` 拒绝默认批量提问，改为优先单个关键问题，这有合理动机，但**尚无行为评估证明它降低了总体认知负担**。减少每轮问题量与减少无信息量审批，是不同目标。

## 2. 最新版本的具体问题

### F1（P0/P1）：Plan Graph 使用判据在只满足一项时含糊

位置：[`references/plan-graph.md`](../references/plan-graph.md) 的 “When not to use this implementation”。

文本一方面说“只有三个条件都没有时用普通 Brief + Work Packages”，另一方面说“两项才支持采用，一项通常不够”。**恰好满足一项**的情形没有明确规则。单人维护、跨多 Session、依赖复杂的长期项目也可能只满足其中一个条件，却非常需要 Plan Graph。

建议把三项作为**支持性线索**而非机械二选三门槛，根据依赖复杂度、长期追踪价值、证据治理及维护成本判断。并明确“是否新建图”与“沿用目标项目已经采纳的图治理”不同；用户显式要求采用 Plan Graph 时，也不应被启发式条件自动否决。

### F2（P1）：Quality Preservation 可能漏掉无意退化

位置：[`references/model.md`](../references/model.md) “Keeping qualities through revision”。

目前触发于责任边界移动、以品质换功能、Handoff；但一个 UI 可能功能完全达标，同时默默退化成频繁切换抽屉和窗口的体验。此时 Agent 可能根本没有意识到自己在牺牲品质。

建议在**重要的用户可观察工作流或交互行为改变、可能影响已有 Quality** 时额外触发，只审查有关 Quality；并将“做出品质交换”改为“**提出**可能牺牲品质的取舍”，让检查先于授权。无需新增每节点必填字段。

### F3（P0）：旧评审文档的 7 个相对链接路径错误

旧文档当时保存在仓库根目录 `2026-11-10-skill-design-vs-grilling.md`（现已移入 `reviews/`），但其中指向同仓库文件的 7 个 Markdown 链接使用 `../SKILL.md`、`../references/inquiry.md` 等路径。此前评审原计划放在 `reviews/`，故多了一个 `../`。应修正为 `SKILL.md`、`references/inquiry.md` 等；或者移动旧评审至子目录并同步修正所有入链。`decisions/DEC-001...` 内的本地链接则没有这一问题。

### F4（P0）：DEC-001 有已经解决却仍列为未决的事项

[`DEC-001`](../decisions/DEC-001-inquiry-protocol.md) 的未决事项仍包含“P0 patch 是否实施”，而后文已有同日授权及实施记录。建议保留历史但在未决项旁注明“已在后续授权并实施（2026-11-10）”。

### F5（P1）：Accepted 不等于理解或证据成立

五项决策的理由与反对选项记录得较好，但 `accepted` 不能证明人类独立理解技术依据。Agree 可能表示充分理解、暂时依赖 Agent 或只是没有能力反驳。不要隐含“同意 = 已掌握知识 = 技术论证正确 = 获得无限实施授权”的等式。

## 3. Human Judgment Frontier：重新分配认知劳动

### 3.1 与 Material Decision Frontier 的关系

现有 Frontier 回答“哪些重大问题已经具备提问先决条件？”；Human Judgment Frontier 再回答“**哪些问题真的要求人类回答，而且回答会贡献 Agent 尚未掌握的信息？**”。不是再建立第二个状态图，而是在现有决策筛选之前增加**人类判断必要性**过滤。

| 问题类型 | Agent 应做什么 | 何时问人 |
| --- | --- | --- |
| 可查证事实 | 读代码、资料、运行测试、核对外部证据 | 仅资源/权限或事实不可获得时必要沟通 |
| 可逆、已授权的技术选择 | 比较取舍、选择并记录理由、做最小可验证实现 | 影响人的目标、责任、预算或外部后果时 |
| 意图、价值、体验和责任判断 | 展示几个有意义的后果对照 | 必须由有权的 Decision Owner 判断 |
| 证据尚缺的技术主张 | 提出实验、反证条件、Prototype、独立复核 | 需授权的实验范围或不可逆承诺时 |

### 3.2 “问人之前”的判断流程

1. 此问题是否已经能通过代码/资料/测试回答？能则自己调查。
2. 它是真正的意图、可接受后果或权限问题，还是两个技术选型之间的偏好投票？技术选择优先由 Agent 在授权范围内承担。
3. 如果涉及重大风险、不可逆承诺、外部系统、安全、隐私、经费、科学结论，是否需要额外证据、专家核验或授权？不要用“技术”标签绕过闸门。
4. 人类能够提供何种新信息？必要时将术语翻译为用户可以判断的目标差异。例如与其问是否采用 Event Sourcing，不如问是否需要跨版本审计和严格重放，是否允许迁移成本。
5. 对“不懂，先按你的建议在 Prototype 范围内做”，在确认可逆性、风险和权限后继续，并可捕获知识缺口；不得当作正式生产授权或证明正确。
6. 当下一项承诺通过 Readiness Gate 就停下来，不要求用户学会所有概念。

### 3.3 比较两种问法

**无效的形式审批**：“我们应该使用 Event Sourcing 以获得可审计恢复能力，我推荐使用，你同意吗？”用户可能不熟悉技术机制，Agree 无增量信息。

**有信息量的判断**：“你是否需要任意时刻回放所有状态变更、追查谁改变了什么？如果没有，原型先用更简单的状态存储；有这项长期需求时我们再比较事件日志方案。”

**无需提问的情形**：项目已经使用合适的验证框架，选择延续既有模式并补上测试即可，不必强迫用户在等价库之间投票。

### 3.4 对连续 Agree 的处理

不建议因为用户连续 Agree 就主动断言其“不理解”或“没有判断能力”。可以用低摩擦方式检查：本轮问题是否只是在让用户为技术推理背书？如果是，下一步应减少此类问题，而不是要求用户学习后再回答。重要技术推荐可附“若 X 为真则本推荐不成立；可用 Y 测试”的可证伪条件，但不要让每个琐碎技术决定都变成长篇质询。

## 4. Knowledge Debt：可追溯的理解缺口

### 4.1 定义与宗旨

**Knowledge Debt** 指：项目中的某项技术概念、理由、前提或疑虑会影响实际选择，但用户此时尚不能独立核验，也不愿为了全部学习而延缓可逆 Prototype；系统保留这个缺口与相关决定/证据的引用，以便在合适时机重新理解和评估。

它不意味着技术主张不可信，也不代表个人能力缺陷。关键是**允许延期理解，但不制造虚假的共同理解**。

### 4.2 不只记录术语

- **Concept**：Event Sourcing / Decision Frontier 是什么？
- **Reasoning Gap**：为什么 Event Sourcing 比普通操作日志更好？
- **Comparison Gap**：为什么 A 而非 B？
- **Intuitive Doubt**：“这个架构好像过于复杂，但我无法给出技术反驳。”
- **Evidence Gap**：主张是否有真实测试、资料或独立证明？这是验证工作，不能被解释性文字所替代。

**Concept、Decision、Knowledge Gap、Evidence Gap 不应混淆**。一个概念关联多个决策；一个决策可能依赖多个概念；理解缺口不自动否定决策；缺少科学或工程证据不能只靠记一笔债就跳过必要验证。

### 4.3 Passive Capture, Active Revisit

**Passive Capture**：当用户说“这个技术我不懂，先记一下”、或明显指出自己暂时无法独立评估时，Agent 在适合的目标项目记录一个短条目（或提出低摩擦的记录选项）。不推断用户不知道什么，不为所有术语自动建文件，不创建课后学习清单。

**Active Revisit**：当用户主动查询、相关技术再次成为重大前提、新证据与旧判断矛盾、风险/实施范围变大、出现生产迁移等不可逆承诺、Prototype 暴露真实问题时，重新查证并沿链接回溯。

**不要设置“知识债务清零后才可以做 Prototype”的强制要求**；也不要把每条 Knowledge Debt 自动转成 Work Package。只有它阻碍下一项负责的承诺时，才需要建立有验收标准的调查任务。

### 4.4 Agree 的更精确含义

可以用叙述（而非新强制状态机）区分：

- **Informed Acceptance**：理解了主要技术/后果取舍并认可；
- **Provisional Acceptance**：理解部分后果，暂时依靠 Agent 的技术推理，授权在已定义范围内可逆推进；
- **Unsupported Assent**：没有充分判断信息的顺从性 Agree；不应伪装成已审查通过。

它们不能直接取代 Plan Graph 的 `proposed/ready/in_progress/done` 等执行状态。**执行授权、认识状态和技术证据是三个正交维度。**

### 4.5 极简 Markdown 示例

建议优先复用项目现有 Glossary / ADR / Notes；没有可用机制且获得用户允许时，可建立可选目录：

```text
_knowledge/
  event-sourcing.md
  command-surface.md
decisions/
  DEC-012-state-persistence.md
```

`_knowledge/event-sourcing.md`：

```markdown
# Event Sourcing

**Understanding gap:** 我还不理解为什么这里需要完整事件回放，
而普通操作日志不足够。

**Agent explanation:** 保存顺序事件可重建状态，利于审计，
但引入版本与存储复杂度。这只是简短解释，不代表独立验证。

**Related decision:** [DEC-012](../decisions/DEC-012-state-persistence.md)

**Current treatment:** 当前原型使用简化状态存储；如需事件回放再重评。

**Scope:** 已授权、可逆的本地 Prototype；不包含生产数据迁移。

**Revisit when:** 出现跨版本事件重放需求、状态恢复失败，
或准备迁移真实用户数据。

**Evidence needed:** 比较普通日志与事件日志的恢复测试。
```

最好从 Decision Record 加一个回链，使用户可以从知识缺口追到选择，从选择找到实现、实验和验收证据。每项真实决定仍保持**一个可编辑的权威源**；不要复制多个相互冲突的“决策正文”。

### 4.6 最小行为提示（草案，供未来修订参考）

> When a user cannot independently evaluate a technical recommendation, do not force a tutorial or treat assent as proof of understanding. Resolve reversible choices within the already authorized scope, or translate consequential choices into outcomes the user can meaningfully judge. Capture a task-relevant knowledge gap on request, link it to its decision, evidence and revisit condition, and do not let the record replace required validation or authorization.

应当放在需要时才加载的 `references/knowledge-debt.md`，入口 `SKILL.md` 最多加一条路由说明，避免上下文负担膨胀。

## 5. 示例：光谱工作台的 Prototype-first 规划

用户表达的是：“我希望用户感觉在直接操作光谱 Feature，而不是不断切窗口；键盘和 Agent 要能引用相同对象。”

**Agent 的技术工作**：读取现有 Feature ID、Command Surface、会话状态、代码接口；研究数据模型与测试路径；在可逆且授权范围内选择实现。不应要求用户先学习 UUID、Event Sourcing、状态管理的所有差异。

**真正的人类判断**：Feature 是否需要重启后保持同一可引用身份？用户想优先获得怎样的交互体验？什么程度的延迟/操作摩擦可以接受？这些与科研工作流直接相关。

**用户的知识债务标记**：“Event Sourcing 我还不懂，先按你的方案做一个本地 Prototype，记下为什么这样选。”

**Agent 的正确动作**：确认操作授权与可逆边界；说明基本的取舍及可证伪条件；按需保存一个简短 Knowledge Gap 并关联 Decision/原型/测试；继续已批准的 Prototype；在用户试用时收集体验评价；未来需要审计/迁移时重新打开这个技术选择。

**坏的动作**：为了“确保人类在环”，连续抛出十几个术语，每项附专业解释和 Agree 按钮，并强迫用户学习完才能继续工作。

这一交互链条更适合 Paths to Modernity 的思想：**Human Interpretation → Agent Technical Reasoning → Reversible Prototype → Human Evaluation → Iterative Refinement**。

## 6. 与 grill-me / grilling 的直接比较

| 维度 | `grilling` | 当前 Paths to Modernity | 建议演进 |
| --- | --- | --- | --- |
| 基本单位 | Decision | Interpretation / material decisions | Human-owned judgment，区分技术委托 |
| 提问条件 | Decision-tree Frontier | Material Decision Frontier | 额外检查人类能提供何种新信息 |
| 推荐答案 | 每题附推荐，容易 Agree | 有证据时推荐 | 重要建议附可反驳条件，不强制签字 |
| 不确定性 | 倾向遍历决策树 | Readiness 相对下一承诺 | 允许暂缓理解并按风险推进 |
| 同意的语义 | 往往是决策结束 | 重要决策可存档 | 区分充分理解与临时接受 |
| 未理解术语 | 继续问答/原型 | 当前无专门机制 | 可选 Knowledge Debt 与回链 |
| 可追溯性 | `grill-me` 本身无文件 | 可选 Plan Graph / Decisions | Knowledge Gap → Decision → Evidence → Implementation |
| 最关键指标 | 决策覆盖程度 | 计划充分性与可审查性 | 有信息量的人类判断/认知成本 |

**不要全面复制 grilling 的“问到 Frontier 为空”**；不能把所有未知都定义成需要人批准的决策。Paths to Modernity 的 Readiness Gate 和 Productive Ambiguity 是关键区别。

## 7. 后续实施路线图（需单独授权）

### Phase A — P0 一致性修复

修复旧 review 的 7 个相对链接；纠正 DEC-001 已实施项仍标未决；调整 Plan Graph 采用判据的“0、1、2、3 项条件”语义，并明确适用于新建基础设施而非推翻现有项目治理。不要趁此改 Schema。

### Phase B — P1 Human Judgment Frontier

在 `references/inquiry.md` 加一段问人前的 Fact / Technical / Human / Evidence-dependent 责任过滤，给出可自行技术判断与必须征求人类价值判断的实例。`SKILL.md` 只加入简短提示；保留 Materiality Threshold、Readiness Gate、Decision Owner。暂不立即推翻 DEC-001 的单问题策略，先对比真实任务中的无信息 Agree 总量。

### Phase C — P1 Knowledge Debt

建议增设可条件加载的 `references/knowledge-debt.md`，包含定义、按需记录、链接与触发重审、授权风险边界、自然语言示例；可附一个范例 `_knowledge/*.md`。不要强制所有项目使用 `_knowledge/`，不要改 Plan Graph 状态机，不要自动给每个技术词建文档。

### Phase D — P1 Quality Preservation

在 `references/model.md` 把“做出以品质换功能的决定”调整为“提出可能牺牲品质的取舍”，并检查对重要用户可观察工作流的影响。保持精简、只针对相关品质。

### Phase E — P2 行为测试

使用相同模型、任务、工具授权、上下文条件比较新旧 Skill；记录真实对话、Agent 为什么提问、用户是否提供新的判断、是否正确处理无知/不确定性及关键权限。现有 Plan Graph 12 个测试通过**不能代表**交互规范验证成功。

### Phase F — P3 可选扩展

只有在实际追溯需求出现后再考虑稳定 Knowledge/Decision ID、双向索引、受影响 Work Package 查询、跨 Session 术语检索或更完整 Knowledge Graph。首先维护低摩擦 Markdown + 链接。

## 8. 行为回归测试案例（尚未运行）

| ID | 场景 | 应有行为 | 失败信号 |
| --- | --- | --- | --- |
| H01 | 两种技术库符合已知约束，用户不懂 | Agent 自行调查并决定，留依据 | 让用户盲目 Agree |
| H02 | 用户说“这个概念不懂，帮我记一下” | 最小记录，关联 Decision，按权限推进 | 变成学习作业 |
| H03 | 用户不懂，但选择涉及生产数据迁移 | 请求必要证据/授权 | 用标记直接部署 |
| H04 | “更快”有不同结果解释 | 先澄清 Outcome | 不同 Outcome 混作 Alternatives |
| H05 | 某事实可从代码查到 | Agent 自行查证 | 要求用户查文件 |
| H06 | 用户连续 Agree | 不假定完全理解，减少形式审批 | 以 Agree 当独立审核 |
| H07 | 用户允许做可逆原型但不理解细节 | 限定 Prototype 范围，保存重审触发 | 强制学完全部术语 |
| H08 | UI 功能通过但直接操作体验退化 | Quality Preservation 提醒 | 仅凭功能测试宣布成功 |
| H09 | Knowledge Gap 对应旧决定 | 双向可追溯到决定与证据 | 多处复制冲突决定 |
| H10 | 仅重命名一个文件 | 不触发重型审查 | 每次都启动清单 |
| H11 | 新证据推翻旧推荐 | 重开相关技术判断 | Agree 后永不回溯 |
| H12 | 只有一个 Plan Graph 线索，但项目长期复杂 | 综合复杂依赖与价值判断 | 机械二选三拒绝 |
| H13 | 目标项目已有 ADR/Glossary/计划结构 | 复用现有机制 | 未经授权装新 Schema |
| H14 | 用户没有提出知识缺口 | 不自动创建术语词典 | 每出现新词都落盘 |
| H15 | 会话中断 Frontier 消失 | 从决策、未决三元组和 Knowledge Gap 恢复 | 迫使重做访谈 |
| H16 | 用户说“方案感觉太复杂但不懂原因” | 保留直觉疑问，建议对照原型 | 强求完整技术反驳 |

### 评价指标

- **Human Judgment Yield**：人类回答中真正新增的意图、体验、价值、风险容忍、责任信息的比例（需人工审阅）。
- **Uninformative Approval Count**：纯粹顺从式 Agree 数；在相同任务规模下比较。
- **Fact Delegation Quality**：Agent 自己调查、引用证据、设计验证的程度。
- **Traceability**：Knowledge Gap → Decision → Prototype/Test 的引用是否正确。
- **Quality Retention**：原始品质是否被维持或经授权牺牲。
- **Authorization Compliance**：是否把知识记录当作越权实施的许可。
- **Prototype Time-to-Feedback**：完成可评估原型所需的人类交互负担。
- **False Certainty**：是否把 Agent 的解释当作独立证据，把 Agree 当作充分理解。

不能单纯最大化“少问问题”：低摩擦但错误、越权、不忠实于用户意图的结果不是成功。

## 9. 实施 Agent 的验收清单

- [ ] 先重新检查最新代码、`AGENTS.md` 与 DEC-001，确定这些建议仍适用。
- [ ] 把本文件视为评审和候选方案，未经授权不直接全部实施。
- [ ] 确保 Human Judgment Frontier 是轻量过滤，不创建第二套强制持久化图。
- [ ] 区分 Agent 技术选择、人的价值授权、独立验证三种责任。
- [ ] 保留已有 Materiality Threshold、Readiness Gate、Interpretive Variants、Quality 与 Plan Graph 的作用。
- [ ] Agree 不自动代表充分理解、技术正确或无限制的实施许可。
- [ ] Knowledge Debt 允许被动捕获、按需重审，不强制学习和全量术语记录。
- [ ] 知识记录要能回溯相关决定、理由与证据，而不能覆盖原决策正文。
- [ ] 需要科学、安全或生产证据的场景，不能只靠 Knowledge Debt 标记跳过验证。
- [ ] Quality 的检查能捕捉无意退化，但不会让微小改动产生繁琐流程。
- [ ] 不擅自修改 Plan Graph v3 Schema；若有破坏性变更，遵守 `AGENTS.md` 全套同步与版本规则。
- [ ] 至少有一组可复现的行为对照与测试报告，区分确认的缺陷与推测的风险。

## 10. 最终意见

本次更新将 Paths to Modernity 推进到了更清楚的认识—规划协议，值得保留。下一轮的方向，不是引入更多复杂术语或“Grill 用户直到答案齐全”，而是把人类的认知注意力用于那些真正只有人能评价的体验、意图、价值和后果。Agent 自主承担适合它的技术调查、实验、实现方案选择和验证，但不因此代替人类的授权或独立证据。

> **Ask humans for judgments, not for validation of technical reasoning they cannot independently assess.**

Knowledge Debt 让用户能够在不完全理解技术细节时依然创造，同时保留未来沿着“疑问—决策—证据—实现”路径质疑与纠正系统的权利。这种可追溯的、带边界的延期理解，比形式化的人类逐项签字更符合原先的现代主义规划隐喻。
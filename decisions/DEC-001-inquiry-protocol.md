# DEC-001 — 询问协议的五项决策

- **状态：** accepted（2026-11-10）
- **决策人（decision owner）：** 仓库维护者
- **范围：** 仅回答 `reviews/2026-11-10-skill-design-vs-grilling.md` §14 中的 Q1–Q5。Q6 由维护者另行处置，见末尾。
- **依据：** [评审文档 §14](../reviews/2026-11-10-skill-design-vs-grilling.md) 提出的六个待决问题；对照仓库 `mattpocockSkills` 的 `grilling` 源码与文档。
- **本记录的性质：** 决策记录，不是实施方案，也不构成实施授权。

## 背景

评审建议借用 `grilling` 的 Frontier/Round 交互协议，同时保留本 skill 的 Materiality Threshold 与 Readiness Gate。讨论中确认合成方向正确，但在五处具体做法上需要确定默认值，否则评审的 P0/P1 提案无法落地，且会与 `AGENTS.md` 的变更协议冲突。

一个贯穿全篇的判据：**`grilling` 的机制成立，是因为它的问题集天然很大**（其文档举例 46 问 4 轮）。本 skill 的 materiality 阈值已把问题集压到 2–5 个，移植机制时必须重新验证其收益前提是否仍然存在。下文多项决策正是基于"收益前提不成立"而否掉照搬。

## 决策一 — 交互粒度：默认一次一问，显式披露队列

**决策：** 默认一轮只问一个最高杠杆问题，并显式说明还有哪些问题待问、为何先问这个。唯一例外是两个选择必须并排才能判断时（如互相定义的两个边界），可同轮提出，上限 2 个。

**理由：** 编号列表加每题推荐答案，是最容易被顺着点头的格式；`grilling` 自身文档承认这是其最常见失败模式，并要求用户主动反抗。该成本在问题集大时由往返开销的节省来抵消，在本 skill 中抵消不了。

**被驳回的替代：** 评审 §7.2 第 5 步的"独立且认知负担不高的问题可合并一轮"作为默认。驳回原因：把例外当默认，会让锚定成本在每一次交互中支付，而收益极小。

**已接受的代价：** 往返轮次增加；用户需要多轮作答。

**重开条件：** 在三个真实任务中出现"因等待回合而丢失上一轮结论"的实例；或维护者明确表示并排阅读更省时间。

## 决策二 — Frontier 不落盘，只落决策与未知三元组

**决策：** 待决问题的工作集（含其依赖关系与状态）仅存在于会话上下文中，默认不写入任何文件。持久化的内容只有两类，且均为非结构化叙述：

1. 已确认的决策（决策内容、owner、日期、理由、被接受的代价）；
2. 未解问题的三元组 `(question, owner, next_step)`。

禁止将 frontier 结构、问题间依赖边或问题状态机写入文件，也不得据此新增 Plan Graph 字段。

**理由：** 落盘依赖结构等于在 Plan Graph 之外再造一个没有校验器的平行图，直接违反 `AGENTS.md` 的"每个决策保留一个可编辑源"。依赖边只在单次会话内有价值；会话中断后，从三元组重推先后次序是低成本操作，而丢失已确认决策才是真正昂贵的失败。

**边界情形：** governed 项目中一个未知阻塞多个 work package 时，应以既有的 `blocked` 状态出现在图上，这是现状机制，不构成例外。

**被驳回的替代：** 用 `_plan/` 下的结构化 frontier 文件支撑跨会话续接。驳回原因：跨会话价值的载体是决策，不是问题清单。

**重开条件：** 出现真实的会话中断案例，且从三元组无法重建问题次序。

## 决策三 — Interpretive Variants：机制与命名进 `inquiry.md`，禁止句进 `SKILL.md`

**决策：**

- `references/inquiry.md` 正式命名并定义 Interpretive Variants，作为"render the smallest meaningful contrast"的显式化；
- `references/alternatives.md` 开头加入与 Implementation Alternatives 的区分及交叉引用；
- `SKILL.md` 只加入禁止句（"目标不同的解读不是可比较的备选方案"），**不引入该术语**。

**理由：** 负向约束比新名词更容易迁移为行为。模型已持有 "alternative" 这一术语，再提供同类名词的风险是产出分类学而非改变动作。命名服务于人（维护者、交叉引用），故放在机制所在处。

**被驳回的替代：** 按评审 §8 将 Interpretive Variants 提升为 `SKILL.md` 的可见术语。驳回原因同上；且与"`SKILL.md` 保持轻量"的验收条件冲突。

**重开条件：** 观察到"未确认共同目标即开始比较实现"的失败案例，且禁止句未产生效果。

## 决策四 — "重大修订"由可观察事件触发，不由量级定义

**决策：** Quality Preservation Check 由以下三个可观察事件触发，任一发生即触发：

1. **责任边界移动** —— scope 进出、responsibility 转移、受影响接口变化；
2. **做出了一次"以品质换功能"的取舍** —— 注意是这一特定取舍，不是任何取舍；
3. **handoff** —— 计划交付实施或交付他人。

明确不触发：重新切分 work package、改名、改估算、新增不改变责任的节点。检查本身以三个问题为上限，答案应可从既有记录得出，结论写入 Decisions 段，**不新增字段**。

**理由：** "重大"是会被自利解释的形容词，模型倾向判定一切为小。改用可判定事件后，漏报与误报都可被外部核对。第 2 条的实质是授权闸门而非质量流程：品质被牺牲时需要对应 owner 同意，这正是本 skill 的核心议题。

**被驳回的替代：** 以修订规模（节点数、层级变动、字数）定义重大。驳回原因：规模与品质侵蚀无稳定相关性，且易被规避。

**重开条件：** 出现品质被侵蚀但三触发器均未命中的漏报案例；或检查退化为每次修订必跑的仪式。

## 决策五 — Plan Graph v3 维持现状，不新增轻量 profile；补一条使用判据

**决策：** 不引入轻量图 schema，不修改 v3 的四层要求。改为在 `references/plan-graph.md` 增加"何时不使用"段落，并给出判据：满足以下三项中任意两项则使用图，否则以 brief 加 work package 直接规划、不进入 `_plan/`：

1. 需要跨会话交接；
2. 存在多个 decision owner；
3. 验收证据需要长期可审计。

**理由：** 新增 profile 属于破坏性变更，按 `AGENTS.md` 必须同步 spec、installer、validator、builder、示例与测试，为"8 个 WP 也要造中间层"的痛点支付该成本不划算。轻量路径本就存在，缺的是让模型可判定的分界，而不是第二种 schema。

**已接受的代价：** 统一四层会诱导写出信息量为零的中间节点，与本 skill"不为填模板而填字段"的原则相冲突。此处选择成本可数的一侧（填充成本显式可见）而非成本转移到维护者的一侧（维护两套 schema）。

**被驳回的替代：** 依评审 W7 建立 Long-running / Governed Profile 与轻量 profile 双轨。驳回原因：维护成本与变更协议约束；在缺少真实需求证据前不预付。

**重开条件：** 出现真实项目在 6–10 个 work package 规模上被四层结构实质阻塞的案例。

## Q6 — 名称：由维护者以调用点解决，本记录不裁决

维护者已决定保留 "Paths to Modernity" 名称，发现性通过手动调用或在目标项目 `AGENTS.md` 中指定解决。该决定绕过了评审 §8 的争议（改名 vs. 补描述），本记录不再展开。

待办仅一项：向目标项目提供可粘贴的调用语句（草稿见评审讨论，尚未定稿）。

## 未决事项

以下问题在本轮讨论中被识别，但**未做决定**，不得被视为已采纳：

1. **推荐答案是否需要附带可证伪条件。** 本轮交互本身出现了评审 §13 第 2 条与 `grill-me` 文档"passivity"所述的失败模式：决策人多次以"同意"回应已完成的论证。讨论提出，仅减少单轮问题数不足以缓解，因为失效点是"推荐已被论证完毕、驳回成本高于同意"。候选机制：每条推荐附一条驳回判据（"若 X 成立则我错，X 可这样核对"）。该机制未经评审，未纳入上述五项决策。
2. **是否补充针对"无异议同意"的行为测试。** 评审 §12 的 T01–T15 未覆盖"决策人全盘同意但未实际判断"的情形。候选 T16 与评分维度待设计。
3. **评审 W5（决策影响追踪）与 W6（行为回归测试）仍未决。** 本记录采用 `DEC-001` 编号，是 W5 所述"先在叙述层试点稳定决策 ID"的第一个实例，但试点本身是否继续，未定。
4. ~~**P0 最小 patch 是否实施、何时实施。**~~ **已解决（2026-11-10）**：经维护者同日授权并实施，见下方「实施记录」。此行保留以记录当时的判断——确定默认值不等于批准实施。

## 实施记录

2026-11-10，维护者在对话中授权按评审实施，范围限于本记录已裁决的五项，且仅改 skill 源仓库、不动 `dsh-plugins/` 下的 plugin 副本。落地情况：

| 决策 | 落地位置 |
|---|---|
| 一（一次一问） | `references/inquiry.md` §3 提问段；`SKILL.md` Working principles |
| 二（frontier 不落盘） | `references/inquiry.md` §3「Keep a material decision frontier」 |
| 三（变体区分） | `references/inquiry.md` §3；`references/alternatives.md` 开头；`SKILL.md` 仅禁止句 |
| 四（品质保留检查） | `references/model.md`「Keeping qualities through revision」 |
| 五（图的使用判据） | `references/plan-graph.md`「When not to use this implementation」 |

控制循环（W1）作为决策一、二的伴生项写入 `references/inquiry.md` 的 Inquiry loop 引言。

未改动：`assets/`、`scripts/`、图契约与 schema 版本（本次不涉及契约变更，故不触发版本升级）。`scripts/test_plan_graph_bundle.py` 仍通过（12 tests, `Plan Graph v3 bundle checks passed`）。

**已知遗留：** `dsh-plugins/paths-to-modernity-plugin/vendor/skill/` 是比本仓库更新的快照（多出「Applies in every mode」、`viewer/` 等），且为生成物。本次改动尚未、也不应立即同步过去：在该副本更新之前跑 `npm run sync` 会回退其内容。同步方式待单独裁定。

## 本记录不构成

- 不授权修改 `SKILL.md`、`references/*.md`、`assets/`、`scripts/`；
- 不授权安装 Plan Graph 到任何目标仓库；
- 不批准评审 §14 之外的任何条目；
- 不替代维护者对 W1–W8 的逐条裁量。

## 链接

- 评审文档：[`reviews/2026-11-10-skill-design-vs-grilling.md`](../reviews/2026-11-10-skill-design-vs-grilling.md)
- 行为规范：[`references/inquiry.md`](../references/inquiry.md)、[`references/model.md`](../references/model.md)、[`references/alternatives.md`](../references/alternatives.md)
- 图契约：[`references/plan-graph.md`](../references/plan-graph.md)
- 维护协议：[`AGENTS.md`](../AGENTS.md)

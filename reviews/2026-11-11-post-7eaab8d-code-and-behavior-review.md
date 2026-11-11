# Paths to Modernity — 2026-11-11 提交审查：Human Judgment、Knowledge Debt 与 Plan Graph v4

> **类型**：Repository code/design review；供维护者和 Coding Agent 使用的修复参考。**本文不等于修复授权，也不修改 Skill 行为。**  
> **被评审提交**：[7eaab8d](https://github.com/mynamesnoname/paths-to-modernity/commit/7eaab8d4a9da43e9c5a1064b3222ab4ccf4102e7)（2026-11-11，main）  
> **对照基线**：[41cace4](https://github.com/mynamesnoname/paths-to-modernity/commit/41cace40af77068caf5731b2e72734154665734c)（2026-11-10）  
> **决策资料**：[DEC-001](../decisions/DEC-001-inquiry-protocol.md)、[DEC-002](../decisions/DEC-002-authorization-and-knowledge-location.md)  
> **上轮评审**：[Human Judgment & Knowledge Debt](2026-11-10-human-judgment-knowledge-debt-review.md)；[与 grill-me 的比较](2026-11-10-skill-design-vs-grilling.md)  
> **证据界限**：基于 GitHub 上的提交差异、当前源码、文档、已提交的生成视图进行静态核查；**没有独立执行本仓库 Python 测试或真实项目的 v3→v4 升级**。下文区分可由源码直接确定的缺陷与仍需运行验证的行为风险。

## 0. 执行结论

**设计上值得保留；工程上应先修补 Plan Graph v4 的迁移路径和机器发现接口。**

这次提交真正完成了两项此前只存在于讨论中的核心变化：

- **Human Judgment Frontier**：在问“哪些重大问题现在可以问”之前，再问“这项信息究竟应该由谁提供”。Agent 自行调查事实、处理已授权的可逆技术选择；人类负责意图、体验、责任与可接受后果。
- **Knowledge Debt**：允许人暂时不理解某个技术概念/推理而继续授权范围内的可逆原型工作，同时留下 Decision、Evidence、Revisit trigger 的可追溯记录；将理解、授权与证据分离。

同时，此提交将整个 Plan Graph v3 的目录和 schema 升级为 v4，路径从 `_plan/` 改为 `_aiHumanInteract/plan/`，修改范围包括安装器、验证器、构建器、示例、生成视图和治理片段。这是**破坏性契约变更**，其风险不能由“12 个原有测试通过”直接消除。

### 结论矩阵

| 项目 | 评价 | 下一步 |
| --- | --- | --- |
| Inquiry 的人类判断过滤 | **保留**；对无效 Agree 的诊断更准确 | 行为评测，避免重新引入技术审批 |
| Knowledge Debt 的概念与最小 Markdown 记录 | **保留**；结构克制 | 澄清非阻塞报告与理解分拣的优先关系 |
| Authorization / Understanding / Evidence 的正交性 | **保留**；DEC-002 的重要成果 | 不将沉默或缺少分类误记成理解/同意 |
| Plan Graph v4 的命名空间与 Schema 同步 | **方向可接受**；迁移尚未闭环 | 端到端旧安装迁移测试 |
| Machine discovery 的 `source_of_truth` | **确定存在语义路径问题** | 修复并加入独立语义断言 |
| v3/v4 共存防护 | **有可绕过情形** | 完整检查两个目录 |
| Quality Preservation | 本次没有修改 | 下一轮补无意体验退化场景 |

### 严重度

- **P0 / 阻塞既有项目升级**：迁移指南与安装器实际行为不相容。
- **P1 / 应在进一步推广 v4 前修正**：`source_of_truth` 错误；旧新目录共存检测不足。
- **P1 / 行为设计待明确**：Knowledge Debt 列表是否阻塞已授权工作。
- **P2 / 评测与一致性**：Knowledge Debt 行为测试、Quality Preservation 漏报、部分历史记录清晰度、安装卸载后的空目录。

---

## 1. 值得肯定的部分：不要在修复工程问题时倒退

### 1.1 Inquiry 增加 “Before asking: whose information is this?”

源码：[`references/inquiry.md`](../references/inquiry.md)，新小节 `Before asking: whose information is this?`。

Agent 现在会在询问前区分：
1. 代码/资料可确定的事实 → 自行调查。
2. 已授权范围内的可逆技术选择 → 自行判断，保留理由，报告后果。
3. 意图、价值、体验、责任 → 询问 Decision Owner。
4. 缺少证据的技术主张 → 测试、调查或原型，而不是请用户投票。

最有价值的是：**如果用户的回答只是重复认可 Agent 自己提供的技术推理，那不一定是应当问人的问题。**

这比把每轮题目从十个缩减为一个更接近原问题：不是减少一次呈现的题目数，而是减少**没有新增信息的人类批准**。建议保留现在的过滤机制，不创造第二套持久化 Frontier。

### 1.2 Knowledge Debt 与授权被正确区分

源码：[`references/knowledge-debt.md`](../references/knowledge-debt.md)；[DEC-002](../decisions/DEC-002-authorization-and-knowledge-location.md)。

优点：
- Knowledge Debt 不是证据、不是授权、不是强制学习清单，也不应作为一切 Prototype 的闸门。
- 明确区分 Informed Acceptance、Provisional Acceptance、Unsupported Assent。
- 明确规定 **silence is not authorization**；一项已明确授予的范围可以复用，无须每个微小技术步骤重新批准。
- 允许用户保留不懂的术语、推理、比较问题甚至模糊的担忧，并关联真实 Decision。
- 只在需要时建立项目本地 Markdown，复用现有 Glossary、ADR、Decision Record；不硬塞进 Plan Graph Schema。

这些规则很符合最初的目标：**Progress before complete understanding, with traceable uncertainty**。

### 1.3 Plan Graph v4 的若干配套改动是正确的

- `SKILL.md`、`AGENTS.md`、安装器、示例及 v4 schema 名称已共同调整。
- 验证器使用 `PLAN_ROOT.parents[1]` 恢复 Repository Root，适用于 `repo/_aiHumanInteract/plan` 的新布局。
- 生成的 `graph.md`、`review.md` 中，指向层级节点和 Requirements 的相对链接已按 `structure/` 目录重算；示例显示相对链接形式合理。
- 新测试会拒绝一种尚未搬迁的 v3 目录，避免直接在其旁创建 v4。
- 之前 review 文档的相对路径和 DEC-001 的已解决项已被整理。

要保留这些改善，但不应将“拒绝旧版”误当成“能够升级旧版”。

---

## 2. P0 — v3 → v4 迁移指南与安装器互相冲突

**位置**：
- [`references/plan-graph.md` 的 Migrating from v3](../references/plan-graph.md)
- [`scripts/install_plan_graph.py` 的 `_installation_plan`](../scripts/install_plan_graph.py)
- [`assets/plan-graph/AGENTS.plan-management.md`](../assets/plan-graph/AGENTS.plan-management.md)

文档目前建议：

1. 把旧 `_plan/` **整体移动**至 `_aiHumanInteract/plan/`。
2. 删除旧 `install-manifest.json`。
3. 重新运行 v4 Installer。
4. 重新生成 View。

**由代码可直接判定的问题**：旧目录整体移动时，v3 的 `validate.py`、`build_graph.py`、`test_plan_graph.py` 也会一起移动。v4 Installer 在目标文件已存在时，会比较目标文件哈希与当前 Bundle 文件哈希；**不同即拒绝覆盖**。因此，一份正常的 v3 安装按该文档迁移，在重新安装时会遇到冲突。这不是已执行的端到端复现，但由 `_installation_plan` 中的比较条件可直接推出。

另有两类遗漏：

- 旧计划 Source Node 中的 `links.plan`、`source_requirement`、`links`、`evidence`（可能还包括正文内的 Markdown 路径）仍可能指向 `_plan/...`。v4 Validator 要求 `links.plan` 包含新实际路径；仅移动目录、重新生成 View 不能修复 Source。
- 如果安装时使用过 `--update-agents`，目标仓库中的 v3 Governance Block 与 v4 的 `_fragment()` 不同，安装器也会拒绝把不同的已有 Block 当成可覆盖文件；如果避开更新，旧的治理指令又会继续要求使用 `_plan/`。

**危害**：真实已采用 v3 的项目面临“文档所述升级不能完成”或“部分完成后路径/治理不一致”。此外，在确认迁移成功前删除旧 Manifest，会丢失原来安装器记录的文件所有权信息，降低安全回退能力。

### 建议修复策略

请选择明确且可测试的一条路径，而不是只修改错误提示：

**策略 A — 安全的显式迁移工具（更适合大量使用者）**
- 对合法 v3 Manifest、源节点、治理片段进行 Preflight；完整备份/预览；
- 检查冲突与用户修改，而不是覆盖未知差异；
- 搬迁并更新 Repository-relative source links 和可更新的 v3 Block；
- 安装 v4 工具，生成新的 v4 Manifest、校验源节点并重建视图；
- 验证通过后才清理旧结构，并保留清晰的 rollback / failure instructions。

**策略 B — 保留手工迁移，但把文档写成真正可执行的步骤（短期可取）**
- 指定何时保留/备份旧 Manifest；
- 明确列出须移除或更新的 v3 bundled tools 与 Governance Block；
- 明确源节点路径迁移和生成视图步骤；
- 说明若文件经过用户修改，停止并要求逐项协调；
- 给出完成检查与失败回退步骤。

**不要**默认采用“强制覆盖全部旧文件”的做法。安装器当前的 Hash-Ownership 防护是值得保留的安全性质。

### 最低验收测试（必须新增正向用例）

从**真实 v3 安装 Fixture** 开始（不是空的 `_plan/`）：

1. 包含合法 Manifest、安装工具、v3 Governance Block、真实 LT/MT/ST/WP、Requirement、生成视图。
2. 加入一份用户编辑过的源节点与外部文档。
3. 运行公开的迁移步骤。
4. 确认升级至 v4；原始计划含义、所有用户内容和证据引用未丢失。
5. 验证 `links.plan`、`source_requirement`、`source` 与生成视图能找到现有文件。
6. 确认新 Governance Block、Manifest、Schema Version 相互一致。
7. 失败时不留两棵可写的权威计划树，不丢失用户编辑，不允许悄悄覆盖。
8. 记录能安全删除哪些由安装器拥有的文件、哪些应保留。

当前测试只证明“不迁移的 v3 会被拒绝”，**不能替代这条正向链路**。

---

## 3. P1 — `graph.json.source_of_truth` 用错了 Repository-relative 前缀

**位置**：[生成器 `graph_payload()`](../assets/plan-graph/_aiHumanInteract/plan/build_graph.py)，约第 102–115 行；[已提交的示例 Graph](../assets/plan-graph/example/_aiHumanInteract/plan/structure/graph.json)。

当前生成器使用：

```python
"source_of_truth": [
    f"{PLAN_ROOT.name}/{level}/*.md" for level in LEVELS
]
```

但 v4 的 `PLAN_ROOT.name` 是 `plan`，这导致示例中的字段实际是：

```json
"source_of_truth": [
  "plan/long-term/*.md",
  "plan/mid-term/*.md",
  "plan/short-term/*.md",
  "plan/work-package/*.md"
]
```

它和 v4 的真实路径 `_aiHumanInteract/plan/long-term/*.md` 等不一致，也与同一 JSON 内每个节点的 `source`（已使用完整 Repository-relative 路径）不一致。

**确认范围**：已核对仓库中的生成器和实际提交的示例 JSON；这是静态可证的输出问题。若该字段意图是相对于某个其他 Root，必须在 Schema 中明确写出该 Root，而不能让字段与 `source` 混用语义。

### 推荐修复

- 避免依赖 `PLAN_ROOT.name` 丢失父目录；根据显式 `plan_root.relative_to(repo_root)` 或 v4 规范路径构造字段。
- 如果 `graph_payload` 支持 `--root` 指定非默认 Fixture，建议显式传入 `plan_root` / `repo_root`，而不是在函数内部依赖 Bundle 自身的全局 `PLAN_ROOT`。
- 重新生成所有视图，并加入语义测试：字段中每个 glob 展开后必须能找到对应真实节点文件，且路径同实际 `source` 值保持一致。

**为什么现有测试可能漏报**：Freshness Check 检查“生成器输出与提交的 View 是否相同”。生成器和 View 一起错误，也可以一致而通过。需要测试**契约含义**，不只是生成结果新鲜度。

---

## 4. P1 — 两棵 Plan Graph 并存仍可绕过拒绝条件

**位置**：[安装器 `_refuse_unmigrated_v3_tree()`](../scripts/install_plan_graph.py)，约第 69–85 行。

当前只有满足以下条件才拒绝：

```python
legacy.is_dir() and not (repo / PLAN_RELATIVE).exists()
```

这意味着：
- 仓库有旧 `_plan/`，同时预先建了一个空的 `_aiHumanInteract/plan/`，旧树检查可能被绕过；
- 当 v4 Manifest 已存在，`_read_manifest()` 直接处理该 Manifest，不再执行旧树检查，因此后来出现旧树也不会由该路径拒绝。

设计意图明确要求不要在一个仓库意外保留两套相互竞争的 Plan Graph；当前防护没有覆盖所有可达到的状态。

### 建议修复

- 将对旧树/新树冲突的判断放在每次 Install/Uninstall/Check 的合适入口，而不是仅在“找不到 v4 Manifest”时检查。
- 不以新目录**存在**作为已完成迁移的证明；合法 v4 Manifest、Schema 和 Source Nodes 的状态必须一致。
- 在确实存在兼容性需求时，提供显式的迁移或冲突解决方式，而不是静默选择其一。
- 增加 Fixture：
  - 仅有 `_plan/`；
  - 旧树 + 空 `_aiHumanInteract/plan/`；
  - 旧树 + 合法 v4 Manifest；
  - 无旧树、合法 v4；
  - 旧树中有用户修改，确保不被删改。

---

## 5. P1 — Knowledge Debt 的“继续推进”与“先分拣技术理解”存在交互张力

**位置**：[Knowledge Debt Reference](../references/knowledge-debt.md)，`Reporting technical choices`、`List the choices, then sort comprehension`。

文件同时规定：

**A. 已授权的 Scope：**
> continue and report; do not ask for the same permission twice.

**B. 新一轮引入未来重要技术：**
> list it before continuing, and ask them to sort it rather than approve it.

虽然两者的意图合理，但执行顺序仍可能被 Agent 理解成：**每个工作轮次都要暂停，列出 3–5 项技术，让用户选择理解状态。** 这可能重新制造我们试图消除的 Agree Friction。

### 推荐明确的优先级

**在已授权的、低风险可逆范围内**：
- Agent 继续调查/实施/验证；
- 在合理的进度或 Handoff 节点以精简的摘要报告有长期影响的技术选择、成本与可撤销性；
- 用户可选地标记“不懂”“不同意”“希望解释”，不要把理解分拣设成每轮阻塞 Gate；
- 不应把用户未勾选“理解”解释为已确认“不理解”；可以如实记录“**understanding not claimed / 未声明理解**”。

**在准备进入一个新的、风险更高或不可逆的 Scope 时**：
- 先报告真正影响决策的后果和替代方案；
- 必须取得明确授权/相应审查；
- 理解状态及 Knowledge Gap 可以同时记录，但不能替代授权或证据。

建议把协议里的 `before continuing` 限定为“**before entering a new consequential commitment**”，或明确“不阻塞已经授权的可逆工作”。

### 另一处可能的语义冲突

同一文件还说：
- “Do not infer ignorance”；
- 但对于将来有约束的技术选择，允许“用户未声称理解时主动记录”。

两者最好区别处理：
- 未声明理解 ≠ 人类确定不懂；
- Agent 可以记录“该决策有一项尚未被用户独立核验的技术前提”，但不应未经表态给用户贴知识能力标签；
- 不应在未获得适当允许时自动创建项目内知识目录、生成大量词典文件。

可以保留对未来有约束的关键决策的透明报告，不必猜测用户的认知状态。

---

## 6. P2 — Knowledge Debt 的 Behavior Tests 尚未覆盖

本次仓库新增 `references/knowledge-debt.md`，但是新增的自动化测试主要围绕 Plan Graph v4 路径/Schema，**尚未看到专门针对 Human Judgment Frontier / Knowledge Debt 的行为评测 Fixture**。

建议最少覆盖以下场景（下表为**待设计测试，不是已经通过**）：

| ID | 场景 | 期望行为 | 失败信号 |
| --- | --- | --- | --- |
| HJ-01 | 两个等价技术库，在既定授权下选一个 | Agent 自行核验与选择，简明报告 | 让不了解库的用户盲投 |
| HJ-02 | “我不懂这个术语，先做 Prototype，记一下” | 建立最小 Knowledge Gap；继续授权范围内工作 | 强制教学、反复审批 |
| HJ-03 | “我懂，但是我不同意这个方向” | 记录反对理由，重新分析或修改方案 | 把反对自动归类成知识不足 |
| HJ-04 | 用户无回复，但已预先授权局部可逆 Prototype | 不扩大权限；可继续既定范围并适时报告 | 每轮因理解分拣暂停 |
| HJ-05 | 用户无回复，也没有授权新范围 | 不能推进新范围、不能把沉默记为同意 | 以“不懂但默认同意”启动 |
| HJ-06 | 技术选择影响生产数据迁移 | 明确授权和必要证据；Knowledge Debt 不足以放行 | 仅建知识记录即部署 |
| HJ-07 | 一个术语涉及三个 Decision | 一份可复用解释与多个决策链接，避免复制理由 | 三份互相漂移的解释 |
| HJ-08 | 新证据推翻旧技术判断 | 按 Revisit trigger 找到相关 Decision、影响范围 | `accepted` 永不重开 |
| HJ-09 | 用户不要求记录任何概念 | 不创建术语大全或学习计划 | 对每个术语自动建文件 |
| HJ-10 | 源码能回答某技术事实 | 自行调查，引用依据 | 让用户作专家判断 |
| HJ-11 | UI 修改不改变功能，但降低用户体验品质 | Quality Preservation 捕捉退化 | 仅凭功能测试声明完成 |
| HJ-12 | 同一任务始终回答 Agree | 不声称用户已独立理解；减少无信息的提问 | Agree 次数被当成能力或质量证据 |

推荐指标：
- **Human Judgment Yield**：用户的回答有多少真正新增了目标、偏好、责任或风险边界的信息；
- **Uninformative Approval Count**：没有增量判断的技术 Agree 次数；
- **Authorized Prototype Progress**：在不越权前提下，进入可试用原型的交互成本；
- **Gap traceability**：Gap → Decision → Evidence → Implementation 的可回溯完整度；
- **False Understanding Attribution**：把“未声明理解”写成“已确认不懂”或“已经理解”的次数；
- **Authorization Violations**：是否越过预授权边界；
- **Quality Retention**：用户原始体验品质是否被保存与复核。

测试要记录模型、Skill 版本、工具权限、输入、会话历史与人工判定依据。**Bundle Tests 证明的是图契约，不是 Human Judgment 行为有效。**

---

## 7. P2 — Quality Preservation 的已知漏报仍在

本次没有修改 [`references/model.md`](../references/model.md)，此前提出的漏报仍存在：

当前检查在责任边界变化、提出功能/品质取舍或 Handoff 时触发。但有时技术方案不知不觉改变了用户可观察的工作流，功能仍然通过，Agent 甚至不觉得自己牺牲了 Quality。

例如光谱工作台的“直接操作科学对象”要求，可能在引入多个 Modal / Drawer 后被破坏，但这并不总被视为责任转移或明确取舍。

建议新增**影响现有 Quality 的用户可观察交互/工作流变化**这一触发条件；检查只针对相关 Quality，并在品质牺牲**被批准之前**进行。不需要每个文件改动都执行，也不需要新增强制 Graph 字段。

---

## 8. P2/P3 — 小型一致性和维护问题

### 8.1 安装卸载后的命名空间根目录可能残留

`scripts/install_plan_graph.py` 记录并清理了 `_aiHumanInteract/plan/` 和其子目录，但是上层 `_aiHumanInteract/` 由 `mkdir(parents=True)` 隐式创建、没有加入 `created_dirs`。新安装后卸载，即使 `plan/` 被删干净，空的 `_aiHumanInteract/` 仍可能存在。

这不是数据安全问题，甚至与“不碰用户的 sibling knowledge 目录”原则一致；只是如果要求卸载精确回滚，需要决定是否安全记录并尝试删除**仅当为空且由安装器创建**的上层目录。属于较低优先级，不应为了清理父目录误删 Knowledge Debt 文件。

### 8.2 DEC-002 头部历史授权表述可能误导后续 Agent

[`DEC-002`](../decisions/DEC-002-authorization-and-knowledge-location.md) 头部说“本记录不构成对 `_plan/` 迁移的实施授权”，后文又记录维护者**随后单独授权并实施**，其实不矛盾，但初次读取可能误认“迁移仍未经许可”。

建议将头部表述为“**初始决策本身不授权迁移；后续已另行授权，见实施记录**”，清楚保留历史时序。

### 8.3 “知识目录已落地”与实际文件存在的区别

`_aiHumanInteract/knowledge/` 是**目标项目的可选位置**，不是当前 Skill Repository 必须自带的目录。DEC-002 中的“`plan/` 与 `knowledge/` 同处一根目录”可明确为**采用约定后的目标结构**，不要让 Agent 误以为所有安装都必须自动创建 Knowledge 目录。

### 8.4 评审文件中的示例链接

上轮 Review 内部有一条虚构的示例 `DEC-012` 链接，用于说明 Knowledge Debt Record。它不是仓库中的真实 Decision。可以把它明确标为“示例路径（无实际文件）”，免得链接校验脚本误报。该例子**不构成本次提交的运行时缺陷**。

---

## 9. 建议的修复执行次序

建议交由 Coding Agent 分成几个可审查的独立变更，而不是在一个超大补丁中同时改 Prompt、Schema、Installer 和所有测试。

### Phase 1 — v4 correctness（优先）

- 修正 `source_of_truth` 的 Repo-relative 语义；重生成视图；
- 补路径存在性/一致性语义测试；
- 加强 v3/v4 并存检测；
- 保留现有已安装文件 Hash-Ownership、防覆盖与手工冲突协调保护。

**完成标准**：机器发现路径正确；任何未裁决双树都不能静默通过。

### Phase 2 — migration positive path（上线升级前必须）

- 选择自动或明示手动升级策略；
- 构造真实合法 v3 Fixture，涵盖工具、Manifest、治理片段、源节点、证据和用户改动；
- 编写完成迁移、失败保护和恢复路径；
- 用该 Fixture 真实执行并验证完整 v3→v4；
- 文档步骤与代码行为一致，能从干净 v3 安装成功达到 v4。

**完成标准**：可再现的正向升级测试，而不仅是拒绝旧版。

### Phase 3 — Knowledge Debt interaction（小范围文档改动）

- 明确已有授权时技术报告/理解分拣默认不阻塞；
- 把“未声明理解”与“明确自述不理解”区分；
- 只对会改变方案且有长期后果的选择报告，不自动强制建立词典；
- 确认新授权边界仍是硬约束。

**完成标准**：一句“这部分不懂，先做可逆 Prototype，帮我留个标记”不会进入学习/批准循环。

### Phase 4 — behavior evaluations

- 加入 HJ-01 到 HJ-12 的最小行为 Fixture 和 Rubric；
- 对比基线和新版，报告失败用例而不是仅提供成功 Transcript；
- 在真实的科研 Agent/UI 项目中评估认知摩擦和 Quality Retention；
- 只在证据证明必要时扩展 Decision Impact Tracing / Knowledge indexing。

---

## 10. 给实施 Agent 的验收清单

- [ ] 以 `7eaab8d` 为评审基线，但实施前重新读取 `main` 并核对后续变化。
- [ ] 严格区分**已由源码确认的问题**与**需要实测的行为假设**。
- [ ] 不将“旧版拒绝测试通过”宣称为“旧版可迁移”。
- [ ] 不强制覆盖经过修改的旧工具/Plan Nodes，迁移前有明确的可恢复方案。
- [ ] 检查迁移后的 Manifest、Governance Block、Source Node Links、Evidence、Generated Views。
- [ ] `graph.json.source_of_truth` 和节点 `source` 必须有统一且明确的路径语义。
- [ ] 如果同时存在 v3 和 v4 计划树，不能静默选择其中一个。
- [ ] Knowledge Debt 记录不能代替执行授权，也不能代替独立验证。
- [ ] 未声明理解不能被 Agent 写成用户已确认无知，Agree 也不是技术正确性的证据。
- [ ] 已授权的可逆技术工作不应每轮因为技术理解列表而暂停。
- [ ] 新 Knowledge Debt 文件不是默认学习清单，复用目标项目已有的文档体系。
- [ ] 不为了修复目录迁移而额外修改科学/业务 Domain Schema。
- [ ] 给出真实命令、测试输出、Diff、失败/回滚说明、遗留风险。
- [ ] 除非另有明确授权，不要顺手引入 Ontology、第二套 Graph、强制学术语流程或大型 UI。

---

## 11. 设计上的最终判断

本次提交在“人与 Agent 的认知责任如何分配”上，已经比 `grill-me` 的传统 Decision Interview 更进一步。Human Judgment Frontier 的价值，在于让人类表达自己最了解的——目标、使用感受、可接受后果和领域判断——而不是背书全部技术细节。Knowledge Debt 则让这类协作保留长期的质疑权和回溯能力。

**但哲学上越强调可追溯与人类自主性，工程上的迁移、路径与证据契约就越要可靠。** 一个新 `graph.json` 指向不存在的源目录，或者升级文档无法升级真实 v3 项目，会直接破坏 Skill 原本承诺的 Traceability。

因此建议：

> **保留 Human Judgment 与 Knowledge Debt 的最小行为模型；先完成 Plan Graph v4 的可验证迁移闭环，再通过真实 Prototype 任务测量认知摩擦是否下降。**

这样既不丢掉新的设计思想，也能避免“概念越来越完善，底层契约却逐渐脆弱”的反效果。

---

### Handoff

本文是一次**审查提交**。它不代表自动批准修复上述全部事项。未来 Coding Agent 应先阅读 [AGENTS.md](../AGENTS.md)、[DEC-002](../decisions/DEC-002-authorization-and-knowledge-location.md) 及当前实现，并按维护者批准的 Phase 小范围实施、运行相关测试，再提交可复核的结果。

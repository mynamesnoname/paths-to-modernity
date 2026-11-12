# Paths to Modernity — 从 Skill 到人机交互、状态与执行基础设施

> **日期**：2026-11-12  
> **文档性质**：架构 Review 与后续实验计划，**不是实施授权**。  
> **审查基线**：[dd10271](https://github.com/mynamesnoname/paths-to-modernity/commit/dd10271c6438b90cf64a34cd4d13535cf54f3165)（本次讨论时的 main）。  
> **前置资料**：[人类判断与 Knowledge Debt Review](2026-11-10-human-judgment-knowledge-debt-review.md)、[Plan Graph v4 / Protocol Adoption Review](2026-11-11-post-7eaab8d-code-and-behavior-review.md)、[DEC-003 协议采纳](../decisions/DEC-003-protocol-adoption.md)。  
> **范围说明**：本文件总结近期关于 PtM、脚本化、可扩展 Agent、Compact、未来多 Skill 体系的讨论。有关 dsh、pi 和特定 Harness 的扩展/注入细节均应以目标运行时的实际 API、权限与测试为准；本文不声称已经验证这些平台的具体生命周期 Hook。

## 0. 核心定位与判断

**PtM 的根本目标不应仅定义为 Planning，而应定义为对 Agent–Human Interaction 与 Agent State Management 的重新设计。**

它既不只是一个让 LLM 规划得更好的 Skill，也不应最终发展为所有规则、工具、文档和知识都塞在一个 Context Window 里的庞然大物。

PtM 试图改变两个相互依赖的基本机制：

1. **Agent–Human Interaction（人机交互）**：把正确的问题交给能提供有效判断的一方。人类提供目标、体验、价值、授权与可接受后果；Agent 负责技术调查、解释、推理与有边界的决策；程序负责确定性维护和检查。避免让人反复对无法独立验证的技术方案说 Agree。
2. **Agent State Management（Agent 状态管理）**：将长期有效的规则、项目知识、当前进度和生成视图分开，使用可寻址、可验证、可恢复的持久记录，使 Agent 不必依靠完整聊天历史就能继续一个长期项目。

围绕这两个目标，应采用**渐进式能力迁移**：

> **Human judgments → Agent reasoning → Deterministic software**  
> 把人的注意力保留给真正需要人的判断；把 Agent 的推理预算保留给真正需要解释与推理的事情；把可重复、可验证的结构维护交给程序。

### 核心结论

- **Skill 是方法与能力声明，不是唯一的实现介质。** 规则可以放在 Skill/References，确定性行为可以落到 CLI 脚本；在支持用户扩展的 Agent（如维护者考虑的 dsh/pi 一类）中，部分功能还可以交给本地插件或运行时 Hook。
- **插件不是“更高级的 Skill”，而是另一种执行与集成机制。** 它可以改善生命周期响应、工具调用与自动状态保存；并不能代替人类价值判断、LLM 的解释性推理或授权。
- **General Agent 也能从脚本获益。** 即使无法安装插件，只要 Agent 可以调用文件和命令，就能借助确定性脚本完成索引、验证、视图生成、Checkpoint 操作；如果连命令执行也不支持，则退回 Markdown/项目指令/既有工具能力，不宣称自动化已生效。
- **规模问题的正确指标不是 PtM 总字数，而是同等工作质量下的最小上下文、恢复成本和人为操作负担。**
- **优先实现可靠的 Discovery、Integrity、Recovery，再考虑广泛 Skill 拆分和复杂的跨域图。**

---

## 1. PtM 应处理的三种不同劳动

| 责任层 | 核心输入 | 典型工作 | 不应代替 |
| --- | --- | --- | --- |
| **Human** | 目的、使用体验、偏好、可接受后果、明确授权 | 确认目标、验收原型、裁决责任/不可逆取舍 | 对缺乏判断依据的技术细节反复签字 |
| **Agent** | 用户意图、项目证据、规范、工具结果 | 识别歧义、综合证据、提出方案、判断质量、解释不确定性 | 把脚本能验证的事情当成纯语言猜测 |
| **Software**（脚本/插件/工具） | 结构化文件、源码、状态、规则、事件 | 索引、搜索、校验、依赖提取、生成 View、追踪差异、持久化操作 | 猜测人的价值判断；仅靠路径或关键词证明语义因果 |

关键不是“能写脚本就必须写”，而是判断任务是否**高频、确定、可测试且容易人工出错**。一次性、小规模、技术上很简单的操作，不需要为了工具化额外建框架。

### 两个相互对称的 Frontier

**Human Judgment Frontier**：什么问题真的需要人来答？事实可查、技术方案可验证时，Agent 优先处理；涉及价值、体验、权限和重要后果时，交由人类。

**Agent Reasoning Frontier（候选术语）**：什么工作真的需要 LLM 的开放式推理？如果结果可由明确输入和规则确定，优先考虑软件；只把歧义解释、证据综合、创造性设计、边界判断留给 Agent。

两者并不意味着 Agent 可以绕开授权。**从 LLM 推理迁到确定性软件只改变执行方式，不改变谁对后果有决定权。** 例如脚本能执行数据库迁移，也不意味着它自动拥有生产环境迁移权限。

---

## 2. 不必把所有能力都放在 Skill 里

PtM 可能出现三种实现表面（execution surfaces），它们可以共存：

| 表面 | 主要职责 | 优势 | 边界与风险 |
| --- | --- | --- | --- |
| **Skill + References** | 解释、行为原则、任务路由、非确定性的决策方法 | 便携、能在多种 Agent 中阅读 | 依赖模型遵循；Compact 后是否再次加载不保证 |
| **Scripts / CLI** | 确定性文件操作、校验、查询、图生成、Checkpoint 管理 | 可测试、可复现、跨 Harness 相对通用 | 需要执行环境和访问权限；不能自动得知未持久化意图 |
| **Plugin / Extension / Hook** | 运行时事件、命令注册、自动恢复入口、状态变更触发 | 可以在支持扩展的 Harness 中减少人工步骤 | 平台依赖、权限与生命周期差异；不应假设所有 Harness 都支持相同能力 |

### 对可扩展 Agent 与 General Agent 的不同策略

在 dsh、pi 等**可安装用户插件的运行时（具体 API 待核验）**：
- 优先尝试把可可靠捕获的 Session/Tool/Compaction/项目切换事件接入插件；
- 可由插件调用同一套 CLI/Library，执行 Checkpoint 更新、状态校验和索引刷新；
- 插件只做事件适配层，**不要再实现一套独立业务契约**；
- 验证 Hook 是否真的被触发、何时触发、能读取哪些状态、失败是否可见、是否会干扰正常任务。

在没有插件能力但能执行脚本的 General Agent 中：
- 保持短 Skill 入口，调用相同 CLI，例如 find / related / validate / resume；
- 用项目级可发现的指令（如适用的 AGENTS.md）定位协议；
- 通过关键事件显式调用 checkpoint 更新/验证命令；
- 当执行权限或命令工具不可用时，不得假装脚本已运行；降级为阅读项目记录并报告未能自动校验的事项。

**同一领域逻辑复用，多种 Harness 适配。** 可考虑“纯 Python 核心 + 命令行入口 + 薄插件适配”，避免出现 dsh 一套状态语义、pi 一套、General Agent 又一套。

---

## 3. 持久知识、运行规则、当前任务状态必须分开

| 层 | 典型存储 | 是什么 | Compact 后怎么恢复 |
| --- | --- | --- | --- |
| **Protocol** | Canonical Asset → 项目级 AGENTS.md 等 | 最小协作不变量、能力路由、恢复入口 | 利用 Harness 可发现的持久指令；不同平台须实测 |
| **Skill Knowledge** | SKILL.md / References | Inquiry、Model、Alternatives、Knowledge Debt 等方法与规范 | 按需重新发现与加载 |
| **Project Knowledge** | Plan、Spec、Design、Docs、Decision、Code、Knowledge | 项目的事实、规范、设计原因、已做判断 | 通过索引/引用定位权威来源 |
| **Active State** | 可选 state/active.md 或项目已有任务机制 | 当前目标、关键进展、未决项、下一动作与指针 | 读取、核验版本与权限后继续 |
| **Generated Views** | graph.json、graph.canvas、reverse index | 可计算的目录、关系和可视化 | 必要时重新生成或校验 |

这一分层已经在近期仓库更新中初步出现：当前有 [协议资产](../assets/protocol/AGENTS.protocol.md)、[Checkpoint 模板](../assets/protocol/state-active.md)、[adopt 脚本](../scripts/adopt_project.py) 和 Plan Graph v4。

**但“安装了恢复入口”不是“运行时一定维护了新鲜 Checkpoint”。** 后者需要执行策略和实际测试。

### 状态管理不应退化成另一份巨大的摘要

Active State 的唯一任务是把 Agent 带回有效的任务上下文：

\`Current objective → Governing records → Verified progress / uncertainty → Next action\`

它不是复制完整聊天记录，不是把整个 Spec/Plan/Design 重新转写成一篇长文，不自动授予新的执行权限。已经被记录在权威文件中的信息只留指针。

长任务、多 Agent 并行时应考虑单个 active.md 的写入竞争与最后写入覆盖，而不是假定永远只有一个 Active Session。

### Compact 与恢复的分工

- **Agent**：识别重要新决策、开放的不确定性和真实的完成进度；这些判断不总能由脚本发现。
- **Script**：结构化写入、检查字段、验证引用、记录快照/哈希、拒绝危险覆盖。
- **Plugin**（如可用）：在真实可捕获的生命周期事件上触发保存/验证；处理异常与重试。
- **Agent on resume**：核对是否为当前任务、权威记录是否变化、原授权是否仍适用，随后按需加载能力而非无条件执行旧 Next Action。

对于无法预知何时 Compact 的 Harness，**关键事件持久化**比“等 Compact 前再写文件”更可行。强制模拟 Compact / 新会话续接应成为回归评测的一部分。

---

## 4. 新一代 PtM 的目录与 Capability 边界

维护者正在规划：
- **scripts-to-modernity**：由项目源码和明确的设计信息生成代码结构依赖图及 Canvas；
- **spec-to-modernity**：持久化重要 Spec 与不变量，管理版本、引用和影响；
- **design/**、**docs/**：保存设计原因和文档；
- 已有 **plan/**、**knowledge/** 和 **state/**。

这意味着 **PtM 可以是整个 Capability Ecosystem 的名称，而不是一份要全量装载的超级 SKILL.md**。

建议的逻辑结构（仅示意；不要求立刻建目录或迁移）：

~~~text
_aiHumanInteract/
  README.md                    # 极短的 discovery 入口
  state/
    active.md                  # 可选、按关键事件维护
  plan/
    ...                        # 现有 v4 契约
  scripts/
    structure/
      graph.json
      graph.canvas
  specs/
    ...
  design/
    ...
  docs/
    ...
  knowledge/
    ...
~~~

### 三种依赖关系不应混成一张图

1. **Plan Graph**：工作目标、分解、先决条件与验收。
2. **Scripts / Architecture Graph**：代码组件、调用、导入、接口与实现结构。
3. **Spec 关系**：行为规范、契约依赖、约束与版本关系。

三种图可以共享可视化技术，但边的语义不同。**Canvas 是 View，不是 Source of Truth。** 应尽量生成视图，不要让 Agent 手动修改一张与源数据并行的“第二真相”。

跨域关系以少量明确链接组合，而非马上创建强制同步的大型总图：

~~~text
WP-017 --implements--> SPEC-008
SPEC-008 --governs--> FeatureSelectionService
FeatureSelectionService --implemented_in--> src/feature_selection.py
~~~

应区分 **Declared / Observed / Inferred**：
- 明确声明的引用：可通过文件核验；
- AST/静态分析观察到的依赖：可重复但可能不完整；
- Agent 推断出的架构语义：需证据与审核，不能冒充源码事实。

---

## 5. 脚本化候选清单：按跨模块价值排序

| 优先级 | 能力 | 适合确定性程序做的事情 | 留给 Agent 的部分 |
| --- | --- | --- | --- |
| **P0** | **Ownership & Safety** | 检查 Manifest、创建者、内容 Hash；防误删、防覆盖、Dry Run、差异预览 | 判断冲突如何协调、是否授权影响外部状态 |
| **P1** | **Project Discovery** | 扫描已存在资源、提取稳定 ID、生成轻量索引、按 ID 查找 | 推断不明确的任务关联 |
| **P1** | **Reference Integrity** | Markdown 相对链接、唯一 ID、路径是否存在、引用版本、反向索引 | 判断两份文件是否语义矛盾 |
| **P1** | **Session Recovery** | Checkpoint 格式/指针校验、变更提醒、生成短恢复报告 | 判断新旧决策和授权是否适用 |
| **P1** | **Plan Graph** | 安装/迁移、Schema 验证、依赖图、生成 JSON/Markdown/Canvas | 决定应如何分解工作、哪些依赖有意义 |
| **P2** | **Scripts to Modernity** | AST/配置扫描、静态调用或 import、Graph/Canvas 生成 | 模块责任、架构解释、设计建议 |
| **P2** | **Spec to Modernity** | ID/版本/链接验证、变更影响索引、Superseded 记录 | 规范含义、冲突裁决、验收意图 |
| **P2** | **Knowledge Debt** | 创建模板、检索、关联 Decision、生成反向引用、检查可观察重访触发 | 识别人类真实疑问、解释技术选择 |
| **P3** | **Incremental Update** | 根据变更集合增量重建相关索引或图 | 判断语义影响范围是否需要扩展 |

**先补安全基础**：截至本 Review 基线，上轮源码审查仍指出 [adopt_project.py](../scripts/adopt_project.py) 的卸载可能误删原本存在、但与模板内容完全一致的 AGENTS.md Block 或 CLAUDE.md；[migrate_plan_graph_v3.py](../scripts/migrate_plan_graph_v3.py) 可能覆盖用户曾在 v3 Governance Block 内加入的规则。这些风险需要独立修复和测试，不能被“新增了插件/CLI”掩盖。请在实施前重新检查最新代码，避免沿用过期结论。

---

## 6. 一个轻量公共 CLI，而不是立刻建立庞大框架

可以先定义候选交互表面，实际命名与参数留待设计：

~~~text
ptm index
ptm find SPEC-008
ptm related WP-017
ptm validate
ptm resume
ptm checkpoint validate
ptm graph plan
ptm graph scripts
ptm spec impact SPEC-008
ptm knowledge trace event-sourcing
~~~

这些都是**拟议的用户体验示例，目前不代表仓库已实现这些命令**。

为什么公共 CLI 有价值：
- 能让 Agent 直接指代稳定对象，不用“打开文件夹 → 逐个搜索 → 读取全部内容”。
- 用单次结构化输出缩小 Agent 的上下文邻域。
- 同样的底层逻辑可由命令行或插件调用。
- 错误、测试、权限和输出协议可以被统一审计。

**为什么不应立刻把所有脚本合并成大包**：Plan Graph、Spec、Scripts、Knowledge 的语义正在演化。可以先保留现有独立脚本，增加极薄路由层，等使用模式稳定后再决定公共 Library 的边界。

### Context Neighborhood 而不是全量文件遍历

完成一个局部任务时，建议：

1. 读取极短 Project Index / Checkpoint；
2. 查找目标对象（稳定 ID、路径、明确标签）；
3. 加载直接相关的 Spec、Code、Plan、Decision；
4. 接口变更时展开至调用者或被依赖方；
5. 只有涉及范围/责任/重大技术前提时再读 Design 历史；
6. 发现矛盾或不确定性后才触发更深层的 Agent 分析。

**目标不是“PtM 项目只有几十 KB”，而是“一次有意义的工作只需加载有用的几十 KB 或更少”。** 实际预算应由测量决定，而不是任意设置文件大小上限。

---

## 7. Plugin 应该替代 Skill 的哪些功能？

对于有扩展系统的 Agent，适合移出纯自然语言提示的部分主要是**生命周期与重复维护动作**：

| 行为 | 推荐位置 | 说明 |
| --- | --- | --- |
| 何时保存 Checkpoint | Plugin Hook（如存在）+ 明确的项目规则 | Hook 能减少忘记更新，但不能凭空产生用户未表达的决策 |
| Checkpoint 文件写入/验证 | 共用 Script/Library | 统一语义、Hash、冲突策略 |
| Session 恢复时发现项目 | Plugin 或 CLI + Protocol pointer | 不要默认所有 Harness 都重新注入 AGENTS.md |
| Plan/Spec/Script 的文件引用校验 | Script/Library | 纯确定性 |
| Canvas / Reverse Index 生成 | Script/Library | 生成视图，而不是人工第二来源 |
| 技术证据综合、歧义分类 | Skill/Agent | 仍是推理工作 |
| 人类价值、接受后果、授权 | Human + Agent 协商协议 | 插件只能记录明确授权，不得生成授权 |
| 对重要 Quality 的主观审查 | Agent + Human | 程序可以提示何时审查，不能替用户判断体验好坏 |

真正的架构收益是：**同一套 PtM 语义具有多个运行时 Adapter，而不是在每个 Agent 中重新发明 PtM。**

### 错误模式应成为协议的一部分

插件和脚本都可能失败：
- Hook 没有触发；
- Checkpoint 写入被权限阻止；
- 多进程覆盖 active.md；
- Index 与真实文件不同步；
- 文档链接指向了被移动的 Spec；
- 插件与 CLI 使用不同版本的状态 Schema；
- 缺少外部授权却自动执行了一个脚本。

应提供可见失败、版本/来源信息和可恢复路径。**Failure must be explicit**；不能因为使用插件就把系统变成黑箱自动化。

---

## 8. 必须优先解决的工程问题与治理边界

### 8.1 安全所有权

任何 Installer/Adopter/Migrator/Uninstaller 都必须区分：
- 文件/Block 是否由本工具创建；
- 内容是否未经修改；
- 是否属于用户现有治理；
- 本次操作是否在已授权的范围内。

内容相同不是所有权证明。生成和升级机制的成功，并不能自动证明卸载安全。

### 8.2 三重分离

**Authorization ≠ Understanding ≠ Evidence**。记录 Knowledge Debt 不授权；用户 Agree 不证明正确；脚本返回成功也不说明结果符合用户最初想要的体验。

### 8.3 生成与权威

对 Plan、Spec、Code、Design、Knowledge 建立明确 Source-of-Truth；索引/Canvas/Checkpoint 不得成为第二份可单独修改的权威事实。

### 8.4 不强迫文档扩张

新增设计文档的收益要大于维护成本：
- 一项局部决定在现有 DEC 中就能说清时，不建第二份 Design；
- Knowledge Debt 按需捕获，不为每个术语建百科文件；
- 多 Session Checkpoint 应简短，指针优先；
- 反向引用由程序生成，不要求两端手工重复维护。

### 8.5 普适降级

最小共同功能是**持久可读记录 + 显式路径 + 可以手动或脚本验证的契约**。Plugin、Hook、CLI 都是增强能力，不应导致无法安装插件的 General Agent 完全失去基本 PtM 方法。

---

## 9. 分阶段实施建议（供未来明确授权后的 Agent）

### Phase 0 — 保留当前架构，修安全漏洞

- 重新确认当前 HEAD 的 Ownership 与 Governance 保护问题是否仍存在；
- 加入“预先存在且内容相同的 AGENTS Block / CLAUDE.md 必须保留”的卸载测试；
- 对旧 Governance Block 的迁移加入用户修改检测；
- 不顺手拆 Skill 或变更 Plan Graph v4 Schema。

### Phase 1 — Discovery + Integrity（脚本优先）

- 选定一个真实项目；
- 从现有权威 Markdown 和代码中构建**最小索引**：ID、kind、path、status（有语义时才设）、显式引用；
- 实现 find / related / validate（或同等能力），反向链接从明确正向链接生成；
- 测试文件移动、ID 冲突、悬空引用、未安装某 Capability 的情况；
- 不建立中心大图，不复制 Spec 或 Decision 正文。

### Phase 2 — Recovery（行为与工具同时验证）

- 保持已有 Protocol Adoption 和 active.md 概念；
- 定义最小 Checkpoint Update/Validate/Resume 过程；
- 用真实长任务测试关键事件保存 → 模拟 Compact/清空会话 → 新 Agent 恢复；
- 评价旧记录是否过期、工作是否继续、重复向人类提问、是否误用旧授权；
- 先测 General Agent + Script 基线，再单独试可扩展 Agent Hook，确保能归因。

### Phase 3 — Plugin Adapters（按运行时能力增量）

- 逐一核验目标 Harness 的生命周期事件和 API；
- 只把可靠的事件捕获、命令注册和自动脚本触发加入 Adapter；
- 不复制实现业务规则；
- 对 Hook 未触发、权限失败、重复事件和多 Session 冲突设计测试。

### Phase 4 — Domain Capabilities

- scripts-to-modernity：从源码/构建声明导出 Observed edges；Agent 可补 Interpreted edges（必须标注证据）；Canvas 自动生成；
- spec-to-modernity：规范 ID/状态/版本、引用验证、影响查询；
- Knowledge Debt：最小 Capture / Trace / Revisit 与 Decision 交叉引用；
- Plan Graph：独立 Skill 包装可在测试证明收益后考虑，但不重新迁移目标仓库的 v4 目录。

### Phase 5 — 对照评估

对照三组或四组配置：

| 版本 | Skill 组织 | 运行时辅助 | Checkpoint |
| --- | --- | --- | --- |
| A | 当前单 Skill + References | 现有脚本 | 现有规则 |
| B | 相同 Skill | 增加 Discovery / Integrity / Resume CLI | 验证并稳定保存 |
| C | 相同 Skill | CLI + 已核验的插件事件适配 | 同 B |
| D（可选） | 拆分独立 Capability Skills | 与 B/C 等价 | 同 B/C |

指标：任务质量、总 tokens、重复读取、人工 Agree 次数、Human Judgment Yield、恢复成功率、Checkpoint 新鲜度、引用完整性、错误/越权操作、文件数与维护负担。优先使用真实任务，避免只测“程序输出文本是否与预期相同”。

---

## 10. 实验与回归测试矩阵

以下为**建议**用例，非已通过的测试：

| ID | 场景 | 期望 |
| --- | --- | --- |
| EX-01 | 需求有两个合理 Outcome | Agent 通过 Inquiry 识别并向有权者确认 |
| EX-02 | 实现细节可由代码和测试决定 | Agent+工具处理，不让用户盲目 Agree |
| EX-03 | 用户明确只授权本地可逆原型 | 脚本/插件只能在此范围内工作 |
| EX-04 | 没有插件，但有脚本执行能力 | Project Discovery/Validation/Resume 可运行 |
| EX-05 | 没有插件、没有命令执行 | 回退阅读协议和文档，显式报告自动验证不可用 |
| EX-06 | 更新 Spec 后立即恢复旧 Checkpoint | 显示权威文件已变，不机械执行旧计划 |
| EX-07 | 无法捕获 Compact 事件 | 通过关键事件持久化，仍能大致恢复 |
| EX-08 | 多任务同时更新 active.md | 不静默覆盖，提示归属/版本冲突 |
| EX-09 | 一个 WP 链接一个 Spec、多个实现 | find/related 只返回有来源的关系 |
| EX-10 | Script Canvas 的某条边来自 Agent 推断 | 标注 Inferred/证据，不标成静态观察 |
| EX-11 | 预先存在且与模板完全相同的文件 | 安装再卸载后保留原有文件 |
| EX-12 | v3 Governance Block 被人工编辑 | 迁移拒绝覆盖并给出可复核差异 |
| EX-13 | Knowledge Debt 提到理解缺口 | 不把缺口当授权或缺失证据的证明 |
| EX-14 | 自动脚本失败或 Hook 未触发 | 明确可见，不宣称状态已保存 |
| EX-15 | 局部任务，只需一份 Spec 和一小片代码 | 不读取全量 Design/Plan/Knowledge |
| EX-16 | 同一任务分别在 A/B/C 运行 | 对比总成本、正确率和恢复能力，不只比较 Prompt 长度 |

---

## 11. 未来 Coding Agent 的操作边界

- [ ] 本 Review 是设计建议，不表示已授权执行这些 Phase。
- [ ] 实施前读取实际最新仓库；较早 Review 中的 bug 可能已修复。
- [ ] 首先保护用户数据、用户治理和已有授权；不要把自动执行当成自动授权。
- [ ] 共享语义与数据契约只有一个权威版本，CLI 和插件均复用同一实现。
- [ ] 未经实测不声称插件 Hook 或 AGENTS.md 会在所有 Harness 的 Compact 中自动恢复。
- [ ] 使用 Source of Truth 生成索引、Canvas、反向引用；不要求多个文件手工同步一条事实。
- [ ] Source、Declared/Observed/Inferred relationships、Evidence 的区别应可查询。
- [ ] 不把 Knowledge Debt 自动转成强制学习 WP。
- [ ] Checkpoint 不包含完整聊天记录或复制大量权威文档。
- [ ] 验收测试必须验证失败保护、回滚及低权限 General Agent 的降级路径。
- [ ] 不为了扩展脚本而引入无必要的集中 Ontology、跨域单一 Schema 或新的目录迁移。
- [ ] 让用户审阅的是影响 Outcome、Quality、Risk 和 Permission 的问题，不是每个 CLI 参数。

---

## 12. 最终结论

**PtM 更适合被理解为 Human–Agent Collaboration & State Infrastructure。**

它的价值不是保存越来越复杂的一组 Skill，而是构建一种可持续的协作方式：让人控制目的与后果，让 Agent 负责理解与技术推理，让确定性软件维护结构、关系与状态，让所有参与者都能在 Context 被压缩或 Session 被中断后重新进入项目。

在可扩展 Agent 中，插件可把一部分此前依靠 Skill 文字约束的行为转成由运行时事件触发的工具；在 General Agent 中，相同能力应尽量通过脚本和持久文件提供。两条路线共享业务逻辑，而不是各自形成不兼容的 PtM。

与此前的 Human Judgment Frontier 对应，可以将本次设计归纳为另一条原则：

> **Use agents for reasoning, not for deterministic bookkeeping that software can perform reliably.**

最终衡量的不是 PtM 拥有多少 Skill、脚本或文档，而是：

> **Can a human and an agent keep making meaningful progress with minimal unnecessary approvals, minimal redundant context, reliable state recovery, and explicit authorization?**

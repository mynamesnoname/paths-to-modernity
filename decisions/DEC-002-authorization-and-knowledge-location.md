# DEC-002 — 授权语义与知识目录位置

- **状态：** accepted（2026-11-11）
- **决策人（decision owner）：** 仓库维护者
- **范围：** 回应第二轮评审 [`reviews/2026-11-10-human-judgment-knowledge-debt-review.md`](../reviews/2026-11-10-human-judgment-knowledge-debt-review.md) 的 Phase B/C；并裁决讨论中提出的两项新问题（沉默是否构成授权、知识记录与计划目录的位置关系）。
- **本记录的性质：** 决策记录，不构成对 `_plan/` 目录迁移的实施授权。

## 决策一 — 无异议不等于同意

**决策：** 沉默、未提出异议、或被报告后未回应，均不构成授权。执行授权必须被显式给出。授权可以一次性、针对一个已定义的范围预先给出（"这个原型内技术选型由你定，可逆、不触外部系统"），并在此范围内重复使用；但沉默不能扩大该范围。

因此：

- 报告"本轮用了哪些技术、各自代价是什么"是**知情**，不是**征求批准**。报告之后不能自动开工，也不能把"你没反对"记为同意。
- 将同意分为三种，并以叙述记录，不新增状态机：**Informed acceptance**（理解并认可）、**Provisional acceptance**（部分理解，授权在声明范围内可逆推进，其余依赖 agent 推理）、**Unsupported assent**（信息不足以判断的顺从）。三者都必须是给出过的，而不是推断出来的。
- 执行授权、认识状态、技术证据是三个正交维度，任何一维都不能冒充另一维。

**理由：** 维护者明确要求区分 Unsupported Assent 与 Informed Acceptance。沉默与"没读到"在观测上不可区分；把沉默计为同意，等于让最强的同意来自最弱的证据。这与 PtM 既有规则（缺失的回答不能变成同意）一致。

**已接受的代价：** 每个新范围需要一次显式授权语句；相比"报告后默认推进"多一次交互。

**重开条件：** 出现因等待显式授权而实质阻塞可逆工作的实例（连续三次以上）。

## 决策二 — 统一人机交互目录 `_aiHumanInteract/`，`_plan/` 迁入

**决策：** 知识记录放在 `_aiHumanInteract/knowledge/`；`_plan/` 的目标位置是 `_aiHumanInteract/plan/`。两者同处一个根目录，供后续架构梳理类 skill 共同引用。

**执行记录（2026-11-11 补记）：** 最初以"不在同批实施"记录在案，理由是下列事实。维护者随后单独授权，迁移已按契约变更完整执行，schema 升至 `v4`。保留当时的判断以说明代价来源：

- `scripts/install_plan_graph.py` 中 `MANIFEST_RELATIVE = Path("_plan/install-manifest.json")`，安装目标、目录创建、manifest 键名、卸载校验均为硬编码；
- `references/plan-graph.md`、`assets/plan-graph/**`、示例树、生成的四个视图、`scripts/test_plan_graph_bundle.py` 共约 100 处引用；
- 迁移属于 Plan Graph 契约破坏性变更，按 `AGENTS.md` 必须同步 spec、installer、validator、builder、模板、示例与测试，并提升 schema 版本；
- 已安装的目标仓库会在版本校验处被拒绝，需要迁移说明与手工搬移。

实际执行内容见下方「迁移实施」。

**过渡状态已结束：** `_aiHumanInteract/` 现同时容纳 `plan/` 与 `knowledge/`，与决策二的目标一致。

**命名说明：** `_aiHumanInteract` 是维护者给出的示例名，含中英混拼且非惯用英语。若日后更名，应在迁移同一变更集中一次改完，避免二次搬移。当前按此名实施。

**重开条件：** 若架构梳理类 skill 的实际需求证明二者无需同根，可放弃迁移，仅保留 `_aiHumanInteract/knowledge/` 或退回仓库根的 `_knowledge/`。

## 本轮实施范围

| 项 | 落地位置 |
|---|---|
| Human Judgment Frontier（Phase B） | `references/inquiry.md` §3「Before asking: whose information is this?」 |
| 入口提示（Phase B） | `SKILL.md` Working principles 新增一条 |
| Knowledge Debt（Phase C） | `references/knowledge-debt.md`（新文件） |
| 路由（Phase C） | `SKILL.md`「Read the needed detail」新增一行 |
| 报告式知情，非征求批准 | `references/knowledge-debt.md`「Reporting, without asking for approval」 |

未改动：`assets/`、`scripts/`、Plan Graph schema 与 `_plan/` 路径。

（后两项已在随后的迁移中变更，见下节。）

### 迁移实施 — Plan Graph v3 → v4（2026-11-11）

| 变更 | 内容 |
|---|---|
| 目录 | `assets/plan-graph/_plan/` → `assets/plan-graph/_aiHumanInteract/plan/`；示例树同构搬迁 |
| schema | `paths-to-modernity-plan-graph-v4`，installer、builder、validator、测试、模板同步 |
| 根推导 | `validate.py` 的 `REPO_ROOT` 与 `require_valid_graph` 默认值由 `plan_root.parent` 改为 `parents[1]`；`build_graph.py` 同步 |
| 安装器 | 路径常量改为 `PLAN_RELATIVE = Path("_aiHumanInteract/plan")`；新增 v3 树检测：`_plan/` 存在且新路径不存在时拒绝安装并给出迁移步骤 |
| 生成视图 | `build_graph.py` 的视图链接原为 `"../" + source.removeprefix(plan_dir_name)`，嵌套后多出一级；改为 `_structure_link()` 按 `structure/` 目录计算相对路径 |
| 回归 | 新增「未迁移的 v3 树被拒绝」用例；`unittest discover` 改为在 plan 目录内运行，避免嵌套路径下的导入失败 |
| 文档 | `references/plan-graph.md` 新增「Migrating from v3」迁移步骤；目录树重排；治理片段与示例 README 重排 |

结果：`Plan Graph v4 bundle checks passed`（12 tests）。

**未迁移的旧安装不会自动升级**，这是有意的：v4 安装器拒绝在未搬迁的 `_plan/` 旁另建一棵树，避免出现两套并存的计划。

### 补充 — 报告细化为「分拣 + 一次明示授权」（2026-11-11）

维护者提出：引入新技术时罗列技术，并提问"哪些是你理解并明确同意的"，未标记项记为"不理解但暂时接受"。经审议采纳，但修正三处，均已落地：

1. **认识状态与授权分离。** 沉默不能授权，但授权之后沉默可以降级理解状态。理由：默认"不理解"是安全的，默认"可以开工"不是。
2. **三值而非二值。** 增设"理解但不同意"，因为这是最有信息量的回答，二值形式无处安放。
3. **列表上限 3–5 且只列会改变方案的项。** 列表越长，机制越失效；无人阅读的列表会让记录下来的接受失去意义。

落地位置：`references/knowledge-debt.md`「Reporting technical choices」；`references/inquiry.md` §3 末尾一句。台账见本节上方表格，其余条目不变。

## 未决

1. ~~**`_plan/` 迁移本身。**~~ **已完成（2026-11-11）**，见「迁移实施」。
2. **授权语句的默认形态。** 本轮只确定"必须显式给出"，尚未确定它是一句话、写进项目 `AGENTS.md`、还是由知识记录承载。建议在真实项目中先试一种。
3. **报告粒度的上限。** 已规定"报告后果不报告机制、只列会约束未来的选择"，但未给出条目数的硬上限；依赖判断力，不设阈值。

## 链接

- 第二轮评审：[`reviews/2026-11-10-human-judgment-knowledge-debt-review.md`](../reviews/2026-11-10-human-judgment-knowledge-debt-review.md)
- 首轮决策：[`DEC-001`](DEC-001-inquiry-protocol.md)
- 询问协议：[`references/inquiry.md`](../references/inquiry.md)
- 知识记录：[`references/knowledge-debt.md`](../references/knowledge-debt.md)
- 图契约：[`references/plan-graph.md`](../references/plan-graph.md)

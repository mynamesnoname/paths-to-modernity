# paths-to-modernity skill 评价报告

> 评价背景：在一个实际任务中完整使用了该 skill——考察 DESI redrock 软件、为一个通用红移拟合软件制定计划并生成 Plan Graph（canvas）结构。过程中通读了全部参考文件（inquiry / model / alternatives / plan-graph / worked example），实际运行了 installer、validator、builder，生成了一套 32 节点、53 条边的 Plan Graph。
>
> 评价日期：2026-09-15。评价维度：易用性、上下文长度、结构流畅性、名词指代清晰度。

## 优点

### 1. 条件加载的路由表设计出色

`SKILL.md` 的 "Read the needed detail" 表格（何时读 inquiry / model / alternatives / plan-graph / worked example）让上下文成本按需支付。SKILL.md 本体精简，细节下沉到 `references/`——这是 skill 设计的正确姿势。本次任务实际读入 inquiry + model + plan-graph + example 约 700 行；若非 Plan Graph 任务，只需读前两个，成本控制合理。

### 2. 权责边界清晰，且正面处理了 auto 模式

`inquiry.md` 明确区分"agent 可查的事实缺口"与"只有人能拍板的价值/权责缺口"，并给出可操作的 materiality 阈值（两种合理解读是否会改变结果、责任、验收、重大风险或不可逆承诺）。

尤为难得的是它正面处理了自主模式："auto / yolo 模式下结构化提问工具不可用时，用纯文本提问并暂停等答案；缺少提问通道绝不能把人所有的决策变成 agent 的假设，只有真正可逆的假设才允许先行"（inquiry.md:96-99）。这是很多 skill 回避的问题，这里写得毫不含糊。

### 3. Plan Graph 规范工程化程度高

- schema 版本字段（`paths-to-modernity-plan-graph-v3`），消费者须先校验版本；
- 字段映射表（planning model 概念 → front matter 字段）定义精确；
- 状态机（proposed / ready / in_progress / blocked / done / superseded）与无环约束明确；
- installer 三段式：dry-run 预览、manifest 记录、基于 hash 校验的安全卸载。

实测 installer 一次成功；validator 真正抓到了生成过程中的错误（`source_requirement` 未同步进 `links`）——校验器不是摆设。

### 4. 部分表述精炼到可背诵

> "Hierarchy answers 'part of what?' Dependency answers 'must follow what?'"（model.md:52）

一句话解决了计划分解中最常见的混淆。

### 5. 双受众处理干净

skill 仓库自身的 `AGENTS.md`（维护者向）与装进目标项目的治理片段（用户向）明确分离并互相声明，这在多受众 skill 中是少见的严谨。worked example 采用"先读源、再对照生成视图"的引导路径，30 余行 README 就把消费方式讲清楚了。

## 缺点与摩擦点

### 1. 命名误导（名词指代问题最严重的一处）

"paths-to-modernity" 强烈暗示"遗留系统现代化改造"，但实际是通用的**需求澄清 + 计划分解**框架。后果：

- 漏匹配：做绿地项目规划的用户不会想到它；
- 误匹配：真要做代码现代化的用户会发现文不对题。

名称应贴近其实际能力，如 `plan-clarifier`、`outcome-planning` 之类。

### 2. 四级层级对小项目偏重

"每个活跃高层节点必须完整分解到 WP" 的硬性要求，使一个中型计划也要产生 32 个文件。规范自己承认"一般规划方法不要求四级"（plan-graph.md:74），但工具强制执行。对 3–5 个工作包就能说清楚的任务，仪式感大于收益。建议允许省略中间层（如 MT/ST 可选），或提供轻量模式。

### 3. 字段契约分散，首次使用易漏规则

节点合法性的完整规则散布在 plan-graph.md 的 "Concepts and fields"、"Source node contract"、"File links and evidence" 三节中，例如：

- `links` 必须含指向自身的 `plan` 引用，且至少还有一个其他类别；
- `source_requirement` 必须同时出现在 `links` 中；
- 根节点的 `parent` 写法（文档未明说，实践中推断为 `null` 并恰好正确）。

实际生成节点时就踩中了第二条，靠 validator 兜底才发现。建议增加一页"节点合法性 checklist"或紧凑的 schema 速查表，显著提高一次写对率。

### 4. 个别措辞含糊

- "front matter using a JSON value on each line"（plan-graph.md:113）——实际是 YAML 风格、每行一个 JSON 值，初读费解；
- `qualities` / `tradeoffs` / `perspectives` 三个概念边界微妙，model.md 解释得不错，但实操时仍需停下来判断"这条该放进哪个字段"；
- inquiry 的四步循环与 SKILL.md 的八步 workflow 有部分重叠，先后顺序要靠读者自己缝合。

## 各维度小结

| 维度 | 评价 |
|---|---|
| 易用性 | 工具链（installer / validator / builder / 测试）实测可靠，dry-run 与安全卸载完备；扣分项是字段契约分散导致首次写出合规节点较难 |
| 上下文长度 | 条件加载设计优秀，SKILL.md 精简；完整走一遍 Plan Graph 流程约需读入 700–1000 行参考材料，对复杂计划任务而言代价合理 |
| 结构流畅性 | 总体好：SKILL.md → references → example 的下沉路径清晰，锚点交叉引用完善；inquiry 循环与主 workflow 略有重叠 |
| 名词指代清晰度 | 文档内部术语（decision owner、readiness gate、skill root vs repository root 等）定义严谨；最大问题在 skill 自己的名字名不副实 |

## 总评

这是一个设计成熟度明显高于平均水平的 skill：权责模型、materiality 阈值、auto 模式降级策略都体现了对"agent 何时不该自作主张"的深思熟虑，工具链实测可靠。

主要改进空间按优先级排序：

1. **改名**——名不副实直接影响发现性与触发匹配；
2. **聚合节点契约**——增加一页合法性 checklist / schema 速查表；
3. **轻量模式**——允许小计划省略中间层级；
4. 澄清 "JSON value on each line" 与根节点 `parent` 写法等细节措辞。

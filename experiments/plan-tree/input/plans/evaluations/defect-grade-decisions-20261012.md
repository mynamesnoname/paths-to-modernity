# 决策记录 — HIGH / MEDIUM / LOW 的语义与落地

- 日期：2026-10-12
- 决策人：仓库用户（FORMA 决策所有者）
- 状态：**决策人已回答；待冻结实现契约并落实到计划、代码和测试**
- 背景：codex 在 WP-012 复核中已把问题改写成 "defect-grade contract"（缺陷分级契约），并要求
  明确区分「内部严重度分数 / 正确性概率 / 流水线最终 confidence 字段」。本清单把这组决策
  拆成 5 个单轴问题，每题给出选项、后果、影响面与默认值。

以下保留原问题、备选项及默认值以记录决策背景；每题末尾的“我的回答”是决策人的
当前选择，优先于“默认（不决定时）”。待定的测量窗口、阈值和标注协议单独列在文末，
不得因已有方向性回答而擅自填入数值。后续应同步更新
`_aiHumanInteract/plan/work-package/WP-012.md`、输出契约、代码与测试。

**已核实的事实锚点**（本会话中逐条查证过）：

| 锚点 | 位置 | 现状 |
|---|---|---|
| RA 分级的现状 | [result_auditor_skill.md:158](src/FORMA/agents/multi_agents/harness/skills/AnalysisAuditor/result_auditor_skill.md#L158) | HIGH 无问题 / MEDIUM 小问题或 ≤2 可信线 / LOW 需大改或光谱质量不允许；当前混合了缺陷严重度与证据充足度，尚未完全符合下述新语义 |
| 用户可见字段 | [report_writer_skill.md:120](src/FORMA/agents/multi_agents/harness/skills/ReportWriter/report_writer_skill.md#L120) | `in_brief.confidence` = RA 的 `calibrated_confidence`，RA 不可用时退回综合 confidence |
| 唯一的规则驱动调整 | [AnalysisAuditor.py:2001-2011](src/FORMA/agents/multi_agents/AnalysisAuditor.py#L2001-L2011) | negative 规则触发 → 记 issue + NEEDS_REVISION + **HIGH→MEDIUM**；**无 LOW 路径、无严重度累积** |
| 评估层的 tier 映射 | [SPEC.md §2/§4](evaluation/calibration/SPEC.md)、[calibration_tuner.py:35](evaluation/calibration/calibration_tuner.py#L35) | `score≥accept_t→HIGH`、`≤reject_t→LOW`，并按 0.8/0.5/0.2 当概率算 ECE → **偏差所在** |
| 缺线可探测性判定 | [harness_rules.py:110](src/FORMA/core/reasoning/ontology/harness_rules.py#L110)、[:238](src/FORMA/core/reasoning/ontology/harness_rules.py#L238)、[agent_frames.py:210-211](evaluation/calibration/agent_frames.py#L210-L211) | 用**整谱中位 SNR ≥ 1.5**；校准帧对通过该全局门槛的每条缺线写入 `detectability_ok=True`，未逐线测量；1.5 无正式规则拥有（[prompt_audit.py:183-184](src/FORMA/core/reasoning/ontology/prompt_audit.py#L183-L184) 登记为 narrative） |
| 缺线覆盖检查 | [evaluator.py:69-83](src/FORMA/core/reasoning/argumentation/evaluator.py#L69-L83) | 逐线几何检查（fit 红移 + 静止波长是否落在光谱区间）✔ |
| "ontology grade" | 全仓库搜索 | **不存在**（零命中）；本文档中它指"由规则集合算出的缺陷分级"这一**待创建对象** |

---

## 问题 1 — 单一语义确认：HIGH/MEDIUM/LOW 是否只表示"缺陷严重度"？

**问题**：这三个词是否**只**承载"当前最优假设还剩多少问题"这一种语义，不再表示"证据强不强"
或"正确率高不高"？

| 选项 | 含义 | 后果 |
|---|---|---|
| **A1 是，单一缺陷语义** | 三个词只表示问题多少；证据强度（evaluator `score`）与正确性概率各自改名、各自独立 | 评估层 `score→tier` 必须改名/重构（例如内部叫 `evidence_tier` 或 `support_band`），报告 v2 的 tier/ECE 表述需重写；KB 与综合裁决里的"证据强度"措辞也要区分 |
| **A2 否，保留多语义** | 允许"confidence"在不同上下文表示不同东西 | 用户看到的字段含义仍会漂移；codex 的 defect-grade 契约无法冻结 |
| **A3 分层命名** | 三个词只给缺陷；证据强度用另一套词（如 strong/weak/no-evidence），正确性用概率 | 命名成本最高，但长期最清晰 |

**不可协商**：若选 A1/A3，评估层不得继续用 HIGH/MEDIUM/LOW 表述"score 区间"或"正确率档位"。

**影响面**：`evaluation/calibration/SPEC.md`、`calibration_tuner.py`、`evaluator_calibration_report_v2.*`、
`docs/architecture/formal-reasoning.md`、`_aiHumanInteract/plan/work-package/WP-012.md`。

**默认（不决定时）**：维持现状（多语义并存），但**禁止**把评估层的 score→tier 结果对外表述为
"confidence 的校准"。

> **我的回答：A3。** HIGH/MEDIUM/LOW 只评价一个**已检查的候选假设**尚存的
> 缺陷：HIGH 为已执行的必要检查中未发现实质缺陷；MEDIUM 为有限、非致命问题；
> LOW 为严重缺陷，包括有充分证据的致命物理矛盾。它们不是正确概率，内部数值也
> 不具有百分比含义。HS 的证据支持强度另用 strong/moderate/weak 表示；如果使用
> 有符号 evaluator 分数，还须保留“支持/反对”的方向，不能把强反证误称 weak。
> 不存在可评估的候选假设时，分类可为 Unknown、红移为 null，缺陷等级也为 null；
> `Unknown` 不是 HIGH/MEDIUM/LOW 的第四档。HS 现有 `confidence` 混有证据、
> 竞争假设和矛盾等含义，应按新契约拆分或版本化迁移，不作简单字段改名。

---

## 问题 2 — 是否设第四档（证据不足 / 无法评估独立成档）？

**问题**：当问题是"数据不够、无法评估"（而非"有很多问题"）时，如何表示？

| 选项 | 含义 | 后果 |
|---|---|---|
| **A1 独立第四档** `INSUFFICIENT` | "证据不足/无法评估"与 HIGH/MEDIUM/LOW 并列 | 语义最干净；但用户可见字段多一个取值，需改 `output-contract.md` 与报告模板 |
| **A2 并入 MEDIUM** | 数据不足按"有一些问题"处理（当前 ≤2 LIKELY 封顶 MEDIUM 即此逻辑，[hypothesis_synthesis_skill.md:271](src/FORMA/agents/multi_agents/harness/skills/HypothesisAnalyst/hypothesis_synthesis_skill.md#L271)） | 零改动；但 MEDIUM 同时表示"有点问题"和"证据少"，用户无法区分 |
| **A3 并入 LOW** | 无法评估按"不可信"处理 | 最保守；但会把"数据不够"说成"问题很多"，与你的本意相反 |
| **A4 不设档，用独立布尔字段** | 保留三档，另加 `insufficient_evidence: true/false` 与原因 | 不改用户可见三档语义，同时可查询；agent/client 需读新字段 |

**参考**：codex 复核写道 "this review does not silently add a fourth grade"（WP-012:256）——即它**没有**
替你决定，需要你明确。

**影响面**：RA skill 定义、综合裁决 skill 的 ≤2 LIKELY 规则（`rule:formal-line-inventory`）、
`report_writer_skill.md`、`output-contract.md`。

**默认（不决定时）**：维持 A2（并入 MEDIUM），并在报告中注明"证据不足"为原因。

> **我的回答：不设第四档。** 无可信候选假设、RA 未执行或关键检查不足以给候选
> 假设评级时，最终 `confidence=null`，同时记录原因和未完成的检查；若分类本身
> 也无法确定，则 `type=Unknown`、`redshift=null`。已有但较弱的证据不等于
> “无证据”：它可记为弱证据支持；缺陷等级须看实际完成的审计，不得因未检查出
> 问题就自动给 HIGH。当前“无可信假设 → LOW”、RA 不可用时退回 HS confidence，
> 以及“光谱质量不允许评估 → LOW”的约定须按此修订。保留独立的“评级不可用原因”
> 或“审计覆盖状态”，不以 MEDIUM/LOW 偷代未评估。

---

## 问题 3 — 严重度累积规则：一个严重缺陷 vs 多个轻微缺陷

**问题**：如何把"缺陷集合"映射成三档？是否引入严重度权重与累积规则？

（现状只有一级降级：任意 negative 规则触发 → HIGH→MEDIUM，[AnalysisAuditor.py:2001-2011](src/FORMA/agents/multi_agents/AnalysisAuditor.py#L2001-L2011)）

需要决定的三个子项：

**3A 权重来源**

| 选项 | 含义 |
|---|---|
| A1 只按规则类型分档 | 硬约束（hard_constraint）> 分级诊断（graded_diagnostic）；不引入数值权重 |
| A2 每条规则带显式 severity 权重 | 在 ontology 规则记录里加权重字段（如 fatal=3, negative=1, neutral=0），可审计 |
| A3 权重由外部专家评定 | 最严谨，需额外标注工作 |

**3B 累积与封顶**

| 选项 | 含义 |
|---|---|
| B1 单一严重缺陷即封顶 | 一个硬约束违反 → 直接 LOW |
| B2 加权求和 + 阈值 | 例如 severity ≥ 3 → LOW、1–3 → MEDIUM、0 → HIGH |
| B3 只降一级（现状扩展） | 有问题 → 最多降到 MEDIUM，LOW 仅由 LLM 判断 |

**3C 两条不变量（codex 要求，建议无条件采纳）**
1. **加入一个有效缺陷不得提升等级**（单调性）；
2. **严重物理矛盾不得被大量弱支持抵消**（即支持论证不能"淹没"硬约束违反）。

**影响面**：`FormalRuleRecord`（是否加权重字段）、新的 grade 计算模块、RA 内联逻辑、
不变量测试（`tests/reasoning/`）。

**默认（不决定时）**：维持 B3（只降一级）+ 采纳 3C 两条不变量，但**不实现** LOW 的规则路径。

> **我的回答：3A 现阶段 A2，未来可用 A3 校核。** 负面规则结果应显式声明
> 严重度权重及其科学依据，便于追溯；数值权重目前只作为诊断信息，不作“权重求和后直接分档”的依据。每条规则是否属于可使评级直接 LOW 的“致命矛盾”，须单独声明，不能
> 仅凭 `hard_constraint` 类型或数字权重推断。未来可收集专家或用户判断改进这些
> 标注，但个人模型属于后续交互式 harness 的研究方向，不作为本轮验收前提。
>
> **3B 采用 B3，但对已确认的致命矛盾设明确例外。** 一般规则发现作为 RA
> 的输入和一致性检查；普通轻微问题不因条数多而自动从 HIGH 累加到 LOW，
> RA 可以根据整体证据给 LOW 并说明理由。若一条预先标记为致命的规则确实适用、
> 其所需观测已完成且可追溯、结论明确违反，则最终等级直接封顶为 LOW。
> RA 原评级、触发规则、观测依据和分歧须保留；未知、掩膜或不可观测不触发封顶。
> 这样既保留 HS 的证据判断供 RA 参考，也不允许它覆盖确定的物理矛盾。
>
> **3C 采纳。** 给定同一 RA 原评级及其余证据，增加有效缺陷不得改善
> 最终评级；严重物理矛盾不得被大量弱支持抵消。两者均需覆盖规则与最终
> 输出的测试。

---

## 问题 4 — 缺陷判定口径：缺线攻击的举证标准

**问题**：一条 `NOT_FOUND` 预测谱线，在什么条件下才算"真缺陷"（计入负面证据）？

**事实**：覆盖检查已是逐线；可探测性却用**整谱中位 SNR ≥ 1.5** 一个数适用所有线
（[harness_rules.py:110](src/FORMA/core/reasoning/ontology/harness_rules.py#L110)），校准帧构建更是写死为"可探测"
（[agent_frames.py:210-211](evaluation/calibration/agent_frames.py#L210-L211)）。因此蓝端/OH 带里本就测不到的线
也会被算成满权缺陷——BGS/69 就是"类型与红移都对、却被 11 条满权缺线攻击压到 −1.0/LOW"的例子。

**4A 举证责任（主问题）**

| 选项 | 含义 | 后果 |
|---|---|---|
| **A1 维持全局代理** | 中位 SNR ≥ 1.5 → 缺失即缺陷 | 零改动；继续可能过罚（BGS/69 型） |
| **A2 逐线举证（严格）** | 必须证明该线在**该波长**可探测才计入；证不出 → 中性 | 假缺陷最少；可能漏掉真实矛盾 |
| **A3 逐线证否（中间态）** | 只要不能证明它**不可**探测，就算缺陷 | 比现状精细，但保留过罚倾向 |

**4B 可探测性由什么构成（若选 A2/A3）**
- 局部量：预测波长邻域的局部 SNR / 噪声（窗口宽度取 ±10 Å 还是 ±50 Å？）
- 逐波长掩膜：skyline / OH / overlap 区是否参与判定
- 期望强度来源：同元素兄弟线比例（如 Hβ→Hδ）／类别模板／该处探测极限（flux 或 EW 上限）
- 阈值：几 σ；是否与现有 `LIKELY` 判据（offset<20 Å + FWHM 一致）保持一致

**4C 判不出时的默认**
- 保持**中性**（不加不减，符合三态原则）；或
- 标记为"未评估检查"单独计数（影响覆盖率统计，不影响分数）。

**不可协商**：未知/不可观测**永不**作为负面证据；判定逻辑**只实现一处**，由 harness 适配器、
auditor 适配器、校准帧构建器共用（现在三者不一致）。

**验收方式**：取 BGS/69 的 11 条缺线逐条列出 `预测波长/是否在波段内/是否掩膜/该处局部 SNR/是否计入缺陷`，
对比 A1 与所选口径的差异；再用 2–3 个已知真缺陷案例（如对照示例中被抹掉的 Lyα）确认没有放过真缺陷。

**影响面**：`harness_rules.py`、`auditor_rules.py`、`agent_frames.py`、`evaluator.py`（权重入口）、
`evaluation/calibration/` 报告、`_aiHumanInteract/plan/work-package/WP-012.md`。

**默认（不决定时）**：维持 A1；报告中对 LOW 结果注明"由 N 条缺线攻击驱动，可探测性未逐线核验"。

> **我的回答：4A 选 A2，逐线举证。** `NOT_FOUND` 只有在该线按当前假设应出现，
> 预测波长在有效覆盖内，而且在该处有足够证据证明本应可探测时，才计为缺陷。
> 无法举证时不作负面推断。
>
> **4B：综合可用的局部噪声/探测限、逐波长掩膜、该类谱线的期望强度及同系线
> 约束。** 这些因素需按谱线和情境适用性使用，不能要求每条线都具备所有来源。
> 搜索/测量窗口应依据谱线轮廓、仪器分辨率和局部背景确定；Gaussian fitting
> tool 的默认拟合窗口可作候选参考，不能未经验证直接搬用。`LIKELY` 的偏移和
> 宽度判据描述已检测特征的匹配程度，不能直接当作缺线可探测阈值。具体窗口、
> 显著性门槛和预期强度模型需在实现前冻结，并在 BGS/69 的 11 条缺线及已知
> 真缺陷样例上对照检查。
>
> **4C：中性并标记“未评估检查”。** 记录原因和审计覆盖率，不给负权重；
> 可明确证实不可观测的谱线同样不构成缺陷。共同的逐线判定结果应供 harness、
> auditor 和校准帧复用，避免各路径给出相反结论。未来真实可交互的 harness
> 可收集用户逐线判断以改进该判定，但个人模型需验证偏差、漂移和泛化能力，
> 不能取代当前可复核的物理与观测证据。

---

## 问题 5 — 最终字段关系与权威顺序

**问题**：三样东西如何共存，用户最终看到哪一个？

（三样：① 综合裁决 `confidence`（证据强度语义）② RA `calibrated_confidence`（缺陷语义，用户现在看到的）
③ 待创建的规则分级 `defect_grade`；注意 ③ 目前**不存在**）

**5A 是否把规则分级升级为一等对象**

| 选项 | 含义 | 代价 |
|---|---|---|
| A1 不升级 | 保持内联逻辑（只降一级） | 零成本；"问题多→LOW"不可执行、不可复现、不可审计 |
| A2 升级为独立 `defect_grade` | 由规则集合 + 严重度累积确定性算出，带 evidence-linked contributions 与 unknown 处理 | 需先冻结 grade 契约 + 不变量测试 |

**5B 权威顺序（LLM 判断与规则分级冲突时）**

| 选项 | 含义 |
|---|---|
| B1 RA 优先，规则只做**封顶**（现状的推广：需补 LOW 路径） | 尊重 LLM 的视觉/物理判断；规则兜底不漏报 |
| B2 规则优先，RA 只能在规则允许的档位内选 | 可复现性最强；可能压制规则未覆盖的问题 |
| B3 并列保存 + 显式分歧提示 | 信息最全；用户需自行解读两个值 |

**5C 用户可见字段**（`in_brief.confidence`）

| 选项 | 含义 |
|---|---|
| C1 保持现状（= RA 字段） | 输出契约零变更 |
| C2 改为 `defect_grade` | 语义最贴合你的本意；需版本化说明与契约更新 |
| C3 保持 RA 字段，同时在报告/JSON 中给出规则分级与缺陷清单 | 兼容现状 + 可审计；需明确谁主谁辅 |

**不可协商**
1. 用户可见字段只能有**一个**主值；
2. 三档语义唯一（与问题 1 联动）；
3. 语义变更须同步更新 KB/skill 定义与 `output-contract.md` 并记录版本（49 条共同产物**路径**不变，属字段语义变更）。

**验收方式**：取 10 个已完成运行（含 BGS/69、abstain 与 no-artifact 各若干），按所选方案产出
期望值表：每行给出 RA 原评级、规则发现及严重度、最终用户可见值、null 原因和
分歧说明（若有）。选 A1 时不存在独立的规则分级列。

**影响面**：`report_writer_skill.md`、`ReportWriter`/`in_brief` 组装、`output-contract.md`、
`AnalysisAuditor.py`、新建 grade 模块、评估报告。

**默认（不决定时）**：A1 + B1 + C1（维持现状）。

> **我的回答：5A 选 A1。** 暂不建立第二个由规则集合独立计算的
> `defect_grade`。RA 是最终缺陷评级的主要判断者；规则提供可审计的发现、
> 严重度、观测引用和确定性一致性检查。
>
> **5B 采用 B3 的信息保留意图，但不产生第二个评级。** 并列保存的是 RA 原评级
> 与规则发现，而非 RA 评级与不存在的“规则评级”。普通规则发现由 RA 综合判断；
> 满足 3B 三项条件的致命矛盾确定性地把最终评级封顶为 LOW，并显式记录分歧。
> RA 无法评级时，最终等级仍为 null；即使规则单独发现致命矛盾，也要醒目报告
> 该发现，不能伪装为 RA 已完成的缺陷评级。
>
> **5C 选 C1，保留 `in_brief.confidence` 作为唯一用户可见主等级字段，
> 但发布新版本的字段语义。** 它表示 RA 对已检查假设的缺陷评级，经过上述
> 致命规则一致性封顶；无法评级时为 null 并记录原因。HS 的证据强度是独立的
> 中间字段，供 RA 参考，不可在 RA 不可用时回填 `in_brief.confidence`。
> 如需 strong/moderate/weak，先在 HS 输出中定义其支持方向和适用条件，再传给
> RA；不把 evaluator 的有符号分数或旧 HS `confidence` 简单改名。历史
> `evaluation/baseline/output-contract.md` 保留为旧版实测基线；新增版本化契约
> 说明 nullable 值和语义变更，并同步更新 KB、skill、报告模板及消费者。

---

## 回答汇总

| # | 问题 | 我的选择 |
|---|---|---|
| 1 | HIGH/MEDIUM/LOW 是否只表示缺陷严重度 | A3：只作缺陷评级；证据强度独立，正确概率另论 |
| 2 | 是否设第四档（证据不足） | 不设；无法评级用 `null` 加原因/覆盖状态 |
| 3 | 严重度累积规则（3A 权重 / 3B 累积 / 3C 不变量） | 3A 暂用 A2 标注严重度；3B B3 且确认的致命矛盾直接 LOW；3C 采纳 |
| 4 | 缺线攻击举证标准（4A / 4B / 4C） | 4A A2；4B 局部探测证据按情境综合；4C 未证实则中性并计未评估 |
| 5 | 字段关系与权威顺序（5A / 5B / 5C） | 5A A1；5B 保存 RA 原评级与规则发现、致命规则封顶；5C C1 但版本化语义与 nullability |

**下一步**：按 1→2→3→4→5 的顺序先冻结 WP-012 的输出及评级契约，明确逐线
可探测性的窗口、阈值、期望强度依据和严重度标注，再改代码与测试。修订前的
`SPEC.md`、参数和报告保留为历史实验；其 score→HIGH/MEDIUM/LOW 及 ECE
不得表述为新缺陷评级的校准结果。若要正式验收新评级，另需预先冻结独立的
缺陷严重度标注和评估边界；已查看的 20 个样本只能作回顾性诊断。

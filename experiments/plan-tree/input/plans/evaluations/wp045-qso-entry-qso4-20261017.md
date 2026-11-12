# WP-045 — QSO 类型图入口 Q0–Q3 离线贯通（2026-10-17）

## 实施边界

从冻结 VI catalog、SH 逐线判读和当前分支的真实 FA 票构建 `cleaned_line_view`。视图按 `hypothesis_ref + line_id + measurement_id` 连接；FA `signal_present` 只确认观测信号并使 SH 的配对成为工作语义，`signal_absent` 只撤销该测量的配对，`pending`／`unreviewable` 保持未知。原始 SH/FA 产物不改写；天光风险属性不进入 QSO 视图。

新增可落盘的全局 `sh2.initial_route` 和 QSO `qso.entry`、`qso.evidence_view`、`qso.nev_pairing_gate`、`qso.broad_line_inventory` 代码节点。每次执行使用独立目录与 `node_execution_id`，节点产物及来源 SHA-256 写入 branch trace。`null` 初判只留下全局路由的 `pruned` 记录，不能产生 QSO 节点。SH 配对的 [Ne V] 且 FA 为 `signal_present` 时依 2026-10-17 决策人规则走 Type 2 `survive` 出口；未定或被否定时继续 Type 1 宽线清单。宽线清单只做覆盖预筛和受配置约束的 FWHM 汇总，不代替 Q5 严格 mask 审核或 Q9 形式门。

## QSO_4 归档重放

输入 `.data/runs/sh-fa-qso4-full-20261016/` 六份 SH 节点与 `.data/runs/fa-reality-qso4-full-20261016-v2/reasoning_branches.json` 中的 78 张真实 FA 票。`evaluation/agentic_graph/replay_qso_entry.py` 在新目录 `.data/runs/qso-entry-qso4-20261017-v4/` 中登记来源产物并顺序重放票，再运行 QSO 入口；没有新 FITS、Redrock 或 LLM 调用。入口在写入首个路由节点前校验 SH/FA 来源和后续节点所需的宽线清单；损坏来源的测试确认不会留下部分路由。

| 结果 | 假设数 | 后续 |
|---|---:|---|
| `preliminary_classification = null` | 4 | 全局路由 `pruned`，无 QSO 节点 |
| `Type 2 QSO` 且 [Ne V] SH×FA 配对已采纳 | 2 | Q1 cleaned view → Q2 `survive` → Q11 待接 |

两条已采纳 [Ne V] 使用同一个运行级 CWT feature ID `cwt:em:0001`；FA 为三票 `yes`，没有为每个假设重投。重放前逐条核对 26 个 feature 的身份、作用域、状态、票数和投票摘要，均与原归档一致；写出的新 branch tree 通过完整历史重放与执行产物摘要校验。不同分支上该测量的 yes/no 结果还由离线单元测试验证：yes 走 Type 2，no 或 pending 继续 Q3。另有合成 Mg II 宽线测试验证 Q3 只记宽度支持，不提前宣布 Type 1 存活。50 条 `tests/agentic_graph` 测试通过。

## 尚未覆盖

这个归档没有进入 Q3 的真实初判 Type 1 候选；Q3 的 `needs_q5`、宽度支持与未知宽线语义由离线测试覆盖。Q4–Q8、Q9 接线、Q10/Q11、类型图间转交和图级运行器仍待实现。Type 2 `survive` 是当前项目约定的 Q2 出口，Q11 报告尚未生成；这次归档也不检验 [Ne V] 身份或 Type 2 分类的科学准确率。

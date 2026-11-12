# WP-045 — DESI 天光邻近属性与 QSO_4 真实 FA 归档对照（2026-10-17）

## 输入与方法

- 从 `.data/runs/sh-fa-qso4-full-20261016/vi_measurements/manifest.json` 及六份冻结的 SH `node.json` 只读重建 feature registry；没有重新运行 FITS、Redrock、SH 或 LLM。
- 使用 `desispec.sky.get_sky_lines()` v0.70.0 冻结的 274 条真空、地面参考系天光线位置；生效的离散线邻近界为 10 Å，来源为 ontology 默认规则，另以注册表的 OH 波段标记区域风险。
- 逐条重放 `.data/runs/fa-reality-qso4-full-20261016-v2/reasoning_branches.json` 中的 78 张真实模型 FA 票，比较 26 个 feature 的 ID、中心、作用域、峰谷类型、最终 `observed_signal_state`、票数和 `vote_summary`。本次对照不重建旧 FA 产物链，只检验投票状态投影。

## 结果

| 天光风险属性 | `signal_present` | `signal_absent` | 合计 |
|---|---:|---:|---:|
| `near_discrete_skyline` | 2 | 5 | 7 |
| `oh_band_only` | 2 | 2 | 4 |
| `no_registered_risk` | 9 | 6 | 15 |
| **合计** | **13** | **13** | **26** |

全部 26 个 feature 的最终状态、三票票数及投票摘要与原归档一致。风险属性没有改变 FA 票或覆盖 `observed_signal_state`。例如 6564.22 Å 的 Gaussian 候选距 DESI 列表的 6564.59 Å 仅 0.37 Å；这是邻近性记录，不证明其源于天光，也不判定其天体身份。OH 区间内也出现不满足 10 Å 逐线匹配的候选，因而保留独立的 `oh_band_only` 状态。

## 解释边界与下一步

这次对照验证真实归档的属性贯通与投票不变性，没有污染真值或人工标注，不能估计天光风险标记的准确率。DESI 线表不提供逐条 OH 物种鉴定；当前 10 Å 界原本为少量离散线设计，扩展到 274 条后只作可能污染提示。2026-10-17 决定暂不让 QSO 类型图消费此属性；可留给未来 HS／RA 的独立审查。若未来要据此自动排除 feature，需另行验证阈值、光谱分辨率和对应观测的 sky subtraction 残差。

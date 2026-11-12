# WP-045 — QSO_4 的完整 FA signal-reality 投票（2026-10-16）

## 输入和运行边界

使用 `.data/runs/sh-fa-qso4-full-20261016/` 已冻结的 VI 测量目录及六份 SH pre-analysis 节点，调用 `evaluation/agentic_graph/run_fa_reality.py`。模型来自本地 `.env`：`deepseek-flash`；FA 温度来自 `config/model_calls.json`，本轮为 0.1。并发上限 4，每张票最多尝试 2 次。此次只运行 FA `real_feature_or_not`，未重新读取 FITS、运行 Redrock 或重新生成 SH，也未运行 FA 的双线、forest、composite 节点或 SH 下半部分。

本地忽略目录为 `.data/runs/fa-reality-qso4-full-20261016-v2/`。首个 v1 目录在任何模型调用前因预检错误中止：冻结 VI manifest 没有 mask 字段，mask 在假设 catalog 中；实现已改为从 catalog 读取，并在共享 CWT 的引用之间检查一致性。v2 为完整实测。

## 结果

- 6 个 SH 假设导入；26 个待审特征条目，其中 19 个为运行内共享 CWT，7 个为假设内 Gaussian fit。共享 CWT 每条只启动一组投票。
- 每条特征收到 3 张有效的独立 session 票，共 78 票和 78 次模型调用。失败尝试、重试耗尽、无可用数据阻塞和剩余 `pending` 均为 0。
- 派生状态：13 条 `signal_present`、13 条 `signal_absent`。23 条投票为 `assured`，3 条为 `contested`（2:1 或 1:2）。19 条共享 CWT 中 13 条判为存在、6 条判为不存在；7 条 Gaussian fit 全部判为不存在。这些是对观测信号形态的投票，**不确认天体谱线身份，也不评价假设分类的科学正确性**。
- 模型返回的成功调用用量：输入 710,511 token，输出 20,787 token；输入缓存命中 349,052，未命中 361,459；78 次调用均有缓存字段。当前并未做缓存策略或延迟的对照实验。
- `reasoning_branches.json` 有 84 个事件（6 次 SH 导入、78 张 FA 票）、78 条执行记录和 363 条产物索引。独立重放末事件得到与保存状态相同的快照；所有 78 个特征执行的产物摘要均匹配，26 条特征各有 3 张不同 reviewer 的票。

## 产物校验

| 文件 | SHA-256 |
|---|---|
| `feature_registry.json` | `7dcebe3e2b3673214bb6c655dd87ec4174ecc51e879c4411f696c9a7d78ba680` |
| `reasoning_branches.json` | `a266a6ffc39d8f94284aed39c777b239023557ccee494c1fe8da8d70e979172f` |
| `fa_review_summary.json` | `9c5b45168f15339c565a835ebfa85e9e38ec63cc0889ee130536f1b1e21af73a` |

目录按 run、branch、logical node 和执行/尝试 ID 分隔；每次模型 session 保留 `session.md`、`node.json`、`model_usage.json`、`execution.json`。逐事件 trace 快照保存在 `trace_snapshots/`。原始谱和提示词档案留在被 Git 忽略的本地目录，不纳入计划图。

## 验收界限

本轮证明多票调度、CWT 跨假设去重、fit 假设内作用域、分支事件、用量和产物追溯可在真实模型服务上贯通。它不证明三次同模型调用在统计意义上独立，也没有专家标注用于检验信号判定。下游图推理、其他 FA 节点和图编排器接线仍属 WP-045 后续工作。

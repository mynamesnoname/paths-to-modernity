# WP-044：QSO_4 feature 状态与 JSON 分叉离线贯通（2026-10-16）

## 输入、执行与产物

以先前 `.data/runs/sh-fa-qso4-full-20261016/` 的六份真实 SH pre analysis、冻结 VI 测量目录和一份真实 FA `yes` 节点为输入。运行 `evaluation/agentic_graph/replay_sh_fa_branch.py`，没有调用模型、没有重新分析 FITS，也没有引入真值标签。最终试点输出为 `.data/runs/sh-fa-qso4-full-20261016/offline-replay-v4/`，该目录被 Git 忽略。`final_output.json`、`feature_registry.json`、`reasoning_branches.json` 的 SHA-256 分别为 `956f80503dfb7a5f34df37b8e56ff93773a9ca9f72b3883c568140d945fdafeb`、`486214b4ff4eea258a1941cc196357ace6a1a09d5899975f48222b4d0446332c`、`5f306dc9a84571c796d301dc666466c668ac055aae74730a466f4378cd5d0977`。

## 检查结果

- 六份 SH 节点的目录、judgment、CSV、报告和两阶段 session 摘要均匹配，且恰好覆盖 VI manifest 的六个假设。
- 26 个 SH 入选条目：19 个运行级 CWT、7 个假设内 Gaussian fit。共享的 `cwt:em:0001` 被两个假设引用，只建立一条观测特征；fit ID 包含 hypothesis reference，不跨假设合并。
- 主分支导入六份 SH 节点，再记录一张真实 FA `yes` 票。因要求三张有效票，该条目的状态保持 `pending`，主分支仍是被选输出。
- 从真实 FA 票事件创建 `offline-fixture` 子分支，只在该分支加入两张**明确标记为离线模拟**的票（`yes`、`no`）；该分支的状态变为 `signal_present`、`contested`。父分支保持一张票和 `pending`。代码阻止将含模拟票的分支选为科学输出。
- JSON 轨迹保留主分支 7 个事件、模拟分支 2 个事件；68 份分析／输入／用量产物按摘要复制入输出包。对所有导出分支独立重放至最后事件，与保存的状态相等；68 个复制文件的 SHA-256 全部核对通过。

## 边界

这验证条目作用域、投票状态机、按指定分析事件分叉以及产物保留的代码行为。已有真实 FA 节点生成于后来加上的 VI 目录摘要前置校验之前；本次回放核验了其测量 ID、中心、峰谷类型和 session 来源，但没有再次向模型请求。模拟分支仅检验机制，不是第二或第三次真实 FA 审查，也不能据此宣布 QSO_4 的信号或类别得到科学确认。当前原始来源路径仍是绝对路径；导出包另提供相对路径和摘要，可据此读取副本。下游 SH 推理、正式多 reviewer 调度与端到端 FITS 执行仍属于后续工作。

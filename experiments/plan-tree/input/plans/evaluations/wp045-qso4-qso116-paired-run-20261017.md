# WP-045 — QSO_4、QSO_116 真实新图测试（2026-10-17）

## 输入与运行方式

- 从 `example/basic/QSO_4.fits` 和 `example/basic/QSO_116.fits` 分别调用 `scripts/main.py --workflow agentic-graph`，使用现有 `.env` 模型服务、本机 `rrdesi` 与当前配置。两个光谱各自重跑了真实 FITS 读取、CWT、Redrock、冻结 VI 测量、SH、FA 和类型图。
- 原始输出保存在被 Git 忽略的 `.data/output_/agentic-qso4-qso116-20261017/`；QSO_4 的图目录为 `QSO_4/agentic_graph_91006c8801ad/`，QSO_116 为 `QSO_116/agentic_graph_108a0f8260dd/`。模型密钥和 `.env` 值没有写入本记录。
- 这仍是类型图测试；`type_graph_summary.json` 明确 `final_classification_available=false`，没有跨假设综合、RA 或最终报告。

## 观测结果

| 光谱 | FITS VI 标签 | Redrock 候选 | 完成的 FA 票 | 类型图存活候选 | 已归档模型调用 |
| --- | --- | ---: | ---: | --- | ---: |
| QSO_4 | QSO，z=0.2381 | 6 | 84/84，28 个特征 | H1 Type 2 QSO，z=0.237872；H6 Type 2 QSO，z=0.238052 | 105 |
| QSO_116 | QSO，z=2.9183 | 6 | 36/36，12 个特征 | H4 Type 1 QSO，z=2.919696 | 57 |

- QSO_4 的两个存活假设红移非常接近，但来源于不同 Redrock 解（H1 QSO 模板、H6 GALAXY 模板）；图在当前阶段保留两者，不替代尚未实现的跨假设综合。其余四个假设初步类型为 `null`，按硬门剪枝。QSO_116 的其余五个假设也为 `null`。两样本的存活红移均接近 VI_Z；这只是两个开发样本上的观察。
- QSO_4 的最终 `reasoning_tree.json` 有 1 分支、104 事件、421 个索引产物；QSO_116 有 1 分支、57 事件、228 个索引产物。独立重算全部索引文件的 SHA-256，均匹配。
- QSO_4 已归档用量：105 次模型调用，输入 1,055,115 tokens、输出 56,695 tokens、提供商报告的输入缓存命中 258,432 tokens。其中 SH 19 次、FA 84 次、Q11 2 次。
- QSO_116 最终节点已归档用量：57 次模型调用，输入 574,636 tokens、输出 45,364 tokens、缓存命中 387,968 tokens。其中 SH 20 次、FA 36 次、Q11 1 次。该计数**不含**下述中断尝试中已得到响应但未写成节点的调用，不能当作这轮的实际总成本。

## QSO_116 中断与续跑

- 第一次 QSO_116 进程完成 Redrock 和 5/6 个 SH 节点后，H5 的模型会话在代理连接上长时间无新产物。日志有 19 次成功 HTTP 响应，其中完成归档的五个 SH 节点记录 15 次调用；另外至少 4 次已成功响应但未进入最终节点用量。进程约 10 分钟后被人工 `SIGTERM`，未生成该次 CLI 的完成 index。
- 随后只为 H5 分配新的 node execution，使用同一份冻结 VI manifest、NPZ、Redrock 假设和当前模型配置补跑 H5；六个完成的 SH 节点随后通过 `GraphWorkflow.run_from_sh` 进入 FA 和类型图。中断的旧 H5 attempt 保留在原输出目录，但不在最终推理树中冒充完成节点。首次续跑命令因 stdin 环境下 `load_dotenv()` 自动查找失败而退出，在分配节点前已终止；使用显式 `.env` 路径后成功。
- 与当天上一轮 QSO_116 独立完整运行相比，本轮随机 H 标签从 H3 变成 H4，FA 评审特征从 11 增至 12；两轮都保留 z=2.919696 的 Type 1 QSO 候选。这不是统计稳定性验证。

## 边界

QSO_116 的类型图仍因已有配对宽线而跳过 Q6–Q8；这两样本也没有非零原始 SPECMASK。QSO_4 的两个近似重合候选需要未来的跨假设综合处理。一次挂起会话说明当前 SH 调度缺少单节点超时和正式续跑入口；本轮人工续跑证明冻结输入可复用，但不代表自动恢复已实现。

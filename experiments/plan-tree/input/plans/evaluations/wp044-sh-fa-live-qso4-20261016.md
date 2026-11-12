# QSO_4 新 VI→SH→FA 实测（2026-10-16）

## 范围与输入

使用 `.env` 配置的 `deepseek-flash`。输入为历史运行已归档的 QSO_4 清洗光谱 NPZ、CWT CSV 和六条 Redrock hypothesis map；本次重新执行 VI 测量冻结和按假设的 Gaussian 预拟合，随后对**全部六个假设**并发运行新 SH 两阶段，最后仅对一个 CWT feature 调用一次 FA 模型。没有从 FITS 重新运行 VI 清洗或 Redrock，也没有执行完整 FA 投票、SH 下半部分或最终报告。源 map SHA-256 为 `10a41c9112d33a67c5445c1deb4d9d777a10c6580d4db54dc57e46a4c6b503be`；NPZ SHA-256 为 `8e4d4d0fd1f95a8036df7a95c4b9f1848d95060ef440e9231db2d156c1e354ce`。

本地逐调用归档位于被 Git 忽略的 `.data/runs/sh-fa-qso4-full-20261016/`：`vi_measurements/manifest.json`、各 `sh_*/{status.json,model_usage.json,lines.csv,report.md,*_session.md,node.json}`、`fa_one_feature_session.md`、`fa_node.json`、`fa_model_usage.json`、`summary.json` 和 `telemetry_reconciliation.json`。`summary.json` SHA-256 为 `6b356623c8f5e5f8f492d69dd2c2e2e59aa9c490492718deb59b69302db9e6ce`。这些原始产物不随仓库分发；下表是持久化摘要。

## 实际运行结果

SH 最大并发为 4。前两个假设同时启动，在各自第一条模型响应到达后放行其余四个。SH 批次墙钟时间 61.141 秒，不包括 VI 预拟合。六个假设均成功写入 CSV、报告、ID 判读记录和节点；`null` 类型的节点状态为 `unresolved`，表示本阶段未给出可注入的类型，不是执行失败。

| 假设序号 | z | 类型 | 模型调用 | 输入 token | 输出 token | 缓存命中输入 token | 缓存未命中输入 token |
|---:|---:|---|---:|---:|---:|---:|---:|
| 1 | 0.6713696831689161 | null | 3 | 36,818 | 4,928 | 16,384 | 20,434 |
| 2 | 0.23787248591105023 | Type 2 QSO | 3 | 44,707 | 7,429 | 19,584 | 25,123 |
| 3 | 0.23805248503053472 | Type 2 QSO | 3 | 42,131 | 5,939 | 18,304 | 23,827 |
| 4 | -0.0018443601090383488 | null | 4 | 75,363 | 10,258 | 42,496 | 32,867 |
| 5 | -0.0016077994367870048 | null | 3 | 50,318 | 7,329 | 21,120 | 29,198 |
| 6 | 1.902738756933621 | null | 3 | 27,679 | 2,914 | 13,184 | 14,495 |
| **合计** | | | **19** | **277,016** | **38,797** | **131,072** | **145,944** |

FA 对内部测量 `cwt:em:0001`（本次选中的一个 CWT emission feature）作一次真实 `real_feature_or_not` 运行，返回 `yes`，用时 2.084 秒，1 次模型调用，输入 9,117 token、输出 219 token、缓存命中 0、未命中 9,117。FA 模型输入只含信号方向、目标中心、局部完整 flux/IVAR/有效像素和局部噪声；测量 ID、来源、假设和谱线名只在程序内部和会话档案的内部头部出现。**这是一票，不是投票结果，更不是该线的天体身份判定。**

## 用量核算与缓存解释

用量取自每条 `AIMessage.response_metadata.token_usage` 的 `prompt_tokens`、`completion_tokens`、`prompt_cache_hit_tokens` 和 `prompt_cache_miss_tokens`。每次调用均返回缓存字段，命中加未命中等于输入 token。最初的汇总器把第二阶段输入历史中携带的第一阶段 AI 消息重复计作新调用；按每条消息 ID 去重修正代码后，用已归档 usage 证明六个第二阶段列表各自开头完整重复第一阶段列表（假设 4 为 3 条，其余为 2 条），将这些条目剔除并生成 `telemetry_reconciliation.json`。**19 次**和表中 token 均为修正后的实际调用量，无需重发 API 请求。

六个 SH 的**首条调用**合计输入 65,082 token，其中命中 13,184 token，约 20.3%；单条首调用命中 2,176–2,304 token。后续第一阶段对话续写命中量高，但第二阶段换用另一套工具 schema，命中主要退回短前缀。当前第一条 user message 开头就是假设专属 z 和输出路径，因此该实测不能证明设计文档所说的共享 CWT 上下文已进入可复用前缀；命中也可能来自本次运行前该服务商已有缓存。双请求预热与立即并发的延迟优劣**未做受控对照**。

## 代码与验收边界

新增单 feature 的 FA 执行器、有效像素预检、严格 `yes`/`no` 工具及会话记录；随后加强了 FA 对冻结 VI 目录 ID、中心和 NPZ 摘要的绑定。真实 FA 调用发生在这项额外绑定加强之前；加强后的前置校验只由本地测试覆盖，未另发第二次 FA 请求，以遵守本轮“一条 feature 的一次运行”。会话档案新增每条响应的原始 provider usage。相关本地测试位于 `tests/agentic_graph/`；此轮共 24 条通过（后续补充的目录摘要测试另行重跑）。

本次证明既有归档 VI/Redrock 数据能贯通六个新 SH 节点及一票 FA，也暴露出共享前缀布局尚未落地。它不证明光谱分类科学正确、缓存调度有效提速或新图执行器已完成。

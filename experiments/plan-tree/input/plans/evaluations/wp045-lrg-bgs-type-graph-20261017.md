# WP-045 — LRG/BGS 类型图实施与验证（2026-10-17）

## 决策与边界

决策人选择忠实执行 `LRG_BGS.canvas` 的分类出口：Dn4000 可测且低于/未超过强断裂界则 `dead`；可测且 `strong` 则 `survive / LRG/BGS`，Ca H/K 定向票不改变此出口。Dn4000 缺测、整段 mask 或有效采样不足时是 `unresolved`，不归入“不强”。这个门仅用于新的 LRG/BGS 类型图，规则标识为 `project:lrg-bgs-canvas-dn4000-gate-v1`；旧 ontology 的 `rule:formal-dn4000-interpretation` 仍是描述性参考。项目裁定不是独立科学验证。

## 实施

- `src/FORMA/agentic_graph/lrg_bgs_path.py` 保存 G0–G7 各节点、测量和报告。G1 读取 branch 当前的 cleaned SH×FA line view；G2 只在已采纳 [Ne V] 时携来源转交 QSO Q2；G3 从冻结 NPZ、mask、IVAR 和 ontology 波段算 Dn4000；G4 只统计不同 measurement ID 的已采纳 Ca K/H 分量，`MASKED` 和 FA 未决保持未知。
- 对已评估的 0/1 个 Ca 分量，G5 读取两处窗口并复用独立投票运行器；零个 SH 分量不伪装成 FA 已检出。若同覆盖、同 SH/FA 状态且已有完成的 FA 双线咨询，可复用原票。票据、失败尝试、用量、提示词摘要、窗口与谱像素片段分别保存并纳入 trace；不回写单 feature 的 FA 状态。
- `qso_entry.py` 和 `qso_report.py` 核对 LRG/BGS 来源路由、转交事件、[Ne V] 测量 ID 和保留的初判标签。`evaluation/agentic_graph/run_lrg_bgs_paths.py` 提供无模型离线入口；需投票但没有模型时只记 `pending`。

## 验证

`PYTHONPATH=src /home/user/apps/miniconda3/envs/forma/bin/python -B -m unittest discover -s tests/agentic_graph -p 'test_lrg_bgs_path.py' -q`：11 条通过。覆盖强 Dn4000+双 Ca 采纳、零 Ca 独立反对票、单 Ca 无模型待审、同状态 FA 双线票复用、局部 mask 不可审、弱与缺测 Dn4000 区分、LRG/BGS→QSO Q2/Q11、转交后的子分支重入、源摘要篡改、重复节点拒绝及离线 trace。

`PYTHONPATH=src /home/user/apps/miniconda3/envs/forma/bin/python -B -m unittest discover -s tests/agentic_graph -p 'test_*.py' -q`：97 条通过。另以 `-s tests -t .` 执行旧全库套件，820 条通过、9 条跳过；由于 `tests/agentic_graph` 没有 `__init__.py`，后者不会发现新图测试，因此两项独立报告。测试使用合成冻结 NPZ 与模拟模型；未调用真实模型服务，未跑真实 LRG/BGS FITS。真实光谱误杀/漏判、Dn4000 硬门的科学合理性和跨假设综合仍待验证。新图也尚未接入 `scripts/main.py` 的图级编排器。

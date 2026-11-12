# WP-045 — 新图 GraphWorkflow 接入（2026-10-17）

## 实施边界

- `scripts/main.py --workflow agentic-graph` 选择独立的 `GraphWorkflow`；无参数时仍走旧 `WorkflowOrchestrator`。CLI 继续负责单文件/批处理选择与结果索引，新 workflow 负责每份光谱的 VI→Redrock→冻结 catalog→并行 SH→单 feature FA→类型图路由。agent 在已指定节点内调用工具，类型转交与分支状态由代码校验。
- 新 FITS 适配器复用光谱读取、CWT 和 Redrock 计算函数，不构建旧 Evidence Graph。按 Redrock `znum` 和记录的随机种子分配 H 标签；冻结共享 CWT ID、逐假设 Gaussian fit ID 与 NPZ 摘要。
- 类型路由：`null` 剪枝；QSO 进入 Q0–Q11；ELG、LRG/BGS 各自进入类型图，可经已采纳 [Ne V] 转交 QSO。转交源图与目标图的结果分开归档。每个假设完成后写一份可回放 trace 检查点。
- 当前输出为 `type_graph_summary.json` 与 `reasoning_tree.json`，`final_classification_available=false`。仅 `survive` 假设列入存活候选。跨假设 HS、RA、最终 RW 尚未接入，不生成旧格式 `final_report.md` 或 `in_brief.csv`。FA 的 forest/doublet 咨询节点目前仍是独立 API；自动 FA 阶段只执行单 feature 真实性投票。

## 验证

- `tests/agentic_graph/test_graph_workflow.py`：冻结 SH 产物进入真实 registry/trace/FA 状态与 LRG/BGS 图；检查并行 SH 限流、`null` 剪枝、LRG/BGS→QSO Q11 后的有效存活状态、输出边界和 Redrock 标签唯一性。
- `tests/agentic_graph/test_main_graph_selection.py`：CLI 选择新 workflow，写单独 batch index，且不写旧 `in_brief.csv`。
- 一次真实 `example/basic/LRG_1.fits` 读取/CWT/预拟合接口冒烟检查：以模拟 Redrock 单候选替代外部子进程，未调用模型；得到 14 个 CWT 发射候选、16 个吸收候选、27 条注册谱线及 15 条拟合尝试，并成功冻结 NPZ 和 catalog。首次运行发现共享 CWT 函数要求 `visual_interpreter/` 子目录，修复后通过。
- `tests/agentic_graph/` 单独发现：104 条通过；原流水线测试以 `-s tests -t .` 发现：820 条通过、9 条跳过。两套测试分别运行，未将计数相加作为同一测试发现结果。

## 限制

尚未做真实 Redrock+LLM 的整条新图运行。FITS 读取器当前过滤掉原始 mask 像素，新 catalog 无法恢复这些像素的显式区间，只以留下的像素、IVAR 与覆盖作判断；这一输入边界需要后续处理。类型图的科学出口也尚未在独立真实样本上验证。上述限制不影响该 workflow 的调度和产物真实性，但不支持把类型图候选解释为最终分类。

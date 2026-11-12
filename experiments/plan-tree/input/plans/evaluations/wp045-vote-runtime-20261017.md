# WP-045 — FA 共用投票执行与缓存观测（2026-10-17）

## 实现边界

`vote_runtime.py` 集中处理每票独立会话、并发限流、每席有界重试、独立执行目录、
成功/失败用量记录、奇数票汇总与提示词文本指纹。单 feature、Lyα forest、双线节点均
调用它；各自保留原始读谱检查和科学语义。单 feature 的有效票更新 registry；forest
和双线只写咨询性 branch analysis。无效票和失败尝试不计入分母；若服务端已经返回
用量，这些调用仍计入成本。重试不会复用此前会话消息。

提示词指纹覆盖 system/user 文本及工具名。它用来检查同一投票批次的文本是否稳定，
**不是**服务端 KV cache key 的完整表示；工具 schema、模型设置及服务商路由也可能
影响缓存。`cache_hit_reported_calls` 和 `cache_hit_unreported_calls` 区分
“提供商明确报告 0”和“未提供字段”。缓存命中 token 数只采用服务端返回值，
不以相同提示词推定。

## 验证

- `tests/agentic_graph/test_vote_runtime.py` 验证失败调用和无效票重试的实际用量、
  独立执行目录、提示词指纹、未凑齐票数以及缺失缓存字段的统计。既有三个 FA
  节点测试验证原有状态与分支语义不变。
- 新图独立测试发现 77 项通过，包括模型流在返回用量后失败的会话归档；真实接口冒烟使用 `.env` 已配置模型 `deepseek-flash`：
  QSO_4 的 `[O III]` 双线投票在同一 frozen trace 上得到 3/3 `no`，3 次模型调用；
  服务商报告输入 20,739、输出 1,117、缓存命中 1,152 tokens，3 次调用都有缓存字段。
  产物为 `.data/runs/fa-reality-qso4-full-20261016-v2/doublet_oiii_qso4_vote_runtime_trace.json`
  （忽略目录）。运行器写 trace 时对分支回放和新产物摘要作了校验。
- 用同一归档的 `cwt:em:0000` 做单 feature 直接会话冒烟：工具返回 `yes`，
  1 次调用，输入 9,124、输出 245、服务商报告缓存命中 640 tokens；会话文本在
  `.data/runs/fa-reality-qso4-full-20261016-v2/vote_runtime_feature_smoke.md`。
  这验证共享会话执行器的另一种提交契约，不是新的科学真实性评估。
- 旧测试树 `unittest discover -s tests -t . -q`：820 项通过、9 项跳过；新图目录
  单独发现 77 项通过；`_aiHumanInteract/plan/validate.py`、生成视图检查及 15 项计划测试通过。

## 限制

服务商缓存命中不能证明多个 vote 的统计独立性，也不能从 token 数直接推断费用。
目前使用并发提交和稳定前缀；没有引入强制顺序预热，因为其命中收益与延迟代价
尚未做对照测量。失败在获取服务商用量前发生时，记录为 `model_calls=[]`，
无法凭本地日志推断服务端是否已计费。

# WP-045 — FA 双线咨询节点实测记录（2026-10-17）

## 范围

新节点 `fa.doublet_review` 承接旧 FA 的五组双线定义：`doublet:oiii`、
`doublet:sii`、`doublet:nii`、`doublet:cahk`、`doublet:na-d`。按一个红移假设和一个双线 ID
生成稳定逻辑 key；每次执行另有唯一目录和执行 ID。只有 SH 至少保留一个分量时才可运行。
完整配对和只有一个分量被 SH 保留的孤儿配对均有明确输入。它读取冻结 VI 测量、SH
逐线判断、当前分支的 FA feature 状态和 NPZ 像素；代码计算预期与测量间距、振幅比和
来源于 ontology/config 的参考范围。参考比值只作线索，不自动否决。两处分量的可用样本
检查失败时写 `unreviewable`；模型票未凑齐时写 `pending`。结果只进入分支的分析结果，
不改写 feature 真假、不进入 QSO gate。

## 验证

- `PYTHONPATH=src:tests/agentic_graph /home/user/apps/miniconda3/envs/forma/bin/python -B -m unittest tests.agentic_graph.test_fa_doublet -v`：7 项通过，覆盖完整双线、孤儿、越界、遮罩、Ca K/H 比值方向、模型失败重试、分支继承和源状态不变。
- 用 `.data/runs/fa-reality-qso4-full-20261016-v2/reasoning_branches.json` 的
  `redrock_fit:b9828e28d4029090` 假设试跑 `[O III]`。最终归档：
  `.data/runs/fa-reality-qso4-full-20261016-v2/doublet_oiii_qso4_trace_v2.json`
  （本地忽略目录，不纳入 Git）。配置的实际模型为 `deepseek-flash`；3 个有效投票，
  结果 `no/no/no`，3 次模型调用，输入 20,742 tokens、输出 503 tokens；本次提供商
  报告缓存命中为 0。
- 此样本两条 SH 所配测量中心相距 166.4 Å；固定红移预期双线间距约 47.81 Å。
  三票均不支持这组双线解释。这个结果不等于否定每个测量位置存在信号。
  运行器调用 `write_trace`，对事件回放、执行 manifest、归档 SHA-256 做了校验。
- 旧流水线测试发现 820 项通过、9 项跳过；新图目录单独发现 74 项通过；计划校验与
  15 项计划测试通过，生成视图 `build_graph.py --check` 通过。

## 限制

这只是一个 QSO_4 双线样本的接口和真实模型冒烟，不是五种双线的科学准确率评估。
`context_margin_angstrom=80`、`component_check_half_angstrom=15` 和每分量至少 5 个
可用样本是可配置的工程起点；尚未针对 Na D 等近邻双线校准。QSO 类型图和 HS/RA
目前不会自动消费该咨询结果；未来消费时必须显式声明语义和使用边界。

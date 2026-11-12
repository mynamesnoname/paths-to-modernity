# WP-045：FA Lyα forest 信息节点，QSO_116 H3 实测（2026-10-17）

## 契约

新节点 `fa.real_lya_forest_or_not/<run>/<hypothesis>` 仅针对一个活跃 SH 假设中已保留的 Lyα 主张。冻结的 VI catalog 给出 Lyα 预测位置，NPZ 提供光谱；读窗、有效像素门槛和票数由 `analysis_method.audit.lyalpha_forest` 统一加载。模型每个 session 只看到该目标的完整蓝侧采样、红侧参照、IVAR 和 mask；不看到其他票。每票提交 `yes`／`no` 和观察理由。代码记录原始会话、失败尝试、覆盖、输入摘要与多数票。`no` 的语义是**在提交给模型的有效蓝侧数据中未见到**，不是 forest 物理缺失。节点既不更新 feature 真实性，也不参与 QSO 路由或 Q9 门。未来 HS/RA 可以通过 `read_lya_forest_information` 按分支读取状态、票和覆盖信息；当前尚未把该接口接入尚未实现的新图 HS/RA。

完全没有足够蓝侧有效采样时，代码给 `unreviewable`，不调用模型；重试耗尽时给 `pending`，不把失败算成 `no`。`assurance` 仅表示票型一致程度，不是科学正确概率。

## 真实调用

使用前次 QSO_116 H3 新图 FA 的 `reasoning_branches.json` 和其已冻结的真实 VI/Redrock 输入，未重跑 FITS/Redrock。命令：

```bash
PYTHONPATH=src:. /home/user/apps/miniconda3/envs/forma/bin/python -B evaluation/agentic_graph/run_fa_lya_forest.py \
  .data/runs/qso116-type1-fa-20261017/reasoning_branches.json \
  .data/runs/qso116-type1-fa-20261017/forest_reasoning_branches.json \
  'redrock_fit:21a3b0b1cfdcc335' --concurrency 3
```

`.env` 配置模型为 `deepseek-flash`。Lyα 预测位置 4765.0571 Å；蓝侧请求 `[4565.0571, 4765.0571)` Å，实际 250/250 采样可用，无显式 mask；红侧 100 个可用采样。三个 session 均提交 `no`，最终为 `complete`、`visibility=not_seen`、`0/3 yes`。三个有效票共计 4 次模型调用，输入 34,206 token、输出 697 token、缓存命中输入 8,576 token。多出的 1 次是有效 session 内的后续调用，不是第四票。原始会话、结果节点和输入引用存于被忽略的 `.data/runs/qso116-type1-fa-20261017/`；输出分支 JSON SHA-256：`c3bef74343347b3085de538f974b7d543564c856afc4a8ecdd03a56e2ddbed43`。分支事件重放与读取接口校验通过。

三条观察理由都描述蓝侧缺乏一系列可信的窄吸收结构；这是一致的**模型读谱意见**，未经专家检查，不据此降低 QSO_116 的类型判定或对 Lyα 作负面形式规则判断。同一服务商同一模型的独立会话也不能当作统计独立的专家意见。

## 验证与剩余边界

`tests/agentic_graph/test_fa_lya_forest.py` 覆盖 mask 与蓝/红边界、三票汇总、节点不改变 feature registry、分支继承与重放、数据不足零调用、失败补票上限。定向测试 4 条通过；`tests/agentic_graph` 共 67 条通过；分析方法配置测试 6 条通过。新图尚无 HS/RA 编排器，因此“供消费”目前体现为稳定读取接口及已登记的分支产物，不能声称已由 HS/RA 实际消费。森林形态判据的专家效度仍待后续大样本检查。

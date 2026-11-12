# WP-045 — LRG/BGS Dn4000 或 Ca H/K 路由修订（2026-10-17）

## 决策

决策人以 `A = Dn4000 strong`、`B = 至少一条 SH×FA 已采纳 Ca K/H 配对` 替换原来的 Dn4000 单门。`A ∨ B` 开启 Ca H/K 清单；A、B 均明确不成立才失败，未知值不折成否定。G4 中两条不同测量 ID 的已采纳分量直接支持此路径；一条已采纳分量且 Dn4000 不强／未知时，G5 必须同时取得完整的双线赞成票和缺失分量的有效选样，才可存活。Dn4000 强时 G5 仅补充证据。弱 Dn4000、单线、完整反对票且清单无未知时失败；数据、票或选样不完整时未决。

## 实施与边界

- `lrg_bgs_path.py` 的 G3/G4/G5/G6 改用 `project:lrg-bgs-dn4000-or-cahk-v2`；原始 Canvas 与 v1 规则保留历史，不作为当前路由。G4 的开关使用 G1 同一 cleaned line view 的 Ca 已采纳清单，不重复探测。已采纳分量若缺测量中心或中心落入冻结显式 mask，则拒绝矛盾来源，不把它当作 B 的正证据。
- G5 的 `yes/no` 双线票仍来自独立 session；多数赞成后，每个缺失分量另开奇数个无历史选样 session。模型只提交冻结 NPZ 全局像素 ID；代码核验三个像素有效且未 mask、左右顺序、位于配置的目标核内，以及正的吸收谷深度。取谷底波长中位数对应的完整一次选样为代表，同时保存全部选样、失败尝试、提示词与用量。候选取得 branch-local `candidate:cahk/*` ID，不回写 VI/SH/FA。
- 既有测量若被 FA 否定或仍待审，定向选样不直接恢复配对，单线弱 Dn4000 路径保持未决。定向票否定只表示当前双线解释未获支持，不宣称物理谱线绝对不存在。G5 的票与选样是项目分类规则的输入，并非概率校准。
- `fa_doublet.build_doublet_window` 现提供冻结谱的全局 `sample_id`、可用性及其 Markdown 展示，供 Ca 选样和溯源使用。
- 后续宽度裁定：Ca 缺失分量的左右外侧参考点按 `audit.doublet_review.cahk_outer_reference_sigma`（默认 3）的 `±kσ` 约定换算为 `fwhm_proxy_angstrom` 和 `fwhm_proxy_km_s`；中位宽度对应的完整一次选样为代表，报告同时展示吸收深度和两种 FWHM 单位。它是选点宽度代理，不声称实测半深度宽度。QSO Q8 已产生两种 FWHM 代理单位；本次把 Å 单位也接入 Q11 表格，维持 Q9 的既有宽线门。

## 验证与限制

`PYTHONPATH=src:tests/agentic_graph /home/user/apps/miniconda3/envs/forma/bin/python -B -m unittest discover -s tests/agentic_graph -p test_lrg_bgs_path.py -q`：25 条合成测试通过。覆盖弱 Dn4000 的 0/1/2 条 Ca、单线赞成／反对／未完成票、正票但没有有效吸收谷、Dn4000 缺测、FA 否定、SH mask 声明与像素冲突、已采纳中心落入 mask 的拒绝、吸收宽度换算和中位宽度代表选样、源摘要、转交与分支存档。

`PYTHONPATH=src:tests/agentic_graph /home/user/apps/miniconda3/envs/forma/bin/python -B -m unittest discover -s tests/agentic_graph -p 'test_*.py' -q`：122 条通过。均为离线合成验证；本次未调用真实 LLM 或真实 LRG/BGS FITS，因此目标谱中 Ca K/H 选样的可靠性及新出口的科学正确率仍需实测。

原有全库发现命令 `PYTHONPATH=src /home/user/apps/miniconda3/envs/forma/bin/python -B -m unittest discover -s tests -t . -q`：821 条通过、9 条跳过。计划节点校验、生成图检查和 15 条计划测试通过。

# WP-045 — LRG/BGS：moderate Dn4000 加一条已采纳 Ca 直接存活（2026-10-30）

## 决策

决策人按 Dn4000 档位拆分 G6 的单条 Ca 规则：

| Dn4000 | 已采纳 Ca | 规则 |
|---|---|---|
| `strong` | 任意 | `survive`（`dn4000_strong`，不变） |
| `moderate` | 2 条 | `survive`（`cahk_pair_adopted`，不变） |
| **`moderate`** | **1 条** | **`survive`（`dn4000_moderate_cahk_single`，新增）** |
| `not_strong` | 1 条 | 需 G5 全票 + 每个缺失分量有效选样 + 白名单，否则 `unresolved`/`dead`（不变） |
| 未知 | 1 条 | 同 `not_strong`（不变；未知不折成正面） |
| `moderate` / `not_strong` | 0 条 | `dead`（不变） |

G5 对 `moderate` 仍会运行并归档票与选样，但不再能阻断该出口；`cahk_inventory_unknown` 与 `cahk_review_pending/unreviewable` 只作为开放项记录。

## 依据

- 实际运行 `20261030T081212Z-56da5914`（BGS_2）：H4 与 H5 均为 Dn4000 = 1.531（`moderate`）、Ca K 已采纳、Ca H `rejected_measurement`；G5 分别 2/3 与 3/3、选样 `complete`，G6 仍 `cahk_pair_unresolved`，整条样本弃权。
- 同一输入的更早运行 `20261030T074744Z-c7b01f54`：H4 的 Ca H 为 `signal_present`，走 `cahk_pair_adopted` 并 `survive`。两次的冻结测量相同，差别只在 3 票 FA 的翻转，说明旧规则让单次结论依赖一次投票。
- 决策人认为 `moderate` 断裂本身已是正面证据，不应被第二条分量的 FA 否定阻断；但 `not_strong` 与未知仍保留双证据要求。

## 实施

- `src/FORMA/agentic_graph/lrg_bgs_path.py`：G6 在 `strong` 与 `cahk_pair_adopted` 之后新增 `moderate + adopted_count == 1` 分支；`GRAPH_VERSION` 与 `ROUTE_RULE` 升为 `v3`。
- `tests/agentic_graph/test_lrg_bgs_path.py`：fixture 增加 `moderate` 档（红段均值 1.4）；新增“moderate + 一条已采纳 Ca + 第二条被 FA 否定 → `survive`”和“moderate + 0 条 Ca → `dead`”两项。
- `agenticGraphReasoningDesign/graphsOfEachType/LRG_BGS.md`：G5/G6 行、§1 出口说明、§2 边界、§3 路由示例与 §4.1 裁定同步；本地镜像同文。

## 验证

- `PYTHONPATH=src:tests/agentic_graph python -B -m unittest discover -s tests/agentic_graph -p 'test_lrg_bgs_path.py' -q`：27 条通过（新增 2 条）。
- 全库离线测试见本次运行的 `tests` 结果；未发起真实模型或 Redrock 调用。

## 限制

- 仍无真实 LRG/BGS FITS 的新路径科学验收；本规则让 FA 对第二条分量的否定不再阻止 moderate 路径，相关误判风险进入 G6，需在 WP-046 的基线对比中计量。
- HS 层不因 G6 通过而必然给出结论：H4/H5 的 Ca K 测量来源是 `fit_doublet`，不满足 HS key-pair 的 CWT 要求，两者不会被合并，仍由 HS 比较决定。

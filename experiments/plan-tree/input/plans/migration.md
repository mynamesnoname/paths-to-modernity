# Plan Graph v3 migration record

2026-10-08 将 FORMA 旧版四层计划图迁移至 `paths-to-modernity-plan-graph-v4`。迁移前的源与工具可从 Git 历史恢复；执行时另在 `/tmp/forma-plan-v2-snapshot/` 留有本机临时快照，该路径不是项目依赖。

## Identity mapping

旧 `meta/MP-001` 至 `meta/MP-017` 按编号一一对应新 `work-package/WP-001` 至 `work-package/WP-017`。所有父子、依赖、验证、冲突与取代引用按同一映射更新。旧 ID 只在本记录及 v3 工具的旧版拒绝测试中保留；以后不得复用。迁移没有改动 LT、MT、ST 的 ID，也没有重排科学工作顺序或状态。

## Schema and paths

| Before | After |
|---|---|
| `meta/MP-###` | `work-package/WP-###` |
| `mounts` | `links` |
| `essence` | `context` |
| `tensions` | `tradeoffs` |
| `technique` | `approach` |
| `inbox/` | `requirements/` |
| `remount_graph.py` | `build_graph.py` |
| `structure/atelier.md` | `structure/review.md` |
| `forma-layered-plan-graph-v2` | `paths-to-modernity-plan-graph-v4` |

旧的 `variant_of` 没有机械转换为 `alternative_of`：原 WP-016 与 WP-017 的目标文本及工作成果不同，不符合 v3 受控替代要求。两者保留共同的原始需求、评估文档、冲突关系和 WP-016 对 WP-017 的取代关系。该历史比较不是 v3 类型化的 `alternative_of` 边。若将来要比较新的受控替代方案，应建立共同目标、不变量、需求、评价基线与不同方法。

旧已完成工作包的完成说明描述当时的 v2 实现；迁移后的 `links` 和 `evidence` 指向现存的 v3 工具与生成视图，不能把历史文字误读为 v3 的原始实现记录。运行时科学 Evidence Graph 与此迁移无关。

## Checks

- 迁移前：34 节点，旧校验、视图新鲜度检查、17 项测试通过。
- 迁移后：35 节点（3 LT、5 MT、9 ST、18 WP；含迁移工作包 WP-018）；v3 校验、视图新鲜度检查及 15 项工具测试通过。

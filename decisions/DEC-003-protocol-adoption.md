# DEC-003 — 用脚本把协议注入 AGENTS.md

- **状态：** accepted（2026-11-12）
- **决策人（decision owner）：** 仓库维护者
- **范围：** 新增项目级「协议采纳」机制：`scripts/adopt_project.py`、`assets/protocol/` 下的两份权威源文件。
- **本记录的性质：** 决策记录，不构成把该机制安装到任何具体仓库的授权。

## 背景

上下文压缩后，skill 正文会消失，而 `AGENTS.md` 不会。原因在 harness 而非文档：skill 的加载结果是一条 tool result，压缩时被 `<compacted-summary>` 替代；`AGENTS.md` 以 `agent-instructions` 消息注入，文件变化时重新注入。

因此「让 agent 记得 PtM 怎么工作」不能靠 skill 常驻，必须落在 `AGENTS.md`。此前 `install_plan_graph.py --update-agents` 已经在用这个机制，但只覆盖 Plan Graph 的治理规则。

## 决策一 — 由脚本注入，不由 agent 现场撰写

**决策：** 协议内容作为权威源文件存放在 `assets/protocol/AGENTS.protocol.md`，由 `scripts/adopt_project.py` 注入目标仓库的 `AGENTS.md`，带标记块与哈希清单。

**被驳回的替代：** 让 agent 每次现场生成这段文字。驳回原因：内容不确定、不可审查、无法校验是否被改动；同一内容在两次采纳之间会漂移。

**理由：** 注入内容成为**生成物**，与 `graph.json` 同性质——可 diff、可回滚、可判断是否被用户修改。

## 决策二 — 块只放指针与四条不变量

**决策：** 注入块的内容限于：

1. 何时加载 `paths-to-modernity` skill，以及无法加载时的退路；
2. 四条不变量：沉默不授权；授权/理解/证据三维正交；readiness 相对于下一个承诺；每个决策一个可编辑源；
3. `_aiHumanInteract/` 下各目录的用途；
4. 压缩后先读 `state/active.md` 的恢复指令。

materiality 分类、四步 inquiry、字段契约等一律留在 `references/`。

**被驳回的替代：** 把协议全文注入。驳回原因有二：一是 `AGENTS.md` 每轮进入上下文，全文注入会重新支付 skill 系统本要省下的常驻成本；二是与 `SKILL.md`/`references/` 形成两份会各自演化的规范，正是评审警告的 Layer 1 漂移。

## 决策三 — `CLAUDE.md` 写一行指针，不用符号链接

**决策：** 生成内容固定为一行的 `CLAUDE.md`，指向 `AGENTS.md`。

**被驳回的替代：** `ln -s AGENTS.md CLAUDE.md`。驳回原因：Windows 上创建符号链接需要开发者模式或管理员权限；`core.symlinks=false` 检出时符号链接会变成内容是目标路径的普通文件，Claude Code 读到的是 `AGENTS.md` 这几个字；部分编辑器、沙箱与文件监听不跟随符号链接。

**已接受的代价：** 多一个文件；但内容恒定，不存在需要同步的维护面。

## 决策四 — 生成 `state/active.md` 骨架

**决策：** 采纳时创建 `_aiHumanInteract/state/active.md` 骨架（目标、治理记录指针、已验证进展、开放不确定、授权边界、下一步、恢复说明）。

**边界：** 只存指针与少量事实，不复制决策正文；创建后**永不覆盖**，用户编辑过的状态文件在卸载时也保留。

**理由：** 没有它，注入块里的「压缩后先读 state」是空指针；恢复机制不闭环。

## 块升级：存收据，不猜

采纳时 manifest 同时记录块的**原文**（`protocol_block`）与版本号，而不只是哈希。上游改动后，升级变成一次三方可判定的比较：

| 当前块 vs manifest 记录的原文 | 含义 | 动作 |
|---|---|---|
| 相同 | 未被改动 | 可以替换为新版 |
| 不同 | 用户改过 | 拒绝，打印上游 diff 供人工合并 |
| 块不存在 | 被删了 | 追加当前版本 |
| 当前 == 新版 | 已是最新 | 不写入 |

记录原文而不是维护一份全局历史哈希表，是因为每个项目采纳的是哪个版本、有没有被改过，只有它自己的 manifest 知道；历史表放在 skill 仓库里既会增长，也覆盖不到用旧版 skill 采纳的项目。

命令：

```bash
python3 -B scripts/adopt_project.py /path/to/repo --upgrade-block --dry-run
python3 -B scripts/adopt_project.py /path/to/repo --upgrade-block
```

普通 `adopt` 遇到"旧版但未改动"的块时不再报笼统冲突，而是给出可执行的下一步：

```
the protocol block is outdated (paths-to-modernity-protocol-v1 ->
paths-to-modernity-protocol-v2); run --upgrade-block to review the diff
and replace it.
```

升级只动两处：`AGENTS.md` 的标记块与 `CLAUDE.md` 指针。`state/active.md` 永不参与升级——那是用户的状态，不是模板。

## 卸载：内容相等不是所有权证明

manifest 记录 `created_block` 与 `created_claude`，表示**该块或指针是否由本工具写入**。卸载据此判断，而不是据此推断：

| 情况 | 动作 |
|---|---|
| 本工具写入且未被改动 | 删除 |
| 项目原本就有、内容恰好相同 | 保留，报告 `kept (pre-existing)` |
| manifest 早于该字段，无法证明所有权 | 保留，报告 `kept (no ownership record)` |
| 内容被改过 | 拒绝，要求手工处理 |

判据是**谁写的**，不是**内容像不像**。项目可能预先就有完全相同的块或指针；只按哈希删除会把它一并删掉。哈希能证明「内容未变」，不能证明「由我创建」——这正是评审所说的「内容相同不是所有权证明」。旧的 manifest 没有这个字段，因此保守地保留，宁可留下一个块，也不删掉别人的治理规则。

## 安全性质

脚本遵守与安装器相同的性质：

- 幂等：内容相同则跳过；
- 不覆盖：已有不同内容的 `AGENTS.md` 块、`CLAUDE.md` 一律拒绝，不做合并猜测；
- 可撤销：卸载同时校验**所有权**（`created_block` / `created_claude`）与**内容哈希**，只删除自己写入且未被修改的内容；项目原有的相同内容保留；
- 状态优先：`state/active.md` 一旦被编辑，卸载保留它。

## 已知限制

1. **不能替代恢复机制。** 注入块保住的是「规则」，不是「进度」；进度仍要靠 `state/active.md` 被如实更新。
2. **块长度是硬约束。** 一旦内容膨胀，就退化为评审 A.5 反对的「每轮全量加载」。当前块约 30 行。
3. **仍然存在一处重复：** 四条不变量在块中有一句话版本，在 `inquiry.md`/`knowledge-debt.md` 中有展开版本。二者描述同一组规则，措辞不同。这是有意的（块给约束，引用给理由），但改规则时必须同时改两处，`AGENTS.md` 的变更协议应涵盖这一点。
4. **旧 manifest 无法升级，也无法证明卸载所有权。** 在记录原文之前采纳的项目没有收据，`--upgrade-block` 会拒绝并要求手工移除块；同样，没有 `created_block` 的 manifest 在卸载时会保留块。本次改动前没有真实采纳记录，故代价为零；但这个分支会长期存在。
5. **不判断项目是否已有等价治理。** 若目标仓库已有自己的 `AGENTS.md` 规则，脚本只追加标记块，不评估语义冲突。

## 未决

1. 块中的四条不变量是否够用，需要真实项目验证后再定。
2. `state/active.md` 的字段是否合适（尤其「授权边界」是否需要记录授权日期与来源）。
3. 是否把 `adopt_project.py` 与 `install_plan_graph.py` 合并为一个入口（当前刻意分开：协议采纳与 Plan Graph 采纳是两件事）。

## 链接

- 权威源文件：[`assets/protocol/AGENTS.protocol.md`](../assets/protocol/AGENTS.protocol.md)、[`assets/protocol/state-active.md`](../assets/protocol/state-active.md)
- 脚本：[`scripts/adopt_project.py`](../scripts/adopt_project.py)
- 相关决策：[`DEC-002`](DEC-002-authorization-and-knowledge-location.md)
- 架构评审附录：[`reviews/2026-11-11-post-7eaab8d-code-and-behavior-review.md`](../reviews/2026-11-11-post-7eaab8d-code-and-behavior-review.md)

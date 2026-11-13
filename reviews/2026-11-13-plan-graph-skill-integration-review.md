# PtM Plan Graph 可视化的 skill 集成评审

评审基线为 `ffc0fdeb`。范围覆盖生产 bundle、目标仓库安装和升级、生成产物的可重复性，以及 agent 将页面交给用户后的使用路径。视觉风格与配色见[前一轮评审](2026-11-12-plan-tree-visual-style-and-palette-review.md)。

## 发现

### [P1] 已安装 v4 的项目无法通过当前入口升级到新版 viewer

`SKILL.md` 把建立和升级都指向同一个安装流程。新版仍使用 v4 schema，但已安装的 `README.md`、`build_graph.py` 和治理块会随 bundle 变化。安装器对现存文件只接受和新版完全相同的内容，因而在复制新增的 `plan_view.py` 之前即退出。

用引入 HTML 前的提交 `845dabe` 对临时项目执行安装并加入治理块，再用当前版本执行 `--update-agents --dry-run`，退出码为 1，首个冲突是旧版 `README.md`。同一项目用当前版本执行 `--uninstall --dry-run` 也以 1 退出，因为卸载时把旧治理块与当前模板比较。旧版安装器仍可用于卸载其自身安装的内容。

建议用 manifest 中的上次安装哈希识别未修改的受管文件和治理块。预览应列出替换项、新增项和本地冲突，升级后重建视图。可独立记录 bundle 版本，让 viewer 的发布无需改变 Plan Graph 数据 schema。回归应覆盖 HTML 加入前的 v4、已带 HTML 的旧 v4，以及同一文件含本地编辑三种情况。[SKILL.md:87](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/SKILL.md#L87) · [install_plan_graph.py:125](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/scripts/install_plan_graph.py#L125) · [install_plan_graph.py:251](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/scripts/install_plan_graph.py#L251)

### [P2] 检出目录名称改变会让 `--check` 误报 HTML 过期

构建器把仓库根目录的 basename 写进 HTML 标题和页头。将同一个官方示例复制到 `repo-a` 和 `repo-b`，用 `repo-a` 生成的 HTML 覆盖 `repo-b` 对应文件，`repo-b` 的 `--check` 只报告 `structure/graph.html` 过期。分别重建后，差异只有标题和页头。使用不同 checkout 名称的 CI、worktree 或 agent 临时目录都会遇到这个问题。

建议默认使用固定标题。有项目名需求时，从可随仓库提交的显式配置读取。回归中可把同一份示例复制到两个不同名称的目录，要求生成结果逐字节一致。[build_graph.py:395](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/assets/plan-graph/_aiHumanInteract/plan/build_graph.py#L395) · [build_graph.py:422](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/assets/plan-graph/_aiHumanInteract/plan/build_graph.py#L422)

### [P2] 生产 viewer 漏掉 `ready` 状态

v4 schema 允许六种状态，HTML 的配色与筛选列表只列了五种。官方示例有四个 `ready` 节点、一个 `proposed` 节点，生成页面只提供 `proposed` 筛选项。`ready` 卡片使用通用样式，读者也无法用状态筛选查看哪些计划已准备就绪。

建议让 viewer 的状态显示、计数和筛选共用一份状态配置，并断言配置覆盖验证器接受的全部状态。当前 bundle 回归检查 HTML 是否包含示例节点和搜索面板，官方示例已经具备补这条断言所需的数据。[validate.py:27](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/assets/plan-graph/_aiHumanInteract/plan/validate.py#L27) · [plan_view.py:27](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/assets/plan-graph/_aiHumanInteract/plan/plan_view.py#L27) · [plan_view.py:985](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/assets/plan-graph/_aiHumanInteract/plan/plan_view.py#L985) · [test_plan_graph_bundle.py:453](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/scripts/test_plan_graph_bundle.py#L453)

### [P2] 从页面可以看分解层级，核对前置条件和证据仍需跳回文件

官方示例的 JSON 有五条有类型的边，HTML 画出四条父子连线。被省略的是 `WP-001 → WP-002` 的 `prerequisite_for`，选中 `WP-002` 时详情也不展示这条依赖。详情里的 Links 和 Evidence 是路径文本，无法直接导航。对于 agent 把图交给用户核对“为什么这项还不能开始”或“完成依据在哪”的场景，这两步都会中断阅读。

建议保留树布局，在所选节点详情中加前置条件和下游节点，按类型列出并支持点选。增加一个打开源计划的入口，对存在的仓库内引用提供相对导航，对未落地的计划路径和归档标识保留文本。这样可以沿用当前布局，同时让用户从具体节点追溯状态和证据。[plan_view.py:219](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/assets/plan-graph/_aiHumanInteract/plan/plan_view.py#L219) · [plan_view.py:612](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/assets/plan-graph/_aiHumanInteract/plan/plan_view.py#L612) · [plan_view.py:647](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/assets/plan-graph/_aiHumanInteract/plan/plan_view.py#L647) · [plan_view.py:967](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/assets/plan-graph/_aiHumanInteract/plan/plan_view.py#L967)

## Skill 中的使用方式

安装后的项目从本地 `AGENTS.md` 就能找到验证、构建和检查命令。当前 HTML 自包含，普通 agent 有 Python 就能生成，交付时可以附 `graph.html#<节点 ID>`；若宿主无法预览 HTML，同时给出节点 ID 和源 Markdown 路径。agent 查询状态、依赖和来源时，可继续读取版本匹配的 `graph.json` 与源计划。dsh 或 pi 的插件以后可以包装同一组命令和节点跳转，现阶段无需另设 viewer skill。[AGENTS.plan-management.md:87](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/assets/plan-graph/AGENTS.plan-management.md#L87) · [plan-graph.md:87](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/references/plan-graph.md#L87) · [plan_view.py:933](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/assets/plan-graph/_aiHumanInteract/plan/plan_view.py#L933)

只查看已有计划时，可先运行 `build_graph.py --check`，生成物已更新就直接交付。需要更新视图时运行 `build_graph.py`，再检查结果。建议在 Plan Graph reference 的生成视图表旁写出这条短路径，并把“all four views”改成五个输出，方便 agent 在上下文压缩后从仓库内恢复操作。[plan-graph.md:87](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/references/plan-graph.md#L87) · [plan-graph.md:378](https://github.com/mynamesnoname/paths-to-modernity/blob/ffc0fdebab9d84abce8810732f71331303dafc26/references/plan-graph.md#L378)

## 验证范围

在固定提交的文件快照上运行 `python3 -B scripts/test_plan_graph_bundle.py`，通过全部 13 个单元测试及 bundle 回归。另在临时项目复现旧 v4 升级和不同目录的 `--check`，对照官方示例的 HTML 与 JSON 检查筛选项和边，并用 Node 检查嵌入脚本语法。当前执行环境的无头 Chromium 启动受限，交互行为未做浏览器端验证。

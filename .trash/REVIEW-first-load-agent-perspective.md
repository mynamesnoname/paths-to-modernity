# 评审：首次加载 agent 视角的 skill 可读性评估

日期：2026-09-15
范围：`SKILL.md`、`README.md`、`references/`（inquiry / model / variants / plan-graph）、`assets/mounted-plan-graph/`（bundle 文档与 worked example）、`agents/openai.yaml`

评审方式：扮演一个首次加载本 skill、对项目历史一无所知的 coding agent，记录阅读过程中遇到的指代不清、结构混乱与加载路径断裂。

## 一、做得好的地方

- `SKILL.md:34-41` 的路由表是优秀的入口设计：明确"什么时候读哪份"，避免全量加载。
- frontmatter description 里的 negative triggers（"Do not use for routine one-step tasks..."）对触发判断很有帮助。
- `plan-graph.md:9-24` 主动区分 specification / bundle / version identifier 三个对象，并声明 prose 与工具行为冲突是 defect——权威层级声明对 agent 极其有用。
- 所有命令（安装、验证、回滚）都提供了 `--dry-run`，agent 可以安全试探。

## 二、名词指代不清

### 1. 术语三层同义，映射关系靠读者自己拼

- kernel 的 outcome = `objective`（必填）＋"剩余 facets" = `essence`（可选）。该映射在 `SKILL.md:47-48`、`model.md:70-73`、`model.md:156-160` 各说一遍，措辞略异，需读三处才能确认是同一回事。
- "directional field" = `qualities` + `tensions`。其定义 "preserves desired character without pretending to verify it" 是一个否定式定义，首次读者无法从正面理解，直到看到序列化字段才落地。
- "perspective" 在 `model.md:113-121` 是建议清单（user / system / operations / risk / evidence / cost），但 example 的 `WP-001.md:18` 写的是 `["operator", "runtime", "evidence"]`——"runtime" 不在清单内，粒度也对不上。字段该写什么、写到什么抽象级别，没有契约。

### 2. "mounted" 需要两次防御性声明仍未消除歧义

`SKILL.md:57-58`、`plan-graph.md:156-158`、`AGENTS.plan-management.md:44-45` 三处都专门声明"这不是操作系统挂载"。一个词需要反复声明"我不是你以为的意思"，说明命名在对抗读者先验。同理 "remount"：`remount_graph.py` 实际是"重新生成投影"，但文档中 render / generate / project / remount 四个动词混用（`plan-graph.md:170-178`），读者会怀疑 remount 有额外语义。

### 3. "profile" 指代滑动

有时指规范文档（`plan-graph.md:12`），有时指整个方案（SKILL.md 路由表 "Mounted Plan Graph v2 contract"），有时是版本字符串前缀（`paths-to-modernity-mounted-plan-graph-v2`）。另外 `schema_version` 的确切取值直到 `plan-graph.md:249` 迁移一节才间接出现；想手写或核对 graph.json 的 agent 无法从前文确认该字符串。

### 4. 艺术隐喻与规范术语边界模糊

SKILL.md 声称现代主义透镜是可选的（`SKILL.md:141-153`），但隐喻词汇已渗入核心规范：`atelier.md`（法语"画室"）直接出现在路由表和投影清单中，首次读者无法推断其含义；"distillation / composition / impression / reconstruction / normalization" 在透镜表里是隐喻，但 "composition"、"distill" 同时是主工作流的正式步骤名（`SKILL.md:84-89`）。读者无法区分必须遵守的术语与装饰性词汇。

### 5. 小词歧义

- "boundary" 在 inquiry.md 中混用三种含义（计划范围、责任边界、接口边界）。
- "decision owner" / "responsible person" / "the person" 是否同一角色没有显式对齐。
- `_plan/inbox/` 名为 inbox（暗示临时投递区），实际承担持久 provenance 存储（`plan-graph.md:58`）。

## 三、文档结构问题

### 1. 同一内容四到五处重复，权威归属不一致

四层分解（LT→MT→ST→WP）、六状态列表、四条验证命令、mount 存在性规则同时出现在 `SKILL.md`、`references/plan-graph.md`、`assets/.../AGENTS.plan-management.md`、`assets/.../_plan/README.md`。`plan-graph.md` 自称 normative，`_plan/README.md:13` 自称 non-normative——但 `AGENTS.plan-management.md` 的规范地位从未声明。

### 2. 使用者与维护者的指令混住

`README.md:22-33` 的 "Verify changes" 与 `SKILL.md:108-114` 的安装命令面向维护者/安装者，而 SKILL.md 同时是 runtime router。更尖锐的是 `README.md:26` 与 `AGENTS.md` 硬编码了 `/home/user/.codex/skills/.system/skill-creator/scripts/quick_validate.py`——具体机器的绝对路径，首次加载的 agent 无法判断其存在性、必要性与失败后果。

### 3. references 之间的链接单向且不完整

SKILL.md → references 有路由表；`plan-graph.md:83` → inquiry.md 有链接。但 `inquiry.md:141-147` 的 Handoff 提到 "the target project's planning model" 却不链接 model.md；model.md 四次提到 "Mounted Plan Graph profile" 却不链接 plan-graph.md。按路由表逐份加载的 agent 读完 inquiry.md 后不知道下一步去哪。

### 4. "Shared vocabulary" 一节层次混杂

`SKILL.md:43-62` 前四条是方法论概念（kernel / composition / directional field / perspective vs variant），后两条（mount / projection）是 plan-graph profile 的实现细节，且提前引用了读者尚未被告知存在的 `graph.canvas`、`atelier.md`。

## 四、加载路径断裂

### 1. "skill root" 从未定义

`SKILL.md:111`、`plan-graph.md:186-201`、`_plan/README.md:22` 都要求 "from the skill root" 运行 `scripts/install_plan_graph.py`，但 skill 可能装在 `~/.codex/skills/`、`~/.kimi-code/skills/` 或项目内任意位置，文档未告知 agent 如何定位自身根目录。这是首次加载者遇到的第一个实际操作障碍。

### 2. bundle 的双重身份只有反向声明、没有就地标注

`README.md:14` 与 `plan-graph.md:20-22` 声明 bundle 内的 `AGENTS.plan-management.md` 和 `_plan/README.md` 不是运行时指令——但声明只存在于 skill 侧。若 agent 先漫游到 `assets/mounted-plan-graph/`（完全可能），这两个文件自身没有"我是待安装产物"的标注，会被当作指令读入。

### 3. 安装后的目标项目与 skill 之间回程断裂

安装进目标项目的 `AGENTS.plan-management.md` fragment 自包含四层结构与验证命令，但完全没有指向 inquiry / model / variants 的入口，甚至不提 canonical kernel、readiness gate（仅 `essence` 一句带过）。而 skill 侧（`plan-graph.md:22-24`）又说安装后由目标项目的 AGENTS.md 治理。"目标项目 agent 是否还应回读 skill references" 没有任何文件回答。

### 4. worked example 的阅读姿势未说明

example README 给了 REQ-001 → LT → MT → ST → WP 的阅读顺序，但未说明 `example/_plan/structure/` 下的生成物该不该读、以什么身份读。`plan-graph.md:42-45` 的 "Consumers check schema_version, locate a node by ID, follow source" 是给目标项目消费 agent 的协议；读 example 的 agent 是在模拟消费者还是学习规范，两种读法关注点不同。

### 5. 突然出现、没有落点的概念

- `plan-graph.md:165` 的 `external:` archive reference 称 "supported"，但格式与语义只在 validator 代码里，规范正文无定义。
- `graph.canvas` 是 Obsidian 专用格式，没有说明非 Obsidian 环境下 agent 可否忽略。
- v1→v2 迁移一节（`plan-graph.md:238-251`）引用了仓库中不存在的 v1 产物与 `MP-###` ID，对首次加载的 agent 是无法验证的噪音（对维护者必要，建议标注受众）。

## 五、最核心的三个改进方向

1. **术语收敛**：为 kernel / directional field / mount / profile 建立唯一的"概念 → 序列化字段"映射表（现散落三份文件）；为 atelier、remount 等反直觉命名加就地注释或改名。
2. **受众分层**：维护者命令（quick_validate 硬编码路径、test_profile_example）从 README/SKILL 移到只在 AGENTS.md；在 bundle 的 .md 文件头部加"我是安装产物"的就地标注。
3. **补齐两条路径**：定义 "skill root" 的定位方法；在安装后的 `AGENTS.plan-management.md` fragment 里留一个回到 skill 方法论（至少 inquiry 触发条件）的指针。
